# Sources

## Official sources

### 1. Bureau of Labor Statistics

- Publisher: U.S. Bureau of Labor Statistics
- Release page title: `Union membership rates highest in Hawaii and New York, lowest in North Carolina in 2024`
- URL: https://www.bls.gov/opub/ted/2025/union-membership-rates-highest-in-hawaii-and-new-york-lowest-in-north-carolina-in-2024.htm
- Related BLS news release PDF: https://www.bls.gov/news.release/pdf/union2.pdf
- Variable used here: state union membership rate among employed wage and salary workers in 2024
- Local file derived from it: `data/bls_union_membership_rates_2024.csv`

### 2. U.S. Census Bureau

- Publisher: U.S. Census Bureau
- Dataset: ACS 2024 1-year
- Variable: `B19013_001E`
- Variable meaning: median household income in the past 12 months
- Exact API query used by the script:
  https://api.census.gov/data/2024/acs/acs1?get=NAME,B19013_001E&for=state:*
- Checked-in snapshot derived from it: `data/census_acs_2024_B19013_001E_state.csv`
- Local script consumer: `scripts/collect_and_regress.py`

### 3. U.S. Bureau of Economic Analysis

- Publisher: U.S. Bureau of Economic Analysis
- Dataset: Regional Price Parities by state, table `SARPP`, years 2008-2024 (release of February 19, 2026)
- Release page: https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area
- Direct download used by the script: https://apps.bea.gov/regional/zip/SARPP.zip (the `SARPP_STATE_2008_2024.csv` member)
- Checked-in dump: `data/bea_sarpp_state_2008_2024.csv` (byte-for-byte copy of the BEA CSV)
- Supplementary BEA files also checked in so the dump can be interpreted offline:
  `data/bea_sarpp_definition.xml`, `data/bea_sarpp_footnotes.html`
- Variable used here: line code `1` (RPPs: All items) for the most recent year in the file
- Local script consumer: `scripts/collect_and_regress.py`

## Transformations

The repository does not scrape arbitrary websites, estimate missing values, or invent state rows.

It performs these explicit transformations:

1. Keep the checked-in BLS extract as the unionization input.
2. Keep a checked-in snapshot of the exact Census API values used by the analysis.
3. Keep the BEA SARPP state dump unmodified; at run time, filter to
   `LineCode == 1` (All items) and the most recent year column.
4. Exclude the District of Columbia so the merged file covers exactly the 50 U.S. states.
5. Join on the full state name.
6. Sort the merged rows alphabetically by state.
7. Compute `median_household_income_real_usd = median_household_income_usd / (rpp_all_items / 100)`.
8. Run two unweighted OLS regressions on the merged 50-state file — one on
   nominal income and one on RPP-adjusted income.

## What is checked in

- The BLS extract is checked in because the source site blocked automated shell retrieval from the environment used during assembly.
- The Census snapshot is checked in so reviewers can reproduce the analysis offline and compare exactly against committed outputs.
- The BEA SARPP state CSV is checked in verbatim (no hand-editing), alongside its BEA definition XML and footnotes HTML, so reviewers can confirm the RPP inputs without needing network access.
- The processed CSV and report outputs are checked in so reviewers can compare regenerated outputs against committed outputs.
