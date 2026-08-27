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


# ---------------------------------------------------------------------------
# CONSERVATIVE CONSENSUS SETTINGS
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 0.72

# A row may be geometrically near another OCR observation, but geometry alone
# is NEVER enough to merge text/components. Textual or SKU agreement is also
# required.
MAX_ROW_CENTER_DISTANCE = 0.014
MIN_ROW_TEXT_SIMILARITY = 0.48
MIN_DESCRIPTION_SIMILARITY = 0.50

# Components not already present in the selected full-receipt line require
# independent support. A single observation is accepted only for a SKU-anchored
# merchandise row when that observation is very high confidence.
MIN_COMPONENT_SUPPORT = 2
SINGLE_OBSERVATION_MIN_CONFIDENCE = 92.0

SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
TAX_PATTERN = re.compile(
    r"(?<![A-Za-z])(FA|FB|NA|NB|TLF|TF|LF|F|T)(?![A-Za-z])",
    re.IGNORECASE,
)
GARBAGE_TOKEN_PATTERN = re.compile(r"^[^A-Za-z0-9]+$")

# These are receipt sections / metadata, not merchandise. These checks happen
# BEFORE SKU detection so an authorization/reference number can never become a
# product SKU merely because it happens to contain six digits.
NON_MERCHANDISE_TERMS = (
    "subtotal",
    "total tax",
    "amount due",
    "balance to pay",
    "credit card",
    "visa credit",
    "visa debit",
    "auth code",
    "auth trace",
    "auth/trace",
    "reference",
    "customer copy",
    "sale transaction",
    "purchase transaction",
    "payment card",
    "items in transaction",
    "items in trans",
    "approved",
    "entrymode",
    "entry mode",
    "aid ",
    "tsi ",
    "store manager",
    "your cashier",
    "sign up",
    "thank you",
    "change due",
    "cash tendered",
)

ADDRESS_HINTS = (
    " ave",
    " avenue",
    " blvd",
    " boulevard",
    " road",
    " rd",
    " street",
    " st ",
    " highway",
    " hwy",
    "melbourne",
    "indian harbour",
    "town center",
)


# ---------------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_line(text: str) -> str:
    text = text.lower().replace(",", ".")
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
        value.upper()
        for value in TAX_PATTERN.findall(text)
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

    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    union = left_tokens | right_tokens

    token_score = (
        len(left_tokens & right_tokens) / len(union)
        if union
        else 0.0
    )

    score = (
        sequence_score * 0.70
        + token_score * 0.30
    )

    if _shared_sku(left, right):
        score = max(score, 0.96)

    return min(score, 1.0)


def _garbage_penalty(text: str) -> float:
    tokens = text.split()

    if not tokens:
        return 20.0

    penalty = 0.0

    if len(tokens) == 1 and len(tokens[0]) <= 2:
        penalty += 12.0

    punctuation_only = sum(
        1
        for token in tokens
        if GARBAGE_TOKEN_PATTERN.match(token)
    )
    penalty += punctuation_only * 4.0

    alnum_chars = sum(
        1
        for character in text
        if character.isalnum()
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


# ---------------------------------------------------------------------------
# OCR RECORDS / GEOMETRY
# ---------------------------------------------------------------------------

def _build_records(candidates: list[dict]) -> list[dict]:
    records = []

    for candidate in candidates:
        result = candidate["result"]
        image_height = result.get(
            "image",
            {},
        ).get(
            "height",
            1,
        ) or 1

        for index, line in enumerate(
            result.get("text", [])
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
                    "image_height": image_height,
                    "skus": _extract_skus(text),
                    "prices": _extract_prices(text),
                    "tax_codes": _extract_tax_codes(text),
                }
            )

    return records


def _row_center_distance(
    left: dict,
    right: dict,
) -> float | None:
    left_y = left.get("normalized_y")
    right_y = right.get("normalized_y")

    if left_y is None or right_y is None:
        return None

    return abs(float(left_y) - float(right_y))


def _same_physical_row(
    left: dict,
    right: dict,
) -> bool:
    distance = _row_center_distance(
        left,
        right,
    )

    if distance is None:
        return False

    # Small OCR lines receive a narrow band. Large PSM bounding boxes do not
    # get permission to swallow neighboring rows; the tolerance stays capped.
    left_bbox = left.get("bbox") or {}
    right_bbox = right.get("bbox") or {}

    left_height = (
        float(left_bbox.get("height", 0))
        / float(left.get("image_height", 1) or 1)
    )
    right_height = (
        float(right_bbox.get("height", 0))
        / float(right.get("image_height", 1) or 1)
    )

    natural_tolerance = max(
        0.0035,
        min(
            MAX_ROW_CENTER_DISTANCE,
            max(left_height, right_height) * 0.40,
        ),
    )

    return distance <= natural_tolerance


def _description_without_components(text: str) -> str:
    working = text

    working = SKU_PATTERN.sub(" ", working)
    working = PRICE_PATTERN.sub(" ", working)
    working = TAX_PATTERN.sub(" ", working)

    working = re.sub(
        r"\s+",
        " ",
        working,
    ).strip()

    return working.strip(
        " -:;,.|_~'\"()[]{}$"
    )


def _description_similarity(
    left: dict,
    right: dict,
) -> float:
    left_description = _description_without_components(
        left["text"]
    )
    right_description = _description_without_components(
        right["text"]
    )

    if not left_description or not right_description:
        return 0.0

    return SequenceMatcher(
        None,
        _normalize_line(left_description),
        _normalize_line(right_description),
    ).ratio()


def _strong_row_match(
    anchor: dict,
    record: dict,
) -> tuple[bool, float, str]:
    """
    Determine whether two FULL-receipt OCR lines are observations of the same
    physical receipt row.

    Geometry alone is intentionally insufficient.
    """
    shared_sku = _shared_sku(
        anchor["text"],
        record["text"],
    )

    if shared_sku:
        return True, 1.0, "sku"

    line_similarity = _line_similarity(
        anchor["text"],
        record["text"],
    )

    if not _same_physical_row(
        anchor,
        record,
    ):
        return False, line_similarity, "different_row"

    description_similarity = _description_similarity(
        anchor,
        record,
    )

    if (
        line_similarity >= MIN_ROW_TEXT_SIMILARITY
        or description_similarity
        >= MIN_DESCRIPTION_SIMILARITY
    ):
        return (
            True,
            max(
                line_similarity,
                description_similarity,
            ),
            "geometry_plus_text",
        )

    return False, line_similarity, "geometry_only_rejected"


def _row_family(
    anchor: dict,
    all_records: list[dict],
) -> list[dict]:
    """
    Full-receipt observations that are credibly the same row as anchor.
    """
    family = []

    for record in all_records:
        if record["candidate_scope"] != "full":
            continue

        if record["candidate_id"] == anchor["candidate_id"]:
            if (
                record["candidate_line_index"]
                == anchor.get(
                    "candidate_line_index"
                )
            ):
                family.append(record)
            continue

        matched, _, _ = _strong_row_match(
            anchor,
            record,
        )

        if matched:
            family.append(record)

    if not family:
        family.append(anchor)

    return family


# ---------------------------------------------------------------------------
# COMPONENT EVIDENCE
# ---------------------------------------------------------------------------

def _component_word_observations(
    record: dict,
    component: str,
) -> list[dict]:
    observations = []

    words = record.get("words", [])

    for word in words:
        word_text = str(
            word.get("text", "")
        ).strip()

        if not word_text:
            continue

        if component == "price":
            values = _extract_prices(word_text)
        elif component == "sku":
            values = _extract_skus(word_text)
        elif component == "tax_code":
            values = _extract_tax_codes(word_text)
        else:
            values = []

        for value in values:
            observations.append(
                {
                    "value": value,
                    "candidate_id": record["candidate_id"],
                    "candidate_scope": record["candidate_scope"],
                    "confidence": word.get(
                        "confidence",
                        record.get("confidence"),
                    ),
                    "normalized_y": word.get(
                        "normalized_y",
                        record.get("normalized_y"),
                    ),
                    "normalized_x": word.get(
                        "normalized_x",
                        record.get("normalized_x"),
                    ),
                    "source_text": record["text"],
                }
            )

    # Tesseract occasionally creates a valid component across punctuation that
    # is easier to recover from the complete line than from a single word.
    if component == "price":
        line_values = _extract_prices(record["text"])
    elif component == "sku":
        line_values = _extract_skus(record["text"])
    elif component == "tax_code":
        line_values = _extract_tax_codes(record["text"])
    else:
        line_values = []

    existing_values = {
        observation["value"]
        for observation in observations
    }

    for value in line_values:
        if value in existing_values:
            continue

        observations.append(
            {
                "value": value,
                "candidate_id": record["candidate_id"],
                "candidate_scope": record["candidate_scope"],
                "confidence": record.get("confidence"),
                "normalized_y": record.get("normalized_y"),
                "normalized_x": record.get("normalized_x"),
                "source_text": record["text"],
            }
        )

    return observations


def _observation_near_anchor(
    observation: dict,
    anchor: dict,
) -> bool:
    observation_y = observation.get("normalized_y")
    anchor_y = anchor.get("normalized_y")

    if observation_y is None or anchor_y is None:
        return False

    distance = abs(
        float(observation_y)
        - float(anchor_y)
    )

    bbox = anchor.get("bbox") or {}
    image_height = float(
        anchor.get("image_height", 1)
        or 1
    )

    anchor_height = (
        float(bbox.get("height", 0))
        / image_height
    )

    tolerance = max(
        0.0035,
        min(
            0.010,
            anchor_height * 0.40,
        ),
    )

    return distance <= tolerance


def _component_evidence(
    anchor: dict,
    family: list[dict],
    all_records: list[dict],
    component: str,
) -> list[dict]:
    evidence = []

    family_ids = {
        (
            record["candidate_id"],
            record["candidate_line_index"],
        )
        for record in family
    }

    # Full-receipt component evidence comes ONLY from the same row family.
    for record in family:
        evidence.extend(
            _component_word_observations(
                record,
                component,
            )
        )

    # Right-column OCR is allowed to contribute only price/tax evidence and
    # only when the component itself is tightly aligned with the anchor row.
    if component in (
        "price",
        "tax_code",
    ):
        for record in all_records:
            if record["candidate_scope"] != "right_column":
                continue

            for observation in _component_word_observations(
                record,
                component,
            ):
                if _observation_near_anchor(
                    observation,
                    anchor,
                ):
                    evidence.append(
                        observation
                    )

    return evidence


def _rank_component_values(
    evidence: list[dict],
) -> list[dict]:
    by_value: dict[str, dict] = {}

    for observation in evidence:
        value = observation["value"]
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
            try:
                confidence_float = float(
                    confidence
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence_float = 0.0

            if confidence_float >= 0:
                entry["confidence_sum"] += (
                    confidence_float
                )
                entry["confidence_count"] += 1

        entry["examples"].append(
            {
                "candidate_id": candidate_id,
                "candidate_scope": observation.get(
                    "candidate_scope",
                    "full",
                ),
                "text": observation[
                    "source_text"
                ],
            }
        )

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
            {
                "value": value,
                "support_count": support_count,
                "average_confidence": round(
                    average_confidence,
                    2,
                ),
                "examples": entry["examples"],
            }
        )

    ranked.sort(
        key=lambda item: (
            item["support_count"],
            item["average_confidence"],
        ),
        reverse=True,
    )

    return ranked


def _select_component(
    anchor: dict,
    family: list[dict],
    all_records: list[dict],
    component: str,
    existing_values: list[str],
    allow_single_high_confidence: bool,
) -> tuple[str | None, dict]:
    evidence = _component_evidence(
        anchor=anchor,
        family=family,
        all_records=all_records,
        component=component,
    )

    ranked = _rank_component_values(
        evidence
    )

    empty_meta = {
        "support_count": 0,
        "average_confidence": None,
        "examples": [],
        "selection_reason": (
            "no reliable OCR evidence"
        ),
    }

    if not ranked:
        if existing_values:
            return (
                existing_values[0],
                {
                    **empty_meta,
                    "selection_reason": (
                        "kept value already present "
                        "in selected full-receipt line"
                    ),
                },
            )

        return None, empty_meta

    # If the selected full-receipt line already contains exactly one value,
    # preservation is preferred. Another value must have materially stronger
    # independent evidence before it can replace it.
    if len(existing_values) == 1:
        existing = existing_values[0]

        existing_rank = next(
            (
                item
                for item in ranked
                if item["value"] == existing
            ),
            None,
        )

        best = ranked[0]

        if (
            best["value"] != existing
            and best["support_count"]
            >= max(
                MIN_COMPONENT_SUPPORT + 1,
                (
                    existing_rank[
                        "support_count"
                    ]
                    if existing_rank
                    else 1
                ) + 2,
            )
        ):
            return (
                best["value"],
                {
                    **best,
                    "selection_reason": (
                        "alternate OCR value had "
                        "materially stronger support"
                    ),
                },
            )

        if existing_rank is not None:
            return (
                existing,
                {
                    **existing_rank,
                    "selection_reason": (
                        "preserved value already present "
                        "in selected full-receipt line"
                    ),
                },
            )

        return (
            existing,
            {
                **empty_meta,
                "selection_reason": (
                    "preserved value already present "
                    "in selected full-receipt line"
                ),
            },
        )

    best = ranked[0]

    if best["support_count"] >= MIN_COMPONENT_SUPPORT:
        return (
            best["value"],
            {
                **best,
                "selection_reason": (
                    "selected from multiple independent "
                    "OCR candidates"
                ),
            },
        )

    if (
        allow_single_high_confidence
        and best["average_confidence"]
        >= SINGLE_OBSERVATION_MIN_CONFIDENCE
    ):
        return (
            best["value"],
            {
                **best,
                "selection_reason": (
                    "single very-high-confidence observation "
                    "accepted for strongly anchored row"
                ),
            },
        )

    return (
        None,
        {
            **best,
            "selection_reason": (
                "evidence rejected because support "
                "was too weak"
            ),
        },
    )


# ---------------------------------------------------------------------------
# DESCRIPTION CONSENSUS
# ---------------------------------------------------------------------------

def _best_description(
    anchor: dict,
    family: list[dict],
) -> tuple[str, dict]:
    anchor_description = (
        _description_without_components(
            anchor["text"]
        )
    )

    candidates = []

    for observation in family:
        description = (
            _description_without_components(
                observation["text"]
            )
        )

        if not description:
            continue

        if anchor_description:
            similarity_to_anchor = (
                SequenceMatcher(
                    None,
                    _normalize_line(
                        anchor_description
                    ),
                    _normalize_line(
                        description
                    ),
                ).ratio()
            )
        else:
            similarity_to_anchor = 0.0

        # For SKU-anchored rows, OCR may badly damage the anchor description,
        # so exact SKU agreement is allowed to rescue it.
        sku_anchor = bool(
            _shared_sku(
                anchor["text"],
                observation["text"],
            )
        )

        if (
            anchor_description
            and similarity_to_anchor < 0.42
            and not sku_anchor
        ):
            continue

        support = 1

        for other in family:
            if (
                other["candidate_id"]
                == observation[
                    "candidate_id"
                ]
            ):
                continue

            other_description = (
                _description_without_components(
                    other["text"]
                )
            )

            if not other_description:
                continue

            similarity = SequenceMatcher(
                None,
                _normalize_line(description),
                _normalize_line(
                    other_description
                ),
            ).ratio()

            if similarity >= 0.64:
                support += 1

        confidence = observation.get(
            "confidence"
        ) or 0.0

        score = (
            support * 5.0
            + float(confidence)
            + min(
                len(description.split()),
                10,
            ) * 1.2
            + similarity_to_anchor * 8.0
            - _garbage_penalty(
                description
            )
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
                "similarity_to_anchor": round(
                    similarity_to_anchor,
                    4,
                ),
                "score": score,
            }
        )

    if not candidates:
        return (
            anchor_description,
            {
                "source_candidate": anchor[
                    "candidate_id"
                ],
                "source_text": anchor["text"],
                "support_count": 1,
                "confidence": anchor.get(
                    "confidence"
                ),
                "score": 0.0,
                "selection_reason": (
                    "kept selected full-receipt "
                    "description"
                ),
            },
        )

    candidates.sort(
        key=lambda item: (
            item["score"],
            len(item["description"]),
        ),
        reverse=True,
    )

    selected = candidates[0]

    return (
        selected["description"],
        {
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
            "similarity_to_anchor": selected[
                "similarity_to_anchor"
            ],
            "score": round(
                selected["score"],
                4,
            ),
            "selection_reason": (
                "best description among strongly "
                "matched full-receipt row observations"
            ),
        },
    )


# ---------------------------------------------------------------------------
# MERCHANDISE CLASSIFICATION
# ---------------------------------------------------------------------------

def _contains_non_merchandise_term(
    text: str,
) -> bool:
    normalized = _normalize_line(text)

    return any(
        term in normalized
        for term in NON_MERCHANDISE_TERMS
    )


def _looks_like_address_or_header(
    text: str,
) -> bool:
    lowered = " " + text.lower() + " "

    if any(
        hint in lowered
        for hint in ADDRESS_HINTS
    ):
        return True

    # US-style phone number.
    if re.search(
        r"\b\d{3}[-.) ]\d{3}[- ]\d{4}\b",
        text,
    ):
        return True

    return False


def _alphabetic_character_count(
    text: str,
) -> int:
    return sum(
        1
        for character in text
        if character.isalpha()
    )


def _looks_like_merchandise_row(
    anchor: dict,
    family: list[dict],
    all_records: list[dict],
) -> tuple[bool, str]:
    text = anchor["text"]

    # Metadata rules always beat SKU/price heuristics.
    if _contains_non_merchandise_term(
        text
    ):
        return (
            False,
            "known receipt metadata/total/payment row",
        )

    if _looks_like_address_or_header(
        text
    ):
        return (
            False,
            "address/header-like row",
        )

    description = (
        _description_without_components(
            text
        )
    )

    if (
        _alphabetic_character_count(
            description
        )
        < 3
    ):
        return (
            False,
            "insufficient product-like text",
        )

    anchor_skus = _extract_skus(text)
    anchor_prices = _extract_prices(text)

    if len(anchor_skus) == 1:
        return (
            True,
            "selected full-receipt line contains one SKU",
        )

    if len(anchor_prices) == 1:
        return (
            True,
            "selected full-receipt line contains one price",
        )

    # A price missing from the chosen line can still be recovered, but only
    # when the same textual row is independently observed and the price has
    # multiple-candidate support.
    price_evidence = _component_evidence(
        anchor=anchor,
        family=family,
        all_records=all_records,
        component="price",
    )
    ranked_prices = _rank_component_values(
        price_evidence
    )

    full_family_candidates = {
        record["candidate_id"]
        for record in family
        if record["candidate_scope"] == "full"
    }

    if (
        len(full_family_candidates) >= 2
        and ranked_prices
        and ranked_prices[0][
            "support_count"
        ] >= MIN_COMPONENT_SUPPORT
    ):
        return (
            True,
            "multiple matching row observations plus "
            "independent price support",
        )

    return (
        False,
        "no sufficiently supported merchandise evidence",
    )


# ---------------------------------------------------------------------------
# CONSERVATIVE ROW RECONSTRUCTION
# ---------------------------------------------------------------------------

def _reconstruct_row(
    base_line: dict,
    all_records: list[dict],
) -> dict:
    family = _row_family(
        base_line,
        all_records,
    )

    merchandise, classification_reason = (
        _looks_like_merchandise_row(
            base_line,
            family,
            all_records,
        )
    )

    if not merchandise:
        return {
            **base_line,
            "reconstructed": False,
            "reconstruction_reason": (
                classification_reason
            ),
            "row_family_support": len(
                {
                    record["candidate_id"]
                    for record in family
                }
            ),
        }

    existing_skus = _extract_skus(
        base_line["text"]
    )
    existing_prices = _extract_prices(
        base_line["text"]
    )
    existing_tax_codes = (
        _extract_tax_codes(
            base_line["text"]
        )
    )

    sku_anchor = (
        len(existing_skus) == 1
    )

    # A SKU is NEVER injected into a line that did not already have one.
    if sku_anchor:
        sku = existing_skus[0]
        sku_meta = {
            "value": sku,
            "support_count": len(
                {
                    record["candidate_id"]
                    for record in family
                    if sku in record.get(
                        "skus",
                        [],
                    )
                }
            ),
            "selection_reason": (
                "preserved SKU already present "
                "in selected full-receipt line"
            ),
            "examples": [],
        }
    else:
        sku = None
        sku_meta = {
            "value": None,
            "support_count": 0,
            "selection_reason": (
                "SKU injection disabled because "
                "selected line had no SKU"
            ),
            "examples": [],
        }

    description, description_meta = (
        _best_description(
            base_line,
            family,
        )
    )

    price, price_meta = _select_component(
        anchor=base_line,
        family=family,
        all_records=all_records,
        component="price",
        existing_values=existing_prices,
        allow_single_high_confidence=(
            sku_anchor
        ),
    )

    # Tax code is useful for Publix-like rows, but it is not guessed from a
    # single weak observation.
    tax_code, tax_meta = _select_component(
        anchor=base_line,
        family=family,
        all_records=all_records,
        component="tax_code",
        existing_values=existing_tax_codes,
        allow_single_high_confidence=False,
    )

    # Keep Aldi/SKU-style rows clean for the existing Aldi parser, which does
    # not remove tax codes from product text. For no-SKU rows, preserve the
    # Publix-style Description + Tax + Price layout.
    parts = []

    if sku:
        parts.append(sku)

    if description:
        parts.append(description)

    if not sku and tax_code:
        parts.append(tax_code)

    if price:
        parts.append(price)

    reconstructed_text = (
        " ".join(parts).strip()
    )

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
            reconstructed_text
            != base_line["text"]
        ),
        "original_consensus_text": (
            base_line["text"]
        ),
        "reconstruction_method": (
            "conservative receipt-row consensus: "
            "same-row geometry must also have textual/SKU agreement; "
            "SKU cannot be injected; price/tax additions require "
            "independent support; unsupported components remain absent"
        ),
        "row_classification": {
            "is_merchandise": True,
            "reason": classification_reason,
            "family_candidate_count": len(
                {
                    record["candidate_id"]
                    for record in family
                }
            ),
        },
        "component_support": {
            "sku": {
                "value": sku,
                **sku_meta,
            },
            "description": {
                "value": (
                    description
                    or None
                ),
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


# ---------------------------------------------------------------------------
# SELECT BEST ACTUAL OCR LINE
# ---------------------------------------------------------------------------

def _best_row_match(
    anchor: dict,
    records: list[dict],
) -> tuple[dict | None, float, str]:
    sku_matches = []

    for record in records:
        shared = _shared_sku(
            anchor["text"],
            record["text"],
        )

        if shared:
            sku_matches.append(record)

    if sku_matches:
        sku_matches.sort(
            key=lambda record: (
                _line_quality(record),
                _line_similarity(
                    anchor["text"],
                    record["text"],
                ),
            ),
            reverse=True,
        )
        return (
            sku_matches[0],
            1.0,
            "sku",
        )

    strong_matches = []

    for record in records:
        matched, similarity, method = (
            _strong_row_match(
                anchor,
                record,
            )
        )

        if not matched:
            continue

        strong_matches.append(
            (
                record,
                similarity,
                method,
            )
        )

    if strong_matches:
        strong_matches.sort(
            key=lambda item: (
                item[1],
                _line_quality(item[0]),
            ),
            reverse=True,
        )
        return strong_matches[0]

    # Fuzzy fallback is deliberately strict and does not use geometry alone.
    best_record = None
    best_score = 0.0

    for record in records:
        score = _line_similarity(
            anchor["text"],
            record["text"],
        )

        if (
            score >= MATCH_THRESHOLD
            and score > best_score
        ):
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
    all_records: list[dict],
) -> tuple[int, list[dict]]:
    supporting = []

    for candidate in candidates:
        if (
            candidate["candidate_id"]
            == line["candidate_id"]
            or candidate.get(
                "candidate_scope",
                "full",
            )
            != "full"
        ):
            continue

        candidate_records = [
            record
            for record in all_records
            if record["candidate_id"]
            == candidate["candidate_id"]
        ]

        best, similarity, method = (
            _best_row_match(
                line,
                candidate_records,
            )
        )

        if best is None:
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
            or candidate.get(
                "candidate_scope",
                "full",
            )
            != "full"
        ):
            continue

        candidate_records = [
            record
            for record in all_records
            if record["candidate_id"]
            == candidate["candidate_id"]
        ]

        match, similarity, method = (
            _best_row_match(
                backbone_line,
                candidate_records,
            )
        )

        if match is None:
            continue

        alternatives.append(
            {
                **match,
                "match_method": method,
                "match_to_backbone": round(
                    similarity,
                    4,
                ),
            }
        )

    scored = []

    for alternative in alternatives:
        support_count, supporting = (
            _support_for_line(
                alternative,
                candidates,
                all_records,
            )
        )

        quality = _line_quality(
            alternative
        )

        consensus_score = (
            quality
            + (support_count - 1) * 3.5
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


# ---------------------------------------------------------------------------
# CANDIDATE RANKING / PIPELINE
# ---------------------------------------------------------------------------

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
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate["psm"],
                "candidate_scope": candidate.get(
                    "candidate_scope",
                    "full",
                ),
                "comparison_metrics": (
                    _candidate_metrics(
                        candidate
                    )
                ),
                "result": candidate[
                    "result"
                ],
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

    if not ranked_candidates:
        raise ValueError(
            "No full-receipt OCR candidate is available "
            "for the reading-order backbone."
        )

    backbone_ranked = (
        ranked_candidates[0]
    )
    backbone_id = backbone_ranked[
        "candidate_id"
    ]

    all_records = _build_records(
        candidates
    )

    backbone_records = [
        record
        for record in all_records
        if record["candidate_id"]
        == backbone_id
    ]

    consensus_lines = []
    component_reconstructions = 0
    merchandise_lines = 0

    for backbone_record in backbone_records:
        chosen = _choose_consensus_line(
            backbone_record,
            all_records,
            candidates,
        )

        consensus_line = {
            "line_number": (
                len(consensus_lines) + 1
            ),
            "candidate_id": chosen[
                "candidate_id"
            ],
            "candidate_line_index": chosen.get(
                "candidate_line_index"
            ),
            "candidate_scope": chosen.get(
                "candidate_scope",
                "full",
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
            "normalized_y": chosen.get(
                "normalized_y"
            ),
            "bbox": chosen.get(
                "bbox"
            ),
            "words": chosen.get(
                "words",
                [],
            ),
            "image_height": chosen.get(
                "image_height",
                1,
            ),
            "skus": chosen.get(
                "skus",
                [],
            ),
            "prices": chosen.get(
                "prices",
                [],
            ),
            "tax_codes": chosen.get(
                "tax_codes",
                [],
            ),
        }

        reconstructed = _reconstruct_row(
            consensus_line,
            all_records,
        )

        if reconstructed.get(
            "reconstructed"
        ):
            component_reconstructions += 1

        if reconstructed.get(
            "row_classification",
            {},
        ).get(
            "is_merchandise"
        ):
            merchandise_lines += 1

        # Keep output compact and backwards-friendly. Geometry remains available
        # at the line level, while full word arrays stay in the candidate file.
        reconstructed.pop(
            "words",
            None,
        )
        reconstructed.pop(
            "image_height",
            None,
        )
        reconstructed.pop(
            "skus",
            None,
        )
        reconstructed.pop(
            "prices",
            None,
        )
        reconstructed.pop(
            "tax_codes",
            None,
        )
        reconstructed.pop(
            "candidate_scope",
            None,
        )
        reconstructed.pop(
            "candidate_line_index",
            None,
        )

        consensus_lines.append(
            reconstructed
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
            "conservative multi-variant receipt-row consensus: "
            "best full-receipt candidate supplies reading order; "
            "geometry must also have textual/SKU agreement; "
            "SKU is never injected into a row; price/tax additions "
            "require independent OCR support; absence is preferred "
            "to unsupported reconstruction"
        ),
        "backbone_candidate": {
            "candidate_id": backbone_ranked[
                "candidate_id"
            ],
            "image_variant": backbone_ranked[
                "image_variant"
            ],
            "psm": backbone_ranked[
                "psm"
            ],
            "comparison_metrics": (
                backbone_ranked[
                    "comparison_metrics"
                ]
            ),
        },
        "consensus_summary": {
            "backbone_line_count": len(
                backbone_records
            ),
            "consensus_line_count": len(
                consensus_lines
            ),
            "merchandise_line_count": (
                merchandise_lines
            ),
            "component_reconstruction_count": (
                component_reconstructions
            ),
            "candidate_count": len(
                candidates
            ),
            "full_candidate_count": sum(
                1
                for candidate in candidates
                if candidate.get(
                    "candidate_scope",
                    "full",
                )
                == "full"
            ),
            "right_column_candidate_count": sum(
                1
                for candidate in candidates
                if candidate.get(
                    "candidate_scope",
                    "full",
                )
                == "right_column"
            ),
            "match_threshold": (
                MATCH_THRESHOLD
            ),
            "max_row_center_distance": (
                MAX_ROW_CENTER_DISTANCE
            ),
            "minimum_component_support": (
                MIN_COMPONENT_SUPPORT
            ),
        },
        "raw_text": raw_text,
        "text": consensus_lines,
        "candidate_ranking": [
            {
                "rank": rank,
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate[
                    "psm"
                ],
                "comparison_metrics": (
                    candidate[
                        "comparison_metrics"
                    ]
                ),
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
                "All output remains OCR-derived. A full-receipt "
                "observation may join another observation only through "
                "exact SKU agreement or close physical-row geometry plus "
                "textual agreement. Right-column observations can contribute "
                "only price/tax evidence at the same narrow row position. "
                "SKU values cannot be imported into rows that lacked a SKU "
                "in the selected full-receipt observation. Components with "
                "insufficient support are omitted rather than guessed."
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
        "Build Conservative Row Consensus ===\n"
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
            "[OK] Conservative row consensus OCR "
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
            "\nMerchandise lines: "
            f"{summary['merchandise_line_count']}"
            "\nRows reconstructed: "
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
        print(
            f"\n[ERROR] {error}"
        )
