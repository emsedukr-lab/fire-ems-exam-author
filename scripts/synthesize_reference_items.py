#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from typing import Any

from pipeline_common import (
    build_item_fingerprint,
    load_authoritative_rules,
    load_bank,
    load_manifest,
    normalize_text,
    save_bank,
    save_manifest,
    score_rule_relevance,
    workspace_paths,
)


RULE_QUESTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "scene-safety-first": {
        "stem": "응급처치자가 환자에게 접근하기 전에 가장 먼저 해야 할 것은?",
        "correct": "현장과 구조자의 안전을 먼저 확인한다.",
        "distractors": [
            "환자에게 바로 접근해 상태를 확인한다.",
            "곧바로 환자를 이동시킨다.",
            "즉시 가슴압박을 시작한다.",
        ],
    },
    "adult-cpr-30-2": {
        "stem": "성인 기본 심폐소생술에서 가슴압박과 인공호흡의 비율로 옳은 것은?",
        "correct": "가슴압박 30회와 인공호흡 2회의 비율을 적용한다.",
        "distractors": [
            "15:2 비율을 적용한다.",
            "10:1 비율을 적용한다.",
            "5:1 비율을 적용한다.",
        ],
    },
    "adult-cpr-rate": {
        "stem": "성인 고품질 심폐소생술의 가슴압박 속도로 가장 적절한 것은?",
        "correct": "분당 100회에서 120회 범위를 유지한다.",
        "distractors": [
            "분당 80회 정도로 유지한다.",
            "분당 60회 정도로 유지한다.",
            "분당 140회 이상으로 유지한다.",
        ],
    },
    "adult-cpr-depth": {
        "stem": "성인 가슴압박 깊이 기준으로 가장 적절한 것은?",
        "correct": "최소 5cm 수준으로 압박하고 과도한 깊이는 피한다.",
        "distractors": [
            "2cm 정도만 압박한다.",
            "3cm 정도만 압박한다.",
            "7cm 이상 깊게 압박한다.",
        ],
    },
    "responsiveness-breathing-check": {
        "stem": "심정지 여부를 처음 판단할 때 가장 먼저 확인해야 할 것은?",
        "correct": "반응과 호흡 상태를 즉시 확인한다.",
        "distractors": [
            "혈압을 먼저 측정한다.",
            "체온을 먼저 측정한다.",
            "맥박만 먼저 확인한다.",
        ],
    },
    "aed-early-use": {
        "stem": "심정지 환자에게 AED 사용에 대한 설명으로 가장 적절한 것은?",
        "correct": "가능한 한 빨리 AED를 적용해 조기 제세동을 준비한다.",
        "distractors": [
            "10분 정도 지난 뒤 사용한다.",
            "의식이 회복된 뒤에만 사용한다.",
            "이송이 끝난 뒤 사용한다.",
        ],
    },
    "bleeding-direct-pressure": {
        "stem": "외부 출혈 환자의 기본 처치로 가장 적절한 것은?",
        "correct": "직접 압박으로 지혈을 시작한다.",
        "distractors": [
            "상처를 문지르며 세척만 한다.",
            "지혈 없이 상태만 관찰한다.",
            "압박 없이 다른 처치만 먼저 한다.",
        ],
    },
    "burn-cooling": {
        "stem": "열화상 초기 처치로 가장 적절한 것은?",
        "correct": "흐르는 물로 화상 부위를 냉각한다.",
        "distractors": [
            "얼음을 피부에 직접 댄다.",
            "연고부터 먼저 바른다.",
            "치약이나 기름을 먼저 바른다.",
        ],
    },
    "anaphylaxis-epinephrine": {
        "stem": "아나필락시스 환자 처치의 핵심으로 가장 적절한 것은?",
        "correct": "에피네프린 투여를 우선 고려한다.",
        "distractors": [
            "항생제를 먼저 투여한다.",
            "진통제를 먼저 투여한다.",
            "증상 변화를 지켜본다.",
        ],
    },
    "stroke-fast": {
        "stem": "뇌졸중 의심 환자 평가에서 가장 중요한 초기 접근은?",
        "correct": "FAST와 같은 신경학적 이상을 빠르게 확인하고 시간을 기록한다.",
        "distractors": [
            "심전도만 우선 확인한다.",
            "혈압만 측정하고 경과를 본다.",
            "휴식 후 상태를 관찰한다.",
        ],
    },
    "legal-duty-records": {
        "stem": "응급의료 종사자의 법적 책임에 대한 설명으로 가장 적절한 것은?",
        "correct": "관련 법령과 기록 의무를 준수해야 한다.",
        "distractors": [
            "기록은 생략해도 무방하다.",
            "통신과 보고는 필수가 아니다.",
            "구두 보고만 하면 충분하다.",
        ],
    },
}


def detect_requested_item_count(text: str) -> int | None:
    matches = re.findall(r"(\d{1,2})\s*문항", text)
    if not matches:
        return None
    requested = max(int(match) for match in matches)
    return min(max(requested, 1), 10)


def iter_reference_passages(text: str) -> list[str]:
    passages: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"\n\s*\n", text):
        normalized = normalize_text(chunk)
        if len(normalized) >= 18 and normalized not in seen:
            passages.append(normalized)
            seen.add(normalized)

    for line in text.splitlines():
        normalized = normalize_text(line.lstrip("-*•0123456789. )("))
        if len(normalized) >= 18 and normalized not in seen:
            passages.append(normalized)
            seen.add(normalized)
    return passages


def build_generic_template(rule: dict[str, Any]) -> dict[str, Any]:
    negatives = list(rule.get("negative_patterns", []))
    while len(negatives) < 3:
        negatives.append(f"{rule.get('topic_minor', '해당 주제')}와 직접 관련이 없는 처치를 우선한다.")
    return {
        "stem": f"다음 중 {rule.get('topic_minor', '응급처치')}에 대한 설명으로 가장 적절한 것은?",
        "correct": rule.get("basis", "공식 기준을 다시 검토해야 한다."),
        "distractors": negatives[:3],
    }


def build_item_from_rule(
    rule: dict[str, Any],
    source_document_id: str,
    segment_id: str,
    item_number: int,
) -> dict[str, Any]:
    template = RULE_QUESTION_TEMPLATES.get(rule.get("id", ""), build_generic_template(rule))
    choices = [
        {"label": "A", "text": template["correct"]},
        {"label": "B", "text": template["distractors"][0]},
        {"label": "C", "text": template["distractors"][1]},
        {"label": "D", "text": template["distractors"][2]},
    ]
    return {
        "id": f"item-{source_document_id}-generated-{item_number:03d}",
        "item_number": item_number,
        "question_type": "multiple_choice_single_answer",
        "stem": template["stem"],
        "choices": choices,
        "predicted_answer": None,
        "official_answer": None,
        "confidence": 0.0,
        "topic_major": rule.get("topic_major", "unknown"),
        "topic_minor": rule.get("topic_minor", "unknown"),
        "source_refs": [
            {"kind": "source_document", "value": source_document_id},
            {"kind": "source_segment", "value": segment_id},
            {"kind": "authoritative_rule", "value": rule.get("id", "")},
        ],
        "source_segment_ids": [segment_id],
        "quality_flags": ["generated_from_reference"],
        "status": "draft",
        "review_status": "pending",
        "fingerprint": build_item_fingerprint(template["stem"], choices),
        "validation_summary": {
            "official_answer_found": False,
            "external_validation_status": "not_started",
            "matched_rule_ids": [rule.get("id", "")],
            "matched_topic_keywords": list(rule.get("keywords", []))[:4],
            "review_reasons": ["generated from reference material"],
        },
    }


def build_seed_segment(source_document_id: str, seed_index: int, passage: str, rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"seg-{source_document_id}-seed-{seed_index}",
        "source_document_id": source_document_id,
        "segment_type": "authoring_seed",
        "item_number": seed_index,
        "text": passage,
        "normalized_text": normalize_text(passage),
        "line_start": 1,
        "line_end": 1,
        "choice_count": 4,
        "quality_flags": ["generated_from_reference"],
        "parsing_notes": [f"Generated draft item from authoritative rule {rule.get('id', '')}."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize draft exam items from reference-style uploads when no base questions were parsed.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    manifest = load_manifest(paths)

    if bank.get("exam_items"):
        print(json.dumps({"workspace": str(paths.root), "generated_items": 0, "mode": "skipped-existing-items"}, ensure_ascii=False, indent=2))
        return 0

    rules = load_authoritative_rules().get("rules", [])
    if not rules:
        print(json.dumps({"workspace": str(paths.root), "generated_items": 0, "mode": "skipped-no-rules"}, ensure_ascii=False, indent=2))
        return 0

    requested_item_count = 0
    candidates: list[dict[str, Any]] = []
    for source_document in bank.get("source_documents", []):
        if source_document.get("document_role") not in {"reference", "syllabus", "unknown"}:
            continue

        text_path = source_document.get("text_path")
        if not text_path:
            continue

        resolved_text_path = paths.root / text_path
        if not resolved_text_path.exists():
            continue

        text = resolved_text_path.read_text(encoding="utf-8")
        requested = detect_requested_item_count(text)
        if requested:
            requested_item_count = max(requested_item_count, requested)

        for passage in iter_reference_passages(text):
            scored_rules = [
                {"rule": rule, "score": score_rule_relevance(passage, rule)}
                for rule in rules
            ]
            scored_rules = [entry for entry in scored_rules if entry["score"] > 0]
            if not scored_rules:
                continue
            scored_rules.sort(key=lambda entry: (-entry["score"], entry["rule"].get("id", "")))
            best = scored_rules[0]
            candidates.append(
                {
                    "source_document_id": source_document["id"],
                    "passage": passage,
                    "rule": best["rule"],
                    "score": best["score"],
                }
            )

    if not candidates:
        print(json.dumps({"workspace": str(paths.root), "generated_items": 0, "mode": "skipped-no-reference-matches"}, ensure_ascii=False, indent=2))
        return 0

    unique_candidates: list[dict[str, Any]] = []
    seen_rule_ids: set[str] = set()
    candidates.sort(key=lambda entry: (-entry["score"], entry["source_document_id"], entry["rule"].get("id", "")))
    for candidate in candidates:
        rule_id = candidate["rule"].get("id", "")
        if rule_id in seen_rule_ids:
            continue
        unique_candidates.append(candidate)
        seen_rule_ids.add(rule_id)

    limit = requested_item_count or min(5, len(unique_candidates))
    selected_candidates = unique_candidates[:limit]

    next_item_number = 1
    generated_segments: list[dict[str, Any]] = []
    generated_items: list[dict[str, Any]] = []
    generation_counts_by_source: dict[str, int] = {}

    for seed_index, candidate in enumerate(selected_candidates, start=1):
        source_document_id = candidate["source_document_id"]
        segment = build_seed_segment(source_document_id, seed_index, candidate["passage"], candidate["rule"])
        item = build_item_from_rule(candidate["rule"], source_document_id, segment["id"], next_item_number)
        next_item_number += 1
        generated_segments.append(segment)
        generated_items.append(item)
        generation_counts_by_source[source_document_id] = generation_counts_by_source.get(source_document_id, 0) + 1

    bank["source_segments"] = list(bank.get("source_segments", [])) + generated_segments
    bank["exam_items"] = generated_items
    save_bank(paths, bank)

    for collection in (bank.get("source_documents", []), manifest.get("source_documents", [])):
        for source_document in collection:
            generated_count = generation_counts_by_source.get(source_document.get("id", ""))
            if not generated_count:
                continue
            notes = list(source_document.get("notes", []))
            note = f"Reference fallback generated {generated_count} draft item(s)."
            if note not in notes:
                notes.append(note)
            source_document["notes"] = notes

    save_bank(paths, bank)
    save_manifest(paths, manifest)

    print(
        json.dumps(
            {
                "workspace": str(paths.root),
                "generated_items": len(generated_items),
                "generated_segments": len(generated_segments),
                "mode": "reference-fallback",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
