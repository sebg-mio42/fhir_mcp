# mcp-terminology — Overview

`mcp-terminology` provides a unified MCP interface to clinical terminology
systems: LOINC, SNOMED CT, RxNorm, and ICD-10-CM.

**Status:** ✅ v1.0 — `uvx mcp-terminology`

## Tools

| Tool | Description | Backend |
|------|-------------|--------|
| `lookup_code` | Look up a single code in a terminology system using FHIR `$lookup`. Takes an alias (e.g. `loinc`, `snomed`, `icd-10-gm`) or canonical URI | tx.fhir.org |
| `validate_code` | Check a code exists, or is a member of a ValueSet, using FHIR `$validate-code` | tx.fhir.org |
| `search_codes` | Search for codes by free text within any code system the server hosts | tx.fhir.org |
| `translate_code` | Translate a code from one terminology system to another using FHIR `$translate`, where the server holds a ConceptMap | tx.fhir.org |
| `expand_valueset` | Expand a FHIR ValueSet to retrieve all (or filtered) codes it contains. Accepts any canonical ValueSet URL hosted on tx.fhir.org | tx.fhir.org |

## Architecture

```
Claude / GPT-4o  ──MCP──►  mcp-terminology server
                               ├── lookup_code / search_codes ──► tx.fhir.org $lookup
                               ├── translate_code ──────────────► tx.fhir.org $translate
                               └── expand_valueset ─────────────► tx.fhir.org $expand
                                                                        │
                                                                   LangFuse traces
```

## Supported terminology systems

| Alias | Canonical URI | System |
|-------|--------------|--------|
| `loinc` | `http://loinc.org` | LOINC |
| `snomed` | `http://snomed.info/sct` | SNOMED CT |
| `rxnorm` | `http://www.nlm.nih.gov/research/umls/rxnorm` | RxNorm |
| `icd-10-cm` | `http://hl7.org/fhir/sid/icd-10-cm` | ICD-10-CM |
| `icd-10-gm` | `http://fhir.de/CodeSystem/bfarm/icd-10-gm` | ICD-10-GM |
| `ops` | `http://fhir.de/CodeSystem/bfarm/ops` | OPS |
| `atc` / `atc-gm` | `http://www.whocc.no/atc` / `http://fhir.de/CodeSystem/bfarm/atc` | ATC (WHO / BfArM) |

Availability depends on the configured server (`TERMINOLOGY_BASE_URL`); the full list of aliases is in `constants.py`.
