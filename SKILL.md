---
name: fire-ems-exam-author
description: Use when creating Korean firefighter first-aid exam assets for "응급처치학개론", including 기출문항 분석, 요약집 생성, 모의고사 생성, and 오답 만다라트 확장. Supports PDF, PNG/JPG, DOCX, XLSX, HWP, and HWPX inputs, combines user files with authoritative external standards, and produces Markdown plus JSON outputs in the current working directory.
---

# Fire EMS Exam Author

## Overview

Use this skill for four fixed request types:
- `기출 분석`
- `요약집 생성`
- `모의고사 생성`
- `오답 만다라트 확장`

Always write outputs into the current working directory, never into the skill folder.

## Bundled Resources

- `scripts/init_exam_workspace.py`
  - Create the standard workspace folders and starter JSON files in the current working directory.
- `scripts/extract_source_text.py`
  - Copy source files into `sources/`, extract text where possible, and write an intake manifest.
- `references/data-contracts.md`
  - Canonical folder layout and JSON type contracts.
- `references/source-intake.md`
  - Format-specific extraction routes and fallbacks.
- `references/review-checklist.md`
  - Review gates, conflict handling, and publication rules.

Read the references only when needed. Keep the active context lean.

## Inputs

Collect these inputs before analysis:
- Required: source files for the exam content
- Optional: answer key file
- Optional: chapter taxonomy or official unit mapping file

Supported source formats:
- `PDF`
- `PNG`, `JPG`, `JPEG`
- `DOCX`
- `XLSX`
- `HWP`
- `HWPX`

If no answer key is provided, infer the answer and record both `confidence` and `review_status`.

## Default Workspace

Initialize the workspace in the current working directory first:

```bash
python3 /Users/chungji/.codex/skills/fire-ems-exam-author/scripts/init_exam_workspace.py .
```

Standard folders:
- `sources/`
- `bank/`
- `outputs/`
- `review/`

Then ingest files:

```bash
python3 /Users/chungji/.codex/skills/fire-ems-exam-author/scripts/extract_source_text.py --workspace . <source-file>...
```

## Workflow

1. Initialize the workspace in the current working directory.
2. Copy raw files into `sources/` and extract text into `sources/extracted/`.
3. Convert each source into normalized text blocks and provenance records.
4. Structure detected questions into `exam_item` objects.
5. Map each question to topic taxonomy:
   - Use the official firefighter first-aid scope for `topic_major`.
   - Infer `topic_minor` from the source material unless the user supplied a chapter map.
6. Confirm answers:
   - Prefer official answer sheets.
   - If no answer sheet exists, infer answers and set `predicted_answer`, `confidence`, and `review_status`.
7. Generate explanations for every choice:
   - Why the correct answer is right
   - Why each wrong answer is wrong
   - Which misconception each distractor represents
   - Which evidence supports the explanation
8. Expand every wrong choice into a `distractor_mandalart`.
9. Assemble downstream outputs from the same bank:
   - `기출 분석`
   - `요약집`
   - `모의고사`
   - `오답 만다라트`
10. Route low-confidence, conflicting, OCR-damaged, or answer-key-missing items into `review/`.
11. Refuse to produce a publication-ready final pack until review is complete.

## Source Handling Rules

Read `references/source-intake.md` when selecting an extraction route.

Use these routes by default:
- `PDF`: try text extraction first; if the PDF is image-only, use OCR
- `PNG/JPG`: preprocess if needed, then OCR
- `DOCX`: use structured extraction first; fall back to `textutil` if needed
- `XLSX`: extract sheet-wise rows and preserve sheet provenance
- `HWPX`: try ZIP/XML parsing first
- `HWP`: try a dedicated parser or converter first; if unavailable or failed, require `PDF` re-export as the default fallback

Never silently discard a failed source. Record the failure and fallback in `sources/intake-manifest.json`.

## Evidence Rules

Use both:
- user-provided source materials
- authoritative external standards

When external verification is needed, prefer official or professional standards over informal summaries.

If user materials conflict with authoritative standards:
- keep the item
- mark the conflict explicitly
- prefer the authoritative standard as the provisional conclusion
- send the item to `review/`

Record source references in every derived item.

## Required Output Rules

Every run must produce both:
- human-readable `Markdown`
- reusable `JSON`

At minimum:
- `bank/exam-bank.json`
- one or more `outputs/*.md`

Common outputs:
- `outputs/past-analysis.md`
- `outputs/summary-book.md`
- `outputs/mock-exam-set-01.md`
- `outputs/distractor-mandalart.md`
- `review/review-queue.json`
- `review/review-queue.md`

## Quality Bar

Read `references/review-checklist.md` before finalizing.

Do not mark the work complete unless all of the following hold:
- every analyzed item has full choice-by-choice explanations
- every distractor has a mandal-art expansion
- Markdown and JSON were generated together
- all unresolved items were moved to `review/`
- no publication-ready output was produced from unresolved items

## Type Contract

Read `references/data-contracts.md` before building JSON outputs.

Use these normalized internal types:
- `source_document`
- `exam_item`
- `choice_analysis`
- `explanation_bundle`
- `distractor_mandalart`
- `summary_unit`
- `mock_exam_set`

Keep keys stable. If you add extra fields, do not remove the required ones.

## Review and Publication Gate

Publication-ready assets are blocked when any item has:
- `review_status != approved`
- unresolved source conflicts
- OCR quality issues
- missing answer validation

In those cases:
- write the incomplete item to `review/`
- keep it in the bank with explicit status
- exclude it from the final publication bundle

## External Verification Notes

This domain is accuracy-sensitive. When you verify medical or first-aid facts externally:
- prefer current official standards
- capture source name and URL in `source_refs`
- clearly label any inference

Do not hide uncertainty.
