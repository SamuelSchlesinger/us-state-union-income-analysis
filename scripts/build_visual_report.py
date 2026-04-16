#!/usr/bin/env python3
"""Build a self-contained HTML report from the processed dataset.

This script does not collect or transform source data. It reads:
- `data/us_states_union_income_2024.csv`
- `results/union_income_regression_2024.json`

and turns them into `results/union_income_visual_report.html`.

The numerical processing happens in `collect_and_regress.py`. This file is only
responsible for presentation.
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "us_states_union_income_2024.csv"
REGRESSION_JSON = ROOT / "results" / "union_income_regression_2024.json"
REPORT_HTML = ROOT / "results" / "union_income_visual_report.html"

STATE_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
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
                    "median_household_income_usd": int(row["median_household_income_usd"]),
                }
            )
    return rows


def load_regression() -> dict[str, float | int | str | list[float]]:
    return json.loads(REGRESSION_JSON.read_text(encoding="utf-8"))


def scale(
    value: float,
    domain_min: float,
    domain_max: float,
    range_min: float,
    range_max: float,
) -> float:
    if domain_max == domain_min:
        return (range_min + range_max) / 2
    ratio = (value - domain_min) / (domain_max - domain_min)
    return range_min + ratio * (range_max - range_min)


def currency(value: float) -> str:
    return f"${value:,.0f}"


def compact_currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if abs(value) >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.1f}M"
    if abs(value) >= 1000:
        return f"{sign}${amount / 1000:.1f}k"
    return f"{sign}{currency(amount)}"


def state_chip(row: dict[str, float | int | str]) -> str:
    state = escape(str(row["state"]))
    union = f"{float(row['union_membership_rate_pct']):.1f}%"
    income = compact_currency(float(row["median_household_income_usd"]))
    color = QUADRANT_COLORS[str(row["quadrant"])]
    return (
        '<span class="chip" style="--chip-accent: '
        + color
        + '">'
        + f"<strong>{state}</strong><span>{union} · {income}</span>"
        + "</span>"
    )


def enrich_rows(
    rows: list[dict[str, float | int | str]],
    regression: dict[str, float | int | str | list[float]],
) -> list[dict[str, float | int | str]]:
    x_mean = float(regression["x_mean"])
    y_mean = float(regression["y_mean"])
    slope = float(regression["slope"])
    intercept = float(regression["intercept"])

    for row in rows:
        x = float(row["union_membership_rate_pct"])
        y = float(row["median_household_income_usd"])
        predicted = intercept + slope * x
        residual = y - predicted

        if x >= x_mean and y >= y_mean:
            quadrant = "high_union_high_income"
        elif x >= x_mean and y < y_mean:
            quadrant = "high_union_low_income"
        elif x < x_mean and y >= y_mean:
            quadrant = "low_union_high_income"
        else:
            quadrant = "low_union_low_income"

        row["predicted_income_usd"] = predicted
        row["residual_income_usd"] = residual
        row["quadrant"] = quadrant
        row["abbr"] = STATE_ABBR[str(row["state"])]

    return rows


def choose_labels(rows: list[dict[str, float | int | str]]) -> set[str]:
    selected: set[str] = set()
    selectors = [
        sorted(rows, key=lambda row: float(row["union_membership_rate_pct"]), reverse=True)[:4],
        sorted(rows, key=lambda row: float(row["union_membership_rate_pct"]))[:4],
        sorted(rows, key=lambda row: float(row["median_household_income_usd"]), reverse=True)[:4],
        sorted(rows, key=lambda row: float(row["median_household_income_usd"]))[:4],
        sorted(rows, key=lambda row: float(row["residual_income_usd"]), reverse=True)[:3],
        sorted(rows, key=lambda row: float(row["residual_income_usd"]))[:3],
    ]
    for group in selectors:
        for row in group:
            selected.add(str(row["state"]))
    selected.update({"California", "Texas", "New York"})
    return selected


def scatter_svg(
    rows: list[dict[str, float | int | str]],
    regression: dict[str, float | int | str | list[float]],
) -> str:
    width = 1060
    height = 620
    margin_left = 90
    margin_right = 36
    margin_top = 40
    margin_bottom = 72

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    x_values = [float(row["union_membership_rate_pct"]) for row in rows]
    y_values = [float(row["median_household_income_usd"]) for row in rows]

    x_min = min(x_values) - 1.0
    x_max = max(x_values) + 1.5
    y_min = 55_000
    y_max = 110_000

    x_mean = float(regression["x_mean"])
    y_mean = float(regression["y_mean"])
    slope = float(regression["slope"])
    intercept = float(regression["intercept"])

    selected_labels = choose_labels(rows)

    def sx(value: float) -> float:
        return scale(value, x_min, x_max, margin_left, width - margin_right)

    def sy(value: float) -> float:
        return scale(value, y_min, y_max, height - margin_bottom, margin_top)

    def radius(workers: int) -> float:
        return scale(workers ** 0.5, 500, 4100, 6, 24)

    line_x1 = x_min
    line_x2 = x_max
    line_y1 = intercept + slope * line_x1
    line_y2 = intercept + slope * line_x2

    x_ticks = [2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25]
    y_ticks = [60_000, 70_000, 80_000, 90_000, 100_000, 110_000]

    svg: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" '
        'aria-label="Scatterplot of state unionization and median income">'
    ]

    quadrants = [
        (x_min, y_mean, x_mean, y_max, "#d4f1ea"),
        (x_mean, y_mean, x_max, y_max, "#ffe4d9"),
        (x_min, y_min, x_mean, y_mean, "#dde8ef"),
        (x_mean, y_min, x_max, y_mean, "#ffe9d5"),
    ]
    for x0, y0, x1, y1, fill in quadrants:
        svg.append(
            '<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" opacity="0.35"/>'.format(
                x=f"{sx(x0):.1f}",
                y=f"{sy(y1):.1f}",
                w=f"{sx(x1) - sx(x0):.1f}",
                h=f"{sy(y0) - sy(y1):.1f}",
                fill=fill,
            )
        )

    for x_tick in x_ticks:
        x_pos = sx(x_tick)
        svg.append(
            f'<line x1="{x_pos:.1f}" y1="{margin_top}" x2="{x_pos:.1f}" '
            f'y2="{height - margin_bottom}" class="gridline"/>'
        )
        svg.append(
            f'<text x="{x_pos:.1f}" y="{height - margin_bottom + 28}" class="axis-label" '
            f'text-anchor="middle">{x_tick:.1f}%</text>'
        )

    for y_tick in y_ticks:
        y_pos = sy(y_tick)
        svg.append(
            f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" y2="{y_pos:.1f}" class="gridline"/>'
        )
        svg.append(
            f'<text x="{margin_left - 14}" y="{y_pos + 5:.1f}" class="axis-label" text-anchor="end">'
            f"{int(y_tick / 1000)}k</text>"
        )

    svg.append(
        f'<line x1="{margin_left}" y1="{sy(y_mean):.1f}" x2="{width - margin_right}" y2="{sy(y_mean):.1f}" class="mean-line"/>'
    )
    svg.append(
        f'<line x1="{sx(x_mean):.1f}" y1="{margin_top}" x2="{sx(x_mean):.1f}" y2="{height - margin_bottom}" class="mean-line"/>'
    )
    svg.append(
        f'<text x="{width - margin_right - 4}" y="{sy(y_mean) - 10:.1f}" class="annotation" text-anchor="end">'
        f"mean income {currency(y_mean)}</text>"
    )
    svg.append(
        f'<text x="{sx(x_mean) + 8:.1f}" y="{margin_top + 18}" class="annotation">'
        f"mean union {x_mean:.1f}%</text>"
    )

    svg.append(
        f'<line x1="{sx(line_x1):.1f}" y1="{sy(line_y1):.1f}" x2="{sx(line_x2):.1f}" y2="{sy(line_y2):.1f}" class="trend-line"/>'
    )

    for row in rows:
        x = float(row["union_membership_rate_pct"])
        y = float(row["median_household_income_usd"])
        bubble_radius = radius(int(row["employed_wage_salary_workers"]))
        fill = QUADRANT_COLORS[str(row["quadrant"])]
        title = (
            f"{row['state']}: {x:.1f}% union, {currency(y)}, "
            f"{int(row['employed_wage_salary_workers']):,} wage and salary workers"
        )
        svg.append(
            f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="{bubble_radius:.1f}" '
            f'fill="{fill}" class="bubble"><title>{escape(title)}</title></circle>'
        )

    for row in rows:
        if str(row["state"]) not in selected_labels:
            continue
        x = sx(float(row["union_membership_rate_pct"]))
        y = sy(float(row["median_household_income_usd"]))
        x_offset = 10 if float(row["union_membership_rate_pct"]) < x_mean else -10
        anchor = "start" if x_offset > 0 else "end"
        y_offset = -12 if float(row["median_household_income_usd"]) > y_mean else 18
        svg.append(
            f'<text x="{x + x_offset:.1f}" y="{y + y_offset:.1f}" class="point-label" text-anchor="{anchor}">'
            f"{escape(str(row['abbr']))}</text>"
        )

    svg.append(
        f'<text x="{width / 2:.1f}" y="{height - 18}" class="axis-title" text-anchor="middle">'
        "Union membership rate of employed wage and salary workers</text>"
    )
    svg.append(
        f'<text x="24" y="{height / 2:.1f}" class="axis-title" text-anchor="middle" '
        f'transform="rotate(-90 24 {height / 2:.1f})">Median household income (USD)</text>'
    )
    svg.append("</svg>")
    return "\n".join(svg)


def residual_panel_svg(
    rows: list[dict[str, float | int | str]],
    positive: bool,
) -> str:
    ranked = sorted(rows, key=lambda row: float(row["residual_income_usd"]), reverse=positive)
    selected = ranked[:8]
    values = [abs(float(row["residual_income_usd"])) for row in selected]

    width = 500
    row_height = 38
    height = 70 + len(selected) * row_height
    left = 130
    right = 32
    top = 26
    max_value = max(values) * 1.12
    color = "#17887b" if positive else "#d9643b"
    title = "Above the line" if positive else "Below the line"
    subtitle = (
        "Higher income than the simple model predicts"
        if positive
        else "Lower income than the simple model predicts"
    )

    svg = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg small" role="img" aria-label="{title} residual chart">',
        f'<text x="{left}" y="20" class="panel-title">{title}</text>',
        f'<text x="{left}" y="40" class="panel-subtitle">{subtitle}</text>',
    ]

    for idx, row in enumerate(selected):
        residual = float(row["residual_income_usd"])
        bar_width = scale(abs(residual), 0, max_value, 0, width - left - right)
        y = top + 20 + idx * row_height
        svg.append(
            f'<line x1="{left}" y1="{y + 8:.1f}" x2="{width - right}" y2="{y + 8:.1f}" class="mini-grid"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 13:.1f}" class="mini-label" text-anchor="end">{escape(str(row["state"]))}</text>'
        )
        svg.append(
            f'<rect x="{left}" y="{y - 2:.1f}" width="{bar_width:.1f}" height="18" rx="9" fill="{color}" opacity="0.9"/>'
        )
        svg.append(
            f'<text x="{left + bar_width + 10:.1f}" y="{y + 13:.1f}" class="mini-value">{compact_currency(residual)}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


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
                -float(row["median_household_income_usd"]),
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


def build_html(
    rows: list[dict[str, float | int | str]],
    regression: dict[str, float | int | str | list[float]],
) -> str:
    n_obs = int(regression["n_obs"])
    slope = float(regression["slope"])
    correlation = float(regression["correlation"])
    r_squared = float(regression["r_squared"])
    p_value = float(regression["slope_p_value"])
    x_mean = float(regression["x_mean"])
    y_mean = float(regression["y_mean"])

    high_union = max(rows, key=lambda row: float(row["union_membership_rate_pct"]))
    low_union = min(rows, key=lambda row: float(row["union_membership_rate_pct"]))
    high_income = max(rows, key=lambda row: float(row["median_household_income_usd"]))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Unionization and Income by State, 2024</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f6f0e6;
      --paper: rgba(255, 250, 243, 0.86);
      --ink: #17212a;
      --muted: #5b6670;
      --grid: rgba(23, 33, 42, 0.12);
      --line: rgba(23, 33, 42, 0.3);
      --hero: linear-gradient(135deg, #11212d 0%, #213f4a 48%, #d9643b 100%);
      --shadow: 0 18px 50px rgba(16, 23, 31, 0.12);
      --radius: 28px;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
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
      font-family: "Instrument Serif", Georgia, serif;
      font-size: clamp(2.8rem, 5.4vw, 5rem);
      line-height: 0.94;
      max-width: 10.5ch;
      font-weight: 400;
    }}

    .subhead {{
      max-width: 54rem;
      font-size: 1rem;
      line-height: 1.6;
      color: rgba(255, 248, 241, 0.88);
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
      padding: 16px 18px;
      min-height: 108px;
    }}

    .metric .label {{
      font-size: 0.76rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      opacity: 0.7;
    }}

    .metric .value {{
      margin-top: 8px;
      font-size: 1.7rem;
      font-weight: 700;
    }}

    .metric .note {{
      margin-top: 6px;
      font-size: 0.93rem;
      line-height: 1.45;
      color: rgba(255, 248, 241, 0.8);
    }}

    .section {{
      margin-top: 26px;
    }}

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

    .two-up {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
      margin-top: 22px;
    }}

    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
      margin-top: 14px;
    }}

    .chart-svg.small {{
      margin-top: 0;
    }}

    .gridline {{
      stroke: var(--grid);
      stroke-width: 1;
    }}

    .mean-line {{
      stroke: rgba(23, 33, 42, 0.45);
      stroke-width: 1.5;
      stroke-dasharray: 6 6;
    }}

    .trend-line {{
      stroke: #17212a;
      stroke-width: 3;
      stroke-dasharray: 12 9;
      opacity: 0.9;
    }}

    .bubble {{
      stroke: rgba(255, 255, 255, 0.75);
      stroke-width: 1.7;
      opacity: 0.9;
    }}

    .axis-label {{
      fill: var(--muted);
      font-size: 13px;
    }}

    .axis-title {{
      fill: var(--ink);
      font-size: 15px;
      font-weight: 700;
    }}

    .annotation {{
      fill: var(--muted);
      font-size: 12px;
      font-weight: 500;
    }}

    .point-label {{
      fill: var(--ink);
      font-size: 12px;
      font-weight: 700;
      paint-order: stroke;
      stroke: rgba(255, 250, 243, 0.95);
      stroke-width: 3px;
      stroke-linejoin: round;
    }}

    .panel-title {{
      fill: var(--ink);
      font-size: 18px;
      font-weight: 700;
    }}

    .panel-subtitle {{
      fill: var(--muted);
      font-size: 12px;
    }}

    .mini-grid {{
      stroke: var(--grid);
      stroke-width: 1;
    }}

    .mini-label {{
      fill: var(--ink);
      font-size: 13px;
    }}

    .mini-value {{
      fill: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}

    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
      margin-top: 16px;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .legend span {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}

    .dot {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }}

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

    .quadrant-header h3 {{
      margin: 0;
      font-size: 1rem;
    }}

    .count {{
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .swatch {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }}

    .chip-wrap {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

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

    .chip strong {{
      font-size: 0.9rem;
    }}

    .chip span {{
      color: var(--muted);
    }}

    .footnote {{
      margin-top: 20px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.94rem;
    }}

    code {{
      font-family: "SFMono-Regular", Menlo, monospace;
      background: rgba(23, 33, 42, 0.08);
      padding: 0.15rem 0.35rem;
      border-radius: 6px;
    }}

    @media (max-width: 980px) {{
      .metric-grid,
      .two-up,
      .quadrant-grid {{
        grid-template-columns: 1fr;
      }}

      .hero {{
        padding: 28px 24px 24px;
      }}

      .page {{
        padding: 18px 14px 40px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <p class="kicker">United States · 50 states · 2024</p>
      <h1>Union density and household income tend to rise together.</h1>
      <p class="subhead">
        This report uses the BLS state union membership rate and the Census ACS 1-year median household income.
        Bubble size in the main chart reflects each state's employed wage and salary workforce. The line is the
        simple OLS fit across all 50 states.
      </p>
      <div class="metric-grid">
        <article class="metric">
          <div class="label">Regression slope</div>
          <div class="value">{currency(slope)}</div>
          <div class="note">Associated with each +1 percentage point in state union membership.</div>
        </article>
        <article class="metric">
          <div class="label">Correlation</div>
          <div class="value">{correlation:.3f}</div>
          <div class="note">A moderate positive cross-state relationship.</div>
        </article>
        <article class="metric">
          <div class="label">R-squared</div>
          <div class="value">{r_squared:.3f}</div>
          <div class="note">About {r_squared * 100:.1f}% of the state income variation is explained by this one-variable model.</div>
        </article>
        <article class="metric">
          <div class="label">Sample</div>
          <div class="value">{n_obs} states</div>
          <div class="note">Means: {x_mean:.1f}% union and {currency(y_mean)} median household income.</div>
        </article>
      </div>
    </section>

    <section class="section card">
      <h2>Bubble scatter: union membership rate vs. median household income</h2>
      <p class="deck">
        Hawaii sits furthest to the right at {float(high_union["union_membership_rate_pct"]):.1f}% union membership.
        North Carolina anchors the far-left edge at {float(low_union["union_membership_rate_pct"]):.1f}%.
        The District of Columbia is excluded, so New Jersey holds the highest state median household income in this
        50-state file at {currency(float(high_income["median_household_income_usd"]))}.
      </p>
      {scatter_svg(rows, regression)}
      <div class="legend">
        <span><i class="dot" style="background:#ff6b4a"></i> high union / high income</span>
        <span><i class="dot" style="background:#d4702f"></i> high union / lower income</span>
        <span><i class="dot" style="background:#17887b"></i> lower union / high income</span>
        <span><i class="dot" style="background:#456173"></i> lower union / lower income</span>
        <span><i class="dot" style="background:#17212a"></i> dashed line = OLS fit</span>
      </div>
    </section>

    <section class="section two-up">
      <article class="card">
        {residual_panel_svg(sorted(rows, key=lambda row: float(row["residual_income_usd"]), reverse=True), positive=True)}
      </article>
      <article class="card">
        {residual_panel_svg(sorted(rows, key=lambda row: float(row["residual_income_usd"])), positive=False)}
      </article>
    </section>

    <section class="section card">
      <h2>Quadrant view</h2>
      <p class="deck">
        States are grouped around the two sample means. This is a quick way to see who clusters in the upper-right,
        who stays affluent despite lower union density, and who remains in the lower-left corner of both measures.
      </p>
      <div class="quadrant-grid">
        {quadrant_markup(rows)}
      </div>
      <p class="footnote">
        Regression p-value for the slope: <code>{p_value:.6f}</code>. This is still descriptive, not causal:
        the chart compares state-level averages and does not control for cost of living, industrial mix, education,
        housing markets, or regional composition.
      </p>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    rows = load_rows()
    regression = load_regression()
    enrich_rows(rows, regression)
    html = build_html(rows, regression)
    REPORT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote visual report to {REPORT_HTML}")


if __name__ == "__main__":
    main()
