#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from pipeline_common import build_review_entry, load_bank, save_json, severity_rank, workspace_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Build review queue artifacts from the current exam bank.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    explanations_by_item = {bundle["item_id"]: bundle for bundle in bank.get("explanation_bundles", [])}
    item_mandalarts_by_item = {record["item_id"]: record for record in bank.get("item_mandalarts", [])}
    mandalarts_by_item = defaultdict(list)
    for record in bank.get("distractor_mandalarts", []):
        mandalarts_by_item[record.get("item_id")].append(record)

    review_entries: list[dict] = []
    parsed_segment_source_ids = {
        segment.get("source_document_id")
        for segment in bank.get("source_segments", [])
        if segment.get("source_document_id")
    }

    for source_document in bank.get("source_documents", []):
        source_id = f"source:{source_document.get('id')}"
        if source_document.get("quality_flags"):
            review_entries.append(
                build_review_entry(
                    source_id,
                    f"source quality flags: {', '.join(source_document['quality_flags'])}",
                    "medium",
                    "원본 스캔 품질 또는 추출 결과를 다시 확인하세요.",
                )
            )
        if source_document.get("status") != "extracted":
            review_entries.append(
                build_review_entry(
                    source_id,
                    f"source status is {source_document.get('status')}",
                    "high",
                    "추출 실패 원인과 fallback 경로를 확인하세요.",
                )
            )
        if source_document.get("document_role") in {"question_sheet", "answer_sheet"} and source_document.get("id") not in parsed_segment_source_ids:
            review_entries.append(
                build_review_entry(
                    source_id,
                    "no parsed segments emitted",
                    "high",
                    "원본 문서 형식과 파싱 규칙을 점검하세요.",
                )
            )

    for item in bank.get("exam_items", []):
        item_id = item["id"]
        if not item.get("official_answer"):
            review_entries.append(
                build_review_entry(item_id, "official answer missing", "high", "정답표 또는 공식 해설을 확인하세요.")
            )
        if item.get("validation_summary", {}).get("external_validation_status") == "not_found":
            review_entries.append(
                build_review_entry(item_id, "authoritative rule not found", "medium", "공식 기준 자료를 추가로 연결하세요.")
            )
        if item.get("validation_summary", {}).get("external_validation_status") == "conflicted":
            review_entries.append(
                build_review_entry(item_id, "authoritative conflict", "high", "공식 기준과 사용자 자료를 대조 검수하세요.")
            )
        if item.get("quality_flags"):
            review_entries.append(
                build_review_entry(item_id, f"quality flags: {', '.join(item['quality_flags'])}", "medium", "OCR 또는 문항 구조를 다시 확인하세요.")
            )
        if item.get("confidence", 0.0) < 0.80:
            review_entries.append(
                build_review_entry(item_id, "confidence below threshold", "medium", "정답 근거와 선지 해설을 재검토하세요.")
            )

        explanation = explanations_by_item.get(item_id)
        if not explanation or len(explanation.get("choice_analyses", [])) != len(item.get("choices", [])):
            review_entries.append(
                build_review_entry(item_id, "choice explanations incomplete", "high", "모든 선지 해설을 채우세요.")
            )
        item_mandalart = item_mandalarts_by_item.get(item_id)
        if len(item.get("choices", [])) == 4:
            if not item_mandalart:
                review_entries.append(
                    build_review_entry(item_id, "item mandalart missing", "high", "4지 선다형 전용 만다라트를 생성하세요.")
                )
            else:
                if item_mandalart.get("frame_type") != "four_choice_dedicated":
                    review_entries.append(
                        build_review_entry(item_id, "four-choice dedicated frame missing", "high", "4지 선다형 전용 3x3 프레임을 적용하세요.")
                    )
                if len(item_mandalart.get("variant_items", [])) < 5:
                    review_entries.append(
                        build_review_entry(item_id, "variant set below minimum", "high", "원형+A/B/C 기반+통합 비교형 최소 5세트를 만드세요.")
                    )
                checklist = item_mandalart.get("completion_checklist", [])
                for check in checklist:
                    if not check.get("passed"):
                        review_entries.append(
                            build_review_entry(item_id, f"completion check failed: {check.get('criterion')}", "high", check.get("label", "오답 반영 체크리스트를 확인하세요."))
                        )
        wrong_choice_count = sum(1 for choice in item.get("choices", []) if choice.get("label") != (item.get("official_answer") or item.get("predicted_answer")))
        if len(mandalarts_by_item[item_id]) != wrong_choice_count:
            review_entries.append(
                build_review_entry(item_id, "mandalart count mismatch", "high", "오답 선지마다 만다라트를 생성하세요.")
            )
        for mandalart in mandalarts_by_item[item_id]:
            if len(mandalart.get("axes", [])) != 8:
                review_entries.append(
                    build_review_entry(item_id, f"incomplete mandalart for {mandalart.get('choice_label')}", "high", "8축 만다라트를 완성하세요.")
                )
            required_fields = [
                ("center_misconception", "오개념 태그를 채우세요."),
                ("student_reason", "학생이 왜 고르는지 기록하세요."),
                ("key_condition_gap", "정답과 갈라지는 핵심 조건을 기록하세요."),
                ("correction_condition", "이 선지가 맞아지려면 무엇이 바뀌어야 하는지 기록하세요."),
                ("variant_question_types", "이 오답으로 만들 수 있는 변형문항 유형을 기록하세요."),
                ("remediation_note", "오답 교정용 해설 1문장을 기록하세요."),
            ]
            for field_name, action in required_fields:
                value = mandalart.get(field_name)
                if value is None or value == [] or value == "":
                    review_entries.append(
                        build_review_entry(item_id, f"{field_name} missing for {mandalart.get('choice_label')}", "high", action)
                    )
            if not mandalart.get("dedicated_variant_ids"):
                review_entries.append(
                    build_review_entry(item_id, f"dedicated variant missing for {mandalart.get('choice_label')}", "high", "각 오답마다 전용 변형문항을 1개 이상 만드세요.")
                )
            if len(set(mandalart.get("appearance_roles", []))) < 2:
                review_entries.append(
                    build_review_entry(item_id, f"single-use distractor {mandalart.get('choice_label')}", "high", "어떤 오답도 단순 소거용 보기로만 쓰이지 않게 다시 배치하세요.")
                )

    deduped: dict[tuple[str, str], dict] = {}
    for entry in review_entries:
        key = (entry["item_id"], entry["reason"])
        if key not in deduped:
            deduped[key] = entry
        elif severity_rank(entry["severity"]) < severity_rank(deduped[key]["severity"]):
            deduped[key] = entry

    queue = sorted(deduped.values(), key=lambda entry: (severity_rank(entry["severity"]), entry["item_id"], entry["reason"]))
    if not bank.get("exam_items"):
        queue.append(
            build_review_entry(
                "workspace",
                "no exam items were parsed",
                "high",
                "문항 구조화 규칙 또는 원본 품질을 확인하세요.",
            )
        )
        queue.sort(key=lambda entry: (severity_rank(entry["severity"]), entry["item_id"], entry["reason"]))
    save_json(paths.review_queue_json_path, queue)

    if queue:
        lines = ["# Review Queue", ""]
        for entry in queue:
            lines.extend(
                [
                    f"## {entry['item_id']}",
                    f"- Severity: {entry['severity']}",
                    f"- Reason: {entry['reason']}",
                    f"- Action: {entry['recommended_action']}",
                    "",
                ]
            )
    else:
        lines = ["# Review Queue", "", "아직 검수 대기 항목이 없습니다.", ""]
    paths.review_queue_md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"workspace": str(paths.root), "review_entries": len(queue)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
