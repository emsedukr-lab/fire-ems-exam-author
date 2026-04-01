#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


STEPS = [
    "parse_exam_items.py",
    "resolve_answers.py",
    "build_explanations.py",
    "build_mandalart.py",
    "build_review_queue.py",
    "render_past_analysis.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fire-ems question analysis pipeline.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    workspace = Path(args.workspace).expanduser().resolve()
    for step in STEPS:
        command = [sys.executable, str(script_dir / step), "--workspace", str(workspace)]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
