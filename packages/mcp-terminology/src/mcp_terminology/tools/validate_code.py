"""Tool: validate_code — check that a code exists in a code system, or belongs to a ValueSet.

Calls the FHIR $validate-code operation:
    GET {base}/CodeSystem/$validate-code?url={system}&code={code}
    GET {base}/ValueSet/$validate-code?url={valueset}&system={system}&code={code}
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fhir_mcp_shared.langfuse import span

from mcp_terminology import validation
from mcp_terminology.constants import SYSTEM_DISPLAY
from mcp_terminology.settings import settings

log = structlog.get_logger(__name__)


def _values(params: dict[str, Any]) -> dict[str, Any]:
    """Top-level value[x] of a Parameters resource by name (keeps result=false)."""
    return {
        p["name"]: v
        for p in params.get("parameter") or []
        for k, v in p.items()
        if k.startswith("value")
    }


async def validate_code(
    system: str,
    code: str,
    display: str = "",
    valueset_url: str = "",
) -> dict[str, Any]:
    """Validate a code against its code system, or against a ValueSet if one is given.

    Args:
        system:       System alias (e.g. ``"loinc"``, ``"icd-10-gm"``) or canonical URI.
        code:         The code to check.
        display:      Optional display to check against the code's designations.
        valueset_url: Optional canonical ValueSet URL; checks membership instead of existence.

    Returns:
        Dict with ``result`` (bool), ``message`` (why it failed, or a warning),
        the canonical ``display``, ``version``, ``system_url``, ``code`` and ``valueset_url``.
    """
    system_url = validation.resolve_system(system)
    safe_code = validation.validate_code(code)
    base = settings.terminology_base_url.rstrip("/")

    if valueset_url:
        valueset_url = validation.validate_url(valueset_url, "valueset_url")
        endpoint = f"{base}/ValueSet/$validate-code"
        params = {"url": valueset_url, "system": system_url, "code": safe_code}
    else:
        endpoint = f"{base}/CodeSystem/$validate-code"
        params = {"url": system_url, "code": safe_code}
    if display:
        params["display"] = validation.sanitise_filter(display, max_len=500)
    if settings.terminology_display_language:
        params["displayLanguage"] = settings.terminology_display_language

    with span("validate_code", system=system_url, code=safe_code, valueset_url=valueset_url):
        log.info("validate_code", url=endpoint, system=system_url, code=safe_code)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.get(
                endpoint, params=params, headers={"Accept": "application/fhir+json"}
            )
            response.raise_for_status()
            values = _values(response.json())

    return {
        "result": values.get("result", False),
        "message": values.get("message", ""),
        "system_url": system_url,
        "system_name": SYSTEM_DISPLAY.get(system_url, system_url),
        "code": safe_code,
        "display": values.get("display", ""),
        "version": values.get("version", ""),
        "valueset_url": valueset_url,
    }
