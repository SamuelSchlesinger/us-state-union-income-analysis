# Unionization and Median Income Regression (2024)

Model: `median_household_income_usd ~ union_membership_rate_pct`

- Observations: 50
- Slope: $1256.30 per 1 percentage point of union membership
- Intercept: $69018.36
- Correlation: 0.540
- R-squared: 0.292
- Slope p-value: 0.0001
- Slope 95% CI: $688.09 to $1824.50

Top 5 states by union membership rate:
- Hawaii: 26.5% union, $100,745 median household income
- New York: 20.6% union, $85,820 median household income
- Alaska: 17.7% union, $95,665 median household income
- Connecticut: 16.5% union, $96,049 median household income
- New Jersey: 16.2% union, $104,294 median household income

Bottom 5 states by union membership rate:
- North Carolina: 2.4% union, $73,958 median household income
- South Dakota: 2.7% union, $76,881 median household income
- South Carolina: 2.8% union, $72,350 median household income
- Arkansas: 3.5% union, $62,106 median household income
- Arizona: 3.7% union, $81,486 median household income

Notes:
- Union measure: BLS union membership rate among employed wage and salary workers.
- Official BLS source URL: https://www.bls.gov/opub/ted/2025/union-membership-rates-highest-in-hawaii-and-new-york-lowest-in-north-carolina-in-2024.htm
- Income measure: Census ACS 2024 median household income.
- Official Census API URL: https://api.census.gov/data/2024/acs/acs1?get=NAME,B19013_001E&for=state:*
- The merged dataset excludes the District of Columbia to keep a 50-state comparison.
- This is an ecological cross-sectional regression across states and should not be read causally.
