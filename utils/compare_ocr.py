from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from utils.constants import RAW_OCR_DIR
from utils.run_ocr import run_all_ocr_candidates
from utils.session_state import (
    get_selected_ocr_candidates_file,
    set_selected_raw_ocr_file,
)


MATCH_THRESHOLD = 0.58
EXTRA_LINE_MIN_SUPPORT = 2


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_line(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return set(_normalize_line(text).split())


def _line_similarity(left: str, right: str) -> float:
    left_norm = _normalize_line(left)
    right_norm = _normalize_line(right)

    if not left_norm or not right_norm:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        left_norm,
        right_norm,
    ).ratio()

    left_tokens = _tokens(left)
    right_tokens = _tokens(right)

    union = left_tokens | right_tokens
    token_score = (
        len(left_tokens & right_tokens) / len(union)
        if union
        else 0.0
    )

    # Strongly reward shared long numeric identifiers. This is useful for
    # receipt SKUs while still allowing one candidate to contain extra fields
    # such as a price or tax marker.
    left_numbers = set(re.findall(r"\b\d{4,}\b", left_norm))
    right_numbers = set(re.findall(r"\b\d{4,}\b", right_norm))

    numeric_anchor = 1.0 if left_numbers & right_numbers else 0.0

    return (
        sequence_score * 0.55
        + token_score * 0.30
        + numeric_anchor * 0.15
    )


def _candidate_metrics(candidate: dict) -> dict:
    result = candidate["result"]
    metrics = result["metrics"]

    mean_confidence = metrics["mean_word_confidence"] or 0.0
    recognized_word_count = metrics["recognized_word_count"]
    low_confidence_rate = metrics["low_confidence_rate"]
    raw_text = result["raw_text"]

    digit_count = len(re.findall(r"\d", raw_text))
    price_like_count = len(
        re.findall(r"\b\d+[.,]\d{2}\b", raw_text)
    )

    score = (
        mean_confidence
        + min(recognized_word_count, 250) * 0.03
        + min(digit_count, 300) * 0.01
        + min(price_like_count, 80) * 0.08
        - low_confidence_rate * 15.0
    )

    return {
        "score": round(score, 4),
        "mean_word_confidence": mean_confidence,
        "recognized_word_count": recognized_word_count,
        "low_confidence_rate": low_confidence_rate,
        "digit_count": digit_count,
        "price_like_count": price_like_count,
    }


def _line_quality(line: dict) -> float:
    text = line["text"]
    confidence = line.get("confidence")

    if confidence is None:
        confidence = 0.0

    token_count = len(text.split())
    digit_count = len(re.findall(r"\d", text))
    price_count = len(
        re.findall(r"\b\d+[.,]\d{2}\b", text)
    )
    sku_count = len(
        re.findall(r"\b\d{5,7}\b", text)
    )

    # Prefer high-confidence lines, but also reward useful receipt structure
    # and fuller versions of the same line. This is intentionally a ranking
    # score, not an accuracy percentage.
    return (
        float(confidence)
        + min(token_count, 14) * 0.55
        + min(digit_count, 16) * 0.22
        + price_count * 3.0
        + sku_count * 2.0
    )


def _build_line_records(candidates: list[dict]) -> list[dict]:
    records = []

    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        variant = candidate["image_variant"]
        psm = candidate["psm"]

        for index, line in enumerate(
            candidate["result"]["text"]
        ):
            text = line.get("text", "").strip()

            if not text:
                continue

            records.append(
                {
                    "candidate_id": candidate_id,
                    "image_variant": variant,
                    "psm": psm,
                    "candidate_line_index": index,
                    "text": text,
                    "confidence": line.get("confidence"),
                }
            )

    return records


def _best_match(
    target_text: str,
    records: list[dict],
    excluded_candidate_id: str | None = None,
) -> tuple[dict | None, float]:
    best_record = None
    best_score = 0.0

    for record in records:
        if (
            excluded_candidate_id is not None
            and record["candidate_id"] == excluded_candidate_id
        ):
            continue

        score = _line_similarity(
            target_text,
            record["text"],
        )

        if score > best_score:
            best_record = record
            best_score = score

    return best_record, best_score


def _support_for_line(
    line: dict,
    candidates: list[dict],
) -> tuple[int, list[dict]]:
    supporting = []

    for candidate in candidates:
        if candidate["candidate_id"] == line["candidate_id"]:
            continue

        best = None
        best_similarity = 0.0

        for candidate_line in candidate["result"]["text"]:
            candidate_text = candidate_line.get("text", "").strip()

            if not candidate_text:
                continue

            similarity = _line_similarity(
                line["text"],
                candidate_text,
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best = candidate_line

        if best is not None and best_similarity >= MATCH_THRESHOLD:
            supporting.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "similarity": round(best_similarity, 4),
                    "text": best["text"],
                }
            )

    return 1 + len(supporting), supporting


def _choose_consensus_line(
    backbone_line: dict,
    all_records: list[dict],
    candidates: list[dict],
) -> dict:
    alternatives = [backbone_line]

    for candidate in candidates:
        if candidate["candidate_id"] == backbone_line["candidate_id"]:
            continue

        candidate_records = [
            record
            for record in all_records
            if record["candidate_id"] == candidate["candidate_id"]
        ]

        match, similarity = _best_match(
            backbone_line["text"],
            candidate_records,
        )

        if match is not None and similarity >= MATCH_THRESHOLD:
            matched = dict(match)
            matched["match_to_backbone"] = round(similarity, 4)
            alternatives.append(matched)

    scored = []

    for alternative in alternatives:
        support_count, supporting = _support_for_line(
            alternative,
            candidates,
        )

        quality = _line_quality(alternative)

        # Consensus is important, but it does not automatically beat a much
        # clearer, more complete line from a single OCR configuration.
        consensus_score = (
            quality
            + (support_count - 1) * 4.0
        )

        scored.append(
            {
                **alternative,
                "support_count": support_count,
                "supporting_candidates": supporting,
                "line_quality_score": round(quality, 4),
                "consensus_score": round(consensus_score, 4),
            }
        )

    scored.sort(
        key=lambda item: (
            item["consensus_score"],
            len(item["text"]),
        ),
        reverse=True,
    )

    return scored[0]


def _collect_supported_extra_lines(
    backbone_candidate: dict,
    candidates: list[dict],
    all_records: list[dict],
) -> list[dict]:
    backbone_texts = [
        line["text"]
        for line in backbone_candidate["result"]["text"]
        if line.get("text", "").strip()
    ]

    extras = []
    seen_normalized = set()

    for record in all_records:
        if record["candidate_id"] == backbone_candidate["candidate_id"]:
            continue

        normalized = _normalize_line(record["text"])

        if not normalized or normalized in seen_normalized:
            continue

        seen_normalized.add(normalized)

        best_backbone_similarity = max(
            (
                _line_similarity(record["text"], text)
                for text in backbone_texts
            ),
            default=0.0,
        )

        if best_backbone_similarity >= MATCH_THRESHOLD:
            continue

        support_count, supporting = _support_for_line(
            record,
            candidates,
        )

        if support_count < EXTRA_LINE_MIN_SUPPORT:
            continue

        extras.append(
            {
                **record,
                "support_count": support_count,
                "supporting_candidates": supporting,
                "line_quality_score": round(
                    _line_quality(record),
                    4,
                ),
            }
        )

    # Deduplicate extras that represent the same line.
    deduplicated = []

    for extra in sorted(
        extras,
        key=lambda item: (
            item["support_count"],
            item["line_quality_score"],
            len(item["text"]),
        ),
        reverse=True,
    ):
        if any(
            _line_similarity(
                extra["text"],
                existing["text"],
            ) >= MATCH_THRESHOLD
            for existing in deduplicated
        ):
            continue

        deduplicated.append(extra)

    return deduplicated


def _score_and_rank_candidates(
    candidates: list[dict],
) -> list[dict]:
    scored = []

    for candidate in candidates:
        scored.append(
            {
                "candidate_id": candidate["candidate_id"],
                "image_variant": candidate["image_variant"],
                "psm": candidate["psm"],
                "comparison_metrics": _candidate_metrics(
                    candidate
                ),
                "result": candidate["result"],
            }
        )

    scored.sort(
        key=lambda item: item[
            "comparison_metrics"
        ]["score"],
        reverse=True,
    )

    return scored


def _get_or_create_candidates_file() -> Path | None:
    candidates_path = get_selected_ocr_candidates_file()

    if (
        candidates_path is not None
        and candidates_path.exists()
    ):
        return candidates_path

    print(
        "[INFO] OCR candidates have not been generated "
        "in this session yet. Running the earlier pipeline "
        "automatically."
    )

    return run_all_ocr_candidates()


def compare_and_build_raw_ocr() -> Path | None:
    candidates_path = _get_or_create_candidates_file()

    if candidates_path is None:
        return None

    candidates_data = _load_json(candidates_path)
    candidates = candidates_data["candidates"]

    if not candidates:
        raise ValueError("OCR candidates file contains no candidates.")

    ranked_candidates = _score_and_rank_candidates(
        candidates
    )

    backbone_ranked = ranked_candidates[0]
    backbone_id = backbone_ranked["candidate_id"]

    backbone_candidate = next(
        candidate
        for candidate in candidates
        if candidate["candidate_id"] == backbone_id
    )

    all_records = _build_line_records(candidates)

    consensus_lines = []

    for line_index, line in enumerate(
        backbone_candidate["result"]["text"],
        start=1,
    ):
        text = line.get("text", "").strip()

        if not text:
            continue

        backbone_record = {
            "candidate_id": backbone_candidate["candidate_id"],
            "image_variant": backbone_candidate["image_variant"],
            "psm": backbone_candidate["psm"],
            "candidate_line_index": line_index - 1,
            "text": text,
            "confidence": line.get("confidence"),
        }

        chosen = _choose_consensus_line(
            backbone_record,
            all_records,
            candidates,
        )

        consensus_lines.append(
            {
                "line_number": len(consensus_lines) + 1,
                "text": chosen["text"],
                "confidence": chosen["confidence"],
                "source_candidate": chosen["candidate_id"],
                "image_variant": chosen["image_variant"],
                "psm": chosen["psm"],
                "support_count": chosen["support_count"],
                "line_quality_score": chosen[
                    "line_quality_score"
                ],
                "consensus_score": chosen[
                    "consensus_score"
                ],
            }
        )

    # Preserve additional content that the clean backbone omitted when that
    # content is independently seen by at least two OCR candidates. Extras
    # are kept separate rather than silently spliced into existing lines.
    extra_lines = _collect_supported_extra_lines(
        backbone_candidate,
        candidates,
        all_records,
    )

    source_receipt = Path(
        candidates_data["source_receipt"]
    )

    output_path = (
        RAW_OCR_DIR
        / f"{source_receipt.stem}_raw_ocr.json"
    )

    raw_text = "\n".join(
        line["text"]
        for line in consensus_lines
    )

    output = {
        "source_receipt": str(source_receipt),
        "selection_method": (
            "multi-candidate consensus: highest-ranked OCR candidate "
            "is used as the reading-order backbone; each backbone line "
            "may be replaced by a higher-quality matching line from any "
            "of the six OCR candidates; independently supported lines "
            "missing from the backbone are preserved separately"
        ),
        "backbone_candidate": {
            "candidate_id": backbone_ranked["candidate_id"],
            "image_variant": backbone_ranked["image_variant"],
            "psm": backbone_ranked["psm"],
            "comparison_metrics": backbone_ranked[
                "comparison_metrics"
            ],
        },
        "consensus_summary": {
            "backbone_line_count": len(
                backbone_candidate["result"]["text"]
            ),
            "consensus_line_count": len(consensus_lines),
            "supported_extra_line_count": len(extra_lines),
            "candidate_count": len(candidates),
            "match_threshold": MATCH_THRESHOLD,
            "extra_line_min_support": EXTRA_LINE_MIN_SUPPORT,
        },
        "raw_text": raw_text,
        "text": consensus_lines,
        "supported_extra_lines": [
            {
                "text": line["text"],
                "confidence": line["confidence"],
                "source_candidate": line["candidate_id"],
                "image_variant": line["image_variant"],
                "psm": line["psm"],
                "support_count": line["support_count"],
                "line_quality_score": line[
                    "line_quality_score"
                ],
            }
            for line in extra_lines
        ],
        "candidate_ranking": [
            {
                "rank": rank,
                "candidate_id": candidate["candidate_id"],
                "image_variant": candidate["image_variant"],
                "psm": candidate["psm"],
                "comparison_metrics": candidate[
                    "comparison_metrics"
                ],
            }
            for rank, candidate in enumerate(
                ranked_candidates,
                start=1,
            )
        ],
        "provenance": {
            "candidates_file": str(
                candidates_path.resolve()
            ),
            "rule": (
                "Consensus output never edits OCR characters inside a "
                "chosen line. Every emitted line is copied verbatim from "
                "one Tesseract candidate, with its source recorded."
            ),
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    set_selected_raw_ocr_file(output_path)

    return output_path.resolve()


def run_compare_ocr() -> None:
    print(
        "\n=== Compare OCR Results / Build Consensus ===\n"
    )

    try:
        output_path = compare_and_build_raw_ocr()

        if output_path is None:
            return

        data = _load_json(output_path)
        backbone = data["backbone_candidate"]
        summary = data["consensus_summary"]

        print(
            "[OK] Consensus OCR built from all candidates."
        )

        print(
            "\nBackbone candidate:"
            f"\nVariant: {backbone['image_variant']}"
            f"\nPSM: {backbone['psm']}"
            "\nScore: "
            f"{backbone['comparison_metrics']['score']}"
        )

        print(
            "\nConsensus:"
            f"\nLines: {summary['consensus_line_count']}"
            "\nSupported extra lines: "
            f"{summary['supported_extra_line_count']}"
        )

        print(
            "\n[OK] Final raw OCR JSON created:"
            f"\n{output_path}"
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
