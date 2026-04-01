#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from pipeline_common import (
    build_item_fingerprint,
    choice_label_to_text,
    find_item_answer,
    infer_topic,
    load_authoritative_rules,
    load_bank,
    load_topic_taxonomy,
    match_authoritative_rule,
    save_bank,
    workspace_paths,
)


def build_answer_resolution(
    item: dict[str, Any],
    source_documents_by_id: dict[str, dict[str, Any]],
    answer_segments: list[dict[str, Any]],
    taxonomy: dict[str, Any],
    rules: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    official_answer, conflict_notes = find_item_answer(item, answer_segments, source_documents_by_id)
    topic_major, topic_minor, matched_topic_keywords = infer_topic(
        " ".join([item.get("stem", "")] + [choice.get("text", "") for choice in item.get("choices", [])]),
        taxonomy,
    )
    matched_rule_result = match_authoritative_rule(item, rules)
    matched_rule = matched_rule_result["rule"] if matched_rule_result else None
    predicted_answer = matched_rule_result["best_choice"]["label"] if matched_rule_result else None
    external_validation_status = "not_found"
    matched_rule_ids: list[str] = []
    conflict_note = None

    if matched_rule:
        matched_rule_ids.append(matched_rule.get("id", ""))
        if topic_major == "unknown":
            topic_major = matched_rule.get("topic_major", topic_major)
        if topic_minor == "unknown":
            topic_minor = matched_rule.get("topic_minor", topic_minor)
        if official_answer:
            external_validation_status = "matched" if predicted_answer == official_answer else "conflicted"
            if predicted_answer != official_answer:
                conflict_note = (
                    f"Official answer {official_answer} conflicts with authoritative rule prediction {predicted_answer}."
                )
        else:
            external_validation_status = "matched"

    if conflict_notes and not conflict_note:
        conflict_note = " ".join(conflict_notes)

    final_answer = official_answer or predicted_answer
    confidence = 0.0
    if official_answer and external_validation_status == "matched":
        confidence = 0.98
    elif official_answer and external_validation_status == "not_found":
        confidence = 0.93
    elif official_answer and external_validation_status == "conflicted":
        confidence = 0.55
    elif predicted_answer:
        confidence = 0.84

    quality_flags = list(item.get("quality_flags", []))
    review_status = "approved"
    status = "approved"
    review_reasons: list[str] = []

    if quality_flags:
        review_status = "needs_review"
        status = "needs_review"
        review_reasons.append("source quality flags present")
    if not official_answer:
        review_status = "needs_review"
        status = "needs_review"
        review_reasons.append("official answer missing")
    if external_validation_status == "not_found":
        review_status = "needs_review"
        status = "needs_review"
        review_reasons.append("authoritative rule not found")
    if external_validation_status == "conflicted" or conflict_note:
        review_status = "conflict"
        status = "conflict"
        review_reasons.append("authoritative conflict detected")
    if final_answer is None:
        review_status = "needs_review"
        status = "needs_review"
        review_reasons.append("no answer could be resolved")

    resolution = {
        "id": f"answer-{item['id']}",
        "item_id": item["id"],
        "official_answer": official_answer,
        "predicted_answer": predicted_answer,
        "final_answer": final_answer,
        "confidence": confidence,
        "topic_major": topic_major,
        "topic_minor": topic_minor,
        "external_validation_status": external_validation_status,
        "matched_rule_ids": matched_rule_ids,
        "matched_topic_keywords": matched_topic_keywords,
        "conflict_note": conflict_note,
        "review_status": review_status,
        "review_reasons": review_reasons,
        "source_refs": item.get("source_refs", []),
    }

    updated_item = dict(item)
    updated_item["official_answer"] = official_answer
    updated_item["predicted_answer"] = predicted_answer
    updated_item["confidence"] = confidence
    updated_item["topic_major"] = topic_major
    updated_item["topic_minor"] = topic_minor
    updated_item["status"] = status
    updated_item["review_status"] = review_status
    updated_item["fingerprint"] = updated_item.get("fingerprint") or build_item_fingerprint(
        updated_item.get("stem", ""),
        updated_item.get("choices", []),
    )
    updated_item["validation_summary"] = {
        "official_answer_found": official_answer is not None,
        "external_validation_status": external_validation_status,
        "matched_rule_ids": matched_rule_ids,
        "matched_topic_keywords": matched_topic_keywords,
        "conflict_note": conflict_note,
        "review_reasons": review_reasons,
    }
    if final_answer:
        updated_item["resolved_answer"] = {
            "label": final_answer,
            "text": choice_label_to_text(updated_item, final_answer),
        }
    return resolution, updated_item


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve official or predicted answers for parsed exam items.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    taxonomy = load_topic_taxonomy()
    rules = load_authoritative_rules().get("rules", [])

    source_documents_by_id = {doc["id"]: doc for doc in bank.get("source_documents", [])}
    answer_segments = [
        segment for segment in bank.get("source_segments", [])
        if segment.get("segment_type") == "answer_candidate"
    ]

    resolutions: list[dict[str, Any]] = []
    updated_items: list[dict[str, Any]] = []
    for item in bank.get("exam_items", []):
        resolution, updated_item = build_answer_resolution(
            item,
            source_documents_by_id,
            answer_segments,
            taxonomy,
            rules,
        )
        resolutions.append(resolution)
        updated_items.append(updated_item)

    bank["exam_items"] = updated_items
    bank["answer_resolutions"] = resolutions
    save_bank(paths, bank)

    summary = {
        "workspace": str(paths.root),
        "exam_items": len(updated_items),
        "resolved_with_official_answer": sum(1 for item in updated_items if item.get("official_answer")),
        "resolved_with_prediction": sum(1 for item in updated_items if item.get("predicted_answer")),
        "conflicts": sum(1 for item in updated_items if item.get("review_status") == "conflict"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
