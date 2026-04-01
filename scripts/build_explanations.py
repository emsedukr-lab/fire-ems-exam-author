#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from pipeline_common import (
    choice_label_to_text,
    infer_misconception_tag,
    load_authoritative_rules,
    load_bank,
    save_bank,
    workspace_paths,
)


def build_student_reason(tag: str, choice_text: str) -> str:
    templates = {
        "개념 혼동": f"`{choice_text}` 선택지가 핵심 개념과 비슷하게 보여 정답처럼 느껴질 수 있다.",
        "조건 누락": f"`{choice_text}` 선택지가 일부 상황에서는 맞지만 이 문항의 우선 조건을 빠뜨리고 있다.",
        "계산 절차 오류": f"`{choice_text}` 선택지는 계산 또는 절차의 한 단계를 잘못 적용했을 때 고르기 쉽다.",
        "과잉 일반화": f"`{choice_text}` 선택지를 모든 상황에 그대로 적용해도 된다고 오해할 수 있다.",
        "용어 혼동": f"`{choice_text}` 선택지와 정답 개념의 용어를 같은 의미로 착각하기 쉽다.",
        "부분정답": f"`{choice_text}` 선택지는 일부 설명은 맞지만 정답이 되기 위한 핵심 조건이 빠져 있다.",
    }
    return templates.get(tag, f"`{choice_text}` 선택지가 부분적으로 그럴듯해 보여 선택할 수 있다.")


def build_condition_gap(tag: str, item: dict[str, Any], correct_text: str) -> str:
    if tag == "조건 누락":
        return "문항이 묻는 우선순위 또는 예외 조건을 확인해야 한다."
    if tag == "과잉 일반화":
        return "정답은 특정 상황에만 성립하며 모든 상황으로 일반화할 수 없다."
    if tag == "계산 절차 오류":
        return "정답에 도달하려면 절차의 핵심 단계를 순서대로 적용해야 한다."
    if tag == "용어 혼동":
        return "정답과 유사한 용어를 구분하고 정의를 다시 확인해야 한다."
    if tag == "부분정답":
        return f"정답 `{correct_text}`가 되려면 빠진 조건을 함께 만족해야 한다."
    return f"정답 `{correct_text}`가 성립하는 핵심 근거를 확인해야 한다."


def build_correction_condition(tag: str, choice_text: str, correct_text: str) -> str:
    if tag == "조건 누락":
        return f"`{choice_text}` 선택지가 맞으려면 문항의 우선순위가 아닌 다른 상황 또는 추가 조건을 묻도록 바뀌어야 한다."
    if tag == "과잉 일반화":
        return f"`{choice_text}` 선택지가 맞으려면 적용 범위를 특정 상황으로 제한해야 한다."
    if tag == "계산 절차 오류":
        return f"`{choice_text}` 선택지가 맞으려면 수치 기준이나 계산 전제가 `{choice_text}`에 맞게 조정되어야 한다."
    if tag == "용어 혼동":
        return f"`{choice_text}` 선택지가 맞으려면 용어 정의 또는 분류 기준이 `{choice_text}` 중심으로 다시 설정되어야 한다."
    if tag == "부분정답":
        return f"`{choice_text}` 선택지가 맞으려면 원래 정답 `{correct_text}`에 요구되던 조건이 제거되거나 다른 상황으로 바뀌어야 한다."
    return f"`{choice_text}` 선택지가 맞으려면 정답 판단 기준이 `{choice_text}`에 유리한 상황으로 조정되어야 한다."


def build_choice_analysis(
    item: dict[str, Any],
    choice: dict[str, Any],
    final_answer: str | None,
    correct_text: str,
    matched_rule: dict[str, Any] | None,
) -> dict[str, Any]:
    is_correct = choice.get("label") == final_answer
    if is_correct:
        rationale = matched_rule.get("basis") if matched_rule else f"`{correct_text}`가 문항의 핵심 조건을 충족한다."
        return {
            "choice_label": choice.get("label"),
            "is_correct": True,
            "why_wrong_or_right": rationale,
            "misconception_tag": None,
            "student_reason": None,
            "key_condition_gap": None,
            "evidence_strength": "high" if matched_rule else "medium",
            "external_validation_status": item.get("validation_summary", {}).get("external_validation_status", "not_found"),
            "evidence_refs": (matched_rule or {}).get("source_refs", item.get("source_refs", [])),
        }

    tag = infer_misconception_tag(item, choice.get("text", ""), correct_text)
    condition_gap = build_condition_gap(tag, item, correct_text)
    correction_condition = build_correction_condition(tag, choice.get("text", ""), correct_text)
    rationale = f"`{choice.get('text', '')}` 선택지는 {tag}에 해당하며, {condition_gap}"
    return {
        "choice_label": choice.get("label"),
        "is_correct": False,
        "why_wrong_or_right": rationale,
        "misconception_tag": tag,
        "student_reason": build_student_reason(tag, choice.get("text", "")),
        "key_condition_gap": condition_gap,
        "correction_condition": correction_condition,
        "evidence_strength": "medium" if matched_rule else "low",
        "external_validation_status": item.get("validation_summary", {}).get("external_validation_status", "not_found"),
        "evidence_refs": (matched_rule or {}).get("source_refs", item.get("source_refs", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build choice-by-choice explanations for parsed exam items.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    rules_by_id = {rule["id"]: rule for rule in load_authoritative_rules().get("rules", [])}

    explanation_bundles: list[dict[str, Any]] = []
    for item in bank.get("exam_items", []):
        final_answer = item.get("official_answer") or item.get("predicted_answer")
        correct_text = choice_label_to_text(item, final_answer)
        matched_rule_ids = item.get("validation_summary", {}).get("matched_rule_ids", [])
        matched_rule = rules_by_id.get(matched_rule_ids[0]) if matched_rule_ids else None

        choice_analyses = [
            build_choice_analysis(item, choice, final_answer, correct_text, matched_rule)
            for choice in item.get("choices", [])
        ]
        answer_basis = (
            matched_rule.get("basis")
            if matched_rule
            else f"정답 `{final_answer}`는 문항의 핵심 조건과 우선순위를 충족한다."
            if final_answer
            else "정답이 확정되지 않아 검수가 필요하다."
        )
        explanation_bundles.append(
            {
                "item_id": item["id"],
                "answer_basis": answer_basis,
                "official_basis": answer_basis if item.get("official_answer") else None,
                "external_basis": matched_rule.get("basis") if matched_rule else None,
                "choice_analyses": choice_analyses,
                "confidence": item.get("confidence", 0.0),
                "conflict_note": item.get("validation_summary", {}).get("conflict_note"),
                "source_confidence_reason": ", ".join(item.get("validation_summary", {}).get("review_reasons", [])) or "validated",
                "review_status": item.get("review_status", "needs_review"),
            }
        )

    bank["explanation_bundles"] = explanation_bundles
    save_bank(paths, bank)

    summary = {
        "workspace": str(paths.root),
        "explanation_bundles": len(explanation_bundles),
        "complete_items": sum(1 for bundle in explanation_bundles if bundle.get("choice_analyses")),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
