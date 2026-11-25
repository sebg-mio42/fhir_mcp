"""Input validation helpers for mcp-terminology tools.

All external inputs are sanitised here before being forwarded to the
terminology server. The goal is to prevent SSRF, injection, and
malformed requests from reaching the upstream API.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from mcp_terminology.constants import SYSTEM_ALIASES

# ValueSet / system URL: must be absolute HTTP(S)
_HTTP_RE = re.compile(r"^https?://")

# Free-text query / filter: strip to 200 chars, no control characters
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def resolve_system(system: str) -> str:
    """Resolve a system alias or URL to a canonical FHIR system URI.

    Raises:
        ValueError: If the value is neither a known alias nor an HTTP(S) URL.
    """
    s = system.strip()
    if not s:
        raise ValueError("system must not be empty")
    resolved = SYSTEM_ALIASES.get(s.lower(), s)
    if not _HTTP_RE.match(resolved):
        known = ", ".join(sorted(SYSTEM_ALIASES))
        raise ValueError(
            f"system {s!r} is not a known alias or absolute HTTP(S) URI. Known aliases: {known}"
        )
    return resolved


def validate_code(code: str) -> str:
    """Validate a FHIR code value.

    Raises:
        ValueError: If the code contains control characters or is too long.
    """
    c = code.strip()
    if not c:
        raise ValueError("code must not be empty")
    # ponytail: codes only travel URL-encoded in query params, so no character allowlist;
    # UCUM needs [ ] * % ' { } ( ) (e.g. mm[Hg], 10*3/uL, [arb'U])
    if len(c) > 128 or _CONTROL_RE.search(c):
        raise ValueError(
            f"Invalid code {c!r}. Codes must be at most 128 characters without control characters."
        )
    return c


def validate_url(url: str, param_name: str = "url") -> str:
    """Validate that a URL is absolute HTTP(S).

    Raises:
        ValueError: If the URL is not a valid absolute HTTP(S) URL.
    """
    u = url.strip()
    if not u:
        raise ValueError(f"{param_name} must not be empty")
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{param_name} must be an absolute HTTP(S) URL, got {u!r}")
    return u


def sanitise_filter(text: str, max_len: int = 200) -> str:
    """Strip control characters and truncate a free-text filter/query."""
    cleaned = _CONTROL_RE.sub("", text.strip())
    return cleaned[:max_len]


def validate_max_results(n: int, hard_cap: int = 100) -> int:
    """Clamp max_results to a safe range [1, hard_cap]."""
    return max(1, min(n, hard_cap))
