#!/usr/bin/env python3
"""Generate machine-readable audit artifacts for the repository."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_JSON = ROOT / "results" / "union_income_audit_manifest_2024.json"
SHA256SUMS = ROOT / "SHA256SUMS"

BLS_SOURCE_URL = (
    "https://www.bls.gov/opub/ted/2025/"
    "union-membership-rates-highest-in-hawaii-and-new-york-lowest-"
    "in-north-carolina-in-2024.htm"
)
CENSUS_SOURCE_URL = (
    "https://api.census.gov/data/2024/acs/acs1"
    "?get=NAME,B19013_001E&for=state:*"
)
BEA_RELEASE_URL = (
    "https://www.bea.gov/data/prices-inflation/"
    "regional-price-parities-state-and-metro-area"
)
BEA_DOWNLOAD_URL = "https://apps.bea.gov/regional/zip/SARPP.zip"

INPUT_FILES = [
    "README.md",
    "SOURCES.md",
    "AUDIT.md",
    "data/bls_union_membership_rates_2024.csv",
    "data/census_acs_2024_B19013_001E_state.csv",
    "data/bea_sarpp_state_2008_2024.csv",
    "data/bea_sarpp_definition.xml",
    "data/bea_sarpp_footnotes.html",
]

SCRIPT_FILES = [
    "scripts/collect_and_regress.py",
    "scripts/build_visual_report.py",
    "scripts/build_audit_artifacts.py",
    "scripts/reproduce.py",
]

OUTPUT_FILES = [
    "data/us_states_union_income_2024.csv",
    "results/union_income_regression_2024.json",
    "results/union_income_regression_2024.md",
    "results/union_income_visual_report.html",
]

CHECKSUM_FILES = INPUT_FILES + OUTPUT_FILES + [
    "results/union_income_audit_manifest_2024.json",
] + SCRIPT_FILES


def sha256_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(rel_path: str) -> dict[str, str]:
    return {
        "path": rel_path,
        "sha256": sha256_for(ROOT / rel_path),
    }


def build_manifest() -> dict[str, object]:
    return {
        "analysis": "U.S. state unionization and median household income, 2024",
        "checksums_algorithm": "sha256",
        "reproduction_commands": [
            "python3 scripts/reproduce.py",
            "python3 scripts/collect_and_regress.py --refresh-census",
            "python3 scripts/collect_and_regress.py --refresh-rpp",
        ],
        "official_sources": {
            "bls_union_membership_release": BLS_SOURCE_URL,
            "census_acs_2024_api_query": CENSUS_SOURCE_URL,
            "bea_regional_price_parities_release": BEA_RELEASE_URL,
            "bea_sarpp_state_download": BEA_DOWNLOAD_URL,
        },
        "audit_artifacts": {
            "audit_trail": "AUDIT.md",
            "sources": "SOURCES.md",
            "checksums": "SHA256SUMS",
            "manifest": "results/union_income_audit_manifest_2024.json",
            "manifest_checksum_location": "SHA256SUMS",
        },
        "checked_in_inputs": [describe(path) for path in INPUT_FILES],
        "scripts": [describe(path) for path in SCRIPT_FILES],
        "generated_outputs": [describe(path) for path in OUTPUT_FILES],
    }


def write_manifest() -> None:
    MANIFEST_JSON.write_text(
        json.dumps(build_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )


def write_sha256sums() -> None:
    lines = []
    for rel_path in CHECKSUM_FILES:
        lines.append(f"{sha256_for(ROOT / rel_path)}  {rel_path}")
    SHA256SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_manifest()
    write_sha256sums()
    print(f"Wrote audit manifest to {MANIFEST_JSON}")
    print(f"Wrote checksums to {SHA256SUMS}")


if __name__ == "__main__":
    main()
