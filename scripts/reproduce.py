#!/usr/bin/env python3
"""Run the full reproducible pipeline.

This wrapper exists so auditors only need a single command:

    python3 scripts/reproduce.py

It rebuilds:
- the audit artifacts and checksums
- the merged dataset
- the regression summaries
- the standalone HTML visual report
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def clean_git_head() -> str | None:
    """Return the current commit hash when the worktree is clean."""

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout.strip():
        return None

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return head.stdout.strip()


def run(script_name: str, extra_env: dict[str, str] | None = None) -> None:
    """Execute another repository script with the current Python interpreter."""

    script_path = ROOT / "scripts" / script_name
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    subprocess.run([sys.executable, str(script_path)], check=True, env=env)


def main() -> None:
    """Rebuild every generated artifact in order."""

    extra_env: dict[str, str] = {}
    clean_head = clean_git_head()
    if clean_head:
        extra_env["REPO_REF"] = clean_head

    run("collect_and_regress.py", extra_env=extra_env)
    run("build_visual_report.py", extra_env=extra_env)
    run("build_audit_artifacts.py", extra_env=extra_env)


if __name__ == "__main__":
    main()
