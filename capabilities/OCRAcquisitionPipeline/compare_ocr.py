from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.constants import RAW_OCR_DIR
from capabilities.OCRAcquisitionPipeline.run_ocr import run_all_ocr_candidates
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_ocr_candidates_file,
    set_selected_raw_ocr_file,
)


MATCH_THRESHOLD = 0.58
GEOMETRY_Y_TOLERANCE = 0.012
SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
TAX_PATTERN = re.compile(r"\b(FA|FB|NA|NB|F|T|TF|LF|TLF)\b", re.IGNORECASE)

GARBAGE_TOKEN_PATTERN = re.compile(r"^[^A-Za-z0-9]+$")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_line(text: str) -> str:
    text = text.lower()
    text = text.replace(",", ".")
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return set(_normalize_line(text).split())


def _extract_skus(text: str) -> list[str]:
    return SKU_PATTERN.findall(text)


def _extract_prices(text: str) -> list[str]:
    return [
        value.replace(",", ".")
        for value in PRICE_PATTERN.findall(text)
    ]


def _extract_tax_codes(text: str) -> list[str]:
    return [
        match.upper()
        for match in TAX_PATTERN.findall(text)
    ]


def _shared_sku(left: str, right: str) -> str | None:
    shared = set(_extract_skus(left)) & set(_extract_skus(right))
    return sorted(shared)[0] if shared else None


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
        if union else 0.0
    )

    score = (
        sequence_score * 0.65
        + token_score * 0.35
    )

    if _shared_sku(left, right):
        score = max(score, 0.95)

    return min(score, 1.0)


def _garbage_penalty(text: str) -> float:
    tokens = text.split()

    if not tokens:
        return 20.0

    penalty = 0.0

    if len(tokens) == 1 and len(tokens[0]) <= 2:
        penalty += 12.0

    punctuation_only = sum(
        1 for token in tokens
        if GARBAGE_TOKEN_PATTERN.match(token)
    )
    penalty += punctuation_only * 4.0

    alnum_chars = sum(
        1 for char in text
        if char.isalnum()
    )
    if alnum_chars < 2:
        penalty += 10.0

    return penalty


def _candidate_metrics(candidate: dict) -> dict:
    result = candidate["result"]
    metrics = result["metrics"]

    mean_confidence = metrics["mean_word_confidence"] or 0.0
    recognized_word_count = metrics["recognized_word_count"]
    low_confidence_rate = metrics["low_confidence_rate"]
    raw_text = result["raw_text"]

    price_like_count = len(_extract_prices(raw_text))
    sku_count = len(_extract_skus(raw_text))

    plausible_lines = 0
    garbage_lines = 0

    for line in result.get("text", []):
        text = line.get("text", "").strip()
        if not text:
            continue

        confidence = line.get("confidence") or 0.0

        if (
            confidence >= 45
            and len(text) >= 4
            and _garbage_penalty(text) < 10
        ):
            plausible_lines += 1

        if _garbage_penalty(text) >= 10:
            garbage_lines += 1

    # Word count is deliberately capped very low. Hundreds of extra low-quality
    # "words" are usually receipt/background noise, not useful OCR.
    score = (
        mean_confidence
        + min(plausible_lines, 100) * 0.18
        + min(price_like_count, 80) * 0.45
        + min(sku_count, 80) * 0.25
        - low_confidence_rate * 28.0
        - min(garbage_lines, 100) * 0.12
        - max(recognized_word_count - 700, 0) * 0.01
    )

    return {
        "score": round(score, 4),
        "mean_word_confidence": mean_confidence,
        "recognized_word_count": recognized_word_count,
        "low_confidence_rate": low_confidence_rate,
        "price_like_count": price_like_count,
        "sku_count": sku_count,
        "plausible_line_count": plausible_lines,
        "garbage_line_count": garbage_lines,
    }


def _line_quality(record: dict) -> float:
    text = record["text"]
    confidence = record.get("confidence") or 0.0

    return (
        float(confidence)
        + min(len(text.split()), 12) * 0.6
        + len(_extract_prices(text)) * 4.0
        + len(_extract_skus(text)) * 3.0
        + len(_extract_tax_codes(text)) * 1.5
        - _garbage_penalty(text)
    )


def _build_records(candidates: list[dict]) -> list[dict]:
    records = []

    for candidate in candidates:
        for index, line in enumerate(
            candidate["result"].get("text", [])
        ):
            text = line.get("text", "").strip()
            if not text:
                continue

            records.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_scope": candidate.get(
                        "candidate_scope",
                        "full",
                    ),
                    "image_variant": candidate["image_variant"],
                    "psm": candidate["psm"],
                    "candidate_line_index": index,
                    "text": text,
                    "confidence": line.get("confidence"),
                    "normalized_y": line.get("normalized_y"),
                    "normalized_x": line.get("normalized_x"),
                    "bbox": line.get("bbox"),
                    "words": line.get("words", []),
                    "skus": _extract_skus(text),
                    "prices": _extract_prices(text),
                    "tax_codes": _extract_tax_codes(text),
                }
            )

    return records


def _same_row(left: dict, right: dict) -> bool:
    left_y = left.get("normalized_y")
    right_y = right.get("normalized_y")

    if left_y is None or right_y is None:
        return False

    return abs(float(left_y) - float(right_y)) <= GEOMETRY_Y_TOLERANCE


def _records_for_row(
    anchor: dict,
    all_records: list[dict],
) -> list[dict]:
    observations = []

    for record in all_records:
        if record["candidate_id"] == anchor["candidate_id"]:
            observations.append(record)
            continue

        shared_sku = _shared_sku(
            anchor["text"],
            record["text"],
        )

        if shared_sku:
            observations.append(record)
            continue

        if _same_row(anchor, record):
            observations.append(record)
            continue

        similarity = _line_similarity(
            anchor["text"],
            record["text"],
        )

        if (
            record["candidate_scope"] == "full"
            and similarity >= 0.72
        ):
            observations.append(record)

    return observations


def _vote_component(
    observations: list[dict],
    field: str,
) -> tuple[str | None, dict]:
    by_value: dict[str, dict] = {}

    for observation in observations:
        values = observation.get(field, [])

        for value in values:
            entry = by_value.setdefault(
                value,
                {
                    "candidate_ids": set(),
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                    "examples": [],
                },
            )

            candidate_id = observation["candidate_id"]

            if candidate_id in entry["candidate_ids"]:
                continue

            entry["candidate_ids"].add(candidate_id)

            confidence = observation.get("confidence")
            if confidence is not None:
                entry["confidence_sum"] += float(confidence)
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
        support = len(entry["candidate_ids"])
        avg_confidence = (
            entry["confidence_sum"] / entry["confidence_count"]
            if entry["confidence_count"]
            else 0.0
        )
        ranked.append(
            (
                support,
                avg_confidence,
                value,
                entry,
            )
        )

    ranked.sort(reverse=True)
    support, avg_confidence, value, entry = ranked[0]

    return value, {
        "support_count": support,
        "average_confidence": round(avg_confidence, 2),
        "examples": entry["examples"],
    }


def _description_candidate_text(record: dict) -> str:
    text = record["text"]

    text = SKU_PATTERN.sub(" ", text)
    text = PRICE_PATTERN.sub(" ", text)
    text = TAX_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" -:;,.|_~'\"()[]{}")


def _best_description(
    observations: list[dict],
) -> tuple[str, dict]:
    candidates = []

    for observation in observations:
        if observation["candidate_scope"] != "full":
            continue

        description = _description_candidate_text(observation)
        if not description:
            continue

        support = 1

        for other in observations:
            if (
                other["candidate_id"] == observation["candidate_id"]
                or other["candidate_scope"] != "full"
            ):
                continue

            other_description = _description_candidate_text(other)
            if not other_description:
                continue

            similarity = SequenceMatcher(
                None,
                _normalize_line(description),
                _normalize_line(other_description),
            ).ratio()

            if similarity >= 0.62:
                support += 1

        confidence = observation.get("confidence") or 0.0

        score = (
            support * 5.0
            + float(confidence)
            + min(len(description.split()), 10) * 1.2
            - _garbage_penalty(description)
        )

        candidates.append(
            {
                "description": description,
                "source_candidate": observation["candidate_id"],
                "source_text": observation["text"],
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
        "source_candidate": selected["source_candidate"],
        "source_text": selected["source_text"],
        "support_count": selected["support_count"],
        "confidence": selected["confidence"],
        "score": round(selected["score"], 4),
    }


def _looks_like_merchandise_row(
    record: dict,
    observations: list[dict],
) -> bool:
    if _extract_skus(record["text"]):
        return True

    description = _description_candidate_text(record)

    if len(description) < 3:
        return False

    has_price = any(
        observation.get("prices")
        for observation in observations
    )

    if not has_price:
        return False

    # Reject obvious totals/payment/header rows.
    lowered = _normalize_line(record["text"])
    blocked = (
        "subtotal",
        "total tax",
        "amount due",
        "balance to pay",
        "credit card",
        "visa credit",
        "auth code",
        "customer copy",
        "sale transaction",
        "items in transaction",
    )

    return not any(term in lowered for term in blocked)


def _reconstruct_row(
    base_line: dict,
    all_records: list[dict],
) -> dict:
    observations = _records_for_row(
        base_line,
        all_records,
    )

    if not _looks_like_merchandise_row(
        base_line,
        observations,
    ):
        return {
            **base_line,
            "reconstructed": False,
            "reconstruction_reason": (
                "line not classified as a merchandise row"
            ),
        }

    sku, sku_meta = _vote_component(
        observations,
        "skus",
    )
    price, price_meta = _vote_component(
        observations,
        "prices",
    )
    tax_code, tax_meta = _vote_component(
        observations,
        "tax_codes",
    )
    description, description_meta = _best_description(
        observations
    )

    parts = []

    if sku:
        parts.append(sku)

    if description:
        parts.append(description)

    if tax_code:
        parts.append(tax_code)

    if price:
        parts.append(price)

    reconstructed_text = " ".join(parts).strip()

    if not reconstructed_text:
        return {
            **base_line,
            "reconstructed": False,
            "reconstruction_reason": (
                "no reliable components recovered"
            ),
        }

    return {
        **base_line,
        "text": reconstructed_text,
        "reconstructed": (
            reconstructed_text != base_line["text"]
        ),
        "original_consensus_text": base_line["text"],
        "reconstruction_method": (
            "spatial row consensus using normalized y-coordinate; "
            "exact SKU remains a stronger anchor when available; "
            "right-column OCR contributes price/tax evidence"
        ),
        "component_support": {
            "sku": {
                "value": sku,
                **sku_meta,
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
        },
    }


def _best_row_match(
    anchor: dict,
    records: list[dict],
) -> tuple[dict | None, float, str]:
    same_sku = [
        record
        for record in records
        if _shared_sku(anchor["text"], record["text"])
    ]

    if same_sku:
        same_sku.sort(
            key=_line_quality,
            reverse=True,
        )
        return same_sku[0], 1.0, "sku"

    spatial = [
        record
        for record in records
        if _same_row(anchor, record)
    ]

    if spatial:
        spatial.sort(
            key=lambda record: (
                _line_similarity(
                    anchor["text"],
                    record["text"],
                ),
                _line_quality(record),
            ),
            reverse=True,
        )
        selected = spatial[0]
        return (
            selected,
            _line_similarity(
                anchor["text"],
                selected["text"],
            ),
            "geometry",
        )

    best = None
    best_score = 0.0

    for record in records:
        score = _line_similarity(
            anchor["text"],
            record["text"],
        )
        if score > best_score:
            best = record
            best_score = score

    return best, best_score, "fuzzy"


def _support_for_line(
    line: dict,
    candidates: list[dict],
    all_records: list[dict],
) -> tuple[int, list[dict]]:
    supporting = []

    for candidate in candidates:
        if (
            candidate["candidate_id"] == line["candidate_id"]
            or candidate.get("candidate_scope", "full")
            != "full"
        ):
            continue

        candidate_records = [
            record
            for record in all_records
            if (
                record["candidate_id"]
                == candidate["candidate_id"]
            )
        ]

        best, similarity, method = _best_row_match(
            line,
            candidate_records,
        )

        if best is None:
            continue

        if (
            method == "fuzzy"
            and similarity < MATCH_THRESHOLD
        ):
            continue

        supporting.append(
            {
                "candidate_id": candidate["candidate_id"],
                "similarity": round(similarity, 4),
                "match_method": method,
                "text": best["text"],
            }
        )

    return 1 + len(supporting), supporting


def _choose_consensus_line(
    backbone_line: dict,
    all_records: list[dict],
    candidates: list[dict],
) -> dict:
    alternatives = [
        {
            **backbone_line,
            "match_method": "backbone",
        }
    ]

    for candidate in candidates:
        if (
            candidate["candidate_id"]
            == backbone_line["candidate_id"]
            or candidate.get("candidate_scope", "full")
            != "full"
        ):
            continue

        candidate_records = [
            record
            for record in all_records
            if (
                record["candidate_id"]
                == candidate["candidate_id"]
            )
        ]

        match, similarity, method = _best_row_match(
            backbone_line,
            candidate_records,
        )

        if match is None:
            continue

        if (
            method == "fuzzy"
            and similarity < MATCH_THRESHOLD
        ):
            continue

        alternatives.append(
            {
                **match,
                "match_method": method,
            }
        )

    scored = []

    for alternative in alternatives:
        support_count, supporting = _support_for_line(
            alternative,
            candidates,
            all_records,
        )

        quality = _line_quality(alternative)
        consensus_score = (
            quality
            + (support_count - 1) * 4.0
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


def _score_and_rank_candidates(
    candidates: list[dict],
) -> list[dict]:
    scored = []

    for candidate in candidates:
        if not candidate.get(
            "eligible_for_backbone",
            True,
        ):
            continue

        scored.append(
            {
                "candidate_id": candidate["candidate_id"],
                "image_variant": candidate["image_variant"],
                "psm": candidate["psm"],
                "candidate_scope": candidate.get(
                    "candidate_scope",
                    "full",
                ),
                "comparison_metrics": (
                    _candidate_metrics(candidate)
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
        raise ValueError(
            "OCR candidates file contains no candidates."
        )

    ranked_candidates = _score_and_rank_candidates(
        candidates
    )

    if not ranked_candidates:
        raise ValueError(
            "No full-receipt OCR candidate is available "
            "for the reading-order backbone."
        )

    backbone_ranked = ranked_candidates[0]
    backbone_id = backbone_ranked["candidate_id"]

    backbone_candidate = next(
        candidate
        for candidate in candidates
        if candidate["candidate_id"] == backbone_id
    )

    all_records = _build_records(candidates)

    consensus_lines = []
    component_reconstructions = 0

    backbone_records = [
        record
        for record in all_records
        if record["candidate_id"] == backbone_id
    ]

    for backbone_record in backbone_records:
        chosen = _choose_consensus_line(
            backbone_record,
            all_records,
            candidates,
        )

        consensus_line = {
            "line_number": len(consensus_lines) + 1,
            "candidate_id": chosen["candidate_id"],
            "text": chosen["text"],
            "confidence": chosen["confidence"],
            "source_candidate": chosen["candidate_id"],
            "image_variant": chosen["image_variant"],
            "psm": chosen["psm"],
            "support_count": chosen["support_count"],
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
            "normalized_y": chosen.get(
                "normalized_y"
            ),
            "bbox": chosen.get("bbox"),
        }

        reconstructed = _reconstruct_row(
            consensus_line,
            all_records,
        )

        if reconstructed.get("reconstructed"):
            component_reconstructions += 1

        consensus_lines.append(reconstructed)

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
            "multi-variant spatial component consensus: "
            "best full-receipt candidate provides reading order; "
            "rows align by normalized y-coordinate, with exact six-digit "
            "SKU as a stronger anchor when present; right-column OCR "
            "supplies independent price/tax evidence"
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
            "backbone_line_count": len(backbone_records),
            "consensus_line_count": len(consensus_lines),
            "component_reconstruction_count": (
                component_reconstructions
            ),
            "candidate_count": len(candidates),
            "full_candidate_count": sum(
                1 for candidate in candidates
                if candidate.get(
                    "candidate_scope",
                    "full",
                ) == "full"
            ),
            "right_column_candidate_count": sum(
                1 for candidate in candidates
                if candidate.get(
                    "candidate_scope",
                    "full",
                ) == "right_column"
            ),
            "match_threshold": MATCH_THRESHOLD,
            "geometry_y_tolerance": (
                GEOMETRY_Y_TOLERANCE
            ),
        },
        "raw_text": raw_text,
        "text": consensus_lines,
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
                "OCR output is reconstructed only from actual Tesseract "
                "observations. Spatial row alignment may combine description, "
                "SKU, price, and tax evidence from different OCR candidates "
                "when their normalized vertical positions agree. Exact SKU "
                "matches override ordinary fuzzy alignment. No external "
                "product lookup or spelling correction is performed."
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
        "\n=== Compare OCR Results / "
        "Build Spatial Component Consensus ===\n"
    )

    try:
        output_path = compare_and_build_raw_ocr()
        if output_path is None:
            return

        data = _load_json(output_path)
        backbone = data["backbone_candidate"]
        summary = data["consensus_summary"]

        print(
            "[OK] Spatial component consensus OCR "
            "built from all candidates."
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
            "\nProduct lines reconstructed: "
            f"{summary['component_reconstruction_count']}"
            "\nFull OCR candidates: "
            f"{summary['full_candidate_count']}"
            "\nRight-column OCR candidates: "
            f"{summary['right_column_candidate_count']}"
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
        print(f"\n[ERROR] {error}")
