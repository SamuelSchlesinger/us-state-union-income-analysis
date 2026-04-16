#!/usr/bin/env python3
"""Build the merged 2024 state dataset and run OLS regressions.

This script is intentionally dependency-free so that reviewers can audit the
full pipeline with only the Python standard library.

Data provenance:
- `data/bls_union_membership_rates_2024.csv` is a checked-in extract of the
  official BLS 2024 state union-membership table.
- `data/census_acs_2024_B19013_001E_state.csv` is a checked-in snapshot of the
  exact Census values used by the analysis.
- `data/bea_sarpp_state_2008_2024.csv` is the unmodified BEA Regional Price
  Parities state dump (table SARPP, 2008-2024). The script parses line code 1
  (All items) for the latest year directly from that file — nothing about the
  RPP values is hand-transcribed.

Method:
1. Load the checked-in BLS state table.
2. Load the checked-in Census snapshot, or refresh it from the API with
   `--refresh-census`.
3. Load the BEA SARPP dump, or refresh it from the BEA download with
   `--refresh-rpp`. Filter to LineCode 1 (All items) and the latest year.
4. Exclude the District of Columbia so the analysis remains a 50-state
   comparison.
5. Join on state name.
6. Compute a second income column:
   `median_household_income_real_usd = median_household_income_usd / (rpp/100)`
7. Run two unweighted simple OLS regressions across the 50 states:
   - nominal:   `median_household_income_usd ~ union_membership_rate_pct`
   - RPP-real:  `median_household_income_real_usd ~ union_membership_rate_pct`
8. Write a merged CSV plus machine-readable and Markdown summaries that
   include both regressions side by side.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNION_CSV = ROOT / "data" / "bls_union_membership_rates_2024.csv"
CENSUS_SNAPSHOT_CSV = ROOT / "data" / "census_acs_2024_B19013_001E_state.csv"
RPP_DUMP_CSV = ROOT / "data" / "bea_sarpp_state_2008_2024.csv"
MERGED_CSV = ROOT / "data" / "us_states_union_income_2024.csv"
REGRESSION_JSON = ROOT / "results" / "union_income_regression_2024.json"
REGRESSION_MD = ROOT / "results" / "union_income_regression_2024.md"

BLS_SOURCE_URL = (
    "https://www.bls.gov/opub/ted/2025/"
    "union-membership-rates-highest-in-hawaii-and-new-york-lowest-"
    "in-north-carolina-in-2024.htm"
)
CENSUS_URL = (
    "https://api.census.gov/data/2024/acs/acs1"
    "?get=NAME,B19013_001E&for=state:*"
)
CENSUS_SOURCE_URL = CENSUS_URL
RPP_DOWNLOAD_URL = "https://apps.bea.gov/regional/zip/SARPP.zip"
RPP_RELEASE_URL = (
    "https://www.bea.gov/data/prices-inflation/"
    "regional-price-parities-state-and-metro-area"
)
RPP_DUMP_MEMBER = "SARPP_STATE_2008_2024.csv"

US_STATE_NAMES = frozenset(
    [
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
        "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
        "New Hampshire", "New Jersey", "New Mexico", "New York",
        "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
        "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
        "West Virginia", "Wisconsin", "Wyoming",
    ]
)


def load_union_rows() -> list[dict[str, object]]:
    """Load the checked-in BLS state table.

    The BLS table is stored locally because `bls.gov` blocked automated shell
    retrieval from this environment. Auditors should compare the CSV directly
    against the official BLS release page at `BLS_SOURCE_URL`.
    """

    rows: list[dict[str, object]] = []
    with UNION_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "state": row["state"],
                    "union_membership_rate_pct": float(row["union_membership_rate_pct"]),
                    "union_members": int(row["union_members"]),
                    "employed_wage_salary_workers": int(row["employed_wage_salary_workers"]),
                    "union_rate_year": int(row["union_rate_year"]),
                    "union_source_url": row["bls_source_url"],
                }
            )
    if len(rows) != 50:
        raise ValueError(f"Expected 50 state union rows, found {len(rows)}")
    return rows


def fetch_census_rows() -> dict[str, dict[str, object]]:
    """Fetch median household income by state from the official Census API."""

    request = urllib.request.Request(
        CENSUS_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)

    header = payload[0]
    name_idx = header.index("NAME")
    income_idx = header.index("B19013_001E")
    state_idx = header.index("state")

    rows: dict[str, dict[str, object]] = {}
    for record in payload[1:]:
        state_name = record[name_idx]
        if state_name == "District of Columbia":
            continue
        rows[state_name] = {
            "state": state_name,
            "state_fips": record[state_idx],
            "median_household_income_usd": int(record[income_idx]),
            "income_year": 2024,
            "income_source_url": CENSUS_SOURCE_URL,
        }
    if len(rows) != 50:
        raise ValueError(f"Expected 50 Census rows after excluding DC, found {len(rows)}")
    return rows


def load_census_snapshot_rows() -> dict[str, dict[str, object]]:
    """Load the checked-in Census snapshot used for reproducible offline builds."""

    rows: dict[str, dict[str, object]] = {}
    with CENSUS_SNAPSHOT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            state_name = row["state"]
            rows[state_name] = {
                "state": state_name,
                "state_fips": row["state_fips"],
                "median_household_income_usd": int(row["median_household_income_usd"]),
                "income_year": int(row["income_year"]),
                "income_source_url": row["income_source_url"],
            }
    if len(rows) != 50:
        raise ValueError(f"Expected 50 Census snapshot rows, found {len(rows)}")
    return rows


def write_census_snapshot(rows: dict[str, dict[str, object]]) -> None:
    """Persist the Census API response in a checked-in CSV for exact reuse."""

    fieldnames = [
        "state",
        "state_fips",
        "median_household_income_usd",
        "income_year",
        "income_source_url",
    ]
    ordered_rows = [rows[state] for state in sorted(rows)]
    with CENSUS_SNAPSHOT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ordered_rows)


def refresh_rpp_dump() -> None:
    """Download the BEA SARPP zip and overwrite the checked-in dump CSV."""

    request = urllib.request.Request(
        RPP_DOWNLOAD_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member_names = archive.namelist()
        member = next(
            (name for name in member_names if name.startswith("SARPP_STATE_") and name.endswith(".csv")),
            None,
        )
        if member is None:
            raise FileNotFoundError(
                f"SARPP state CSV not found in {RPP_DOWNLOAD_URL}: {member_names}"
            )
        data = archive.read(member)
    RPP_DUMP_CSV.write_bytes(data)


def load_rpp_rows() -> tuple[dict[str, float], int]:
    """Parse the BEA dump and return 2024-ish RPP values for the 50 states.

    The dump carries LineCodes 1-5 (All items, Goods, Housing, Utilities, Other
    services) and geographies United States + DC + 50 states. This function
    filters to LineCode 1 and the most recent year column, skipping the US
    aggregate and DC. Returns (state_name -> rpp, latest_year).
    """

    with RPP_DUMP_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, skipinitialspace=True)
        header = next(reader)

        year_columns = [(int(value), index) for index, value in enumerate(header) if value.isdigit()]
        if not year_columns:
            raise ValueError("BEA dump header has no numeric year columns")
        latest_year, year_col = max(year_columns)

        line_code_col = header.index("LineCode")
        geo_name_col = header.index("GeoName")

        rows: dict[str, float] = {}
        for record in reader:
            if len(record) <= year_col:
                continue
            line_code = record[line_code_col].strip()
            if line_code != "1":
                continue
            name = record[geo_name_col].strip()
            if name not in US_STATE_NAMES:
                continue
            value = record[year_col].strip()
            if not value:
                continue
            try:
                rows[name] = float(value)
            except ValueError:
                continue

    if len(rows) != 50:
        raise ValueError(f"Expected 50 state RPP rows, found {len(rows)}")
    return rows, latest_year


def merge_rows(
    union_rows: list[dict[str, object]],
    census_rows: dict[str, dict[str, object]],
    rpp_rows: dict[str, float],
    rpp_year: int,
) -> list[dict[str, object]]:
    """Join BLS, Census, and BEA rows on state name and compute real income."""

    merged: list[dict[str, object]] = []
    for union_row in union_rows:
        state = union_row["state"]
        if state not in census_rows:
            raise KeyError(f"Missing Census row for {state}")
        if state not in rpp_rows:
            raise KeyError(f"Missing BEA RPP row for {state}")

        rpp = rpp_rows[state]
        nominal = int(census_rows[state]["median_household_income_usd"])
        real_income = nominal / (rpp / 100.0)

        merged.append(
            {
                **union_row,
                **census_rows[state],
                "rpp_all_items": rpp,
                "rpp_year": rpp_year,
                "rpp_source_url": RPP_DOWNLOAD_URL,
                "median_household_income_real_usd": round(real_income, 2),
            }
        )

    merged.sort(key=lambda row: row["state"])

    if len(merged) != 50:
        raise ValueError(f"Expected 50 merged rows, found {len(merged)}")
    return merged


def write_csv(rows: list[dict[str, object]]) -> None:
    """Write the merged 50-state dataset used by the regression and visuals."""

    fieldnames = [
        "state",
        "state_fips",
        "union_membership_rate_pct",
        "union_members",
        "employed_wage_salary_workers",
        "median_household_income_usd",
        "rpp_all_items",
        "median_household_income_real_usd",
        "union_rate_year",
        "income_year",
        "rpp_year",
        "union_source_url",
        "income_source_url",
        "rpp_source_url",
    ]
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def student_t_pdf(value: float, degrees_of_freedom: int) -> float:
    """Return the Student t probability density at `value`."""

    numerator = math.gamma((degrees_of_freedom + 1) / 2)
    denominator = (
        math.sqrt(degrees_of_freedom * math.pi) * math.gamma(degrees_of_freedom / 2)
    )
    scale = 1 + (value * value) / degrees_of_freedom
    return (numerator / denominator) * (scale ** (-(degrees_of_freedom + 1) / 2))


def simpson_integral(
    func,
    lower: float,
    upper: float,
    intervals: int = 10000,
) -> float:
    """Numerically integrate `func` with Simpson's rule."""

    if intervals % 2 == 1:
        intervals += 1
    step = (upper - lower) / intervals
    total = func(lower) + func(upper)
    for idx in range(1, intervals):
        coefficient = 4 if idx % 2 == 1 else 2
        total += coefficient * func(lower + idx * step)
    return total * step / 3


def student_t_cdf(value: float, degrees_of_freedom: int) -> float:
    """Compute the Student t cumulative distribution function numerically."""

    if value == 0:
        return 0.5
    abs_value = abs(value)
    area = simpson_integral(
        lambda point: student_t_pdf(point, degrees_of_freedom),
        0.0,
        abs_value,
    )
    if value > 0:
        return 0.5 + area
    return 0.5 - area


def student_t_quantile(probability: float, degrees_of_freedom: int) -> float:
    """Invert the Student t CDF with binary search."""

    lower = 0.0
    upper = 20.0
    while student_t_cdf(upper, degrees_of_freedom) < probability:
        upper *= 2
    for _ in range(60):
        midpoint = (lower + upper) / 2
        if student_t_cdf(midpoint, degrees_of_freedom) < probability:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2


def regress(x_values: list[float], y_values: list[float], model: str) -> dict[str, object]:
    """Run an unweighted simple OLS regression on arbitrary x/y vectors."""

    n = len(x_values)
    if n != len(y_values):
        raise ValueError("x and y vectors must be the same length")

    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    sxx = sum((x - x_mean) ** 2 for x in x_values)
    syy = sum((y - y_mean) ** 2 for y in y_values)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    fitted = [intercept + slope * x for x in x_values]
    residuals = [y - y_hat for y, y_hat in zip(y_values, fitted)]
    sse = sum(residual * residual for residual in residuals)
    r_squared = 1 - (sse / syy)
    correlation = sxy / math.sqrt(sxx * syy)

    degrees_of_freedom = n - 2
    residual_standard_error = math.sqrt(sse / degrees_of_freedom)
    rmse = math.sqrt(sse / n)
    slope_standard_error = residual_standard_error / math.sqrt(sxx)
    intercept_standard_error = residual_standard_error * math.sqrt(
        (1 / n) + (x_mean * x_mean) / sxx
    )
    slope_t_stat = slope / slope_standard_error
    intercept_t_stat = intercept / intercept_standard_error
    slope_p_value = 2 * (1 - student_t_cdf(abs(slope_t_stat), degrees_of_freedom))
    intercept_p_value = 2 * (
        1 - student_t_cdf(abs(intercept_t_stat), degrees_of_freedom)
    )
    t_critical = student_t_quantile(0.975, degrees_of_freedom)

    slope_ci = (
        slope - t_critical * slope_standard_error,
        slope + t_critical * slope_standard_error,
    )
    intercept_ci = (
        intercept - t_critical * intercept_standard_error,
        intercept + t_critical * intercept_standard_error,
    )

    return {
        "model": model,
        "n_obs": n,
        "degrees_of_freedom": degrees_of_freedom,
        "x_mean": x_mean,
        "y_mean": y_mean,
        "slope": slope,
        "intercept": intercept,
        "correlation": correlation,
        "r_squared": r_squared,
        "rmse": rmse,
        "residual_standard_error": residual_standard_error,
        "slope_standard_error": slope_standard_error,
        "intercept_standard_error": intercept_standard_error,
        "slope_t_stat": slope_t_stat,
        "intercept_t_stat": intercept_t_stat,
        "slope_p_value": slope_p_value,
        "intercept_p_value": intercept_p_value,
        "slope_95_ci": list(slope_ci),
        "intercept_95_ci": list(intercept_ci),
    }


def run_regressions(rows: list[dict[str, object]]) -> dict[str, object]:
    """Run the nominal and RPP-adjusted regressions from the merged rows."""

    x_values = [float(row["union_membership_rate_pct"]) for row in rows]
    nominal_y = [float(row["median_household_income_usd"]) for row in rows]
    real_y = [float(row["median_household_income_real_usd"]) for row in rows]

    return {
        "nominal": regress(
            x_values,
            nominal_y,
            "median_household_income_usd ~ union_membership_rate_pct",
        ),
        "rpp_adjusted": regress(
            x_values,
            real_y,
            "median_household_income_real_usd ~ union_membership_rate_pct",
        ),
    }


def format_regression_lines(title: str, summary: dict[str, object]) -> list[str]:
    """Render a single regression's summary to Markdown lines."""

    return [
        f"### {title}",
        "",
        f"Model: `{summary['model']}`",
        "",
        f"- Observations: {summary['n_obs']}",
        f"- Slope: ${summary['slope']:.2f} per 1 percentage point of union membership",
        f"- Intercept: ${summary['intercept']:.2f}",
        f"- Correlation: {summary['correlation']:.3f}",
        f"- R-squared: {summary['r_squared']:.3f}",
        f"- Slope p-value: {summary['slope_p_value']:.4f}",
        (
            f"- Slope 95% CI: ${summary['slope_95_ci'][0]:.2f}"
            f" to ${summary['slope_95_ci'][1]:.2f}"
        ),
        "",
    ]


def write_regression_summary(
    rows: list[dict[str, object]],
    summaries: dict[str, object],
    rpp_year: int,
) -> None:
    """Write machine-readable and human-readable regression summaries."""

    top_union_states = sorted(
        rows,
        key=lambda row: float(row["union_membership_rate_pct"]),
        reverse=True,
    )[:5]
    bottom_union_states = sorted(
        rows,
        key=lambda row: float(row["union_membership_rate_pct"]),
    )[:5]

    REGRESSION_JSON.write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Unionization and Median Income Regression (2024)",
        "",
        (
            "Two regressions are reported side by side: nominal median household"
            " income, and median household income deflated by the BEA Regional"
            f" Price Parity (all items, {rpp_year})."
        ),
        "",
    ]
    lines.extend(format_regression_lines("Nominal income", summaries["nominal"]))
    lines.extend(format_regression_lines("RPP-adjusted (real) income", summaries["rpp_adjusted"]))

    lines.append("Top 5 states by union membership rate:")
    for row in top_union_states:
        lines.append(
            (
                f"- {row['state']}: {row['union_membership_rate_pct']:.1f}% union,"
                f" ${int(row['median_household_income_usd']):,} nominal,"
                f" ${int(row['median_household_income_real_usd']):,} RPP-adjusted"
                f" (RPP {row['rpp_all_items']:.1f})"
            )
        )

    lines.append("")
    lines.append("Bottom 5 states by union membership rate:")
    for row in bottom_union_states:
        lines.append(
            (
                f"- {row['state']}: {row['union_membership_rate_pct']:.1f}% union,"
                f" ${int(row['median_household_income_usd']):,} nominal,"
                f" ${int(row['median_household_income_real_usd']):,} RPP-adjusted"
                f" (RPP {row['rpp_all_items']:.1f})"
            )
        )

    lines.extend(
        [
            "",
            "Notes:",
            (
                "- Union measure: BLS union membership rate among employed wage "
                "and salary workers."
            ),
            "- Official BLS source URL: " + BLS_SOURCE_URL,
            "- Income measure: Census ACS 2024 median household income.",
            "- Official Census API URL: " + CENSUS_SOURCE_URL,
            "- Checked-in Census snapshot: data/census_acs_2024_B19013_001E_state.csv",
            (
                "- Price-level measure: BEA Regional Price Parities (SARPP, "
                f"LineCode 1 All items, {rpp_year}). Real income is nominal "
                "income divided by (RPP / 100)."
            ),
            "- Official BEA release: " + RPP_RELEASE_URL,
            "- BEA SARPP download URL: " + RPP_DOWNLOAD_URL,
            "- Checked-in BEA dump: data/bea_sarpp_state_2008_2024.csv",
            "- The merged dataset excludes the District of Columbia to keep a 50-state comparison.",
            "- These are ecological cross-sectional regressions across states and should not be read causally.",
        ]
    )

    REGRESSION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the full data-processing and regression pipeline."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the merged 2024 state dataset and regression outputs. "
            "By default this uses the checked-in Census snapshot and BEA dump."
        )
    )
    parser.add_argument(
        "--refresh-census",
        action="store_true",
        help="Fetch the Census API live and rewrite the checked-in snapshot first.",
    )
    parser.add_argument(
        "--refresh-rpp",
        action="store_true",
        help="Download the BEA SARPP zip and overwrite the checked-in dump first.",
    )
    args = parser.parse_args()

    union_rows = load_union_rows()
    if args.refresh_census:
        census_rows = fetch_census_rows()
        write_census_snapshot(census_rows)
        print(f"Refreshed Census snapshot at {CENSUS_SNAPSHOT_CSV}")
    else:
        if not CENSUS_SNAPSHOT_CSV.exists():
            raise FileNotFoundError(
                "Missing Census snapshot: "
                f"{CENSUS_SNAPSHOT_CSV}. Run with --refresh-census in a "
                "networked environment to create it."
            )
        census_rows = load_census_snapshot_rows()

    if args.refresh_rpp:
        refresh_rpp_dump()
        print(f"Refreshed BEA RPP dump at {RPP_DUMP_CSV}")
    elif not RPP_DUMP_CSV.exists():
        raise FileNotFoundError(
            "Missing BEA SARPP dump: "
            f"{RPP_DUMP_CSV}. Run with --refresh-rpp in a networked environment to fetch it."
        )

    rpp_rows, rpp_year = load_rpp_rows()
    merged_rows = merge_rows(union_rows, census_rows, rpp_rows, rpp_year)
    write_csv(merged_rows)
    summaries = run_regressions(merged_rows)
    write_regression_summary(merged_rows, summaries, rpp_year)

    print(f"Wrote merged dataset to {MERGED_CSV}")
    print(f"Wrote regression summary to {REGRESSION_JSON}")
    print(f"Wrote regression report to {REGRESSION_MD}")


if __name__ == "__main__":
    main()
