# Review Checklist

## Automatic Review Queue Rules

Send an item to `review/` if any of these apply:
- official answer key is missing
- predicted and official answers conflict
- user source and authoritative source conflict
- OCR quality is poor
- the question structure is incomplete
- duplicate sources disagree on wording or answer
- confidence is below the chosen threshold

Recommended default thresholds:
- `confidence < 0.80` -> review
- `0.80 <= confidence < 0.92` -> review unless corroborated
- `confidence >= 0.92` -> still review if there is source conflict

## Explanation Completeness

Every analyzed item must include:
- one correct-answer basis statement
- one explanation per choice
- one misconception tag per wrong choice
- one evidence reference set per choice explanation

If any choice explanation is missing, the item is incomplete.

## Distractor Mandal-art Completeness

Each wrong choice must produce one mandal-art record with:
- one center misconception
- eight surrounding axes
- one new question idea for each axis
- one correction condition
- one list of variant question types
- one remediation note
- one `오답 검증형`
- one `오답 교정형`

Missing axes means the item is incomplete.

## Item Mandalart Completeness

Each 4-choice base question must produce one `item_mandalart` with:
- one center question summary
- the fixed 8 cells:
  - `출제의도`
  - `정답 근거`
  - `오답① 분석`
  - `오답② 분석`
  - `오답③ 분석`
  - `조건변형`
  - `형식변형`
  - `피드백`
- 5 to 7 variant items
- one `analysis_card`
- one six-item completion checklist

The minimum required variant set is:
- `원형 유지형`
- `오답 A 기반 변형형`
- `오답 B 기반 변형형`
- `오답 C 기반 변형형`
- `통합 비교형`

Recommended additional items:
- `이유 선택형`
- `오답 교정형`

If the variant set drops below 5 items, the question is incomplete.

## All-Distractors-Reflected Gate

All six checks must pass:
- 오답 3개 각각에 오개념 이름이 붙어 있는가
- 오답 3개 각각에 선택 이유가 적혀 있는가
- 오답 3개 각각에 교정 조건이 적혀 있는가
- 오답 3개 각각으로 전용 변형문항이 1개 이상 만들어졌는가
- 오답 3개 각각에 개별 해설이 있는가
- 어떤 오답도 단순 소거용 보기로만 쓰이지 않았는가

## Summary Book Rules

The summary book must:
- group by official major topic
- infer minor topics from the material if no taxonomy file exists
- link key points back to question IDs or source references
- exclude unresolved items from publication-ready sections

## Mock Exam Rules

A valid mock exam set must:
- declare target coverage
- declare difficulty mix
- distribute misconceptions instead of clustering one error type
- include explanation output together with the question set
- write both Markdown and JSON

## Conflict Handling

When a user file conflicts with an authoritative source:
1. record both sides
2. prefer the authoritative source as a provisional answer
3. set `status=conflict`
4. add the item to the review queue
5. exclude it from publication-ready output

## Publication Gate

Do not generate a final publication bundle unless:
- every included item has `review_status=approved`
- every included item has full choice analysis
- every included distractor has a full mandal-art
- the review queue is empty for all items included in the publication bundle

Allowed final outputs before approval:
- draft Markdown
- draft JSON bank
- review queue

Blocked final outputs before approval:
- publish-ready summary book
- publish-ready mock exam packet
- print-ready final manuscript
