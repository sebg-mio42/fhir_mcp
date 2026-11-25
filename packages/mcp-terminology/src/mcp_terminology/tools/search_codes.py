"""Tool: search_codes — free-text search within a terminology system.

Uses the FHIR $expand operation on an inline ValueSet that includes the whole system:
    POST {base}/ValueSet/$expand  (Parameters: valueSet, filter, count)
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fhir_mcp_shared.langfuse import span

from mcp_terminology.constants import SYSTEM_DISPLAY
from mcp_terminology.settings import settings
from mcp_terminology.validation import (
    resolve_system,
    sanitise_filter,
    validate_max_results,
)

log = structlog.get_logger(__name__)


def _parse_expansion(valueset: dict[str, Any]) -> list[dict[str, str]]:
    """Extract code entries from a ValueSet expansion."""
    contains = (valueset.get("expansion") or {}).get("contains") or []
    results: list[dict[str, str]] = []
    for entry in contains:
        results.append(
            {
                "system": entry.get("system", ""),
                "system_name": SYSTEM_DISPLAY.get(entry.get("system", ""), ""),
                "code": entry.get("code", ""),
                "display": entry.get("display", ""),
                "abstract": str(entry.get("abstract", False)).lower(),
                "inactive": str(entry.get("inactive", False)).lower(),
            }
        )
    return results


async def search_codes(
    query: str,
    system: str,
    max_results: int = 0,
) -> dict[str, Any]:
    """Search for codes by free text within a terminology system.

    Calls ``ValueSet/$expand`` with a ``filter`` on an inline ValueSet that
    includes every code of the given system, so any code system the server
    hosts can be searched. A system the server lacks fails with its error.

    Args:
        query:       Free-text search string (e.g. ``"body height"``, ``"diabetes"``).
        system:      System alias or URI (e.g. ``"loinc"``, ``"snomed"``, ``"icd-10-gm"``).
        max_results: Maximum codes to return (1-100). 0 = use server default.

    Returns:
        Dict with ``system_url``, ``query``, ``total`` (expansion total if
        reported), and ``results`` (list of ``{system, code, display}``).
    """
    system_url = resolve_system(system)
    safe_query = sanitise_filter(query)
    if not safe_query:
        raise ValueError("query must not be empty")

    n = validate_max_results(max_results or settings.terminology_max_results)
    parameters: list[dict[str, Any]] = [
        {
            "name": "valueSet",
            "resource": {
                "resourceType": "ValueSet",
                "status": "active",
                "compose": {"include": [{"system": system_url}]},
            },
        },
        {"name": "filter", "valueString": safe_query},
        {"name": "count", "valueInteger": n},
    ]
    if settings.terminology_display_language:
        parameters.append(
            {"name": "displayLanguage", "valueCode": settings.terminology_display_language}
        )

    url = f"{settings.terminology_base_url.rstrip('/')}/ValueSet/$expand"

    with span("search_codes", system=system_url, query=safe_query, max_results=n):
        log.info("search_codes", url=url, system=system_url, query=safe_query)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.post(
                url,
                json={"resourceType": "Parameters", "parameter": parameters},
                headers={
                    "Accept": "application/fhir+json",
                    "Content-Type": "application/fhir+json",
                },
            )
            response.raise_for_status()
            valueset: dict[str, Any] = response.json()

    results = _parse_expansion(valueset)
    total = (valueset.get("expansion") or {}).get("total")

    return {
        "system_url": system_url,
        "system_name": SYSTEM_DISPLAY.get(system_url, system_url),
        "query": safe_query,
        "total": total,
        "results": results,
    }
