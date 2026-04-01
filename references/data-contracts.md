# Data Contracts

## Folder Layout

All generated artifacts must stay under the current working directory.

```text
./sources/
./sources/extracted/
./bank/
./outputs/
./review/
```

Required files:
- `sources/intake-manifest.json`
- `bank/exam-bank.json`
- `bank/source-segments.json`
- `review/review-queue.json`
- `review/review-queue.md`

## source_document

```json
{
  "id": "src-001",
  "filename": "2024-emt-past.pdf",
  "copied_path": "sources/2024-emt-past.pdf",
  "media_type": "pdf",
  "extractor": "pypdf",
  "text_path": "sources/extracted/src-001.txt",
  "status": "extracted",
  "fallback_used": null,
  "document_role": "question_sheet",
  "quality_flags": [],
  "segments": ["seg-src-001-1"],
  "notes": [],
  "source_refs": [
    {
      "kind": "file",
      "value": "sources/2024-emt-past.pdf"
    }
  ]
}
```

Required fields:
- `id`
- `filename`
- `copied_path`
- `media_type`
- `extractor`
- `status`
- `document_role`
- `quality_flags`
- `source_refs`

Recommended `document_role` values:
- `question_sheet`
- `answer_sheet`
- `syllabus`
- `reference`
- `unknown`

## source_segment

```json
{
  "id": "seg-src-001-1",
  "source_document_id": "src-001",
  "segment_type": "question_candidate",
  "item_number": 1,
  "text": "환자에게 가장 먼저 확인해야 할 것은 무엇인가? ① 호흡 ② 의식 ③ 혈압 ④ 체온",
  "normalized_text": "환자에게 가장 먼저 확인해야 할 것은 무엇인가? ① 호흡 ② 의식 ③ 혈압 ④ 체온",
  "line_start": 12,
  "line_end": 15,
  "choice_count": 4,
  "quality_flags": [],
  "parsing_notes": []
}
```

Required fields:
- `id`
- `source_document_id`
- `segment_type`
- `text`
- `normalized_text`
- `quality_flags`
- `parsing_notes`

## exam_item

```json
{
  "id": "item-src-001-1",
  "item_number": 1,
  "question_type": "multiple_choice_single_answer",
  "stem": "환자에게 가장 먼저 확인해야 할 것은 무엇인가?",
  "choices": [
    {"label": "A", "text": "호흡"},
    {"label": "B", "text": "의식"},
    {"label": "C", "text": "혈압"},
    {"label": "D", "text": "체온"}
  ],
  "predicted_answer": "B",
  "official_answer": null,
  "confidence": 0.84,
  "topic_major": "전문심장소생술",
  "topic_minor": "심정지",
  "source_refs": [
    {"kind": "source_document", "value": "src-001"},
    {"kind": "source_segment", "value": "seg-src-001-1"}
  ],
  "source_segment_ids": ["seg-src-001-1"],
  "quality_flags": [],
  "status": "needs_review",
  "review_status": "needs_review",
  "validation_summary": {
    "official_answer_found": false,
    "external_validation_status": "matched",
    "matched_rule_ids": ["responsiveness-breathing-check"],
    "matched_topic_keywords": ["반응", "의식", "호흡"],
    "conflict_note": null,
    "review_reasons": ["official answer missing"]
  }
}
```

Required fields:
- `id`
- `item_number`
- `question_type`
- `stem`
- `choices`
- `predicted_answer`
- `official_answer`
- `confidence`
- `topic_major`
- `topic_minor`
- `source_refs`
- `source_segment_ids`
- `status`
- `review_status`
- `validation_summary`

Recommended `status` values:
- `draft`
- `needs_review`
- `approved`
- `conflict`
- `rejected`

## answer_resolution

```json
{
  "id": "answer-item-src-001-1",
  "item_id": "item-src-001-1",
  "official_answer": null,
  "predicted_answer": "B",
  "final_answer": "B",
  "confidence": 0.84,
  "topic_major": "전문심장소생술",
  "topic_minor": "심정지",
  "external_validation_status": "matched",
  "matched_rule_ids": ["responsiveness-breathing-check"],
  "matched_topic_keywords": ["반응", "의식", "호흡"],
  "conflict_note": null,
  "review_status": "needs_review",
  "review_reasons": ["official answer missing"],
  "source_refs": [
    {"kind": "source_document", "value": "src-001"}
  ]
}
```

Required fields:
- `id`
- `item_id`
- `official_answer`
- `predicted_answer`
- `final_answer`
- `confidence`
- `external_validation_status`
- `review_status`
- `review_reasons`

## choice_analysis

```json
{
  "choice_label": "A",
  "is_correct": false,
  "why_wrong_or_right": "`호흡`은 중요하지만 이 문항의 우선 확인 항목이라는 조건을 충족하지 않는다.",
  "misconception_tag": "조건 누락",
  "student_reason": "`호흡`이 응급상황의 핵심 요소라 정답처럼 느껴질 수 있다.",
  "key_condition_gap": "문항이 묻는 것은 우선순위 판단이다.",
  "correction_condition": "`호흡`이 맞으려면 우선순위가 아니라 다른 평가 상황을 묻도록 문항이 바뀌어야 한다.",
  "evidence_strength": "medium",
  "external_validation_status": "matched",
  "evidence_refs": [
    {"kind": "url", "value": "https://cpr.heart.org/en/resources/what-is-cpr"}
  ]
}
```

Required fields:
- `choice_label`
- `is_correct`
- `why_wrong_or_right`
- `misconception_tag`
- `student_reason`
- `key_condition_gap`
- `correction_condition`
- `evidence_strength`
- `external_validation_status`
- `evidence_refs`

## explanation_bundle

```json
{
  "item_id": "item-src-001-1",
  "answer_basis": "심정지 인지는 반응과 호흡 상태를 즉시 확인하는 것에서 시작한다.",
  "official_basis": null,
  "external_basis": "심정지 인지는 반응과 호흡 상태를 즉시 확인하는 것에서 시작한다.",
  "choice_analyses": [],
  "confidence": 0.84,
  "conflict_note": null,
  "source_confidence_reason": "official answer missing",
  "review_status": "needs_review"
}
```

Required fields:
- `item_id`
- `answer_basis`
- `choice_analyses`
- `confidence`
- `review_status`

## item_mandalart

One record per base question. For 4-choice items, use the dedicated 3x3 frame.

```json
{
  "item_id": "item-src-001-1",
  "frame_type": "four_choice_dedicated",
  "layout": [
    ["출제의도", "정답 근거", "오답① 분석"],
    ["오답② 분석", "중심문항", "오답③ 분석"],
    ["조건변형", "형식변형", "피드백"]
  ],
  "center_question": {
    "stem": "환자에게 가장 먼저 확인해야 할 것은 무엇인가?",
    "answer_label": "B",
    "answer_text": "의식",
    "key_concept": "심정지",
    "exam_point": "반응과 호흡 상태를 즉시 확인하는 것에서 시작한다."
  },
  "cells": [
    {
      "axis": "오답① 분석",
      "choice_label": "A",
      "choice_text": "호흡",
      "misconception_tag": "조건 누락",
      "selection_reason": "`호흡`이 응급상황의 핵심 요소라 정답처럼 느껴질 수 있다.",
      "key_condition_gap": "문항이 묻는 것은 우선순위 판단이다.",
      "correction_condition": "`호흡`이 맞으려면 우선순위가 아닌 다른 상황을 묻도록 문항이 바뀌어야 한다.",
      "variant_question_types": ["A 기반 변형형", "통합 비교형", "오답 교정형"],
      "remediation_note": "`호흡`은 중요하지만 이 문항의 우선 확인 항목이라는 조건을 충족하지 않는다."
    },
    {
      "axis": "출제의도",
      "content": [
        "무엇을 아는지가 아니라 무엇을 판단하는지 묻는다."
      ]
    }
  ],
  "analysis_card": {
    "original_question": {
      "stem": "환자에게 가장 먼저 확인해야 할 것은 무엇인가?",
      "choices": [],
      "answer_label": "B"
    },
    "distractors": []
  },
  "variant_items": [
    {
      "id": "item-src-001-1-variant-01",
      "format": "원형 유지형",
      "role": "원형 유지형",
      "stem": "환자에게 가장 먼저 확인해야 할 것은 무엇인가?",
      "choices": [],
      "answer": "B. 의식",
      "explanation": "정답 근거"
    },
    {
      "id": "item-src-001-1-variant-02",
      "format": "전용 변형형",
      "role": "A 기반 변형형",
      "stem": "원문항의 선지 A가 맞아지도록 조건을 바꾼 상황으로 가장 적절한 것은?",
      "choices": [],
      "answer": "A. 수정된 선지",
      "explanation": "원래 오답 A는 특정 조건이 추가될 때만 맞아진다."
    }
  ],
  "completion_checklist": [
    {
      "criterion": "misconception_tagged",
      "label": "오답 3개 각각에 오개념 이름이 붙어 있는가",
      "passed": true
    }
  ],
  "review_status": "needs_review"
}
```

Rules:
- exactly one `item_mandalart` per `exam_item`
- for 4-choice items, use exactly 8 surrounding cells with:
  - `출제의도`
  - `정답 근거`
  - `오답① 분석`
  - `오답② 분석`
  - `오답③ 분석`
  - `조건변형`
  - `형식변형`
  - `피드백`
- `variant_items` target count is 5 to 7 per 4-choice item
- `analysis_card.distractors` must preserve one block per distractor
- `completion_checklist` must mirror the six-item distractor reflection audit

## distractor_mandalart

One record per wrong choice.

```json
{
  "item_id": "item-src-001-1",
  "choice_label": "A",
  "choice_text": "호흡",
  "center_misconception": "조건 누락",
  "student_reason": "`호흡`이 응급상황의 핵심 요소라 정답처럼 느껴질 수 있다.",
  "key_condition_gap": "문항이 묻는 것은 우선순위 판단이다.",
  "correction_condition": "`호흡`이 맞으려면 우선순위가 아닌 다른 상황을 묻도록 문항이 바뀌어야 한다.",
  "variant_question_types": ["A 기반 변형형", "통합 비교형", "오답 교정형"],
  "remediation_note": "`호흡`은 중요하지만 이 문항의 우선 확인 항목이라는 조건을 충족하지 않는다.",
  "axes": [
    {
      "axis": "출제의도",
      "question_idea": "선지 A를 고르는 학생이 어떤 판단 기준을 잘못 잡는지 묻는 문항"
    }
  ],
  "variant_items": [
    {
      "format": "오답 검증형",
      "stem": "선지 A가 왜 틀렸는가?",
      "answer": "오답 근거"
    }
  ],
  "dedicated_variant_ids": ["item-src-001-1-variant-02"],
  "appearance_roles": ["원문항", "A 기반 변형형 정답화", "통합 비교형"],
  "appearance_variant_ids": ["item-src-001-1-variant-02", "item-src-001-1-variant-05"],
  "review_status": "needs_review"
}
```

Rules:
- exactly one `distractor_mandalart` per wrong choice
- exactly 8 axes per record in final output
- each axis must include one new question idea
- each record should include at least:
  - `오답 검증형` 1개
  - `오답 교정형` 1개
- each record must include:
  - `correction_condition`
  - `variant_question_types`
  - `remediation_note`
  - `dedicated_variant_ids`
  - `appearance_roles`

## summary_unit

```json
{
  "id": "summary-001",
  "topic_major": "전문심장소생술",
  "topic_minor": "심정지",
  "key_points": [
    "반응 확인",
    "호흡 확인",
    "조기 제세동"
  ],
  "linked_item_ids": ["item-src-001-1"],
  "review_status": "needs_review"
}
```

## mock_exam_set

```json
{
  "id": "mock-001",
  "title": "응급처치학개론 모의고사 1회",
  "coverage": [
    {"topic_major": "전문심장소생술", "count": 5}
  ],
  "difficulty_mix": {
    "easy": 0.3,
    "medium": 0.5,
    "hard": 0.2
  },
  "item_ids": ["item-src-001-1"],
  "has_explanations": true,
  "review_status": "draft"
}
```

## Bank File Shape

`bank/exam-bank.json` should be shaped like this:

```json
{
  "version": 2,
  "generated_at": "2026-03-30T00:00:00Z",
  "source_documents": [],
  "source_segments": [],
  "exam_items": [],
  "answer_resolutions": [],
  "explanation_bundles": [],
  "item_mandalarts": [],
  "distractor_mandalarts": [],
  "summary_units": [],
  "mock_exam_sets": []
}
```

## Review Queue Shape

`review/review-queue.json` should list only unresolved items:

```json
[
  {
    "item_id": "item-src-001-1",
    "reason": "official answer missing",
    "severity": "high",
    "recommended_action": "정답표 또는 공식 해설을 확인하세요."
  }
]
```
