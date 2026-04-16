# U.S. State Unionization and Income Analysis

This repository is the canonical source for a small, auditable 2024 dataset and report on:

- state union membership rates
- state median household income
- a simple cross-state OLS regression relating the two

The repository is designed for reproducibility and external review:

- no third-party Python dependencies are required
- every generated file can be rebuilt from the checked-in source extract plus the official Census API
- the exact official source URLs are documented in [SOURCES.md](./SOURCES.md)
- the audit trail and checksums are documented in [AUDIT.md](./AUDIT.md)

## Reproduce

Use any Python 3.10+ interpreter:

```bash
python3 scripts/reproduce.py
```

Or run the steps separately:

```bash
python3 scripts/collect_and_regress.py
python3 scripts/build_visual_report.py
```

## Repository contents

- `data/bls_union_membership_rates_2024.csv`
  Official BLS state union-membership table preserved locally as a checked-in extract.
- `data/us_states_union_income_2024.csv`
  Processed 50-state dataset used for the regression and visuals.
- `results/union_income_regression_2024.json`
  Machine-readable regression summary.
- `results/union_income_regression_2024.md`
  Human-readable regression summary.
- `results/union_income_visual_report.html`
  Standalone HTML report.
- `SHA256SUMS`
  Checksums for the key repository inputs, scripts, and generated outputs.
- `scripts/collect_and_regress.py`
  Data merge and regression script.
- `scripts/build_visual_report.py`
  HTML report generator.
- `scripts/reproduce.py`
  One-command entrypoint for the full pipeline.

## Method summary

The pipeline does exactly this:

1. Load the checked-in BLS state union-membership extract for 2024.
2. Fetch `B19013_001E` from the official Census ACS 2024 1-year API.
3. Drop the District of Columbia so the analysis is a 50-state comparison.
4. Join the BLS and Census rows on state name.
5. Run an unweighted OLS regression:
   `median_household_income_usd ~ union_membership_rate_pct`
6. Build the standalone HTML report from the processed CSV and regression JSON.

## Important provenance note

The BLS file is checked in because automated shell retrieval from `bls.gov` was blocked from the environment used to assemble this repository. The values were preserved from the official BLS release page and should be audited against that page directly. That limitation is documented rather than hidden.
