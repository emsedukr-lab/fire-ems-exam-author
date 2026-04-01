#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from pipeline_common import build_summary_units, choice_label_to_text, load_bank, save_bank, workspace_paths


FOUR_CHOICE_LAYOUT = [
    ["출제의도", "정답 근거", "오답① 분석"],
    ["오답② 분석", "중심문항", "오답③ 분석"],
    ["조건변형", "형식변형", "피드백"],
]
DISTRACTOR_SLOT_NAMES = ["오답① 분석", "오답② 분석", "오답③ 분석"]


def explanation_map(bank: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {bundle["item_id"]: bundle for bundle in bank.get("explanation_bundles", [])}


def wrong_analyses(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [analysis for analysis in bundle.get("choice_analyses", []) if not analysis.get("is_correct")]


def build_generic_variant_items(item: dict[str, Any], bundle: dict[str, Any], correct_text: str) -> list[dict[str, Any]]:
    answer_label = item.get("official_answer") or item.get("predicted_answer")
    answer_line = f"{answer_label}. {correct_text}" if answer_label and correct_text else "검수 필요"
    answer_basis = bundle.get("answer_basis") or "정답 근거 검수 필요"
    return [
        {
            "id": f"{item['id']}-variant-01",
            "format": "원형 유지형",
            "role": "원형 유지형",
            "focus_choice_label": answer_label,
            "stem": item.get("stem"),
            "choices": [f"{choice.get('label')}. {choice.get('text')}" for choice in item.get("choices", [])],
            "answer": answer_line,
            "explanation": answer_basis,
        },
        {
            "id": f"{item['id']}-variant-02",
            "format": "이유 선택형",
            "role": "이유 선택형",
            "focus_choice_label": answer_label,
            "stem": f"{item.get('stem')}의 정답 근거로 가장 적절한 것은?",
            "choices": [
                f"A. {answer_basis}",
                "B. 일부 단서만으로도 항상 정답을 고를 수 있다.",
                "C. 오답도 비슷한 길이이면 정답으로 볼 수 있다.",
                "D. 조건 확인 없이 일반 원칙만 기억하면 충분하다.",
            ],
            "answer": f"A. {answer_basis}",
            "explanation": "비4지선다 문항은 일반형 분석 세트로 유지한다.",
        },
    ]


def build_generic_item_mandalart(item: dict[str, Any], bundle: dict[str, Any], variants: list[dict[str, Any]]) -> dict[str, Any]:
    answer_label = item.get("official_answer") or item.get("predicted_answer")
    correct_text = choice_label_to_text(item, answer_label)
    answer_basis = bundle.get("answer_basis") or "정답 근거 검수 필요"
    wrong_choices = wrong_analyses(bundle)
    return {
        "item_id": item["id"],
        "frame_type": "generic",
        "layout": [],
        "center_question": {
            "stem": item.get("stem"),
            "answer_label": answer_label,
            "answer_text": correct_text,
            "key_concept": item.get("topic_minor"),
            "exam_point": answer_basis,
        },
        "cells": [
            {"axis": "출제의도", "content": [f"상위 단원: {item.get('topic_major', 'unknown')}", f"하위 단원: {item.get('topic_minor', 'unknown')}"]},
            {"axis": "정답 근거", "content": [answer_basis]},
            {
                "axis": "오답 분석",
                "content": [
                    f"{analysis.get('choice_label')}: {analysis.get('misconception_tag')} / {analysis.get('student_reason')}"
                    for analysis in wrong_choices
                ],
            },
            {"axis": "조건변형", "content": ["조건을 조정해 정답/오답 경계를 다시 묻는다."]},
            {"axis": "형식변형", "content": [f"{variant.get('role')}: {variant.get('stem')}" for variant in variants]},
            {"axis": "피드백", "content": [f"정답 해설: {answer_basis}"]},
        ],
        "analysis_card": {
            "original_question": {
                "stem": item.get("stem"),
                "choices": item.get("choices", []),
                "answer_label": answer_label,
            },
            "distractors": [],
        },
        "variant_items": variants,
        "completion_checklist": [],
        "review_status": "needs_review" if len(item.get("choices", [])) != 4 else item.get("review_status", "needs_review"),
    }


def build_distractor_contexts(item: dict[str, Any], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for index, analysis in enumerate(wrong_analyses(bundle)):
        choice_label = analysis.get("choice_label")
        contexts.append(
            {
                "slot_index": index,
                "slot_name": DISTRACTOR_SLOT_NAMES[index] if index < len(DISTRACTOR_SLOT_NAMES) else f"오답{index + 1} 분석",
                "choice_label": choice_label,
                "choice_text": choice_label_to_text(item, choice_label),
                "analysis": analysis,
                "role": f"{choice_label} 기반 변형형",
            }
        )
    return contexts


def build_dedicated_correct_option(context: dict[str, Any]) -> str:
    return f"`{context['choice_text']}` 선택지가 정답이 되는 조건: {context['analysis'].get('correction_condition')}"


def build_misused_correct_option(correct_text: str, answer_basis: str) -> str:
    return f"원정답 `{correct_text}`를 조건 없이 일반화한 설명: {answer_basis}"


def build_supporting_wrong_option(context: dict[str, Any]) -> str:
    return f"{context['choice_text']} 계열 오답: {context['analysis'].get('student_reason')}"


def build_original_variant(item: dict[str, Any], correct_text: str, answer_basis: str) -> dict[str, Any]:
    answer_label = item.get("official_answer") or item.get("predicted_answer")
    answer_line = f"{answer_label}. {correct_text}" if answer_label and correct_text else "검수 필요"
    return {
        "id": f"{item['id']}-variant-01",
        "format": "원형 유지형",
        "role": "원형 유지형",
        "focus_choice_label": answer_label,
        "stem": item.get("stem"),
        "choices": [f"{choice.get('label')}. {choice.get('text')}" for choice in item.get("choices", [])],
        "answer": answer_line,
        "explanation": answer_basis,
    }


def build_dedicated_variant(
    item: dict[str, Any],
    context: dict[str, Any],
    other_contexts: list[dict[str, Any]],
    correct_text: str,
    answer_basis: str,
    variant_index: int,
) -> dict[str, Any]:
    focus_label = context["choice_label"]
    correct_option = build_dedicated_correct_option(context)
    support_a = build_supporting_wrong_option(other_contexts[0]) if other_contexts else "다른 오답 계열"
    support_b = build_supporting_wrong_option(other_contexts[1]) if len(other_contexts) > 1 else "다른 오답 계열"
    return {
        "id": f"{item['id']}-variant-{variant_index:02d}",
        "format": "전용 변형형",
        "role": context["role"],
        "focus_choice_label": focus_label,
        "stem": f"원문항의 선지 {focus_label}가 맞아지도록 조건을 바꾼 상황으로 가장 적절한 것은?",
        "choices": [
            f"A. {correct_option}",
            f"B. {build_misused_correct_option(correct_text, answer_basis)}",
            f"C. {support_a}",
            f"D. {support_b}",
        ],
        "answer": f"A. {correct_option}",
        "explanation": f"원래 오답 {focus_label}는 {context['analysis'].get('correction_condition')}",
    }


def build_integrated_variant(item: dict[str, Any], contexts: list[dict[str, Any]], answer_basis: str, variant_index: int) -> dict[str, Any]:
    correct_summary = "; ".join(
        f"{context['choice_label']}는 {context['analysis'].get('misconception_tag')}"
        for context in contexts
    )
    wrong_a = "; ".join(
        f"{context['choice_label']}는 정답과 거의 같아 오답이 아니다"
        for context in contexts
    )
    wrong_b = "; ".join(
        f"{context['choice_label']}는 모두 같은 이유로 틀렸다"
        for context in contexts
    )
    wrong_c = "; ".join(
        f"{context['choice_label']}를 고른 학생은 이유를 따질 필요가 없다"
        for context in contexts
    )
    return {
        "id": f"{item['id']}-variant-{variant_index:02d}",
        "format": "통합 비교형",
        "role": "통합 비교형",
        "focus_choice_label": None,
        "stem": "다음 중 세 오답과 정답의 경계를 가장 적절하게 설명한 것은?",
        "choices": [
            f"A. {correct_summary}; 정답 근거는 {answer_basis}",
            f"B. {wrong_a}",
            f"C. {wrong_b}",
            f"D. {wrong_c}",
        ],
        "answer": f"A. {correct_summary}; 정답 근거는 {answer_basis}",
        "explanation": "세 오답을 동시에 비교해 어떤 경계에서 틀리는지 한 번에 점검한다.",
    }


def build_reason_variant(item: dict[str, Any], contexts: list[dict[str, Any]], answer_basis: str, variant_index: int) -> dict[str, Any]:
    distractor_reasons = [context["analysis"].get("student_reason") for context in contexts]
    while len(distractor_reasons) < 3:
        distractor_reasons.append("일부 단서만 보고 섣불리 일반화한 이유")
    return {
        "id": f"{item['id']}-variant-{variant_index:02d}",
        "format": "이유 선택형",
        "role": "이유 선택형",
        "focus_choice_label": item.get("official_answer") or item.get("predicted_answer"),
        "stem": f"{item.get('stem')}의 정답 근거로 가장 적절한 것은?",
        "choices": [
            f"A. {answer_basis}",
            f"B. {distractor_reasons[0]}",
            f"C. {distractor_reasons[1]}",
            f"D. {distractor_reasons[2]}",
        ],
        "answer": f"A. {answer_basis}",
        "explanation": "정답을 맞혀도 이유가 틀린 경우를 분리하기 위한 추가 점검 문항이다.",
    }


def build_correction_variant(item: dict[str, Any], contexts: list[dict[str, Any]], variant_index: int) -> dict[str, Any]:
    correct_mapping = "; ".join(
        f"{context['choice_label']} -> {context['analysis'].get('correction_condition')}"
        for context in contexts
    )
    wrong_mapping_a = "; ".join(
        f"{context['choice_label']} -> {context['analysis'].get('key_condition_gap')}"
        for context in reversed(contexts)
    )
    wrong_mapping_b = "; ".join(
        f"{context['choice_label']} -> 항상 정답이 된다"
        for context in contexts
    )
    wrong_mapping_c = "; ".join(
        f"{context['choice_label']} -> 교정 조건이 필요 없다"
        for context in contexts
    )
    return {
        "id": f"{item['id']}-variant-{variant_index:02d}",
        "format": "오답 교정형",
        "role": "오답 교정형",
        "focus_choice_label": None,
        "stem": "다음 중 세 오답을 정답 가능 조건과 올바르게 연결한 것은?",
        "choices": [
            f"A. {correct_mapping}",
            f"B. {wrong_mapping_a}",
            f"C. {wrong_mapping_b}",
            f"D. {wrong_mapping_c}",
        ],
        "answer": f"A. {correct_mapping}",
        "explanation": "오답을 교정 조건과 연결해 재출제용 전환 규칙을 고정한다.",
    }


def register_appearance(appearance_roles: dict[str, list[str]], choice_label: str, role: str) -> None:
    appearance_roles.setdefault(choice_label, [])
    if role not in appearance_roles[choice_label]:
        appearance_roles[choice_label].append(role)


def build_four_choice_variants(item: dict[str, Any], bundle: dict[str, Any], correct_text: str) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    answer_basis = bundle.get("answer_basis") or "정답 근거 검수 필요"
    contexts = build_distractor_contexts(item, bundle)
    appearance_roles = {context["choice_label"]: ["원문항"] for context in contexts}
    appearance_variant_ids = {context["choice_label"]: [] for context in contexts}

    variants: list[dict[str, Any]] = [build_original_variant(item, correct_text, answer_basis)]
    for index, context in enumerate(contexts, start=2):
        others = [candidate for candidate in contexts if candidate["choice_label"] != context["choice_label"]]
        variant = build_dedicated_variant(item, context, others, correct_text, answer_basis, index)
        variants.append(variant)
        register_appearance(appearance_roles, context["choice_label"], f"{context['role']} 정답화")
        appearance_variant_ids[context["choice_label"]].append(variant["id"])
        for other in others:
            register_appearance(appearance_roles, other["choice_label"], f"{context['role']} 보조오답")
            appearance_variant_ids[other["choice_label"]].append(variant["id"])

    integrated_variant = build_integrated_variant(item, contexts, answer_basis, 5)
    variants.append(integrated_variant)
    for context in contexts:
        register_appearance(appearance_roles, context["choice_label"], "통합 비교형")
        appearance_variant_ids[context["choice_label"]].append(integrated_variant["id"])

    reason_variant = build_reason_variant(item, contexts, answer_basis, 6)
    variants.append(reason_variant)
    for context in contexts:
        register_appearance(appearance_roles, context["choice_label"], "이유 선택형 보조오답")
        appearance_variant_ids[context["choice_label"]].append(reason_variant["id"])

    correction_variant = build_correction_variant(item, contexts, 7)
    variants.append(correction_variant)
    for context in contexts:
        register_appearance(appearance_roles, context["choice_label"], "오답 교정형")
        appearance_variant_ids[context["choice_label"]].append(correction_variant["id"])

    return variants, appearance_roles, appearance_variant_ids


def build_completion_checklist(contexts: list[dict[str, Any]], appearance_roles: dict[str, list[str]], dedicated_variant_ids: dict[str, list[str]]) -> list[dict[str, Any]]:
    checks = [
        {
            "criterion": "misconception_tagged",
            "label": "오답 3개 각각에 오개념 이름이 붙어 있는가",
            "passed": all(context["analysis"].get("misconception_tag") for context in contexts),
        },
        {
            "criterion": "selection_reason_recorded",
            "label": "오답 3개 각각에 선택 이유가 적혀 있는가",
            "passed": all(context["analysis"].get("student_reason") for context in contexts),
        },
        {
            "criterion": "correction_condition_recorded",
            "label": "오답 3개 각각에 교정 조건이 적혀 있는가",
            "passed": all(context["analysis"].get("correction_condition") for context in contexts),
        },
        {
            "criterion": "dedicated_variant_created",
            "label": "오답 3개 각각으로 전용 변형문항이 1개 이상 만들어졌는가",
            "passed": all(dedicated_variant_ids.get(context["choice_label"]) for context in contexts),
        },
        {
            "criterion": "individual_explanation_recorded",
            "label": "오답 3개 각각에 개별 해설이 있는가",
            "passed": all(context["analysis"].get("why_wrong_or_right") for context in contexts),
        },
        {
            "criterion": "not_only_elimination",
            "label": "어떤 오답도 단순 소거용 보기로만 쓰이지 않았는가",
            "passed": all(len(set(appearance_roles.get(context["choice_label"], []))) >= 2 for context in contexts),
        },
    ]
    return checks


def build_analysis_card(item: dict[str, Any], contexts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "original_question": {
            "stem": item.get("stem"),
            "choices": item.get("choices", []),
            "answer_label": item.get("official_answer") or item.get("predicted_answer"),
        },
        "distractors": [
            {
                "slot_name": context["slot_name"],
                "choice_label": context["choice_label"],
                "choice_text": context["choice_text"],
                "misconception_tag": context["analysis"].get("misconception_tag"),
                "selection_reason": context["analysis"].get("student_reason"),
                "key_error": context["analysis"].get("why_wrong_or_right"),
                "correction_condition": context["analysis"].get("correction_condition"),
                "dedicated_variant_idea": f"{context['role']}: {context['analysis'].get('correction_condition')}",
            }
            for context in contexts
        ],
    }


def build_four_choice_cells(
    item: dict[str, Any],
    answer_basis: str,
    correct_text: str,
    contexts: list[dict[str, Any]],
    variants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = [
        {
            "axis": "출제의도",
            "content": [
                "무엇을 아는지보다 무엇을 판단하게 하는지 본다.",
                f"상위 단원: {item.get('topic_major', 'unknown')}",
                f"하위 단원: {item.get('topic_minor', 'unknown')}",
            ],
        },
        {
            "axis": "정답 근거",
            "content": [
                answer_basis,
                f"정답 조건: {correct_text or '정답 미확정'}",
                "정답이 되는 최소 근거를 유지한 상태로 변형문항을 확장한다.",
            ],
        },
    ]

    for context in contexts:
        analysis = context["analysis"]
        variant_types = [context["role"], "통합 비교형", "오답 검증형", "오답 교정형"]
        cells.append(
            {
                "axis": context["slot_name"],
                "choice_label": context["choice_label"],
                "choice_text": context["choice_text"],
                "misconception_tag": analysis.get("misconception_tag"),
                "selection_reason": analysis.get("student_reason"),
                "key_condition_gap": analysis.get("key_condition_gap"),
                "correction_condition": analysis.get("correction_condition"),
                "variant_question_types": variant_types,
                "remediation_note": analysis.get("why_wrong_or_right"),
            }
        )

    cells.extend(
        [
            {
                "axis": "조건변형",
                "content": [
                    "원래 오답이 맞아지도록 조건을 조정한다.",
                    "원정답의 오용 버전을 함께 넣어 경계를 유지한다.",
                    "다른 두 오답 계열은 보조 오답으로 재활용한다.",
                ],
            },
            {
                "axis": "형식변형",
                "content": [f"{variant.get('role')}: {variant.get('stem')}" for variant in variants],
            },
            {
                "axis": "피드백",
                "content": [
                    f"정답 해설: {answer_basis}",
                    *[
                        f"오답 {context['choice_label']} 교정: {context['analysis'].get('why_wrong_or_right')}"
                        for context in contexts
                    ],
                ],
            },
        ]
    )
    return cells


def build_item_mandalart(item: dict[str, Any], bundle: dict[str, Any], variants: list[dict[str, Any]]) -> dict[str, Any]:
    answer_label = item.get("official_answer") or item.get("predicted_answer")
    correct_text = choice_label_to_text(item, answer_label)
    answer_basis = bundle.get("answer_basis") or "정답 근거 검수 필요"

    if len(item.get("choices", [])) == 4 and len(wrong_analyses(bundle)) == 3:
        contexts = build_distractor_contexts(item, bundle)
        variants, appearance_roles, appearance_variant_ids = build_four_choice_variants(item, bundle, correct_text)
        dedicated_variant_ids = {
            context["choice_label"]: [variant["id"] for variant in variants if variant.get("role") == context["role"]]
            for context in contexts
        }
        checklist = build_completion_checklist(contexts, appearance_roles, dedicated_variant_ids)
        cells = build_four_choice_cells(item, answer_basis, correct_text, contexts, variants)
        return {
            "item_id": item["id"],
            "frame_type": "four_choice_dedicated",
            "layout": FOUR_CHOICE_LAYOUT,
            "center_question": {
                "stem": item.get("stem"),
                "answer_label": answer_label,
                "answer_text": correct_text,
                "key_concept": item.get("topic_minor"),
                "exam_point": answer_basis,
            },
            "cells": cells,
            "analysis_card": build_analysis_card(item, contexts),
            "variant_items": variants,
            "completion_checklist": checklist,
            "review_status": item.get("review_status", "needs_review") if item.get("review_status") != "approved" else ("approved" if all(check["passed"] for check in checklist) else "needs_review"),
        }

    return build_generic_item_mandalart(item, bundle, variants)


def build_distractor_record(
    item: dict[str, Any],
    context: dict[str, Any],
    appearance_roles: list[str],
    appearance_variant_ids: list[str],
    dedicated_variant_ids: list[str],
) -> dict[str, Any]:
    analysis = context["analysis"]
    axes = [
        {
            "axis": "출제의도",
            "question_idea": f"선지 {context['choice_label']}를 고르는 학생이 어떤 판단 기준을 잘못 잡는지 묻는 문항",
        },
        {
            "axis": "정답논리",
            "question_idea": f"정답과 선지 {context['choice_label']}를 가르는 최소 근거를 고르게 하는 문항",
        },
        {
            "axis": "오답논리",
            "question_idea": analysis.get("why_wrong_or_right"),
        },
        {
            "axis": "조건변형",
            "question_idea": analysis.get("correction_condition"),
        },
        {
            "axis": "형식변형",
            "question_idea": f"{context['role']}과 통합 비교형에서 이 오답을 재활용하는 문항",
        },
        {
            "axis": "난도조절",
            "question_idea": f"선지 {context['choice_label']}와 정답의 유사도를 조정해 난도를 바꾸는 문항",
        },
        {
            "axis": "개념확장",
            "question_idea": f"선지 {context['choice_label']}와 자주 함께 혼동되는 개념을 비교하는 문항",
        },
        {
            "axis": "피드백",
            "question_idea": analysis.get("why_wrong_or_right"),
        },
    ]
    return {
        "item_id": item["id"],
        "choice_label": context["choice_label"],
        "choice_text": context["choice_text"],
        "center_misconception": analysis.get("misconception_tag"),
        "student_reason": analysis.get("student_reason"),
        "key_condition_gap": analysis.get("key_condition_gap"),
        "correction_condition": analysis.get("correction_condition"),
        "variant_question_types": [context["role"], "통합 비교형", "오답 검증형", "오답 교정형"],
        "remediation_note": analysis.get("why_wrong_or_right"),
        "dedicated_variant_ids": dedicated_variant_ids,
        "appearance_roles": appearance_roles,
        "appearance_variant_ids": appearance_variant_ids,
        "axes": axes,
        "variant_items": [
            {
                "format": "오답 검증형",
                "stem": f"선지 {context['choice_label']}가 왜 틀렸는지 가장 적절한 설명을 고르시오.",
                "answer": analysis.get("why_wrong_or_right"),
            },
            {
                "format": "오답 교정형",
                "stem": f"어떤 조건이 추가되면 선지 {context['choice_label']}가 맞아지는가?",
                "answer": analysis.get("correction_condition"),
            },
        ],
        "review_status": item.get("review_status", "needs_review"),
    }


def build_mock_exam_sets(exam_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    approved_items = [item for item in exam_items if item.get("review_status") == "approved"]
    if not approved_items:
        return []

    coverage: dict[str, int] = {}
    for item in approved_items:
        topic = item.get("topic_major", "unknown")
        coverage[topic] = coverage.get(topic, 0) + 1

    return [
        {
            "id": "mock-001",
            "title": "응급처치학개론 모의고사 1회",
            "coverage": [{"topic_major": topic, "count": count} for topic, count in sorted(coverage.items())],
            "difficulty_mix": {
                "easy": 0.4,
                "medium": 0.4,
                "hard": 0.2,
            },
            "item_ids": [item["id"] for item in approved_items[:20]],
            "has_explanations": True,
            "review_status": "draft",
        }
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build mandalart frames and variant items from analyzed questions.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    explanations = explanation_map(bank)

    item_mandalarts: list[dict[str, Any]] = []
    distractor_mandalarts: list[dict[str, Any]] = []
    for item in bank.get("exam_items", []):
        bundle = explanations.get(item["id"])
        if not bundle:
            continue
        correct_text = choice_label_to_text(item, item.get("official_answer") or item.get("predicted_answer"))
        initial_variants = build_generic_variant_items(item, bundle, correct_text)
        item_mandalart = build_item_mandalart(item, bundle, initial_variants)
        item_mandalarts.append(item_mandalart)

        if item_mandalart.get("frame_type") == "four_choice_dedicated":
            contexts = build_distractor_contexts(item, bundle)
            variants = item_mandalart.get("variant_items", [])
            dedicated_ids = {
                context["choice_label"]: [variant["id"] for variant in variants if variant.get("role") == context["role"]]
                for context in contexts
            }
            appearance_roles = {
                context["choice_label"]: ["원문항"]
                for context in contexts
            }
            appearance_variant_ids = {
                context["choice_label"]: []
                for context in contexts
            }
            for variant in variants:
                role = variant.get("role")
                focus_label = variant.get("focus_choice_label")
                if role and role.endswith("기반 변형형") and focus_label:
                    register_appearance(appearance_roles, focus_label, f"{role} 정답화")
                    appearance_variant_ids[focus_label].append(variant["id"])
                    for context in contexts:
                        if context["choice_label"] == focus_label:
                            continue
                        register_appearance(appearance_roles, context["choice_label"], f"{role} 보조오답")
                        appearance_variant_ids[context["choice_label"]].append(variant["id"])
                elif role in {"통합 비교형", "오답 교정형", "이유 선택형"}:
                    for context in contexts:
                        register_appearance(appearance_roles, context["choice_label"], role)
                        appearance_variant_ids[context["choice_label"]].append(variant["id"])

            for context in contexts:
                distractor_mandalarts.append(
                    build_distractor_record(
                        item,
                        context,
                        appearance_roles.get(context["choice_label"], []),
                        appearance_variant_ids.get(context["choice_label"], []),
                        dedicated_ids.get(context["choice_label"], []),
                    )
                )
        else:
            for analysis in wrong_analyses(bundle):
                choice_label = analysis.get("choice_label")
                context = {
                    "choice_label": choice_label,
                    "choice_text": choice_label_to_text(item, choice_label),
                    "role": f"{choice_label} 기반 변형형",
                    "analysis": analysis,
                }
                distractor_mandalarts.append(
                    build_distractor_record(item, context, ["원문항"], [], [])
                )

    bank["item_mandalarts"] = item_mandalarts
    bank["distractor_mandalarts"] = distractor_mandalarts
    bank["summary_units"] = build_summary_units(bank.get("exam_items", []), bank.get("explanation_bundles", []))
    bank["mock_exam_sets"] = build_mock_exam_sets(bank.get("exam_items", []))
    save_bank(paths, bank)

    summary = {
        "workspace": str(paths.root),
        "item_mandalarts": len(item_mandalarts),
        "distractor_mandalarts": len(distractor_mandalarts),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
