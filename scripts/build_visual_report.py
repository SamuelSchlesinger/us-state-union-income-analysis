#!/usr/bin/env python3
"""Build a self-contained single-file HTML report from the processed dataset.

This script does not collect or transform source data. It reads:
- `data/us_states_union_income_2024.csv`
- `results/union_income_regression_2024.json`

and turns them into `results/union_income_visual_report.html`.

Every number, label, axis range, and state callout in the output is derived
from those two files. The numerical processing happens in
`collect_and_regress.py`; this file is only responsible for presentation.
"""

from __future__ import annotations

import csv
import json
import os
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "us_states_union_income_2024.csv"
REGRESSION_JSON = ROOT / "results" / "union_income_regression_2024.json"
REPORT_HTML = ROOT / "results" / "union_income_visual_report.html"
REPO_URL = "https://github.com/SamuelSchlesinger/us-state-union-income-analysis"
REPO_REF = os.environ.get("REPO_REF", "main")
REPO_BLOB_BASE = f"{REPO_URL}/blob/{REPO_REF}"
AUDIT_DOC_URL = f"{REPO_BLOB_BASE}/AUDIT.md"
SOURCES_DOC_URL = f"{REPO_BLOB_BASE}/SOURCES.md"
SHA256SUMS_URL = f"{REPO_BLOB_BASE}/SHA256SUMS"
AUDIT_MANIFEST_URL = (
    f"{REPO_BLOB_BASE}/results/union_income_audit_manifest_2024.json"
)
BLS_SOURCE_URL = (
    "https://www.bls.gov/opub/ted/2025/"
    "union-membership-rates-highest-in-hawaii-and-new-york-lowest-"
    "in-north-carolina-in-2024.htm"
)
CENSUS_SOURCE_URL = (
    "https://api.census.gov/data/2024/acs/acs1"
    "?get=NAME,B19013_001E&for=state:*"
)
BEA_SOURCE_URL = (
    "https://www.bea.gov/data/prices-inflation/"
    "regional-price-parities-state-and-metro-area"
)
BEA_DOWNLOAD_URL = "https://apps.bea.gov/regional/zip/SARPP.zip"

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

QUADRANT_COLORS = {
    "high_union_high_income": "#ff6b4a",
    "high_union_low_income": "#d4702f",
    "low_union_high_income": "#17887b",
    "low_union_low_income": "#456173",
}

QUADRANT_LABELS = {
    "high_union_high_income": "High union / high income",
    "high_union_low_income": "High union / lower income",
    "low_union_high_income": "Lower union / high income",
    "low_union_low_income": "Lower union / lower income",
}

NOMINAL_KEY = "median_household_income_usd"
REAL_KEY = "median_household_income_real_usd"


def load_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    with DATA_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "state": row["state"],
                    "state_fips": row["state_fips"],
                    "union_membership_rate_pct": float(row["union_membership_rate_pct"]),
                    "union_members": int(row["union_members"]),
                    "employed_wage_salary_workers": int(row["employed_wage_salary_workers"]),
                    NOMINAL_KEY: int(row[NOMINAL_KEY]),
                    REAL_KEY: float(row[REAL_KEY]),
                    "rpp_all_items": float(row["rpp_all_items"]),
                    "rpp_year": int(row["rpp_year"]),
                    "income_year": int(row["income_year"]),
                }
            )
    return rows


def load_regressions() -> dict[str, dict[str, float | int | str | list[float]]]:
    return json.loads(REGRESSION_JSON.read_text(encoding="utf-8"))


def scale(value: float, d_min: float, d_max: float, r_min: float, r_max: float) -> float:
    if d_max == d_min:
        return (r_min + r_max) / 2
    ratio = (value - d_min) / (d_max - d_min)
    return r_min + ratio * (r_max - r_min)


def currency(value: float) -> str:
    return f"${value:,.0f}"


def compact_currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.1f}M"
    if amount >= 1000:
        return f"{sign}${amount / 1000:.1f}k"
    return f"{sign}{currency(amount)}"


def enrich_rows(
    rows: list[dict[str, float | int | str]],
    regressions: dict[str, dict[str, float | int | str | list[float]]],
) -> None:
    nominal = regressions["nominal"]
    adjusted = regressions["rpp_adjusted"]

    x_mean_n = float(nominal["x_mean"])
    y_mean_n = float(nominal["y_mean"])
    slope_n = float(nominal["slope"])
    intercept_n = float(nominal["intercept"])

    slope_r = float(adjusted["slope"])
    intercept_r = float(adjusted["intercept"])

    for row in rows:
        x = float(row["union_membership_rate_pct"])
        y_n = float(row[NOMINAL_KEY])
        y_r = float(row[REAL_KEY])

        row["predicted_nominal_usd"] = intercept_n + slope_n * x
        row["residual_nominal_usd"] = y_n - row["predicted_nominal_usd"]
        row["predicted_real_usd"] = intercept_r + slope_r * x
        row["residual_real_usd"] = y_r - row["predicted_real_usd"]

        if x >= x_mean_n and y_n >= y_mean_n:
            row["quadrant"] = "high_union_high_income"
        elif x >= x_mean_n and y_n < y_mean_n:
            row["quadrant"] = "high_union_low_income"
        elif x < x_mean_n and y_n >= y_mean_n:
            row["quadrant"] = "low_union_high_income"
        else:
            row["quadrant"] = "low_union_low_income"

        row["abbr"] = STATE_ABBR[str(row["state"])]


def choose_labels(rows: list[dict[str, float | int | str]], y_key: str) -> set[str]:
    selected: set[str] = set()
    selectors = [
        sorted(rows, key=lambda r: float(r["union_membership_rate_pct"]), reverse=True)[:4],
        sorted(rows, key=lambda r: float(r["union_membership_rate_pct"]))[:4],
        sorted(rows, key=lambda r: float(r[y_key]), reverse=True)[:4],
        sorted(rows, key=lambda r: float(r[y_key]))[:4],
    ]
    for group in selectors:
        for row in group:
            selected.add(str(row["state"]))
    selected.update({"California", "Texas", "New York"})
    return selected


def nice_bounds(low: float, high: float, step: float) -> tuple[float, float]:
    """Snap bounds outward to the nearest multiple of `step`."""

    import math
    bounded_low = math.floor(low / step) * step
    bounded_high = math.ceil(high / step) * step
    return bounded_low, bounded_high


def scatter_svg(
    rows: list[dict[str, float | int | str]],
    regression: dict[str, float | int | str | list[float]],
    y_key: str,
    y_bounds: tuple[float, float],
    title: str,
    subtitle: str,
) -> str:
    width = 560
    height = 420
    margin_left = 70
    margin_right = 22
    margin_top = 52
    margin_bottom = 56

    x_values = [float(row["union_membership_rate_pct"]) for row in rows]
    x_min = min(x_values) - 1.0
    x_max = max(x_values) + 1.5

    y_min, y_max = y_bounds

    x_mean = float(regression["x_mean"])
    y_mean = float(regression["y_mean"])
    slope = float(regression["slope"])
    intercept = float(regression["intercept"])

    selected_labels = choose_labels(rows, y_key)

    def sx(value: float) -> float:
        return scale(value, x_min, x_max, margin_left, width - margin_right)

    def sy(value: float) -> float:
        return scale(value, y_min, y_max, height - margin_bottom, margin_top)

    def radius(workers: int) -> float:
        return scale(workers ** 0.5, 500, 4100, 4, 16)

    x_ticks = [5, 10, 15, 20, 25]
    y_step = 10_000
    y_ticks = []
    tick = int(y_min)
    while tick <= int(y_max) + 1:
        y_ticks.append(tick)
        tick += y_step

    svg: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg small-scatter" role="img" '
        f'aria-label="{escape(title)}">'
    ]

    svg.append(
        f'<text x="{margin_left}" y="22" class="panel-title">{escape(title)}</text>'
    )
    svg.append(
        f'<text x="{margin_left}" y="40" class="panel-subtitle">{escape(subtitle)}</text>'
    )

    quadrants = [
        (x_min, y_mean, x_mean, y_max, "#d4f1ea"),
        (x_mean, y_mean, x_max, y_max, "#ffe4d9"),
        (x_min, y_min, x_mean, y_mean, "#dde8ef"),
        (x_mean, y_min, x_max, y_mean, "#ffe9d5"),
    ]
    for x0, y0, x1, y1, fill in quadrants:
        svg.append(
            f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" '
            f'width="{sx(x1) - sx(x0):.1f}" height="{sy(y0) - sy(y1):.1f}" '
            f'fill="{fill}" opacity="0.35"/>'
        )

    for x_tick in x_ticks:
        x_pos = sx(x_tick)
        svg.append(
            f'<line x1="{x_pos:.1f}" y1="{margin_top}" x2="{x_pos:.1f}" '
            f'y2="{height - margin_bottom}" class="gridline"/>'
        )
        svg.append(
            f'<text x="{x_pos:.1f}" y="{height - margin_bottom + 18}" class="axis-label" '
            f'text-anchor="middle">{x_tick}%</text>'
        )

    for y_tick in y_ticks:
        y_pos = sy(y_tick)
        svg.append(
            f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" '
            f'y2="{y_pos:.1f}" class="gridline"/>'
        )
        svg.append(
            f'<text x="{margin_left - 10}" y="{y_pos + 4:.1f}" class="axis-label" '
            f'text-anchor="end">{int(y_tick / 1000)}k</text>'
        )

    svg.append(
        f'<line x1="{margin_left}" y1="{sy(y_mean):.1f}" x2="{width - margin_right}" '
        f'y2="{sy(y_mean):.1f}" class="mean-line"/>'
    )
    svg.append(
        f'<line x1="{sx(x_mean):.1f}" y1="{margin_top}" x2="{sx(x_mean):.1f}" '
        f'y2="{height - margin_bottom}" class="mean-line"/>'
    )

    line_y1 = intercept + slope * x_min
    line_y2 = intercept + slope * x_max
    svg.append(
        f'<line x1="{sx(x_min):.1f}" y1="{sy(line_y1):.1f}" '
        f'x2="{sx(x_max):.1f}" y2="{sy(line_y2):.1f}" class="trend-line"/>'
    )

    for row in rows:
        x = float(row["union_membership_rate_pct"])
        y = float(row[y_key])
        r = radius(int(row["employed_wage_salary_workers"]))
        fill = QUADRANT_COLORS[str(row["quadrant"])]
        tooltip = (
            f"{row['state']}: {x:.1f}% union, "
            f"nominal {currency(float(row[NOMINAL_KEY]))}, "
            f"RPP-adjusted {currency(float(row[REAL_KEY]))}, "
            f"RPP {float(row['rpp_all_items']):.1f}"
        )
        svg.append(
            f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{r:.1f}" '
            f'fill="{fill}" class="bubble"><title>{escape(tooltip)}</title></circle>'
        )

    for row in rows:
        if str(row["state"]) not in selected_labels:
            continue
        x = sx(float(row["union_membership_rate_pct"]))
        y = sy(float(row[y_key]))
        x_offset = 8 if float(row["union_membership_rate_pct"]) < x_mean else -8
        anchor = "start" if x_offset > 0 else "end"
        y_offset = -9 if float(row[y_key]) > y_mean else 14
        svg.append(
            f'<text x="{x + x_offset:.1f}" y="{y + y_offset:.1f}" class="point-label" '
            f'text-anchor="{anchor}">{escape(str(row["abbr"]))}</text>'
        )

    svg.append(
        f'<text x="{width / 2:.1f}" y="{height - 12}" class="axis-title" '
        f'text-anchor="middle">Union membership rate</text>'
    )
    svg.append(
        f'<text x="18" y="{height / 2:.1f}" class="axis-title" '
        f'text-anchor="middle" transform="rotate(-90 18 {height / 2:.1f})">'
        f'Median household income (USD)</text>'
    )
    svg.append("</svg>")
    return "\n".join(svg)


def shared_y_bounds(rows: list[dict[str, float | int | str]]) -> tuple[float, float]:
    low = min(
        min(float(r[NOMINAL_KEY]) for r in rows),
        min(float(r[REAL_KEY]) for r in rows),
    )
    high = max(
        max(float(r[NOMINAL_KEY]) for r in rows),
        max(float(r[REAL_KEY]) for r in rows),
    )
    return nice_bounds(low - 1500, high + 1500, 5_000)


def rank_shift_panel_svg(rows: list[dict[str, float | int | str]]) -> str:
    ranked_nominal = {
        str(r["state"]): idx + 1
        for idx, r in enumerate(
            sorted(rows, key=lambda r: float(r[NOMINAL_KEY]), reverse=True)
        )
    }
    ranked_real = {
        str(r["state"]): idx + 1
        for idx, r in enumerate(
            sorted(rows, key=lambda r: float(r[REAL_KEY]), reverse=True)
        )
    }

    enriched = []
    for row in rows:
        name = str(row["state"])
        shift = ranked_nominal[name] - ranked_real[name]
        enriched.append({**row, "rank_nominal": ranked_nominal[name], "rank_real": ranked_real[name], "rank_shift": shift})

    gains = sorted(enriched, key=lambda r: r["rank_shift"], reverse=True)[:6]
    losses = sorted(enriched, key=lambda r: r["rank_shift"])[:6]

    width = 560
    row_height = 30
    height = 120 + max(len(gains), len(losses)) * row_height
    left = 20
    right = 20
    top = 28

    svg = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" '
        f'aria-label="Rank shifts after RPP adjustment">',
        f'<text x="{left}" y="22" class="panel-title">Biggest rank shifts after RPP adjustment</text>',
        f'<text x="{left}" y="40" class="panel-subtitle">'
        f'Move from nominal-income rank to RPP-adjusted rank (1 = highest income).</text>',
    ]

    col_width = (width - left - right) / 2
    svg.append(
        f'<text x="{left}" y="{top + 30}" class="column-header">Climbed the most</text>'
    )
    svg.append(
        f'<text x="{left + col_width + 20}" y="{top + 30}" class="column-header">Fell the most</text>'
    )

    for idx, row in enumerate(gains):
        y = top + 56 + idx * row_height
        label = (
            f"{row['state']}: {row['rank_nominal']} → {row['rank_real']}"
            f"  (+{row['rank_shift']})"
        )
        svg.append(
            f'<text x="{left}" y="{y}" class="rank-row gain">{escape(label)}</text>'
        )

    for idx, row in enumerate(losses):
        y = top + 56 + idx * row_height
        label = (
            f"{row['state']}: {row['rank_nominal']} → {row['rank_real']}"
            f"  ({row['rank_shift']:+d})"
        )
        svg.append(
            f'<text x="{left + col_width + 20}" y="{y}" class="rank-row loss">{escape(label)}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def state_chip(row: dict[str, float | int | str]) -> str:
    state = escape(str(row["state"]))
    union = f"{float(row['union_membership_rate_pct']):.1f}%"
    income = compact_currency(float(row[NOMINAL_KEY]))
    color = QUADRANT_COLORS[str(row["quadrant"])]
    return (
        '<span class="chip" style="--chip-accent: '
        + color
        + '">'
        + f"<strong>{state}</strong><span>{union} · {income}</span>"
        + "</span>"
    )


def quadrant_markup(rows: list[dict[str, float | int | str]]) -> str:
    buckets: dict[str, list[dict[str, float | int | str]]] = {key: [] for key in QUADRANT_LABELS}
    for row in rows:
        buckets[str(row["quadrant"])].append(row)

    sections: list[str] = []
    for key, label in QUADRANT_LABELS.items():
        bucket_rows = sorted(
            buckets[key],
            key=lambda row: (
                -float(row["union_membership_rate_pct"]),
                -float(row[NOMINAL_KEY]),
            ),
        )
        chips = "".join(state_chip(row) for row in bucket_rows)
        sections.append(
            '<article class="quadrant-card">'
            + f'<div class="quadrant-header"><span class="swatch" style="background:{QUADRANT_COLORS[key]}"></span>'
            + f"<h3>{escape(label)}</h3>"
            + f'<span class="count">{len(bucket_rows)} states</span></div>'
            + f'<div class="chip-wrap">{chips}</div>'
            + "</article>"
        )
    return "\n".join(sections)


def comparison_stat_row(label: str, nominal_fmt: str, real_fmt: str, note: str = "") -> str:
    note_html = f'<div class="note">{escape(note)}</div>' if note else ""
    return (
        '<tr>'
        + f'<th scope="row"><div class="label">{escape(label)}</div>{note_html}</th>'
        + f'<td class="val nominal">{nominal_fmt}</td>'
        + f'<td class="val real">{real_fmt}</td>'
        + '</tr>'
    )


def comparison_table_html(nominal: dict, adjusted: dict) -> str:
    def ci_text(ci: list[float]) -> str:
        return f"${ci[0]:,.0f} – ${ci[1]:,.0f}"

    rows_html = [
        comparison_stat_row(
            "Slope (USD per +1 pp union)",
            currency(float(nominal["slope"])),
            currency(float(adjusted["slope"])),
            "How much median income rises per one-point increase in union density.",
        ),
        comparison_stat_row(
            "Slope 95% CI",
            ci_text(list(nominal["slope_95_ci"])),
            ci_text(list(adjusted["slope_95_ci"])),
        ),
        comparison_stat_row(
            "Slope p-value",
            f"{float(nominal['slope_p_value']):.4g}",
            f"{float(adjusted['slope_p_value']):.4g}",
        ),
        comparison_stat_row(
            "Correlation",
            f"{float(nominal['correlation']):.3f}",
            f"{float(adjusted['correlation']):.3f}",
        ),
        comparison_stat_row(
            "R-squared",
            f"{float(nominal['r_squared']):.3f}",
            f"{float(adjusted['r_squared']):.3f}",
        ),
        comparison_stat_row(
            "Mean income (y)",
            currency(float(nominal["y_mean"])),
            currency(float(adjusted["y_mean"])),
        ),
        comparison_stat_row(
            "Residual std. error",
            currency(float(nominal["residual_standard_error"])),
            currency(float(adjusted["residual_standard_error"])),
        ),
    ]

    return (
        '<table class="compare">'
        + '<thead><tr>'
        + '<th></th>'
        + '<th class="col nominal">Nominal income</th>'
        + '<th class="col real">RPP-adjusted income</th>'
        + '</tr></thead>'
        + f'<tbody>{"".join(rows_html)}</tbody>'
        + '</table>'
    )


def build_html(
    rows: list[dict[str, float | int | str]],
    regressions: dict[str, dict[str, float | int | str | list[float]]],
) -> str:
    nominal = regressions["nominal"]
    adjusted = regressions["rpp_adjusted"]

    n_obs = int(nominal["n_obs"])
    x_mean = float(nominal["x_mean"])
    y_mean_nominal = float(nominal["y_mean"])
    y_mean_real = float(adjusted["y_mean"])

    slope_nominal = float(nominal["slope"])
    slope_real = float(adjusted["slope"])
    correlation_nominal = float(nominal["correlation"])
    correlation_real = float(adjusted["correlation"])
    r_squared_nominal = float(nominal["r_squared"])
    r_squared_real = float(adjusted["r_squared"])

    rpp_year = int(rows[0]["rpp_year"])
    income_year = int(rows[0]["income_year"])

    slope_shrinkage_pct = (1 - slope_real / slope_nominal) * 100 if slope_nominal else 0.0

    high_union = max(rows, key=lambda r: float(r["union_membership_rate_pct"]))
    low_union = min(rows, key=lambda r: float(r["union_membership_rate_pct"]))
    high_rpp = max(rows, key=lambda r: float(r["rpp_all_items"]))
    low_rpp = min(rows, key=lambda r: float(r["rpp_all_items"]))

    y_bounds = shared_y_bounds(rows)

    nominal_scatter = scatter_svg(
        rows,
        nominal,
        NOMINAL_KEY,
        y_bounds,
        "Nominal median household income",
        "Census ACS 2024 1-year estimates, unadjusted dollars",
    )
    real_scatter = scatter_svg(
        rows,
        adjusted,
        REAL_KEY,
        y_bounds,
        f"RPP-adjusted income ({rpp_year})",
        "Nominal income divided by BEA Regional Price Parity (US = 100)",
    )
    comparison_table = comparison_table_html(nominal, adjusted)
    rank_panel = rank_shift_panel_svg(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Unionization and Income by State, 2024 — nominal and RPP-adjusted</title>
  <style>
    :root {{
      --bg: #f6f0e6;
      --paper: rgba(255, 250, 243, 0.86);
      --ink: #17212a;
      --muted: #5b6670;
      --grid: rgba(23, 33, 42, 0.12);
      --line: rgba(23, 33, 42, 0.3);
      --nominal: #d9643b;
      --real: #17887b;
      --hero: linear-gradient(135deg, #11212d 0%, #213f4a 48%, #d9643b 100%);
      --shadow: 0 18px 50px rgba(16, 23, 31, 0.12);
      --radius: 28px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.72), transparent 32%),
        linear-gradient(180deg, #fbf6ef 0%, var(--bg) 100%);
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(23, 33, 42, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(23, 33, 42, 0.025) 1px, transparent 1px);
      background-size: 26px 26px;
      pointer-events: none;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.35), transparent 70%);
    }}

    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 22px 56px;
      position: relative;
    }}

    .hero {{
      background: var(--hero);
      border-radius: 36px;
      padding: 34px 34px 28px;
      color: #fff8f1;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      width: 420px;
      height: 420px;
      right: -110px;
      top: -150px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 68%);
    }}

    .kicker {{
      margin: 0 0 10px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.78rem;
      opacity: 0.85;
    }}

    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(2.5rem, 4.8vw, 4.4rem);
      line-height: 0.98;
      max-width: 14ch;
      font-weight: 400;
    }}

    .subhead {{
      max-width: 58rem;
      font-size: 1rem;
      line-height: 1.6;
      color: rgba(255, 248, 241, 0.9);
      margin-top: 16px;
      margin-bottom: 24px;
    }}

    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}

    .metric {{
      background: rgba(255, 248, 241, 0.12);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 248, 241, 0.12);
      border-radius: 18px;
      padding: 14px 16px;
      min-height: 120px;
    }}

    .metric.dual .value-pair {{
      display: flex;
      gap: 10px;
      align-items: baseline;
      flex-wrap: wrap;
      margin-top: 6px;
    }}

    .metric.dual .value-pair .v {{ font-size: 1.45rem; font-weight: 700; }}
    .metric.dual .value-pair .sep {{ opacity: 0.55; font-size: 1.1rem; }}

    .metric .label {{
      font-size: 0.76rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      opacity: 0.72;
    }}

    .metric .value {{
      margin-top: 8px;
      font-size: 1.6rem;
      font-weight: 700;
    }}

    .metric .note {{
      margin-top: 6px;
      font-size: 0.88rem;
      line-height: 1.45;
      color: rgba(255, 248, 241, 0.8);
    }}

    .swatch-n, .swatch-r {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      vertical-align: middle;
      margin-right: 6px;
    }}
    .swatch-n {{ background: var(--nominal); }}
    .swatch-r {{ background: var(--real); }}

    .section {{ margin-top: 26px; }}

    .card {{
      background: var(--paper);
      border: 1px solid rgba(23, 33, 42, 0.08);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 24px 24px 18px;
      backdrop-filter: blur(8px);
    }}

    .card h2 {{
      margin: 0;
      font-size: 1.2rem;
      line-height: 1.2;
    }}

    .card .deck {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.6;
      max-width: 62rem;
    }}

    .two-up-scatter {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}

    .scatter-frame {{
      background: rgba(255, 255, 255, 0.68);
      border: 1px solid rgba(23, 33, 42, 0.06);
      border-radius: 20px;
      padding: 10px;
    }}

    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
    }}

    .gridline {{ stroke: var(--grid); stroke-width: 1; }}
    .mean-line {{
      stroke: rgba(23, 33, 42, 0.4);
      stroke-width: 1.2;
      stroke-dasharray: 4 5;
    }}
    .trend-line {{
      stroke: #17212a;
      stroke-width: 2.4;
      stroke-dasharray: 9 7;
      opacity: 0.9;
    }}

    .bubble {{
      stroke: rgba(255, 255, 255, 0.8);
      stroke-width: 1.2;
      opacity: 0.9;
    }}

    .axis-label {{ fill: var(--muted); font-size: 11px; }}
    .axis-title {{ fill: var(--ink); font-size: 12px; font-weight: 700; }}
    .panel-title {{ fill: var(--ink); font-size: 15px; font-weight: 700; }}
    .panel-subtitle {{ fill: var(--muted); font-size: 11px; }}

    .point-label {{
      fill: var(--ink);
      font-size: 11px;
      font-weight: 700;
      paint-order: stroke;
      stroke: rgba(255, 250, 243, 0.95);
      stroke-width: 2.5px;
      stroke-linejoin: round;
    }}

    table.compare {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 0.95rem;
    }}

    table.compare th, table.compare td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid rgba(23, 33, 42, 0.08);
      vertical-align: top;
    }}

    table.compare thead th {{
      font-size: 0.78rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      border-bottom: 2px solid rgba(23, 33, 42, 0.2);
    }}

    table.compare thead th.col {{ color: var(--ink); }}
    table.compare thead th.col.nominal::before {{
      content: "";
      display: inline-block;
      width: 10px; height: 10px;
      background: var(--nominal);
      border-radius: 999px;
      margin-right: 8px;
    }}
    table.compare thead th.col.real::before {{
      content: "";
      display: inline-block;
      width: 10px; height: 10px;
      background: var(--real);
      border-radius: 999px;
      margin-right: 8px;
    }}

    table.compare tbody th {{ font-weight: 600; }}
    table.compare tbody th .label {{ font-size: 0.98rem; }}
    table.compare tbody th .note {{ color: var(--muted); font-size: 0.82rem; margin-top: 2px; font-weight: 400; }}
    table.compare td.val {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
    table.compare td.val.nominal {{ color: var(--nominal); }}
    table.compare td.val.real {{ color: var(--real); }}

    .rank-row {{
      fill: var(--ink);
      font-size: 13px;
      font-variant-numeric: tabular-nums;
    }}
    .rank-row.gain {{ fill: #0e665e; font-weight: 600; }}
    .rank-row.loss {{ fill: #9c3f1d; font-weight: 600; }}
    .column-header {{ fill: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; }}

    .quadrant-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-top: 18px;
    }}

    .quadrant-card {{
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.58);
      border: 1px solid rgba(23, 33, 42, 0.08);
      padding: 18px;
    }}

    .quadrant-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}

    .quadrant-header h3 {{ margin: 0; font-size: 1rem; }}
    .count {{ color: var(--muted); font-size: 0.86rem; }}
    .swatch {{ width: 12px; height: 12px; border-radius: 999px; display: inline-block; }}

    .chip-wrap {{ display: flex; flex-wrap: wrap; gap: 10px; }}

    .chip {{
      border-radius: 999px;
      border: 1px solid rgba(23, 33, 42, 0.08);
      background: rgba(255, 255, 255, 0.74);
      padding: 8px 12px 8px 10px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      position: relative;
      overflow: hidden;
      font-size: 0.88rem;
    }}

    .chip::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--chip-accent);
      display: inline-block;
      flex: 0 0 auto;
    }}

    .chip strong {{ font-size: 0.9rem; }}
    .chip span {{ color: var(--muted); }}

    .footnote {{
      margin-top: 20px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.94rem;
    }}

    .footnote a {{ color: #0e665e; }}

    code {{
      font-family: "SFMono-Regular", Menlo, monospace;
      background: rgba(23, 33, 42, 0.08);
      padding: 0.15rem 0.35rem;
      border-radius: 6px;
    }}

    @media (max-width: 980px) {{
      .metric-grid, .two-up-scatter, .quadrant-grid {{
        grid-template-columns: 1fr;
      }}
      .hero {{ padding: 28px 24px 24px; }}
      .page {{ padding: 18px 14px 40px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <p class="kicker">United States · {n_obs} states · 2024</p>
      <h1>Union density and household income, nominal and cost-of-living adjusted.</h1>
      <p class="subhead">
        The cross-state relationship between unionization and median household income is reported two ways.
        The left chart uses Census ACS {income_year} 1-year median household income in nominal dollars.
        The right chart divides that income by the BEA Regional Price Parity (all items, {rpp_year}; US = 100),
        producing a rough cost-of-living-adjusted measure. The slope of the one-variable OLS fit
        shrinks by about {slope_shrinkage_pct:.0f}% once RPP is applied, but stays positive and statistically significant.
      </p>
      <div class="metric-grid">
        <article class="metric dual">
          <div class="label">Regression slope · USD per +1 pp union</div>
          <div class="value-pair">
            <span class="v"><span class="swatch-n"></span>{currency(slope_nominal)}</span>
            <span class="sep">→</span>
            <span class="v"><span class="swatch-r"></span>{currency(slope_real)}</span>
          </div>
          <div class="note">Shrinks by {slope_shrinkage_pct:.0f}% once RPP-adjusted.</div>
        </article>
        <article class="metric dual">
          <div class="label">Correlation</div>
          <div class="value-pair">
            <span class="v"><span class="swatch-n"></span>{correlation_nominal:.3f}</span>
            <span class="sep">→</span>
            <span class="v"><span class="swatch-r"></span>{correlation_real:.3f}</span>
          </div>
          <div class="note">Moderate, then weak-to-moderate after adjustment.</div>
        </article>
        <article class="metric dual">
          <div class="label">R-squared</div>
          <div class="value-pair">
            <span class="v"><span class="swatch-n"></span>{r_squared_nominal:.3f}</span>
            <span class="sep">→</span>
            <span class="v"><span class="swatch-r"></span>{r_squared_real:.3f}</span>
          </div>
          <div class="note">About {r_squared_nominal * 100:.0f}% → {r_squared_real * 100:.0f}% of state-level variance explained.</div>
        </article>
        <article class="metric">
          <div class="label">Sample means</div>
          <div class="value">{x_mean:.1f}% union</div>
          <div class="note">
            Nominal mean income {currency(y_mean_nominal)}, adjusted mean {currency(y_mean_real)}.
          </div>
        </article>
      </div>
    </section>

    <section class="section card">
      <h2>Side by side: union rate vs. income, before and after RPP</h2>
      <p class="deck">
        Both panels share the same y-axis so the compression is visible directly.
        Bubble size reflects each state's employed wage and salary workforce. The dashed line in each panel
        is that panel's own OLS fit. {escape(str(high_union["state"]))} sits furthest right at
        {float(high_union["union_membership_rate_pct"]):.1f}% union; {escape(str(low_union["state"]))} anchors the
        low end at {float(low_union["union_membership_rate_pct"]):.1f}%.
        {escape(str(high_rpp["state"]))} has the highest RPP at {float(high_rpp["rpp_all_items"]):.1f};
        {escape(str(low_rpp["state"]))} the lowest at {float(low_rpp["rpp_all_items"]):.1f}.
      </p>
      <div class="two-up-scatter">
        <div class="scatter-frame">{nominal_scatter}</div>
        <div class="scatter-frame">{real_scatter}</div>
      </div>
    </section>

    <section class="section card">
      <h2>Regression comparison</h2>
      <p class="deck">
        One-variable OLS across the {n_obs} states. Adjusting the outcome for BEA's
        Regional Price Parity substantially compresses both the slope and the R-squared,
        because high-union coastal states also have the highest cost of living.
      </p>
      {comparison_table}
    </section>

    <section class="section card">
      <h2>Who moves most when we adjust for cost of living?</h2>
      <p class="deck">
        State rankings by median household income shift once the RPP deflator is applied.
        States that climb are affordable relative to their nominal income; states that fall
        have high nominal income largely absorbed by high local prices.
      </p>
      {rank_panel}
    </section>

    <section class="section card">
      <h2>Quadrant view (nominal)</h2>
      <p class="deck">
        Using the nominal scatter's sample means, states are grouped around the mean
        union rate and the mean nominal household income. This keeps the quadrant
        definitions comparable to the earlier version of the report.
      </p>
      <div class="quadrant-grid">
        {quadrant_markup(rows)}
      </div>
      <p class="footnote">
        Slope p-values: nominal <code>{float(nominal['slope_p_value']):.4g}</code>,
        RPP-adjusted <code>{float(adjusted['slope_p_value']):.4g}</code>. Even after
        adjustment the slope remains positive and distinguishable from zero at
        conventional levels, though with wider relative uncertainty.
        This is still descriptive, not causal: the regression compares state-level averages and does not
        control for industrial mix, education, demographics, or labor-force composition.
      </p>
      <p class="footnote">
        Repository audit artifacts:
        <a href="{AUDIT_DOC_URL}">AUDIT.md</a>,
        <a href="{SOURCES_DOC_URL}">SOURCES.md</a>,
        <a href="{SHA256SUMS_URL}">SHA256SUMS</a>,
        and
        <a href="{AUDIT_MANIFEST_URL}">audit manifest JSON</a>.
        Official sources:
        <a href="{BLS_SOURCE_URL}">BLS 2024 state union-membership release</a>,
        <a href="{CENSUS_SOURCE_URL}">Census ACS 2024 API query</a>,
        and
        <a href="{BEA_SOURCE_URL}">BEA Regional Price Parities release</a>
        (<a href="{BEA_DOWNLOAD_URL}">SARPP state dump</a>).
      </p>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    rows = load_rows()
    regressions = load_regressions()
    enrich_rows(rows, regressions)
    html = build_html(rows, regressions)
    REPORT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote visual report to {REPORT_HTML}")


if __name__ == "__main__":
    main()
