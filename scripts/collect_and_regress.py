#!/usr/bin/env python3
"""Build the merged 2024 state dataset and run a simple OLS regression.

This script is intentionally dependency-free so that reviewers can audit the
full pipeline with only the Python standard library.

Data provenance:
- `data/bls_union_membership_rates_2024.csv` is a checked-in extract of the
  official BLS 2024 state union-membership table.
- `data/census_acs_2024_B19013_001E_state.csv` is a checked-in snapshot of the
  exact Census values used by the analysis.

Method:
1. Load the checked-in BLS state table.
2. Load the checked-in Census snapshot, or refresh it explicitly from the
   official API with `--refresh-census`.
3. Exclude the District of Columbia so the analysis remains a 50-state
   comparison.
4. Join on state name.
5. Run an unweighted cross-sectional OLS regression:
   `median_household_income_usd ~ union_membership_rate_pct`
6. Write a merged CSV plus machine-readable and Markdown summaries.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNION_CSV = ROOT / "data" / "bls_union_membership_rates_2024.csv"
CENSUS_SNAPSHOT_CSV = ROOT / "data" / "census_acs_2024_B19013_001E_state.csv"
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


def merge_rows(
    union_rows: list[dict[str, object]],
    census_rows: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Join the BLS and Census rows on state name and sort alphabetically."""

    merged: list[dict[str, object]] = []
    for union_row in union_rows:
        state = union_row["state"]
        if state not in census_rows:
            raise KeyError(f"Missing Census row for {state}")
        merged.append({**union_row, **census_rows[state]})

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
        "union_rate_year",
        "income_year",
        "union_source_url",
        "income_source_url",
    ]
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def student_t_pdf(value: float, degrees_of_freedom: int) -> float:
    """Return the Student t probability density at `value`.

    This is used only for the p-value and confidence interval calculations.
    The regression slope, intercept, correlation, and R-squared do not depend
    on these helpers.
    """

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


def regress(rows: list[dict[str, object]]) -> dict[str, object]:
    """Run an unweighted simple OLS regression across the 50 states."""

    x_values = [float(row["union_membership_rate_pct"]) for row in rows]
    y_values = [float(row["median_household_income_usd"]) for row in rows]
    n = len(rows)

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
        "model": "median_household_income_usd ~ union_membership_rate_pct",
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


def write_regression_summary(
    rows: list[dict[str, object]],
    summary: dict[str, object],
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

    REGRESSION_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Unionization and Median Income Regression (2024)",
        "",
        "Model: `median_household_income_usd ~ union_membership_rate_pct`",
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
        "Top 5 states by union membership rate:",
    ]

    for row in top_union_states:
        lines.append(
            (
                f"- {row['state']}: {row['union_membership_rate_pct']:.1f}% union,"
                f" ${int(row['median_household_income_usd']):,} median household income"
            )
        )

    lines.append("")
    lines.append("Bottom 5 states by union membership rate:")
    for row in bottom_union_states:
        lines.append(
            (
                f"- {row['state']}: {row['union_membership_rate_pct']:.1f}% union,"
                f" ${int(row['median_household_income_usd']):,} median household income"
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
            "- The merged dataset excludes the District of Columbia to keep a 50-state comparison.",
            "- This is an ecological cross-sectional regression across states and should not be read causally.",
        ]
    )

    REGRESSION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the full data-processing and regression pipeline."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the merged 2024 state dataset and regression outputs. "
            "By default this uses the checked-in Census snapshot."
        )
    )
    parser.add_argument(
        "--refresh-census",
        action="store_true",
        help="Fetch the Census API live and rewrite the checked-in snapshot first.",
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
    merged_rows = merge_rows(union_rows, census_rows)
    write_csv(merged_rows)
    summary = regress(merged_rows)
    write_regression_summary(merged_rows, summary)

    print(f"Wrote merged dataset to {MERGED_CSV}")
    print(f"Wrote regression summary to {REGRESSION_JSON}")
    print(f"Wrote regression report to {REGRESSION_MD}")


if __name__ == "__main__":
    main()
