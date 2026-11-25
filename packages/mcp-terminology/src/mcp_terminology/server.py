"""mcp-terminology server entrypoint.

Registers five MCP tools:
  - lookup_code      — look up a single code (LOINC, SNOMED, ICD-10-GM, …)
  - validate_code    — check a code exists, or is in a ValueSet, via $validate-code
  - search_codes     — free-text search within a terminology system
  - translate_code   — translate a code across systems via ConceptMap/$translate
  - expand_valueset  — expand any FHIR ValueSet, optionally filtered

Transport is selected via the MCP_TRANSPORT env var: stdio (default) or http (Streamable HTTP at /mcp).
"""

from __future__ import annotations

import json
import time
import uuid

import anyio
import httpx
import structlog
from fhir_mcp_shared.langfuse import trace as lf_trace
from fhir_mcp_shared.logging import configure_logging
from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_terminology.constants import SYSTEM_ALIASES
from mcp_terminology.settings import settings
from mcp_terminology.tools.expand_valueset import expand_valueset
from mcp_terminology.tools.lookup_code import lookup_code
from mcp_terminology.tools.search_codes import search_codes
from mcp_terminology.tools.translate_code import translate_code
from mcp_terminology.tools.validate_code import validate_code

log = structlog.get_logger(__name__)

_SESSION_ID: str = str(uuid.uuid4())

_SYSTEM_PARAM = {
    "type": "string",
    "description": (
        f"System alias ({', '.join(SYSTEM_ALIASES)}) "
        "or canonical URI of any code system the server hosts."
    ),
}


def _error_text(exc: Exception) -> str:
    """The server's OperationOutcome text ('CodeSystem not found: …') over httpx's status line."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            issues = exc.response.json().get("issue") or []
        except ValueError:
            issues = []
        texts = [(i.get("details") or {}).get("text") or i.get("diagnostics") for i in issues]
        if any(texts):
            return f"{exc.response.status_code}: " + " | ".join(t for t in texts if t)
    return str(exc)


def _build_server() -> Server:
    server = Server("mcp-terminology", version="1.0.0")

    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="lookup_code",
                description=(
                    "Look up a single code in a medical terminology system using FHIR $lookup. "
                    "Returns display name, definition, and alternate designations. "
                    "Works for any code system the terminology server hosts."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "system": _SYSTEM_PARAM,
                        "code": {
                            "type": "string",
                            "description": "The code to look up (e.g. '8302-2', '73211009').",
                        },
                        "version": {
                            "type": "string",
                            "description": "Optional terminology version string.",
                            "default": "",
                        },
                    },
                    "required": ["system", "code"],
                },
            ),
            Tool(
                name="validate_code",
                description=(
                    "Check that a code exists in a code system (FHIR CodeSystem/$validate-code), "
                    "or, if valueset_url is given, that it is allowed by that ValueSet "
                    "(ValueSet/$validate-code). Use it to verify a code before relying on it. "
                    "Returns result=true/false and a message explaining any problem."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "system": _SYSTEM_PARAM,
                        "code": {"type": "string", "description": "The code to check."},
                        "display": {
                            "type": "string",
                            "description": "Optional display text to check against the code.",
                            "default": "",
                        },
                        "valueset_url": {
                            "type": "string",
                            "description": "Optional ValueSet URL to check membership in.",
                            "default": "",
                        },
                    },
                    "required": ["system", "code"],
                },
            ),
            Tool(
                name="search_codes",
                description=(
                    "Search for codes by free text within any code system the terminology "
                    "server hosts. Uses FHIR ValueSet/$expand. "
                    "For exact code lookup use lookup_code instead."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Free-text search (e.g. 'body height', 'diabetes mellitus').",
                        },
                        "system": _SYSTEM_PARAM,
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum codes to return (1-100). Default: 20.",
                            "default": 20,
                        },
                    },
                    "required": ["query", "system"],
                },
            ),
            Tool(
                name="translate_code",
                description=(
                    "Translate a code from one terminology system to another "
                    "using FHIR ConceptMap/$translate. Only works where the server holds a "
                    "ConceptMap between the two systems; otherwise returns result=false "
                    "and a message."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to translate.",
                        },
                        "source_system": {
                            "type": "string",
                            "description": "Source system alias or URI.",
                        },
                        "target_system": {
                            "type": "string",
                            "description": "Target system alias or URI.",
                        },
                    },
                    "required": ["code", "source_system", "target_system"],
                },
            ),
            Tool(
                name="expand_valueset",
                description=(
                    "Expand a FHIR ValueSet to retrieve all (or filtered) codes it contains. "
                    f"Accepts any canonical ValueSet URL hosted on {settings.terminology_base_url}. "
                    "Useful for exploring allowed values for coded FHIR elements."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": (
                                "Canonical ValueSet URL "
                                "(e.g. 'http://hl7.org/fhir/ValueSet/administrative-gender')."
                            ),
                        },
                        "filter": {
                            "type": "string",
                            "description": "Optional free-text filter to narrow results.",
                            "default": "",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum codes to return (1-100). Default: 20.",
                            "default": 20,
                        },
                    },
                    "required": ["url"],
                },
            ),
        ]

    @server.call_tool()  # type: ignore
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        call_id = str(uuid.uuid4())
        log.info("tool_call", tool=name, call_id=call_id, session_id=_SESSION_ID)
        t0 = time.perf_counter()

        with lf_trace(
            name=name,
            session_id=_SESSION_ID,
            tags=["mcp-terminology", name],
            call_id=call_id,
            server_version="1.0.0",
        ) as tr:
            try:
                if name == "lookup_code":
                    result = await lookup_code(
                        system=arguments["system"],
                        code=arguments["code"],
                        version=arguments.get("version", ""),
                    )
                elif name == "validate_code":
                    result = await validate_code(
                        system=arguments["system"],
                        code=arguments["code"],
                        display=arguments.get("display", ""),
                        valueset_url=arguments.get("valueset_url", ""),
                    )
                elif name == "search_codes":
                    result = await search_codes(
                        query=arguments["query"],
                        system=arguments["system"],
                        max_results=int(arguments.get("max_results", 0)),
                    )
                elif name == "translate_code":
                    result = await translate_code(
                        code=arguments["code"],
                        source_system=arguments["source_system"],
                        target_system=arguments["target_system"],
                    )
                elif name == "expand_valueset":
                    result = await expand_valueset(
                        url=arguments["url"],
                        filter=arguments.get("filter", ""),
                        max_results=int(arguments.get("max_results", 0)),
                    )
                else:
                    raise ValueError(f"Unknown tool: {name!r}")

                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                payload = json.dumps(result, indent=2, ensure_ascii=False)
                if tr:
                    tr.update(output={"response_bytes": len(payload), "latency_ms": latency_ms})
                log.info(
                    "tool_ok",
                    tool=name,
                    call_id=call_id,
                    latency_ms=latency_ms,
                    response_bytes=len(payload),
                )
                return [TextContent(type="text", text=payload)]

            except Exception as exc:
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                error = _error_text(exc)
                if tr:
                    tr.update(output={"error": error, "latency_ms": latency_ms})
                log.error(
                    "tool_error", tool=name, call_id=call_id, latency_ms=latency_ms, error=error
                )
                return [TextContent(type="text", text=f"Error: {error}")]

    return server


async def _run_stdio(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-terminology",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


async def _run_http(server: Server) -> None:
    """Run the server over Streamable HTTP at /mcp."""
    import contextlib

    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Route

    # ponytail: stateless — tools only, no server-initiated messages, and restarts drop no sessions
    manager = StreamableHTTPSessionManager(app=server, stateless=True)

    class _Endpoint:  # a class, so Starlette hands it raw ASGI instead of wrapping it as a request handler
        async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
            await manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(_app):  # type: ignore[no-untyped-def]
        async with manager.run():
            yield

    config = uvicorn.Config(
        app=Starlette(routes=[Route("/mcp", endpoint=_Endpoint())], lifespan=lifespan),
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )
    await uvicorn.Server(config).serve()


def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    log.info(
        "mcp_terminology_starting",
        transport=settings.mcp_transport,
        version="1.0.0",
        session_id=_SESSION_ID,
    )
    server = _build_server()
    if settings.mcp_transport == "http":
        anyio.run(_run_http, server)
    else:
        anyio.run(_run_stdio, server)


if __name__ == "__main__":
    main()
