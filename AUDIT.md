# Audit Trail

This repository is meant to be auditable by someone who did not create it.

## What to verify

1. Compare `data/bls_union_membership_rates_2024.csv` against the official BLS release page or BLS PDF.
2. Re-run `python3 scripts/reproduce.py`.
3. Confirm that the regenerated files match the committed outputs.
4. Review `SOURCES.md` to confirm the exact official URLs.
5. Review `scripts/collect_and_regress.py` to confirm the merge and regression logic.

## Methodological choices

- Unit of analysis: U.S. states
- Coverage: 50 states
- Excluded: District of Columbia
- Union variable: BLS union membership rate among employed wage and salary workers in 2024
- Income variable: Census ACS 2024 1-year `B19013_001E`
- Model: unweighted simple OLS
- Formula: `median_household_income_usd ~ union_membership_rate_pct`

## Limitations

- The BLS extract is preserved locally rather than fetched live because `bls.gov` blocked automated shell retrieval from the assembly environment.
- The regression is descriptive and ecological. It is not a causal estimate.
- The model does not control for cost of living, education, industrial composition, or housing.

## Checksums

After reproducing, compare the generated files against `SHA256SUMS`.
