# Source Intake

## Default Rule

Always preserve the raw file in `sources/` and write extracted text into `sources/extracted/`.

Do not silently skip failed files. Record the failure route in `sources/intake-manifest.json`.

## Format Routes

### PDF

Preferred order:
1. `pypdf` text extraction
2. If the result is empty or clearly image-only, OCR the pages or request OCR-friendly conversion

Notes:
- If page layout fidelity matters later, render-review is a separate step.
- If the PDF is low-quality scanned material, push low-confidence items into `review/`.

### PNG / JPG / JPEG

Preferred order:
1. preprocess with `sips` or OpenCV if needed
2. OCR with `pytesseract` or `tesseract`

When to review:
- skewed scan
- heavy compression
- handwritten annotations
- mixed Korean/English medical abbreviations with low OCR confidence

### DOCX

Preferred order:
1. `python-docx`
2. `textutil` fallback
3. OOXML unzip/XML inspection if the document is malformed

Preserve:
- paragraph order
- table text
- heading hierarchy when possible

### XLSX

Preferred order:
1. `openpyxl` for workbook structure
2. `pandas` for downstream analysis after extraction

Preserve:
- sheet name
- row and column provenance
- formulas as visible text when needed for traceability

### Markdown / TXT

Preferred order:
1. read as UTF-8 text
2. fallback to `cp949` for legacy Korean text exports

Preserve:
- raw paragraph order
- markdown syntax as plain text when the source is `.md`
- original filename and provenance

### HWPX

Preferred order:
1. ZIP/XML parse
2. XML text extraction with structure-aware cleanup
3. fallback to user-provided `PDF` or `DOCX` export if extraction quality is poor

Record:
- whether the file opened as ZIP
- which XML entries were used
- whether extracted text appears structurally complete

### HWP

Preferred order:
1. dedicated parser or converter if available locally
2. dedicated parser via Python module if available locally
3. if both fail, require `PDF` re-export as the default fallback

Do not pretend `strings` output is a full parse. It is only a diagnostic.

If `HWP` conversion fails:
- keep the source in `sources/`
- write a manifest note
- add a review item that requests `PDF` or `HWPX` re-export

## Intake Manifest Expectations

Each source should capture:
- copied path
- extractor used
- text output path if successful
- fallback used if any
- extraction status
- notes for manual review

Recommended statuses:
- `copied`
- `extracted`
- `partial`
- `failed`
- `conversion_required`

## Deduplication

If the same question appears in multiple sources:
- keep one canonical `exam_item`
- append all relevant `source_refs`
- if answers differ across sources, mark `status=conflict` and route to `review/`

## OCR Risk Flags

Flag items for review when any of these happen:
- answer choices are truncated
- numbering is ambiguous
- medical terminology is garbled
- two or more choices look duplicated due to OCR noise
- a question stem crosses page boundaries with broken order
