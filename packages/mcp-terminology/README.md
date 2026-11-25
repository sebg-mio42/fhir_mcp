# mcp-terminology

<!-- mcp-name: io.github.pcmedsinge/mcp-terminology -->

> Unified LOINC / SNOMED CT / RxNorm / ICD-10 MCP server — v1.0.0
> Part of the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)

Query four major clinical terminology systems through a single MCP server
backed by the free public FHIR R4 terminology server (tx.fhir.org/r4).

---

## Tools

| Tool | Description | Backend operation |
|------|-------------|-------------------|
| `lookup_code` | Look up a single code — returns display, definition, designations | `CodeSystem/$lookup` |
| `validate_code` | Check a code exists (optionally its display), or is a member of a ValueSet | `CodeSystem/$validate-code`, `ValueSet/$validate-code` |
| `search_codes` | Free-text search within any code system the server hosts | `ValueSet/$expand` (inline ValueSet, `filter`) |
| `translate_code` | Translate a code across systems where the server holds a ConceptMap | `ConceptMap/$translate` |
| `expand_valueset` | Expand any canonical FHIR ValueSet by URL | `ValueSet/$expand` |

Which code systems and ConceptMaps exist depends on the server (`TERMINOLOGY_BASE_URL`); see its
`/metadata?mode=terminology`. Set `TERMINOLOGY_DISPLAY_LANGUAGE` (e.g. `de`) to get displays in that
language where the server has them.

### System aliases

Any code system can be passed by canonical URI; these aliases are shortcuts.

| Alias | URI |
|-------|-----|
| `icd-10-gm` | `http://fhir.de/CodeSystem/bfarm/icd-10-gm` |
| `ops` | `http://fhir.de/CodeSystem/bfarm/ops` |
| `atc` / `atc-gm` | `http://www.whocc.no/atc` / `http://fhir.de/CodeSystem/bfarm/atc` |
| `loinc` | `http://loinc.org` |
| `snomed` / `snomed-ct` | `http://snomed.info/sct` |
| `rxnorm` | `http://www.nlm.nih.gov/research/umls/rxnorm` |
| `icd-10-cm` | `http://hl7.org/fhir/sid/icd-10-cm` |
| `icd-10` | `http://hl7.org/fhir/sid/icd-10` |
| `cvx` | `http://hl7.org/fhir/sid/cvx` |
| `cpt` | `http://www.ama-assn.org/go/cpt` |
| `ndc` | `http://hl7.org/fhir/sid/ndc` |
| `ucum` | `http://unitsofmeasure.org` |

---

## Quick start

```bash
# Install into the monorepo workspace
uv sync --all-packages

# Run (stdio mode — for Claude Desktop)
uv run mcp-terminology

# Run with Streamable HTTP transport (http://localhost:8001/mcp)
MCP_TRANSPORT=http uv run mcp-terminology
```

---

## Claude Desktop configuration

```json
{
  "mcpServers": {
    "terminology": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/fhir-mcp-suite",
        "run",
        "mcp-terminology"
      ],
      "env": {
        "TERMINOLOGY_BASE_URL": "https://tx.fhir.org/r4",
        "LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

---

## Example tool calls

### Look up a LOINC code
```json
{ "system": "loinc", "code": "8302-2" }
```
```json
{
  "system_url": "http://loinc.org",
  "system_name": "LOINC",
  "code": "8302-2",
  "display": "Body height",
  "definition": "...",
  "designations": [...],
  "version": "2.78"
}
```

### Translate administrative-gender → HL7 v2
```json
{
  "code": "male",
  "source_system": "http://hl7.org/fhir/administrative-gender",
  "target_system": "http://terminology.hl7.org/CodeSystem/v2-0001"
}
```

### Check that a code exists
```json
{ "system": "loinc", "code": "8302-3" }
```
```json
{ "result": false, "message": "Unknown code '8302-3' in the CodeSystem 'http://loinc.org' version '2.83'", ... }
```

### Expand a ValueSet
```json
{ "url": "http://hl7.org/fhir/ValueSet/administrative-gender" }
```

---

## Architecture

```
Claude Desktop / LangGraph agent
         │  MCP stdio
    mcp-terminology (this package)
         │  HTTPS
    tx.fhir.org/r4  (free public FHIR R4 terminology server)
         └── CodeSystem/$lookup
         └── ValueSet/$expand
         └── ConceptMap/$translate
```

**Observability**: every tool call is traced in LangFuse (input, output, latency, response bytes).
Set `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` to enable.

---

## Eval results

```
mcp-terminology eval — 21 golden cases
  Error/security cases: 6/6   100%  (network-independent)
  Integration cases:    run with `--tags lookup search translate expand`
  CI threshold:         85% pass rate
```

Run locally:
```bash
# Error cases only (no network needed):
uv run python evals/mcp-terminology/run_eval.py --tags error

# Full suite (requires tx.fhir.org):
uv run python evals/mcp-terminology/run_eval.py

# CI gate:
uv run python evals/mcp-terminology/run_eval.py --ci --threshold 0.85
```

---

## Security

- **Input sanitization** on all parameters (length and control-char checks on codes, http/https-only URLs, control-char stripping on filters)
- **Hard cap** of 100 results per query
- **No PHI** — uses only synthetic/public code lookups
- See `validation.py` for the full allowlist

---

## License

Apache-2.0 — see [LICENSE](../../LICENSE).
