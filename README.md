# U.S. State Unionization and Income Analysis

This repository is the canonical source for a small, auditable 2024 dataset and report on:

- state union membership rates
- state median household income, reported two ways — nominal and
  RPP-adjusted (BEA Regional Price Parities, all items)
- two simple cross-state OLS regressions relating union density to each
  income measure

The repository is designed for reproducibility and external review:

- no third-party Python dependencies are required
- every generated file can be rebuilt offline from checked-in raw inputs
- the exact official source URLs are documented in [SOURCES.md](./SOURCES.md)
- the audit trail and checksums are documented in [AUDIT.md](./AUDIT.md)

## Reproduce

Use any Python 3.10+ interpreter:

```bash
python3 scripts/reproduce.py
```

This default path is offline and uses the checked-in Census snapshot and BEA
SARPP dump. When the worktree is clean, `scripts/reproduce.py` also pins the
report's audit links to the current Git commit automatically. Otherwise those
links resolve against `main`.

To refresh either upstream source before rebuilding:

```bash
python3 scripts/collect_and_regress.py --refresh-census
python3 scripts/collect_and_regress.py --refresh-rpp
python3 scripts/build_visual_report.py
python3 scripts/build_audit_artifacts.py
```

Or run the steps separately:

```bash
python3 scripts/collect_and_regress.py
python3 scripts/build_visual_report.py
python3 scripts/build_audit_artifacts.py
```

## Repository contents

- `data/bls_union_membership_rates_2024.csv`
  Official BLS state union-membership table preserved locally as a checked-in extract.
- `data/census_acs_2024_B19013_001E_state.csv`
  Checked-in Census ACS snapshot used for exact offline reproduction.
- `data/bea_sarpp_state_2008_2024.csv`
  Unmodified BEA Regional Price Parities state dump (table SARPP, line codes
  1-5, 2008-2024). The pipeline parses LineCode 1 (All items) for the most
  recent year directly from this file.
- `data/bea_sarpp_definition.xml`, `data/bea_sarpp_footnotes.html`
  BEA metadata shipped alongside the dump.
- `data/us_states_union_income_2024.csv`
  Processed 50-state dataset used for the regression and visuals, including
  both nominal and RPP-adjusted income columns.
- `results/union_income_regression_2024.json`
  Machine-readable regression summary with both `nominal` and `rpp_adjusted` blocks.
- `results/union_income_regression_2024.md`
  Human-readable regression summary for both models.
- `results/union_income_visual_report.html`
  Standalone HTML report with side-by-side scatter plots, a regression
  comparison table, and a rank-shift panel.
- `results/union_income_audit_manifest_2024.json`
  Machine-readable manifest of checked-in inputs, scripts, outputs, and hashes.
- `SHA256SUMS`
  Generated checksums for the key repository inputs, scripts, and outputs.
- `scripts/collect_and_regress.py`
  Data merge and regression script.
- `scripts/build_visual_report.py`
  HTML report generator.
- `scripts/build_audit_artifacts.py`
  Audit manifest and checksum generator.
- `scripts/reproduce.py`
  One-command entrypoint for the full pipeline.

## Method summary

The pipeline does exactly this:

1. Load the checked-in BLS state union-membership extract for 2024.
2. Load the checked-in `B19013_001E` Census ACS 2024 1-year snapshot.
3. Load the checked-in BEA SARPP dump and filter to LineCode 1 (All items)
   for the most recent year.
4. Drop the District of Columbia so the analysis is a 50-state comparison.
5. Join the BLS, Census, and BEA rows on state name.
6. Compute `median_household_income_real_usd = median_household_income_usd / (rpp_all_items / 100)`.
7. Run two unweighted OLS regressions across the 50 states:
   - `median_household_income_usd ~ union_membership_rate_pct`
   - `median_household_income_real_usd ~ union_membership_rate_pct`
8. Build the standalone HTML report from the processed CSV and regression JSON.
9. Generate the audit manifest and refresh `SHA256SUMS`.

## Important provenance note

The BLS file is checked in because automated shell retrieval from `bls.gov` was blocked from the environment used to assemble this repository. The values were preserved from the official BLS release page and should be audited against that page directly. That limitation is documented rather than hidden.

The Census and BEA values are also checked in, so the default audit and reproduction flow does not depend on live network access. The BEA dump is stored byte-for-byte as released; all RPP filtering happens in code at run time. Refreshing either upstream source is an explicit step rather than a hidden runtime dependency.
