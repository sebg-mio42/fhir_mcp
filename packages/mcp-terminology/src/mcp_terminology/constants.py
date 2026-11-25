"""Shared constants for mcp-terminology.

System URI aliases map user-friendly names to canonical FHIR system URIs.
"""

from __future__ import annotations

# Canonical FHIR system URIs
SYSTEM_ALIASES: dict[str, str] = {
    "loinc": "http://loinc.org",
    "snomed": "http://snomed.info/sct",
    "snomed-ct": "http://snomed.info/sct",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "icd-10": "http://hl7.org/fhir/sid/icd-10",
    "icd-10-cm": "http://hl7.org/fhir/sid/icd-10-cm",
    "icd-10-pcs": "http://www.cms.gov/Medicare/Coding/ICD10",
    "ndc": "http://hl7.org/fhir/sid/ndc",
    "cpt": "http://www.ama-assn.org/go/cpt",
    "cvx": "http://hl7.org/fhir/sid/cvx",
    "nucc": "http://nucc.org/provider-taxonomy",
    "ucum": "http://unitsofmeasure.org",
    "icd-10-gm": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
    "ops": "http://fhir.de/CodeSystem/bfarm/ops",
    "atc": "http://www.whocc.no/atc",
    "atc-gm": "http://fhir.de/CodeSystem/bfarm/atc",
}

# Human-readable display names for known system URIs
SYSTEM_DISPLAY: dict[str, str] = {
    "http://loinc.org": "LOINC",
    "http://snomed.info/sct": "SNOMED CT",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "RxNorm",
    "http://hl7.org/fhir/sid/icd-10": "ICD-10",
    "http://hl7.org/fhir/sid/icd-10-cm": "ICD-10-CM",
    "http://www.cms.gov/Medicare/Coding/ICD10": "ICD-10-PCS",
    "http://hl7.org/fhir/sid/ndc": "NDC",
    "http://www.ama-assn.org/go/cpt": "CPT",
    "http://hl7.org/fhir/sid/cvx": "CVX",
    "http://unitsofmeasure.org": "UCUM",
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm": "ICD-10-GM",
    "http://fhir.de/CodeSystem/bfarm/ops": "OPS",
    "http://www.whocc.no/atc": "ATC (WHO)",
    "http://fhir.de/CodeSystem/bfarm/atc": "ATC (BfArM, German)",
}
