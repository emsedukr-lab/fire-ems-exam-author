#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = ROOT_DIR / "references"

CIRCLED_LABEL_MAP = {
    "①": "A",
    "②": "B",
    "③": "C",
    "④": "D",
    "⑤": "E",
    "⑥": "F",
}
LABEL_SEQUENCE = ["A", "B", "C", "D", "E", "F"]
STOPWORDS = {"가장", "다음", "것은", "하는", "하는가", "무엇인가", "무엇은", "대한", "에서", "으로", "및", "또는", "이다", "있다"}


@dataclass
class WorkspacePaths:
    root: Path
    sources_dir: Path
    extracted_dir: Path
    bank_dir: Path
    outputs_dir: Path
    review_dir: Path
    manifest_path: Path
    bank_path: Path
    source_segments_path: Path
    review_queue_json_path: Path
    review_queue_md_path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def workspace_paths(workspace: str | Path) -> WorkspacePaths:
    root = Path(workspace).expanduser().resolve()
    return WorkspacePaths(
        root=root,
        sources_dir=root / "sources",
        extracted_dir=root / "sources" / "extracted",
        bank_dir=root / "bank",
        outputs_dir=root / "outputs",
        review_dir=root / "review",
        manifest_path=root / "sources" / "intake-manifest.json",
        bank_path=root / "bank" / "exam-bank.json",
        source_segments_path=root / "bank" / "source-segments.json",
        review_queue_json_path=root / "review" / "review-queue.json",
        review_queue_md_path=root / "review" / "review-queue.md",
    )


def default_bank() -> dict[str, Any]:
    return {
        "version": 2,
        "generated_at": utc_now(),
        "source_documents": [],
        "source_segments": [],
        "exam_items": [],
        "answer_resolutions": [],
        "explanation_bundles": [],
        "item_mandalarts": [],
        "distractor_mandalarts": [],
        "summary_units": [],
        "mock_exam_sets": [],
    }


def ensure_bank_shape(bank: dict[str, Any]) -> dict[str, Any]:
    merged = default_bank()
    merged.update(bank)
    for key, default_value in default_bank().items():
        if key not in merged or merged[key] is None:
            merged[key] = default_value
    return merged


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(paths: WorkspacePaths) -> dict[str, Any]:
    return load_json(paths.manifest_path, {"version": 1, "generated_at": utc_now(), "source_documents": []})


def save_manifest(paths: WorkspacePaths, manifest: dict[str, Any]) -> None:
    manifest["generated_at"] = utc_now()
    save_json(paths.manifest_path, manifest)


def load_bank(paths: WorkspacePaths) -> dict[str, Any]:
    bank = load_json(paths.bank_path, default_bank())
    bank = ensure_bank_shape(bank)
    if not bank["source_segments"] and paths.source_segments_path.exists():
        bank["source_segments"] = load_json(paths.source_segments_path, [])
    return bank


def save_bank(paths: WorkspacePaths, bank: dict[str, Any]) -> None:
    bank = ensure_bank_shape(bank)
    bank["generated_at"] = utc_now()
    save_json(paths.bank_path, bank)
    save_json(paths.source_segments_path, bank["source_segments"])


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fingerprint_text(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"[^0-9a-z가-힣]+", "", normalized)
    return normalized


def choice_token_to_label(token: str, index: int) -> str:
    token = token.strip()
    if token in CIRCLED_LABEL_MAP:
        return CIRCLED_LABEL_MAP[token]
    if token.upper() in LABEL_SEQUENCE:
        return token.upper()
    if token.isdigit():
        position = int(token) - 1
        if 0 <= position < len(LABEL_SEQUENCE):
            return LABEL_SEQUENCE[position]
    if index < len(LABEL_SEQUENCE):
        return LABEL_SEQUENCE[index]
    return f"CHOICE_{index + 1}"


def label_to_token(label: str) -> str:
    label = label.strip().upper()
    if label in LABEL_SEQUENCE:
        return label
    return label


def tokenize_korean_text(text: str) -> list[str]:
    tokens = re.findall(r"[0-9a-zA-Z가-힣]{2,}", normalize_text(text).lower())
    return [token for token in tokens if token not in STOPWORDS]


def document_group_key(filename: str) -> str:
    base = Path(filename).stem.lower()
    base = re.sub(r"(정답|답안|answer|answers|해설|solution|sheet|정리|요약)", "", base)
    base = re.sub(r"[^0-9a-z가-힣]+", "", base)
    return base or Path(filename).stem.lower()


def build_item_fingerprint(stem: str, choices: list[dict[str, Any]]) -> str:
    choice_blob = "|".join(fingerprint_text(choice.get("text", "")) for choice in choices)
    return f"{fingerprint_text(stem)}::{choice_blob}"


def detect_quality_flags(text: str, extractor: str, notes: list[str] | None = None) -> list[str]:
    flags: list[str] = []
    normalized = normalize_text(text)
    if extractor == "pytesseract":
        flags.append("ocr_source")
    if "■" in normalized or "�" in normalized:
        flags.append("ocr_garbled")
    if notes:
        if any("OCR" in note or "preprocessed OCR" in note for note in notes):
            flags.append("ocr_review_recommended")
        if any("conversion_required" in note for note in notes):
            flags.append("conversion_required")
    if len(normalized) < 20:
        flags.append("very_short_text")
    return sorted(set(flags))


def load_topic_taxonomy() -> dict[str, Any]:
    return load_json(REFERENCES_DIR / "topic-taxonomy.json", {"majors": []})


def load_authoritative_rules() -> dict[str, Any]:
    return load_json(REFERENCES_DIR / "authoritative-rules.json", {"rules": []})


def infer_topic(text: str, taxonomy: dict[str, Any]) -> tuple[str, str, list[str]]:
    lowered = normalize_text(text).lower()
    best_major = "unknown"
    best_minor = "unknown"
    best_score = 0
    matched_keywords: list[str] = []

    for major in taxonomy.get("majors", []):
        major_keywords = major.get("keywords", [])
        major_score = sum(1 for keyword in major_keywords if keyword.lower() in lowered)
        local_minor = "unknown"
        local_minor_score = 0
        local_keywords: list[str] = []
        for minor in major.get("minors", []):
            minor_keywords = minor.get("keywords", [])
            score = sum(1 for keyword in minor_keywords if keyword.lower() in lowered)
            if score > local_minor_score:
                local_minor_score = score
                local_minor = minor.get("name", "unknown")
                local_keywords = [keyword for keyword in minor_keywords if keyword.lower() in lowered]
        combined_score = major_score + local_minor_score
        if combined_score > best_score:
            best_score = combined_score
            best_major = major.get("name", "unknown")
            best_minor = local_minor
            matched_keywords = [keyword for keyword in major_keywords if keyword.lower() in lowered] + local_keywords

    return best_major, best_minor, sorted(set(matched_keywords))


def classify_document_role(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    question_like = 0
    answer_like = 0
    choice_markers = sum(text.count(marker) for marker in CIRCLED_LABEL_MAP)
    taxonomy_hits = sum(1 for keyword in ["응급의료체계", "심정지", "외상", "재난", "소아응급", "산부인과"] if keyword in text)

    question_re = re.compile(r"^\s*\d{1,3}\s*(?:[.)]|번)\s+\S+")
    answer_re = re.compile(r"^\s*\d{1,3}\s*(?:[.)-]|번)?\s*(?:정답[: ]*)?(?:[①②③④⑤⑥]|[A-Fa-f]|[1-6])\s*$")
    for line in lines:
        if answer_re.match(line):
            answer_like += 1
        if question_re.match(line) and len(line) >= 10:
            question_like += 1

    if answer_like >= max(2, question_like + 1) and choice_markers < 4:
        return "answer_sheet"
    if question_like >= 1 and choice_markers >= 2:
        return "question_sheet"
    if taxonomy_hits >= 2 and choice_markers == 0:
        return "syllabus"
    return "reference"


def _find_choice_matches(body: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen_starts: set[int] = set()
    patterns = [
        re.compile(r"[①②③④⑤⑥]"),
        re.compile(r"(?:(?<=\n)|(?<=\s)|^)([A-Fa-f])[\.\)]\s*"),
        re.compile(r"(?:(?<=\n)|(?<=\s)|^)([1-6])[\.\)]\s*")
    ]
    for pattern in patterns:
        for match in pattern.finditer(body):
            start = match.start()
            if start in seen_starts:
                continue
            raw_label = match.group(0).strip()
            token = match.group(1) if match.lastindex else raw_label
            matches.append({"start": start, "end": match.end(), "token": token})
            seen_starts.add(start)
    matches.sort(key=lambda item: item["start"])
    return matches


def parse_question_segments(text: str, source_document_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    question_start_re = re.compile(r"^\s*(?P<num>\d{1,3})\s*(?:[.)]|번)\s*(?P<body>.+)$")
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        match = question_start_re.match(line.strip())
        looks_like_answer = re.match(r"^\s*\d{1,3}\s*(?:[.)-]|번)?\s*(?:정답[: ]*)?(?:[①②③④⑤⑥]|[A-Fa-f]|[1-6])\s*$", line.strip())
        if match and not looks_like_answer and len(match.group("body")) >= 6:
            if current:
                blocks.append(current)
            current = {
                "item_number": int(match.group("num")),
                "lines": [match.group("body").strip()],
                "line_start": index,
                "line_end": index,
            }
            continue
        if current:
            current["lines"].append(line)
            current["line_end"] = index

    if current:
        blocks.append(current)

    if not blocks:
        paragraphs = [normalize_text(chunk) for chunk in re.split(r"\n\s*\n", text) if normalize_text(chunk)]
        for index, paragraph in enumerate(paragraphs, start=1):
            if len(_find_choice_matches(paragraph)) >= 2:
                blocks.append({
                    "item_number": index,
                    "lines": [paragraph],
                    "line_start": 1,
                    "line_end": 1,
                })

    segments: list[dict[str, Any]] = []
    exam_items: list[dict[str, Any]] = []
    for segment_index, block in enumerate(blocks, start=1):
        raw_text = "\n".join(block["lines"]).strip()
        choice_matches = _find_choice_matches(raw_text)
        if len(choice_matches) < 2:
            segments.append({
                "id": f"seg-{source_document_id}-{segment_index}",
                "source_document_id": source_document_id,
                "segment_type": "question_candidate",
                "item_number": block["item_number"],
                "text": raw_text,
                "normalized_text": normalize_text(raw_text),
                "line_start": block["line_start"],
                "line_end": block["line_end"],
                "choice_count": 0,
                "quality_flags": ["incomplete_structure"],
                "parsing_notes": ["Could not detect at least two choices."],
            })
            continue

        stem = normalize_text(raw_text[:choice_matches[0]["start"]])
        choices: list[dict[str, Any]] = []
        for choice_index, match in enumerate(choice_matches):
            next_start = choice_matches[choice_index + 1]["start"] if choice_index + 1 < len(choice_matches) else len(raw_text)
            choice_text = normalize_text(raw_text[match["end"]:next_start])
            if not choice_text:
                continue
            standardized_label = choice_token_to_label(match["token"], choice_index)
            choices.append({
                "label": standardized_label,
                "original_label": match["token"],
                "text": choice_text,
            })

        quality_flags: list[str] = []
        parsing_notes: list[str] = []
        if len(choices) < 2:
            quality_flags.append("incomplete_structure")
            parsing_notes.append("Detected fewer than two valid choices after parsing.")
        if len({fingerprint_text(choice['text']) for choice in choices}) != len(choices):
            quality_flags.append("duplicate_choices")
            parsing_notes.append("At least two parsed choices are textually duplicated.")
        if not stem:
            quality_flags.append("missing_stem")
            parsing_notes.append("Question stem is empty after parsing.")

        segment_id = f"seg-{source_document_id}-{segment_index}"
        segments.append({
            "id": segment_id,
            "source_document_id": source_document_id,
            "segment_type": "question_candidate",
            "item_number": block["item_number"],
            "text": raw_text,
            "normalized_text": normalize_text(raw_text),
            "line_start": block["line_start"],
            "line_end": block["line_end"],
            "choice_count": len(choices),
            "quality_flags": quality_flags,
            "parsing_notes": parsing_notes,
        })

        exam_items.append({
            "id": f"item-{source_document_id}-{block['item_number']}",
            "item_number": block["item_number"],
            "question_type": "multiple_choice_single_answer",
            "stem": stem,
            "choices": choices,
            "predicted_answer": None,
            "official_answer": None,
            "confidence": 0.0,
            "topic_major": "unknown",
            "topic_minor": "unknown",
            "source_refs": [
                {"kind": "source_document", "value": source_document_id},
                {"kind": "source_segment", "value": segment_id}
            ],
            "source_segment_ids": [segment_id],
            "status": "draft",
            "review_status": "pending",
            "quality_flags": quality_flags,
            "validation_summary": {
                "official_answer_found": False,
                "external_validation_status": "not_started",
                "matched_rule_ids": [],
                "matched_topic_keywords": []
            }
        })

    return segments, exam_items


def parse_answer_entries(text: str, source_document_id: str) -> list[dict[str, Any]]:
    answer_re = re.compile(r"(?m)^\s*(?P<num>\d{1,3})\s*(?:[.)-]|번)?\s*(?:정답[: ]*)?(?P<ans>[①②③④⑤⑥]|[A-Fa-f]|[1-6])\s*$")
    segments: list[dict[str, Any]] = []
    for index, match in enumerate(answer_re.finditer(text), start=1):
        answer_label = choice_token_to_label(match.group("ans"), 0)
        segment_id = f"seg-{source_document_id}-answer-{index}"
        segments.append({
            "id": segment_id,
            "source_document_id": source_document_id,
            "segment_type": "answer_candidate",
            "item_number": int(match.group("num")),
            "answer_label": answer_label,
            "text": normalize_text(match.group(0)),
            "normalized_text": normalize_text(match.group(0)),
            "quality_flags": [],
            "parsing_notes": [],
        })
    return segments


def deduplicate_exam_items(exam_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in exam_items:
        fingerprint = build_item_fingerprint(item["stem"], item["choices"])
        if fingerprint not in merged:
            item["fingerprint"] = fingerprint
            merged[fingerprint] = item
            continue
        existing = merged[fingerprint]
        existing["source_refs"].extend(item["source_refs"])
        existing["source_segment_ids"].extend(item["source_segment_ids"])
        existing["quality_flags"] = sorted(set(existing.get("quality_flags", []) + item.get("quality_flags", [])))
    return list(merged.values())


def build_summary_units(exam_items: list[dict[str, Any]], explanation_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explanation_by_item = {bundle["item_id"]: bundle for bundle in explanation_bundles}
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in exam_items:
        key = (item.get("topic_major", "unknown"), item.get("topic_minor", "unknown"))
        bucket = grouped.setdefault(key, {
            "id": f"summary-{len(grouped) + 1:03d}",
            "topic_major": key[0],
            "topic_minor": key[1],
            "key_points": [],
            "linked_item_ids": [],
            "review_status": "approved",
        })
        bucket["linked_item_ids"].append(item["id"])
        basis = explanation_by_item.get(item["id"], {}).get("answer_basis")
        if basis and basis not in bucket["key_points"]:
            bucket["key_points"].append(basis)
        if item.get("review_status") != "approved":
            bucket["review_status"] = "needs_review"
    for bucket in grouped.values():
        bucket["key_points"] = bucket["key_points"][:5]
    return list(grouped.values())


def render_source_ref_markdown(source_refs: list[dict[str, Any]]) -> str:
    parts = []
    for ref in source_refs:
        kind = ref.get("kind", "source")
        value = ref.get("value", "")
        parts.append(f"{kind}: {value}")
    return "; ".join(parts) if parts else "n/a"


def severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def find_item_answer(
    item: dict[str, Any],
    answer_segments: list[dict[str, Any]],
    source_documents: dict[str, dict[str, Any]],
) -> tuple[str | None, list[str]]:
    group_candidates: list[dict[str, Any]] = []
    global_candidates: list[dict[str, Any]] = []
    source_doc_ids = [ref["value"] for ref in item.get("source_refs", []) if ref.get("kind") == "source_document"]
    source_groups = {
        document_group_key(source_documents.get(doc_id, {}).get("filename", ""))
        for doc_id in source_doc_ids
    }
    item_number = item.get("item_number")

    for segment in answer_segments:
        if segment.get("item_number") != item_number:
            continue
        global_candidates.append(segment)
        answer_doc = source_documents.get(segment.get("source_document_id", ""), {})
        answer_group = document_group_key(answer_doc.get("filename", ""))
        if answer_group in source_groups:
            group_candidates.append(segment)

    preferred = group_candidates or global_candidates
    labels = sorted({candidate.get("answer_label") for candidate in preferred if candidate.get("answer_label")})
    if len(labels) == 1:
        return labels[0], []
    if len(labels) > 1:
        return None, [f"Conflicting official answers detected for item {item_number}: {', '.join(labels)}"]
    return None, []


def score_rule_relevance(item_text: str, rule: dict[str, Any]) -> int:
    lowered = normalize_text(item_text).lower()
    keywords = [keyword.lower() for keyword in rule.get("keywords", [])]
    positive_patterns = [pattern.lower() for pattern in rule.get("positive_patterns", [])]
    return sum(1 for keyword in keywords if keyword in lowered) + sum(1 for pattern in positive_patterns if pattern in lowered)


def score_choice_for_rule(choice_text: str, rule: dict[str, Any]) -> int:
    lowered = normalize_text(choice_text).lower()
    keywords = [keyword.lower() for keyword in rule.get("keywords", [])]
    positive_patterns = [pattern.lower() for pattern in rule.get("positive_patterns", [])]
    negative_patterns = [pattern.lower() for pattern in rule.get("negative_patterns", [])]
    keyword_hits = sum(1 for keyword in keywords if keyword in lowered)
    positive_hits = sum(1 for pattern in positive_patterns if pattern in lowered)
    negative_hits = sum(1 for pattern in negative_patterns if pattern in lowered)
    return keyword_hits * 2 + positive_hits * 3 - negative_hits * 2


def match_authoritative_rule(item: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    item_text = " ".join(
        [item.get("stem", "")]
        + [choice.get("text", "") for choice in item.get("choices", [])]
    )
    scored_rules: list[dict[str, Any]] = []
    for rule in rules:
        relevance = score_rule_relevance(item_text, rule)
        if relevance <= 0:
            continue
        choice_scores = [
            {
                "label": choice.get("label"),
                "score": score_choice_for_rule(choice.get("text", ""), rule),
                "text": choice.get("text", ""),
            }
            for choice in item.get("choices", [])
        ]
        choice_scores.sort(key=lambda entry: (-entry["score"], entry["label"] or ""))
        best = choice_scores[0] if choice_scores else None
        second = choice_scores[1] if len(choice_scores) > 1 else None
        if not best or best["score"] <= 0:
            continue
        scored_rules.append(
            {
                "rule": rule,
                "relevance": relevance,
                "best_choice": best,
                "second_choice": second,
                "score_gap": best["score"] - (second["score"] if second else 0),
            }
        )

    if not scored_rules:
        return None

    scored_rules.sort(
        key=lambda entry: (
            -entry["relevance"],
            -entry["best_choice"]["score"],
            -entry["score_gap"],
            entry["rule"].get("id", ""),
        )
    )
    return scored_rules[0]


def choice_label_to_text(item: dict[str, Any], label: str | None) -> str:
    if not label:
        return ""
    for choice in item.get("choices", []):
        if choice.get("label") == label:
            return choice.get("text", "")
    return ""


def infer_misconception_tag(item: dict[str, Any], choice_text: str, correct_text: str) -> str:
    stem = item.get("stem", "")
    if re.search(r"\d", choice_text) and re.search(r"\d", correct_text):
        return "계산 절차 오류"
    if any(token in choice_text for token in ["항상", "절대", "반드시", "모두"]):
        return "과잉 일반화"
    if any(token in stem for token in ["우선", "먼저", "가장", "초기", "첫"]):
        return "조건 누락"
    if fingerprint_text(choice_text) and fingerprint_text(choice_text) in fingerprint_text(correct_text):
        return "부분정답"
    if tokenize_korean_text(choice_text) and set(tokenize_korean_text(choice_text)) & set(tokenize_korean_text(correct_text)):
        return "개념 혼동"
    if any(token in choice_text for token in ["용어", "정의", "명칭"]):
        return "용어 혼동"
    return "개념 혼동"


def build_review_entry(item_id: str, reason: str, severity: str, recommended_action: str) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "reason": reason,
        "severity": severity,
        "recommended_action": recommended_action,
    }
