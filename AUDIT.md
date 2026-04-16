# Audit Trail

This repository is meant to be auditable by someone who did not create it.

## What to verify

1. Compare `data/bls_union_membership_rates_2024.csv` against the official BLS release page or BLS PDF.
2. Compare `data/census_acs_2024_B19013_001E_state.csv` against the official Census API query.
3. Compare `data/bea_sarpp_state_2008_2024.csv` against the BEA SARPP download (`https://apps.bea.gov/regional/zip/SARPP.zip`, member `SARPP_STATE_2008_2024.csv`). The file in this repo is byte-for-byte identical.
4. Re-run `python3 scripts/reproduce.py`.
5. Confirm that the regenerated files match the committed outputs and `SHA256SUMS`.
6. Review `results/union_income_audit_manifest_2024.json` for the machine-readable file inventory and hashes.
7. Review `SOURCES.md` to confirm the exact official URLs.
8. Review `scripts/collect_and_regress.py` to confirm the merge, RPP filtering, and regression logic.

## Methodological choices

- Unit of analysis: U.S. states
- Coverage: 50 states
- Excluded: District of Columbia
- Union variable: BLS union membership rate among employed wage and salary workers in 2024
- Income variable: Census ACS 2024 1-year `B19013_001E`
- Price-level variable: BEA Regional Price Parities table `SARPP`, LineCode 1 (All items), most recent year in the dump
- Derived variable: `median_household_income_real_usd = median_household_income_usd / (rpp_all_items / 100)`
- Model: two unweighted simple OLS regressions
- Formulas:
  - `median_household_income_usd ~ union_membership_rate_pct` (nominal)
  - `median_household_income_real_usd ~ union_membership_rate_pct` (RPP-adjusted)

## Limitations

- The BLS extract is preserved locally rather than fetched live because `bls.gov` blocked automated shell retrieval from the assembly environment.
- The Census snapshot and BEA SARPP dump are preserved locally for exact offline reproduction; updating them requires an explicit refresh step in a networked environment.
- RPP is heavily influenced by housing costs; the adjusted income measure inherits that weighting and is not a full welfare or purchasing-power statistic.
- Both regressions are descriptive and ecological. Neither is a causal estimate.
- The models do not control for education, industrial composition, demographics, or labor-force composition.

## Checksums

After reproducing, compare the generated files against `SHA256SUMS`. The manifest at `results/union_income_audit_manifest_2024.json` records the same file inventory in a machine-readable form.
