#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pipeline_common import load_bank, load_json, render_source_ref_markdown, workspace_paths


def render_choice_lines(bundle: dict) -> list[str]:
    lines: list[str] = []
    for analysis in bundle.get("choice_analyses", []):
        label = analysis.get("choice_label")
        tag = analysis.get("misconception_tag") or "정답"
        lines.extend(
            [
                f"- {label}: {analysis.get('why_wrong_or_right')}",
                f"  태그: {tag}",
            ]
        )
        if analysis.get("student_reason"):
            lines.append(f"  학생이 고르는 이유: {analysis.get('student_reason')}")
        if analysis.get("key_condition_gap"):
            lines.append(f"  갈라지는 조건: {analysis.get('key_condition_gap')}")
    return lines


def render_item_mandalart_lines(mandalart: dict) -> list[str]:
    lines: list[str] = []
    if mandalart.get("frame_type") == "four_choice_dedicated":
        lines.extend(
            [
                f"- 레이아웃: {' / '.join(' | '.join(row) for row in mandalart.get('layout', []))}",
                f"- 중심문항: {mandalart.get('center_question', {}).get('stem')}",
                f"- 중심정답: {mandalart.get('center_question', {}).get('answer_label')} / {mandalart.get('center_question', {}).get('answer_text')}",
            ]
        )
    for cell in mandalart.get("cells", []):
        if cell.get("axis", "").startswith("오답"):
            lines.extend(
                [
                    f"- {cell.get('axis')} ({cell.get('choice_label')}): {cell.get('choice_text')}",
                    f"  오개념 태그: {cell.get('misconception_tag')}",
                    f"  선택 이유: {cell.get('selection_reason')}",
                    f"  핵심 조건: {cell.get('key_condition_gap')}",
                    f"  교정 조건: {cell.get('correction_condition')}",
                    f"  변형 유형: {', '.join(cell.get('variant_question_types', []))}",
                    f"  교정 해설: {cell.get('remediation_note')}",
                ]
            )
            continue
        lines.append(f"- {cell.get('axis')}: {' / '.join(cell.get('content', []))}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Markdown analysis outputs from the exam bank.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Defaults to current directory.")
    args = parser.parse_args()

    paths = workspace_paths(args.workspace)
    bank = load_bank(paths)
    review_queue = load_json(paths.review_queue_json_path, [])
    explanations_by_item = {bundle["item_id"]: bundle for bundle in bank.get("explanation_bundles", [])}
    item_mandalarts_by_item = {record["item_id"]: record for record in bank.get("item_mandalarts", [])}
    distractors_by_item: dict[str, list[dict]] = {}
    for record in bank.get("distractor_mandalarts", []):
        distractors_by_item.setdefault(record["item_id"], []).append(record)

    lines = [
        "# 기출 분석 리포트",
        "",
        "## 입력 요약",
        f"- source_documents: {len(bank.get('source_documents', []))}",
        f"- exam_items: {len(bank.get('exam_items', []))}",
        f"- review_queue: {len(review_queue)}",
        "",
    ]

    for item in bank.get("exam_items", []):
        bundle = explanations_by_item.get(item["id"], {})
        mandalart = item_mandalarts_by_item.get(item["id"], {})
        lines.extend(
            [
                f"## {item['id']}",
                f"- 문항: {item.get('stem')}",
                f"- 정답: {(item.get('official_answer') or item.get('predicted_answer') or '미확정')}",
                f"- 단원: {item.get('topic_major')} / {item.get('topic_minor')}",
                f"- 검수 상태: {item.get('review_status')}",
                f"- 근거: {bundle.get('answer_basis', '미생성')}",
                f"- 출처: {render_source_ref_markdown(item.get('source_refs', []))}",
                "",
                "### 선지 해설",
                *render_choice_lines(bundle),
                "",
            ]
        )

        if mandalart:
            lines.extend(["### 만다라트 9칸", ""])
            lines.extend(render_item_mandalart_lines(mandalart))
            if mandalart.get("completion_checklist"):
                lines.extend(["", "### 오답 반영 체크", ""])
                for check in mandalart.get("completion_checklist", []):
                    marker = "예" if check.get("passed") else "아니오"
                    lines.append(f"- {check.get('label')}: {marker}")
            lines.extend(["", "### 변형문항 세트", ""])
            for variant in mandalart.get("variant_items", []):
                lines.extend(
                    [
                        f"- {variant.get('role')}: {variant.get('stem')}",
                        f"  정답: {variant.get('answer')}",
                        f"  해설: {variant.get('explanation')}",
                    ]
                )
            lines.append("")

        if distractors_by_item.get(item["id"]):
            lines.extend(["### 오답 만다라트", ""])
            for record in distractors_by_item[item["id"]]:
                lines.append(f"- 선지 {record.get('choice_label')} / 오개념: {record.get('center_misconception')}")
                lines.append(f"  학생이 고르는 이유: {record.get('student_reason')}")
                lines.append(f"  교정 조건: {record.get('correction_condition')}")
                lines.append(f"  변형 유형: {', '.join(record.get('variant_question_types', []))}")
                lines.append(f"  교정 해설: {record.get('remediation_note')}")
                for axis in record.get("axes", []):
                    lines.append(f"  - {axis.get('axis')}: {axis.get('question_idea')}")
            lines.append("")

    if review_queue:
        lines.extend(["## 검수 대기", ""])
        for entry in review_queue:
            lines.extend(
                [
                    f"- {entry.get('item_id')}: {entry.get('reason')} ({entry.get('severity')})",
                    f"  조치: {entry.get('recommended_action')}",
                ]
            )

    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    (paths.outputs_dir / "past-analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    mandalart_lines = ["# 오답 만다라트", ""]
    for record in bank.get("distractor_mandalarts", []):
        mandalart_lines.extend(
            [
                f"## {record.get('item_id')} / {record.get('choice_label')}",
                f"- 오개념: {record.get('center_misconception')}",
                f"- 학생이 고르는 이유: {record.get('student_reason')}",
                f"- 핵심 조건: {record.get('key_condition_gap')}",
                f"- 교정 조건: {record.get('correction_condition')}",
                f"- 변형 유형: {', '.join(record.get('variant_question_types', []))}",
                f"- 교정 해설: {record.get('remediation_note')}",
            ]
        )
        for axis in record.get("axes", []):
            mandalart_lines.append(f"- {axis.get('axis')}: {axis.get('question_idea')}")
        mandalart_lines.append("")
    (paths.outputs_dir / "distractor-mandalart.md").write_text("\n".join(mandalart_lines) + "\n", encoding="utf-8")

    summary_lines = ["# 요약집", ""]
    for unit in bank.get("summary_units", []):
        summary_lines.extend(
            [
                f"## {unit.get('topic_major')} / {unit.get('topic_minor')}",
                f"- linked items: {', '.join(unit.get('linked_item_ids', []))}",
            ]
        )
        for point in unit.get("key_points", []):
            summary_lines.append(f"- {point}")
        summary_lines.append("")
    (paths.outputs_dir / "summary-book.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    mock_lines = ["# 모의고사 1회", ""]
    for mock_set in bank.get("mock_exam_sets", []):
        coverage_text = ", ".join(
            f"{entry.get('topic_major')} {entry.get('count')}문항"
            for entry in mock_set.get("coverage", [])
        )
        mock_lines.extend(
            [
                f"## {mock_set.get('title')}",
                f"- review_status: {mock_set.get('review_status')}",
                f"- coverage: {coverage_text}",
                "",
            ]
        )
        for item_id in mock_set.get("item_ids", []):
            item = next((entry for entry in bank.get("exam_items", []) if entry.get("id") == item_id), None)
            if not item:
                continue
            bundle = explanations_by_item.get(item_id, {})
            mock_lines.extend(
                [
                    f"### {item_id}",
                    f"- 문항: {item.get('stem')}",
                    f"- 정답: {item.get('official_answer') or item.get('predicted_answer') or '미확정'}",
                    f"- 해설: {bundle.get('answer_basis', '미생성')}",
                    "",
                ]
            )
    (paths.outputs_dir / "mock-exam-set-01.md").write_text("\n".join(mock_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "workspace": str(paths.root),
                "outputs": [
                    "past-analysis.md",
                    "distractor-mandalart.md",
                    "summary-book.md",
                    "mock-exam-set-01.md",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
