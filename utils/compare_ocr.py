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


# ---------------------------------------------------------------------------
# CONSENSUS SETTINGS
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 0.58
EXTRA_LINE_MIN_SUPPORT = 2

# Aldi item/product codes in the current receipts are normally six digits.
# Keeping this strict prevents prices, dates, transaction numbers, etc.
# from accidentally becoming product-line anchors.
SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


# ---------------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_line(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return set(_normalize_line(text).split())


def _extract_skus(text: str) -> set[str]:
    """
    Return all exact six-digit product codes found in an OCR line.

    We deliberately do NOT try to repair OCR mistakes here.

    Example:

        356537 Cilantro
        356537 Cilantro 0.89 FA

    both return:

        {"356537"}

    while:

        356578 Parsley each

    returns a different SKU and therefore cannot be hard-matched to
    256578 Parsley each.
    """
    return set(
        SKU_PATTERN.findall(text)
    )


def _shared_sku(
    left: str,
    right: str,
) -> str | None:
    """
    Return an exact SKU shared by both lines, if one exists.
    """
    shared = (
        _extract_skus(left)
        & _extract_skus(right)
    )

    if not shared:
        return None

    return sorted(shared)[0]


def _same_sku_line(
    left: str,
    right: str,
) -> bool:
    return _shared_sku(left, right) is not None


# ---------------------------------------------------------------------------
# LINE SIMILARITY
# ---------------------------------------------------------------------------

def _line_similarity(
    left: str,
    right: str,
) -> float:
    """
    General fuzzy similarity for lines that do not necessarily contain
    an exact SKU.

    Exact shared SKUs receive a strong bonus because they are excellent
    evidence that two OCR candidates are looking at the same product line.
    """
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
        len(left_tokens & right_tokens)
        / len(union)
        if union
        else 0.0
    )

    left_numbers = set(
        re.findall(
            r"\b\d{4,}\b",
            left_norm,
        )
    )

    right_numbers = set(
        re.findall(
            r"\b\d{4,}\b",
            right_norm,
        )
    )

    numeric_anchor = (
        1.0
        if left_numbers & right_numbers
        else 0.0
    )

    score = (
        sequence_score * 0.55
        + token_score * 0.30
        + numeric_anchor * 0.15
    )

    # Exact six-digit SKU agreement is stronger evidence than ordinary
    # fuzzy similarity. Raise the effective similarity enough to guarantee
    # that the lines are eligible to compete with each other.
    if _same_sku_line(left, right):
        score = max(
            score,
            0.90,
        )

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# CANDIDATE RANKING
# ---------------------------------------------------------------------------

def _candidate_metrics(candidate: dict) -> dict:
    result = candidate["result"]
    metrics = result["metrics"]

    mean_confidence = (
        metrics["mean_word_confidence"]
        or 0.0
    )

    recognized_word_count = (
        metrics["recognized_word_count"]
    )

    low_confidence_rate = (
        metrics["low_confidence_rate"]
    )

    raw_text = result["raw_text"]

    digit_count = len(
        re.findall(
            r"\d",
            raw_text,
        )
    )

    price_like_count = len(
        re.findall(
            r"\b\d+[.,]\d{2}\b",
            raw_text,
        )
    )

    score = (
        mean_confidence
        + min(
            recognized_word_count,
            250,
        ) * 0.03
        + min(
            digit_count,
            300,
        ) * 0.01
        + min(
            price_like_count,
            80,
        ) * 0.08
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


# ---------------------------------------------------------------------------
# LINE QUALITY
# ---------------------------------------------------------------------------

def _line_quality(line: dict) -> float:
    """
    Rank competing OCR readings.

    This is NOT an accuracy percentage.

    The score favors:
        - Tesseract confidence
        - complete product descriptions
        - numeric information
        - prices
        - SKUs
        - common receipt tax/category markers
    """
    text = line["text"]

    confidence = line.get(
        "confidence"
    )

    if confidence is None:
        confidence = 0.0

    token_count = len(
        text.split()
    )

    digit_count = len(
        re.findall(
            r"\d",
            text,
        )
    )

    price_count = len(
        re.findall(
            r"\b\d+[.,]\d{2}\b",
            text,
        )
    )

    sku_count = len(
        _extract_skus(text)
    )

    tax_marker_count = len(
        re.findall(
            r"\b(?:FA|FB|NA|NB)\b",
            text,
            flags=re.IGNORECASE,
        )
    )

    return (
        float(confidence)
        + min(
            token_count,
            14,
        ) * 0.55
        + min(
            digit_count,
            16,
        ) * 0.22
        + price_count * 3.0
        + sku_count * 2.0
        + tax_marker_count * 1.5
    )


# ---------------------------------------------------------------------------
# BUILD FLAT LINE RECORDS
# ---------------------------------------------------------------------------

def _build_line_records(
    candidates: list[dict],
) -> list[dict]:
    records = []

    for candidate in candidates:
        candidate_id = candidate[
            "candidate_id"
        ]

        variant = candidate[
            "image_variant"
        ]

        psm = candidate["psm"]

        for index, line in enumerate(
            candidate["result"]["text"]
        ):
            text = line.get(
                "text",
                "",
            ).strip()

            if not text:
                continue

            records.append(
                {
                    "candidate_id": candidate_id,
                    "image_variant": variant,
                    "psm": psm,
                    "candidate_line_index": index,
                    "text": text,
                    "confidence": line.get(
                        "confidence"
                    ),
                    "skus": sorted(
                        _extract_skus(text)
                    ),
                }
            )

    return records


# ---------------------------------------------------------------------------
# MATCHING
# ---------------------------------------------------------------------------

def _best_match(
    target_text: str,
    records: list[dict],
    excluded_candidate_id: str | None = None,
) -> tuple[dict | None, float, str]:
    """
    Find the best corresponding OCR line.

    Matching priority:

        1. exact shared SKU
        2. ordinary fuzzy similarity

    Returns:

        record
        score
        match_method
    """
    eligible_records = []

    for record in records:
        if (
            excluded_candidate_id is not None
            and record["candidate_id"]
            == excluded_candidate_id
        ):
            continue

        eligible_records.append(record)

    # ---------------------------------------------------------------
    # FIRST PASS: exact SKU
    # ---------------------------------------------------------------

    sku_matches = []

    for record in eligible_records:
        shared_sku = _shared_sku(
            target_text,
            record["text"],
        )

        if shared_sku is None:
            continue

        similarity = _line_similarity(
            target_text,
            record["text"],
        )

        quality = _line_quality(
            record
        )

        sku_matches.append(
            (
                record,
                similarity,
                quality,
            )
        )

    if sku_matches:
        sku_matches.sort(
            key=lambda item: (
                item[2],
                item[1],
                len(item[0]["text"]),
            ),
            reverse=True,
        )

        record, similarity, _ = (
            sku_matches[0]
        )

        return (
            record,
            similarity,
            "sku",
        )

    # ---------------------------------------------------------------
    # SECOND PASS: fuzzy matching
    # ---------------------------------------------------------------

    best_record = None
    best_score = 0.0

    for record in eligible_records:
        score = _line_similarity(
            target_text,
            record["text"],
        )

        if score > best_score:
            best_record = record
            best_score = score

    return (
        best_record,
        best_score,
        "fuzzy",
    )


# ---------------------------------------------------------------------------
# SUPPORT COUNTING
# ---------------------------------------------------------------------------

def _support_for_line(
    line: dict,
    candidates: list[dict],
) -> tuple[int, list[dict]]:
    """
    Count how many OCR candidates independently support this reading.

    An exact SKU match counts as support even when the remainder of the
    line differs substantially.
    """
    supporting = []

    for candidate in candidates:
        if (
            candidate["candidate_id"]
            == line["candidate_id"]
        ):
            continue

        candidate_records = []

        for index, candidate_line in enumerate(
            candidate["result"]["text"]
        ):
            candidate_text = candidate_line.get(
                "text",
                "",
            ).strip()

            if not candidate_text:
                continue

            candidate_records.append(
                {
                    "candidate_id": candidate[
                        "candidate_id"
                    ],
                    "image_variant": candidate[
                        "image_variant"
                    ],
                    "psm": candidate["psm"],
                    "candidate_line_index": index,
                    "text": candidate_text,
                    "confidence": candidate_line.get(
                        "confidence"
                    ),
                }
            )

        best, similarity, method = (
            _best_match(
                line["text"],
                candidate_records,
            )
        )

        if best is None:
            continue

        supported = (
            method == "sku"
            or similarity
            >= MATCH_THRESHOLD
        )

        if not supported:
            continue

        supporting.append(
            {
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "similarity": round(
                    similarity,
                    4,
                ),
                "match_method": method,
                "text": best["text"],
            }
        )

    return (
        1 + len(supporting),
        supporting,
    )


# ---------------------------------------------------------------------------
# CONSENSUS SELECTION
# ---------------------------------------------------------------------------

def _choose_consensus_line(
    backbone_line: dict,
    all_records: list[dict],
    candidates: list[dict],
) -> dict:
    """
    Choose the best reading for one backbone line.

    Product lines with matching SKUs compete directly even if their
    ordinary fuzzy similarity would previously have fallen below the
    threshold.
    """
    alternatives = [
        {
            **backbone_line,
            "match_to_backbone": 1.0,
            "match_method": "backbone",
        }
    ]

    for candidate in candidates:
        if (
            candidate["candidate_id"]
            == backbone_line["candidate_id"]
        ):
            continue

        candidate_records = [
            record
            for record in all_records
            if record["candidate_id"]
            == candidate["candidate_id"]
        ]

        (
            match,
            similarity,
            method,
        ) = _best_match(
            backbone_line["text"],
            candidate_records,
        )

        if match is None:
            continue

        accepted = (
            method == "sku"
            or similarity
            >= MATCH_THRESHOLD
        )

        if not accepted:
            continue

        matched = dict(match)

        matched[
            "match_to_backbone"
        ] = round(
            similarity,
            4,
        )

        matched[
            "match_method"
        ] = method

        alternatives.append(
            matched
        )

    scored = []

    for alternative in alternatives:
        (
            support_count,
            supporting,
        ) = _support_for_line(
            alternative,
            candidates,
        )

        quality = _line_quality(
            alternative
        )

        consensus_score = (
            quality
            + (
                support_count - 1
            ) * 4.0
        )

        # If this is a SKU product line and it contains a price, reward
        # completeness. This helps:
        #
        #     356537 Cilantro
        #
        # lose to:
        #
        #     356537 Cilantro 0.89 FA
        #
        # while still requiring the winning text to come verbatim from
        # an actual OCR candidate.
        has_sku = bool(
            _extract_skus(
                alternative["text"]
            )
        )

        has_price = bool(
            re.search(
                r"\b\d+[.,]\d{2}\b",
                alternative["text"],
            )
        )

        if has_sku and has_price:
            consensus_score += 4.0

        scored.append(
            {
                **alternative,
                "support_count": support_count,
                "supporting_candidates": supporting,
                "line_quality_score": round(
                    quality,
                    4,
                ),
                "consensus_score": round(
                    consensus_score,
                    4,
                ),
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


# ---------------------------------------------------------------------------
# EXTRA LINE HANDLING
# ---------------------------------------------------------------------------

def _record_matches_consensus(
    record: dict,
    consensus_lines: list[dict],
) -> bool:
    """
    Determine whether a candidate line is already represented by the
    final consensus.

    SKU identity is checked BEFORE fuzzy similarity. This prevents a
    fuller product line from appearing as a false 'extra' merely because
    its description/price differs from the backbone version.
    """
    for consensus in consensus_lines:
        if _same_sku_line(
            record["text"],
            consensus["text"],
        ):
            return True

        similarity = _line_similarity(
            record["text"],
            consensus["text"],
        )

        if similarity >= MATCH_THRESHOLD:
            return True

    return False


def _collect_supported_extra_lines(
    candidates: list[dict],
    all_records: list[dict],
    consensus_lines: list[dict],
) -> list[dict]:
    """
    Preserve independently supported OCR content that genuinely does not
    correspond to an already-selected consensus line.

    Unlike the previous version, this compares extras against the FINAL
    consensus rather than only against the original backbone.
    """
    extras = []
    seen_normalized = set()

    for record in all_records:
        normalized = _normalize_line(
            record["text"]
        )

        if (
            not normalized
            or normalized
            in seen_normalized
        ):
            continue

        seen_normalized.add(
            normalized
        )

        if _record_matches_consensus(
            record,
            consensus_lines,
        ):
            continue

        (
            support_count,
            supporting,
        ) = _support_for_line(
            record,
            candidates,
        )

        if (
            support_count
            < EXTRA_LINE_MIN_SUPPORT
        ):
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

    # ---------------------------------------------------------------
    # Deduplicate extras
    # ---------------------------------------------------------------

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
        duplicate = False

        for existing in deduplicated:
            if _same_sku_line(
                extra["text"],
                existing["text"],
            ):
                duplicate = True
                break

            if (
                _line_similarity(
                    extra["text"],
                    existing["text"],
                )
                >= MATCH_THRESHOLD
            ):
                duplicate = True
                break

        if duplicate:
            continue

        deduplicated.append(
            extra
        )

    return deduplicated


# ---------------------------------------------------------------------------
# CANDIDATE RANKING
# ---------------------------------------------------------------------------

def _score_and_rank_candidates(
    candidates: list[dict],
) -> list[dict]:
    scored = []

    for candidate in candidates:
        scored.append(
            {
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate["psm"],
                "comparison_metrics": (
                    _candidate_metrics(
                        candidate
                    )
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


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

def _get_or_create_candidates_file() -> Path | None:
    candidates_path = (
        get_selected_ocr_candidates_file()
    )

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
    candidates_path = (
        _get_or_create_candidates_file()
    )

    if candidates_path is None:
        return None

    candidates_data = _load_json(
        candidates_path
    )

    candidates = candidates_data[
        "candidates"
    ]

    if not candidates:
        raise ValueError(
            "OCR candidates file contains no candidates."
        )

    ranked_candidates = (
        _score_and_rank_candidates(
            candidates
        )
    )

    backbone_ranked = (
        ranked_candidates[0]
    )

    backbone_id = backbone_ranked[
        "candidate_id"
    ]

    backbone_candidate = next(
        candidate
        for candidate in candidates
        if candidate["candidate_id"]
        == backbone_id
    )

    all_records = (
        _build_line_records(
            candidates
        )
    )

    consensus_lines = []

    sku_anchored_replacements = 0

    for line_index, line in enumerate(
        backbone_candidate["result"]["text"],
        start=1,
    ):
        text = line.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        backbone_record = {
            "candidate_id": backbone_candidate[
                "candidate_id"
            ],
            "image_variant": backbone_candidate[
                "image_variant"
            ],
            "psm": backbone_candidate["psm"],
            "candidate_line_index": (
                line_index - 1
            ),
            "text": text,
            "confidence": line.get(
                "confidence"
            ),
        }

        chosen = _choose_consensus_line(
            backbone_record,
            all_records,
            candidates,
        )

        if (
            chosen["candidate_id"]
            != backbone_record["candidate_id"]
            and chosen.get(
                "match_method"
            ) == "sku"
        ):
            sku_anchored_replacements += 1

        consensus_lines.append(
            {
                "line_number": (
                    len(consensus_lines)
                    + 1
                ),
                "text": chosen["text"],
                "confidence": chosen[
                    "confidence"
                ],
                "source_candidate": chosen[
                    "candidate_id"
                ],
                "image_variant": chosen[
                    "image_variant"
                ],
                "psm": chosen["psm"],
                "support_count": chosen[
                    "support_count"
                ],
                "match_method": chosen.get(
                    "match_method",
                    "unknown",
                ),
                "line_quality_score": chosen[
                    "line_quality_score"
                ],
                "consensus_score": chosen[
                    "consensus_score"
                ],
            }
        )

    # Compare candidate leftovers against the FINAL consensus rather than
    # the original backbone. This should substantially reduce the previous
    # 68 "supported extras" that were actually alternate product readings.
    extra_lines = (
        _collect_supported_extra_lines(
            candidates,
            all_records,
            consensus_lines,
        )
    )

    source_receipt = Path(
        candidates_data[
            "source_receipt"
        ]
    )

    output_path = (
        RAW_OCR_DIR
        / (
            f"{source_receipt.stem}"
            "_raw_ocr.json"
        )
    )

    raw_text = "\n".join(
        line["text"]
        for line in consensus_lines
    )

    output = {
        "source_receipt": str(
            source_receipt
        ),

        "selection_method": (
            "multi-candidate SKU-anchored consensus: "
            "highest-ranked OCR candidate supplies reading order; "
            "exact six-digit product codes are used as hard alignment "
            "anchors across candidates; the highest-quality supported "
            "verbatim OCR reading is selected for each backbone line; "
            "fuzzy matching is retained for non-product lines"
        ),

        "backbone_candidate": {
            "candidate_id": backbone_ranked[
                "candidate_id"
            ],
            "image_variant": backbone_ranked[
                "image_variant"
            ],
            "psm": backbone_ranked["psm"],
            "comparison_metrics": (
                backbone_ranked[
                    "comparison_metrics"
                ]
            ),
        },

        "consensus_summary": {
            "backbone_line_count": len(
                backbone_candidate[
                    "result"
                ]["text"]
            ),
            "consensus_line_count": len(
                consensus_lines
            ),
            "supported_extra_line_count": len(
                extra_lines
            ),
            "candidate_count": len(
                candidates
            ),
            "match_threshold": (
                MATCH_THRESHOLD
            ),
            "extra_line_min_support": (
                EXTRA_LINE_MIN_SUPPORT
            ),
            "sku_anchored_replacements": (
                sku_anchored_replacements
            ),
        },

        "raw_text": raw_text,

        "text": consensus_lines,

        "supported_extra_lines": [
            {
                "text": line["text"],
                "confidence": line[
                    "confidence"
                ],
                "source_candidate": line[
                    "candidate_id"
                ],
                "image_variant": line[
                    "image_variant"
                ],
                "psm": line["psm"],
                "support_count": line[
                    "support_count"
                ],
                "line_quality_score": line[
                    "line_quality_score"
                ],
            }
            for line in extra_lines
        ],

        "candidate_ranking": [
            {
                "rank": rank,
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate["psm"],
                "comparison_metrics": candidate[
                    "comparison_metrics"
                ],
            }
            for rank, candidate
            in enumerate(
                ranked_candidates,
                start=1,
            )
        ],

        "provenance": {
            "candidates_file": str(
                candidates_path.resolve()
            ),
            "rule": (
                "Consensus output never edits OCR characters "
                "inside a chosen line. Exact six-digit SKUs are "
                "used only to align competing OCR observations. "
                "Every emitted line is copied verbatim from one "
                "Tesseract candidate, with its source recorded."
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

    set_selected_raw_ocr_file(
        output_path
    )

    return output_path.resolve()


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def run_compare_ocr() -> None:
    print(
        "\n=== Compare OCR Results / "
        "Build SKU-Anchored Consensus ===\n"
    )

    try:
        output_path = (
            compare_and_build_raw_ocr()
        )

        if output_path is None:
            return

        data = _load_json(
            output_path
        )

        backbone = data[
            "backbone_candidate"
        ]

        summary = data[
            "consensus_summary"
        ]

        print(
            "[OK] SKU-anchored consensus OCR "
            "built from all candidates."
        )

        print(
            "\nBackbone candidate:"
            f"\nVariant: "
            f"{backbone['image_variant']}"
            f"\nPSM: {backbone['psm']}"
            "\nScore: "
            f"{backbone['comparison_metrics']['score']}"
        )

        print(
            "\nConsensus:"
            f"\nLines: "
            f"{summary['consensus_line_count']}"
            "\nSKU-anchored replacements: "
            f"{summary['sku_anchored_replacements']}"
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