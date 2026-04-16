#!/usr/bin/env python3
"""Run the full reproducible pipeline.

This wrapper exists so auditors only need a single command:

    python3 scripts/reproduce.py

It rebuilds:
- the merged dataset
- the regression summaries
- the standalone HTML visual report
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script_name: str) -> None:
    """Execute another repository script with the current Python interpreter."""

    script_path = ROOT / "scripts" / script_name
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    """Rebuild every generated artifact in order."""

    run("collect_and_regress.py")
    run("build_visual_report.py")


if __name__ == "__main__":
    main()
