#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_common import (
    classify_document_role,
    deduplicate_exam_items,
    detect_quality_flags,
    load_bank,
    load_manifest,
    parse_answer_entries,
    parse_question_segments,
    save_bank,
    save_manifest,
    workspace_paths,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse extracted source text into exam items and source segments.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    manifest = load_manifest(paths)
    bank = load_bank(paths)

    source_documents: list[dict] = []
    source_segments: list[dict] = []
    exam_items: list[dict] = []

    for record in manifest.get("source_documents", []):
        text_path = record.get("text_path")
        text = ""
        if text_path:
            resolved = paths.root / text_path
            if resolved.exists():
                text = resolved.read_text(encoding="utf-8")

        document_role = classify_document_role(text) if text else "unknown"
        quality_flags = detect_quality_flags(text, record.get("extractor", ""), record.get("notes", [])) if text else ["no_text_extracted"]
        if document_role == "answer_sheet":
            quality_flags = [flag for flag in quality_flags if flag != "very_short_text"]

        enriched_record = dict(record)
        enriched_record["document_role"] = document_role
        enriched_record["quality_flags"] = quality_flags
        enriched_record["segments"] = []

        if text:
            if document_role == "answer_sheet":
                parsed_segments = parse_answer_entries(text, record["id"])
                source_segments.extend(parsed_segments)
                enriched_record["segments"].extend(segment["id"] for segment in parsed_segments)
            elif document_role == "question_sheet":
                parsed_segments, parsed_items = parse_question_segments(text, record["id"])
                source_segments.extend(parsed_segments)
                exam_items.extend(parsed_items)
                enriched_record["segments"].extend(segment["id"] for segment in parsed_segments)
            else:
                # Keep reference and syllabus documents in provenance even if they do not emit items.
                enriched_record.setdefault("notes", [])
        else:
            enriched_record.setdefault("notes", [])
            enriched_record["notes"] = list(enriched_record["notes"]) + ["No extracted text available for parsing."]

        source_documents.append(enriched_record)

    deduped_items = deduplicate_exam_items(exam_items)

    bank["source_documents"] = source_documents
    bank["source_segments"] = source_segments
    bank["exam_items"] = deduped_items
    bank["answer_resolutions"] = []
    bank["explanation_bundles"] = []
    bank["item_mandalarts"] = []
    bank["distractor_mandalarts"] = []
    bank["summary_units"] = []
    bank["mock_exam_sets"] = []
    save_bank(paths, bank)

    manifest["source_documents"] = source_documents
    save_manifest(paths, manifest)

    summary = {
        "workspace": str(paths.root),
        "source_documents": len(source_documents),
        "source_segments": len(source_segments),
        "exam_items": len(deduped_items),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
