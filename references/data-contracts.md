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
- `source_refs`

## exam_item

```json
{
  "id": "item-001",
  "stem": "환자에게 가장 먼저 확인해야 할 것은 무엇인가?",
  "choices": [
    {"label": "A", "text": "호흡"},
    {"label": "B", "text": "의식"},
    {"label": "C", "text": "혈압"},
    {"label": "D", "text": "체온"}
  ],
  "predicted_answer": "B",
  "official_answer": null,
  "confidence": 0.72,
  "topic_major": "응급처치 총론",
  "topic_minor": "초기 평가",
  "source_refs": [
    {"kind": "source_document", "value": "src-001"},
    {"kind": "page", "value": "12"}
  ],
  "status": "needs_review"
}
```

Required fields:
- `stem`
- `choices`
- `predicted_answer`
- `official_answer`
- `confidence`
- `topic_major`
- `topic_minor`
- `source_refs`
- `status`

Recommended `status` values:
- `draft`
- `needs_review`
- `approved`
- `conflict`
- `rejected`

## choice_analysis

```json
{
  "choice_label": "A",
  "is_correct": false,
  "why_wrong_or_right": "호흡 확인은 중요하지만 이 문항의 우선순위는 의식 확인 후 ABC 평가로 이어진다.",
  "misconception_tag": "ABC 순서 혼동",
  "evidence_refs": [
    {"kind": "standard", "value": "공식 응급처치 지침"},
    {"kind": "source_document", "value": "src-001"}
  ]
}
```

Required fields:
- `choice_label`
- `is_correct`
- `why_wrong_or_right`
- `misconception_tag`
- `evidence_refs`

## explanation_bundle

```json
{
  "item_id": "item-001",
  "answer_basis": "초기 평가에서는 의식 상태를 먼저 확인한다.",
  "choice_analyses": [],
  "confidence": 0.72,
  "review_status": "needs_review"
}
```

Required fields:
- `item_id`
- `answer_basis`
- `choice_analyses`
- `confidence`
- `review_status`

## distractor_mandalart

One record per wrong choice.

```json
{
  "item_id": "item-001",
  "choice_label": "A",
  "center_misconception": "호흡 확인이 가장 먼저라고 오해함",
  "axes": [
    {
      "axis": "우선순위 착각",
      "question_idea": "초기 평가에서 가장 먼저 볼 항목을 묻는 변형 문제"
    }
  ],
  "review_status": "draft"
}
```

Rules:
- exactly one `distractor_mandalart` per wrong choice
- exactly 8 axes per record in final output
- each axis must include one new question idea

## summary_unit

```json
{
  "id": "summary-001",
  "topic_major": "응급처치 총론",
  "topic_minor": "초기 평가",
  "key_points": [
    "의식 확인",
    "ABC 평가",
    "현장 안전 확인"
  ],
  "linked_item_ids": ["item-001", "item-014"],
  "review_status": "draft"
}
```

## mock_exam_set

```json
{
  "id": "mock-001",
  "title": "응급처치학개론 모의고사 1회",
  "coverage": [
    {"topic_major": "응급처치 총론", "count": 5}
  ],
  "difficulty_mix": {
    "easy": 0.3,
    "medium": 0.5,
    "hard": 0.2
  },
  "item_ids": ["item-001", "item-002"],
  "has_explanations": true,
  "review_status": "draft"
}
```

## Bank File Shape

`bank/exam-bank.json` should be shaped like this:

```json
{
  "version": 1,
  "generated_at": "2026-03-30T00:00:00Z",
  "source_documents": [],
  "exam_items": [],
  "explanation_bundles": [],
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
    "item_id": "item-001",
    "reason": "official answer missing",
    "severity": "medium",
    "recommended_action": "check source answer key"
  }
]
```
