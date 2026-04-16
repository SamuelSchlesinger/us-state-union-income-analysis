# Unionization and Median Income Regression (2024)

Two regressions are reported side by side: nominal median household income, and median household income deflated by the BEA Regional Price Parity (all items, 2024).

### Nominal income

Model: `median_household_income_usd ~ union_membership_rate_pct`

- Observations: 50
- Slope: $1256.30 per 1 percentage point of union membership
- Intercept: $69018.36
- Correlation: 0.540
- R-squared: 0.292
- Slope p-value: 0.0001
- Slope 95% CI: $688.09 to $1824.50

### RPP-adjusted (real) income

Model: `median_household_income_real_usd ~ union_membership_rate_pct`

- Observations: 50
- Slope: $536.73 per 1 percentage point of union membership
- Intercept: $77990.43
- Correlation: 0.352
- R-squared: 0.124
- Slope p-value: 0.0121
- Slope 95% CI: $122.77 to $950.69

Top 5 states by union membership rate:
- Hawaii: 26.5% union, $100,745 nominal, $91,627 RPP-adjusted (RPP 110.0)
- New York: 20.6% union, $85,820 nominal, $79,521 RPP-adjusted (RPP 107.9)
- Alaska: 17.7% union, $95,665 nominal, $93,460 RPP-adjusted (RPP 102.4)
- Connecticut: 16.5% union, $96,049 nominal, $92,702 RPP-adjusted (RPP 103.6)
- New Jersey: 16.2% union, $104,294 nominal, $95,854 RPP-adjusted (RPP 108.8)

Bottom 5 states by union membership rate:
- North Carolina: 2.4% union, $73,958 nominal, $78,406 RPP-adjusted (RPP 94.3)
- South Dakota: 2.7% union, $76,881 nominal, $86,786 RPP-adjusted (RPP 88.6)
- South Carolina: 2.8% union, $72,350 nominal, $77,174 RPP-adjusted (RPP 93.7)
- Arkansas: 3.5% union, $62,106 nominal, $71,437 RPP-adjusted (RPP 86.9)
- Arizona: 3.7% union, $81,486 nominal, $80,938 RPP-adjusted (RPP 100.7)

Notes:
- Union measure: BLS union membership rate among employed wage and salary workers.
- Official BLS source URL: https://www.bls.gov/opub/ted/2025/union-membership-rates-highest-in-hawaii-and-new-york-lowest-in-north-carolina-in-2024.htm
- Income measure: Census ACS 2024 median household income.
- Official Census API URL: https://api.census.gov/data/2024/acs/acs1?get=NAME,B19013_001E&for=state:*
- Checked-in Census snapshot: data/census_acs_2024_B19013_001E_state.csv
- Price-level measure: BEA Regional Price Parities (SARPP, LineCode 1 All items, 2024). Real income is nominal income divided by (RPP / 100).
- Official BEA release: https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area
- BEA SARPP download URL: https://apps.bea.gov/regional/zip/SARPP.zip
- Checked-in BEA dump: data/bea_sarpp_state_2008_2024.csv
- The merged dataset excludes the District of Columbia to keep a 50-state comparison.
- These are ecological cross-sectional regressions across states and should not be read causally.
