#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_json(path: Path, payload: object) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_markdown(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the fire-ems exam workspace in the target directory.")
    parser.add_argument("workspace", nargs="?", default=".", help="Target workspace directory. Defaults to current directory.")
    args = parser.parse_args()

    root = Path(args.workspace).expanduser().resolve()
    for relative in ["sources", "sources/extracted", "bank", "outputs", "review"]:
        (root / relative).mkdir(parents=True, exist_ok=True)

    ensure_json(
        root / "sources" / "intake-manifest.json",
        {
            "version": 1,
            "generated_at": utc_now(),
            "source_documents": [],
        },
    )

    ensure_json(
        root / "bank" / "exam-bank.json",
        {
            "version": 1,
            "generated_at": utc_now(),
            "source_documents": [],
            "exam_items": [],
            "explanation_bundles": [],
            "distractor_mandalarts": [],
            "summary_units": [],
            "mock_exam_sets": [],
        },
    )

    ensure_json(root / "review" / "review-queue.json", [])
    ensure_markdown(
        root / "review" / "review-queue.md",
        "# Review Queue\n\n아직 검수 대기 항목이 없습니다.\n",
    )

    print(f"Initialized fire-ems workspace at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
