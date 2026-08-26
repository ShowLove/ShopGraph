from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.constants import RAW_OCR_DIR
from capabilities.OCRAcquisitionPipeline.run_ocr import run_all_ocr_candidates
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_ocr_candidates_file,
    set_selected_raw_ocr_file,
)


MATCH_THRESHOLD = 0.58
EXTRA_LINE_MIN_SUPPORT = 2
SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
TAX_PATTERN = re.compile(r"\b(FA|FB|NA|NB)\b", re.IGNORECASE)


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
    return set(SKU_PATTERN.findall(text))


def _extract_prices(text: str) -> list[str]:
    return PRICE_PATTERN.findall(text)


def _extract_tax_codes(text: str) -> list[str]:
    return [match.upper() for match in TAX_PATTERN.findall(text)]


def _shared_sku(left: str, right: str) -> str | None:
    shared = _extract_skus(left) & _extract_skus(right)

    if not shared:
        return None

    return sorted(shared)[0]


def _same_sku_line(left: str, right: str) -> bool:
    return _shared_sku(left, right) is not None


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

    left_numbers = set(
        re.findall(r"\b\d{4,}\b", left_norm)
    )
    right_numbers = set(
        re.findall(r"\b\d{4,}\b", right_norm)
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

    if _same_sku_line(left, right):
        score = max(score, 0.90)

    return min(score, 1.0)


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
        re.findall(r"\d", raw_text)
    )

    price_like_count = len(
        PRICE_PATTERN.findall(raw_text)
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
    price_count = len(_extract_prices(text))
    sku_count = len(_extract_skus(text))
    tax_marker_count = len(_extract_tax_codes(text))

    return (
        float(confidence)
        + min(token_count, 14) * 0.55
        + min(digit_count, 16) * 0.22
        + price_count * 3.0
        + sku_count * 2.0
        + tax_marker_count * 1.5
    )


def _build_line_records(
    candidates: list[dict],
) -> list[dict]:
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
                    "skus": sorted(_extract_skus(text)),
                }
            )

    return records


def _best_match(
    target_text: str,
    records: list[dict],
    excluded_candidate_id: str | None = None,
) -> tuple[dict | None, float, str]:
    eligible_records = []

    for record in records:
        if (
            excluded_candidate_id is not None
            and record["candidate_id"]
            == excluded_candidate_id
        ):
            continue

        eligible_records.append(record)

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

        quality = _line_quality(record)

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

        record, similarity, _ = sku_matches[0]

        return (
            record,
            similarity,
            "sku",
        )

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


def _support_for_line(
    line: dict,
    candidates: list[dict],
) -> tuple[int, list[dict]]:
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

        best, similarity, method = _best_match(
            line["text"],
            candidate_records,
        )

        if best is None:
            continue

        if (
            method != "sku"
            and similarity < MATCH_THRESHOLD
        ):
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


def _description_without_components(
    text: str,
    sku: str,
) -> str:
    """
    Remove fields that can be independently reconstructed.

    The returned description remains OCR-derived. This function does not
    spell-correct or normalize words.
    """
    working = text

    working = re.sub(
        rf"(?<!\d){re.escape(sku)}(?!\d)",
        " ",
        working,
        count=1,
    )

    working = PRICE_PATTERN.sub(
        " ",
        working,
    )

    working = TAX_PATTERN.sub(
        " ",
        working,
    )

    working = re.sub(
        r"\s+",
        " ",
        working,
    ).strip()

    working = working.strip(
        " -:;,.|_~'\"()[]{}"
    )

    return working


def _component_vote(
    observations: list[dict],
    value_getter,
) -> tuple[str | None, dict]:
    """
    Vote on a component using one vote per OCR candidate.

    Repeated observations from the same candidate do not increase support.
    """
    by_value: dict[str, dict] = {}

    for observation in observations:
        value = value_getter(observation)

        if not value:
            continue

        candidate_id = observation["candidate_id"]

        entry = by_value.setdefault(
            value,
            {
                "candidate_ids": set(),
                "confidence_sum": 0.0,
                "confidence_count": 0,
                "examples": [],
            },
        )

        if candidate_id in entry["candidate_ids"]:
            continue

        entry["candidate_ids"].add(
            candidate_id
        )

        confidence = observation.get(
            "confidence"
        )

        if confidence is not None:
            entry["confidence_sum"] += float(
                confidence
            )
            entry["confidence_count"] += 1

        entry["examples"].append(
            {
                "candidate_id": candidate_id,
                "text": observation["text"],
            }
        )

    if not by_value:
        return None, {
            "support_count": 0,
            "average_confidence": None,
            "examples": [],
        }

    ranked = []

    for value, entry in by_value.items():
        support_count = len(
            entry["candidate_ids"]
        )

        average_confidence = (
            entry["confidence_sum"]
            / entry["confidence_count"]
            if entry["confidence_count"]
            else 0.0
        )

        ranked.append(
            (
                support_count,
                average_confidence,
                len(value),
                value,
                entry,
            )
        )

    ranked.sort(
        reverse=True
    )

    (
        support_count,
        average_confidence,
        _,
        selected_value,
        entry,
    ) = ranked[0]

    return selected_value, {
        "support_count": support_count,
        "average_confidence": round(
            average_confidence,
            2,
        ),
        "examples": entry["examples"],
    }


def _best_description(
    observations: list[dict],
    sku: str,
) -> tuple[str, dict]:
    """
    Pick a product description independently from price/tax.

    The description must come verbatim from one OCR candidate after
    removing the SKU, price, and tax components from that same OCR line.
    """
    candidates = []

    for observation in observations:
        description = _description_without_components(
            observation["text"],
            sku,
        )

        if not description:
            continue

        support = 1

        for other in observations:
            if (
                other["candidate_id"]
                == observation["candidate_id"]
            ):
                continue

            other_description = (
                _description_without_components(
                    other["text"],
                    sku,
                )
            )

            if not other_description:
                continue

            similarity = SequenceMatcher(
                None,
                _normalize_line(description),
                _normalize_line(other_description),
            ).ratio()

            if similarity >= 0.62:
                support += 1

        confidence = observation.get(
            "confidence"
        )

        if confidence is None:
            confidence = 0.0

        score = (
            support * 5.0
            + float(confidence)
            + min(
                len(description.split()),
                8,
            ) * 1.5
        )

        candidates.append(
            {
                "description": description,
                "source_candidate": observation[
                    "candidate_id"
                ],
                "source_text": observation[
                    "text"
                ],
                "confidence": confidence,
                "support_count": support,
                "score": score,
            }
        )

    if not candidates:
        return "", {
            "source_candidate": None,
            "support_count": 0,
            "score": 0.0,
        }

    candidates.sort(
        key=lambda item: (
            item["score"],
            len(item["description"]),
        ),
        reverse=True,
    )

    selected = candidates[0]

    return selected["description"], {
        "source_candidate": selected[
            "source_candidate"
        ],
        "source_text": selected[
            "source_text"
        ],
        "support_count": selected[
            "support_count"
        ],
        "confidence": selected[
            "confidence"
        ],
        "score": round(
            selected["score"],
            4,
        ),
    }


def _component_observations_for_sku(
    sku: str,
    all_records: list[dict],
) -> list[dict]:
    return [
        record
        for record in all_records
        if sku in record.get(
            "skus",
            []
        )
    ]


def _reconstruct_product_line(
    base_line: dict,
    all_records: list[dict],
) -> dict:
    skus = sorted(
        _extract_skus(
            base_line["text"]
        )
    )

    if len(skus) != 1:
        return {
            **base_line,
            "reconstructed": False,
            "reconstruction_reason": (
                "line does not contain exactly one six-digit SKU"
            ),
        }

    sku = skus[0]

    observations = (
        _component_observations_for_sku(
            sku,
            all_records,
        )
    )

    if not observations:
        return {
            **base_line,
            "reconstructed": False,
            "reconstruction_reason": (
                "no matching SKU observations"
            ),
        }

    description, description_meta = (
        _best_description(
            observations,
            sku,
        )
    )

    price, price_meta = _component_vote(
        observations,
        lambda observation: (
            _extract_prices(
                observation["text"]
            )[0]
            if _extract_prices(
                observation["text"]
            )
            else None
        ),
    )

    tax_code, tax_meta = _component_vote(
        observations,
        lambda observation: (
            _extract_tax_codes(
                observation["text"]
            )[0]
            if _extract_tax_codes(
                observation["text"]
            )
            else None
        ),
    )

    parts = [sku]

    if description:
        parts.append(description)

    if price:
        parts.append(price)

    if tax_code:
        parts.append(tax_code)

    reconstructed_text = " ".join(
        parts
    )

    component_support = {
        "sku": {
            "value": sku,
            "support_count": len(
                {
                    record["candidate_id"]
                    for record in observations
                }
            ),
        },
        "description": {
            "value": description or None,
            **description_meta,
        },
        "price": {
            "value": price,
            **price_meta,
        },
        "tax_code": {
            "value": tax_code,
            **tax_meta,
        },
    }

    return {
        **base_line,
        "text": reconstructed_text,
        "reconstructed": (
            reconstructed_text
            != base_line["text"]
        ),
        "original_consensus_text": (
            base_line["text"]
        ),
        "reconstruction_method": (
            "component consensus by exact six-digit SKU"
        ),
        "component_support": (
            component_support
        ),
    }


def _choose_consensus_line(
    backbone_line: dict,
    all_records: list[dict],
    candidates: list[dict],
) -> dict:
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

        if (
            method != "sku"
            and similarity < MATCH_THRESHOLD
        ):
            continue

        matched = dict(match)
        matched["match_to_backbone"] = round(
            similarity,
            4,
        )
        matched["match_method"] = method

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


def _record_matches_consensus(
    record: dict,
    consensus_lines: list[dict],
) -> bool:
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
    extras = []
    seen_normalized = set()

    for record in all_records:
        normalized = _normalize_line(
            record["text"]
        )

        if (
            not normalized
            or normalized in seen_normalized
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
    component_reconstructions = 0

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

        consensus_line = {
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

        reconstructed = (
            _reconstruct_product_line(
                consensus_line,
                all_records,
            )
        )

        if reconstructed.get(
            "reconstructed"
        ):
            component_reconstructions += 1

        consensus_lines.append(
            reconstructed
        )

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
            "multi-candidate component consensus: "
            "best candidate provides reading order; "
            "exact six-digit SKU aligns product observations; "
            "description, price, and tax code are selected "
            "independently from OCR evidence across all candidates; "
            "non-product lines continue to use ordinary consensus"
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
            "component_reconstruction_count": (
                component_reconstructions
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
                "Product lines may be reconstructed from multiple "
                "Tesseract observations only when they share the same "
                "exact six-digit SKU. Description text is OCR-derived, "
                "and price/tax values must each appear in at least one "
                "actual OCR candidate. No spelling correction or "
                "external product lookup is performed."
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


def run_compare_ocr() -> None:
    print(
        "\n=== Compare OCR Results / "
        "Build Component Consensus ===\n"
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
            "[OK] Component consensus OCR "
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
            "\nProduct lines reconstructed: "
            f"{summary['component_reconstruction_count']}"
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
