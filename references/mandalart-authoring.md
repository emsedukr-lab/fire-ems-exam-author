# Mandalart Authoring Standard

## Core Operating Unit

The default production unit for 4-choice items is:

```text
기출 1문항 -> 만다라트 1장 -> 변형문항 5~7개
```

This is the smallest reusable cycle in v1 for Korean firefighter `응급처치학개론`.

## 4-Choice Dedicated 3x3 Frame

Use this fixed layout for every 4-choice multiple-choice item:

| 출제의도 | 정답 근거 | 오답① 분석 |
| --- | --- | --- |
| 오답② 분석 | 중심문항 | 오답③ 분석 |
| 조건변형 | 형식변형 | 피드백 |

The key rule is that each of the three distractors gets its own cell. No distractor is allowed to disappear into a combined `오답논리` slot.

## Center Question

Always record:
- original stem
- full original choices
- resolved answer
- one key concept
- one-sentence exam point

## Distractor Cells

Every distractor cell must record all six of these fields:
- `misconception_tag`
- `selection_reason`
- `key_condition_gap`
- `correction_condition`
- `variant_question_types`
- `remediation_note`

Recommended misconception tags:
- `개념 혼동`
- `조건 누락`
- `계산 절차 오류`
- `과잉 일반화`
- `용어 혼동`
- `부분정답`

## Required Variant Set

For a 4-choice item with 3 distractors, create this minimum 5-item set:
- `원형 유지형`
- `오답 A 기반 변형형`
- `오답 B 기반 변형형`
- `오답 C 기반 변형형`
- `통합 비교형`

Recommended default 7-item set:
- minimum 5-item set above
- `이유 선택형`
- `오답 교정형`

## Dedicated Distractor Variant Rule

For each distractor:
- create one dedicated variant where that distractor becomes correct after the condition is changed
- keep the original correct answer as a misuse distractor
- reuse the other two distractor families as supporting distractors

That means each distractor should appear at least twice:
- once as an actual distractor in the source item
- once as the focus of its own dedicated variant

Prefer reusing it additional times as a supporting distractor in other dedicated variants and in the integrated comparison item.

## Integrated Comparison Rule

Every 4-choice set must include one integrated comparison item.

Preferred prompts:
- `다음 중 가장 적절한 것은?`
- `다음 설명 중 옳은 것만을 고르면?`
- `다음 중 선지 ①, ②, ③이 틀린 이유로 가장 적절한 것은?`

Its job is to compare all three distractors against the answer boundary in a single item.

## Completion Checklist

All six checks must pass before the distractor reflection is considered complete:
- every distractor has a misconception name
- every distractor has a recorded selection reason
- every distractor has a correction condition
- every distractor has at least one dedicated variant
- every distractor has an individual explanation
- no distractor is used only as an elimination filler

## Output Mapping

Map this standard to JSON like this:
- `item_mandalart.frame_type = four_choice_dedicated`
- `item_mandalart.layout`
- `item_mandalart.center_question`
- `item_mandalart.cells`
- `item_mandalart.analysis_card`
- `item_mandalart.variant_items`
- `item_mandalart.completion_checklist`
- `distractor_mandalart.center_misconception`
- `distractor_mandalart.student_reason`
- `distractor_mandalart.key_condition_gap`
- `distractor_mandalart.correction_condition`
- `distractor_mandalart.variant_question_types`
- `distractor_mandalart.remediation_note`
