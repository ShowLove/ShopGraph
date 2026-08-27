from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median

from PIL import Image
import pytesseract


SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
TAX_PATTERN = re.compile(
    r"(?<![A-Za-z])(FA|FB|NA|NB|TLF|TF|LF|F|T)(?![A-Za-z])",
    re.IGNORECASE,
)

MISSING_Y_TOLERANCE = 0.008
MIN_MISSING_CANDIDATES = 3
MIN_SKU_SUPPORT = 2
MIN_PRICE_SUPPORT = 2
MIN_DESCRIPTION_SUPPORT = 3

NUMERIC_RIGHT_START = 0.58
NUMERIC_Y_PADDING = 0.0045
NUMERIC_PSMS = (7, 13)
NUMERIC_REPLACE_RATIO = 1.35
NUMERIC_MIN_SUPPORT = 2

BLOCKED_TERMS = (
    "subtotal", "total tax", "amount due", "balance to pay",
    "credit card", "visa credit", "visa debit", "auth code",
    "auth trace", "auth/trace", "reference", "customer copy",
    "sale transaction", "purchase transaction", "payment card",
    "items in transaction", "items in trans", "approved",
    "entrymode", "entry mode", "store manager", "your cashier",
    "sign up", "thank you", "change due", "cash tendered",
)

ADDRESS_HINTS = (
    " ave", " avenue", " blvd", " boulevard", " road", " rd",
    " street", " st ", " highway", " hwy", "melbourne",
    "indian harbour", "town center",
)


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _norm(text: str) -> str:
    text = text.lower().replace(",", ".")
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    return " ".join(text.split())


def _prices(text: str) -> list[str]:
    return [value.replace(",", ".") for value in PRICE_PATTERN.findall(text)]


def _skus(text: str) -> list[str]:
    return SKU_PATTERN.findall(text)


def _taxes(text: str) -> list[str]:
    return [value.upper() for value in TAX_PATTERN.findall(text)]


def _description(text: str) -> str:
    text = SKU_PATTERN.sub(" ", text)
    text = PRICE_PATTERN.sub(" ", text)
    text = TAX_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" -:;,.|_~'\"()[]{}$")


def _similar(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, _norm(left), _norm(right)).ratio()


def _blocked(text: str) -> bool:
    normalized = _norm(text)
    if any(term in normalized for term in BLOCKED_TERMS):
        return True

    lowered = " " + text.lower() + " "
    if any(hint in lowered for hint in ADDRESS_HINTS):
        return True

    if re.search(r"\b\d{3}[-.) ]\d{3}[- ]\d{4}\b", text):
        return True

    return False


def _candidate_records(candidates_data: dict) -> list[dict]:
    records = []

    for candidate in candidates_data["candidates"]:
        if candidate.get("candidate_scope", "full") != "full":
            continue

        result = candidate["result"]
        image = result.get("image", {})
        height = image.get("height", 1) or 1

        for index, line in enumerate(result.get("text", [])):
            text = line.get("text", "").strip()
            if not text:
                continue

            records.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "image_variant": candidate["image_variant"],
                    "psm": candidate["psm"],
                    "source_image": result.get("source_image"),
                    "candidate_line_index": index,
                    "text": text,
                    "confidence": line.get("confidence") or 0.0,
                    "normalized_y": line.get("normalized_y"),
                    "bbox": line.get("bbox"),
                    "image_height": height,
                    "skus": _skus(text),
                    "prices": _prices(text),
                    "tax_codes": _taxes(text),
                }
            )

    return records


def _numeric_evidence(
    line: dict,
    candidates_data: dict,
) -> list[dict]:
    y = line.get("normalized_y")
    if y is None:
        return []

    bbox = line.get("bbox") or {}
    image_height = float(line.get("image_height", 1) or 1)
    row_height = float(bbox.get("height", 0)) / image_height
    half_height = max(NUMERIC_Y_PADDING, min(0.018, row_height * 0.70))

    top = max(0.0, float(y) - half_height)
    bottom = min(1.0, float(y) + half_height)

    evidence = []
    seen_paths = set()

    for candidate in candidates_data["candidates"]:
        if candidate.get("candidate_scope", "full") != "full":
            continue

        result = candidate["result"]
        path_value = result.get("source_image")

        if not path_value or path_value in seen_paths:
            continue

        seen_paths.add(path_value)
        path = Path(path_value).expanduser()

        if not path.exists():
            continue

        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                width, height = image.size

                crop = image.crop(
                    (
                        int(width * NUMERIC_RIGHT_START),
                        int(height * top),
                        width,
                        int(height * bottom),
                    )
                )

                crop = crop.resize(
                    (
                        max(1, crop.width * 3),
                        max(1, crop.height * 3),
                    )
                )

                for psm in NUMERIC_PSMS:
                    raw = pytesseract.image_to_string(
                        crop,
                        config=(
                            f"--psm {psm} "
                            "-c tessedit_char_whitelist=0123456789.$,"
                        ),
                    ).strip()

                    for price in _prices(raw):
                        evidence.append(
                            {
                                "value": price,
                                "source": (
                                    f"numeric:{candidate['image_variant']}:psm{psm}"
                                ),
                            }
                        )
        except OSError:
            continue

    return evidence


def _weighted_price_votes(
    line: dict,
    candidates_data: dict,
) -> dict[str, float]:
    votes = defaultdict(float)

    existing = _prices(line["text"])
    for price in existing:
        votes[price] += 1.5

    # Ordinary OCR candidates near this row.
    target_y = line.get("normalized_y")

    if target_y is not None:
        for candidate in candidates_data["candidates"]:
            result = candidate["result"]

            for candidate_line in result.get("text", []):
                line_y = candidate_line.get("normalized_y")
                if line_y is None:
                    continue

                if abs(float(line_y) - float(target_y)) > 0.008:
                    continue

                candidate_text = candidate_line.get("text", "")
                desc_score = _similar(
                    _description(line["text"]),
                    _description(candidate_text),
                )

                if desc_score < 0.45:
                    continue

                for price in _prices(candidate_text):
                    votes[price] += 1.0

    for item in _numeric_evidence(line, candidates_data):
        votes[item["value"]] += 1.25

    return dict(votes)


def _refine_existing_prices(
    raw_data: dict,
    candidates_data: dict,
) -> int:
    changes = 0

    # Map source-image dimensions into output lines for targeted OCR.
    variant_result = next(
        (
            candidate["result"]
            for candidate in candidates_data["candidates"]
            if candidate.get("candidate_scope", "full") == "full"
        ),
        None,
    )

    image_height = (
        variant_result.get("image", {}).get("height", 1)
        if variant_result
        else 1
    ) or 1

    for line in raw_data.get("text", []):
        if not line.get("row_classification", {}).get("is_merchandise"):
            continue

        current = _prices(line["text"])
        if len(current) != 1:
            continue

        line["image_height"] = image_height

        votes = _weighted_price_votes(
            line,
            candidates_data,
        )

        if not votes:
            line.pop("image_height", None)
            continue

        ranked = sorted(
            votes.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        best_value, best_weight = ranked[0]
        current_weight = votes.get(current[0], 0.0)

        if (
            best_value != current[0]
            and best_weight >= NUMERIC_MIN_SUPPORT
            and best_weight >= current_weight * NUMERIC_REPLACE_RATIO
        ):
            old_text = line["text"]
            line["text"] = PRICE_PATTERN.sub(
                best_value,
                line["text"],
                count=1,
            )
            line["numeric_refined"] = True
            line["numeric_refinement"] = {
                "old_price": current[0],
                "new_price": best_value,
                "vote_weight": round(best_weight, 2),
                "old_vote_weight": round(current_weight, 2),
                "rule": (
                    "alternate targeted numeric OCR evidence "
                    "materially exceeded the selected-line price"
                ),
            }

            support = line.get("component_support", {})
            if "price" in support:
                support["price"]["value"] = best_value
                support["price"]["numeric_refinement_used"] = True
                support["price"]["replaced_existing_value"] = current[0]

            changes += 1

        line.pop("image_height", None)

    return changes


def _eligible_missing_record(record: dict) -> bool:
    if record.get("normalized_y") is None:
        return False

    if _blocked(record["text"]):
        return False

    description = _description(record["text"])
    alpha_count = sum(character.isalpha() for character in description)

    if alpha_count < 3:
        return False

    return bool(
        record["skus"]
        or record["prices"]
        or len(description.split()) >= 2
    )


def _cluster_missing_records(
    records: list[dict],
) -> list[list[dict]]:
    records = [
        record
        for record in records
        if _eligible_missing_record(record)
    ]
    records.sort(key=lambda record: float(record["normalized_y"]))

    clusters = []

    for record in records:
        chosen = None

        for cluster in clusters:
            representative = max(
                cluster,
                key=lambda item: float(item["confidence"]),
            )

            if abs(
                float(representative["normalized_y"])
                - float(record["normalized_y"])
            ) > MISSING_Y_TOLERANCE:
                continue

            same_sku = bool(
                set(representative["skus"])
                & set(record["skus"])
            )

            desc_sim = _similar(
                _description(representative["text"]),
                _description(record["text"]),
            )

            if same_sku or desc_sim >= 0.55:
                chosen = cluster
                break

        if chosen is None:
            clusters.append([record])
            continue

        # Keep one observation per candidate in a cluster.
        duplicate = next(
            (
                existing
                for existing in chosen
                if existing["candidate_id"]
                == record["candidate_id"]
            ),
            None,
        )

        if duplicate is None:
            chosen.append(record)
        elif record["confidence"] > duplicate["confidence"]:
            chosen.remove(duplicate)
            chosen.append(record)

    return clusters


def _cluster_description(cluster: list[dict]) -> tuple[str, int]:
    best_text = ""
    best_support = 0
    best_confidence = -1.0

    descriptions = [
        (_description(record["text"]), record)
        for record in cluster
        if _description(record["text"])
    ]

    for description, record in descriptions:
        support = sum(
            1
            for other, _ in descriptions
            if _similar(description, other) >= 0.64
        )

        confidence = float(record["confidence"])

        if (
            support > best_support
            or (
                support == best_support
                and confidence > best_confidence
            )
        ):
            best_text = description
            best_support = support
            best_confidence = confidence

    return best_text, best_support


def _component_support(
    cluster: list[dict],
    field: str,
) -> dict[str, int]:
    values = defaultdict(set)

    for record in cluster:
        for value in record[field]:
            values[value].add(record["candidate_id"])

    return {
        value: len(candidate_ids)
        for value, candidate_ids in values.items()
    }


def _represented(
    cluster: list[dict],
    raw_lines: list[dict],
) -> bool:
    y = median(float(record["normalized_y"]) for record in cluster)
    description, _ = _cluster_description(cluster)
    skus = {
        value
        for value, count in _component_support(cluster, "skus").items()
        if count >= MIN_SKU_SUPPORT
    }

    for line in raw_lines:
        line_y = line.get("normalized_y")
        if line_y is None:
            continue

        if abs(float(line_y) - y) > MISSING_Y_TOLERANCE:
            continue

        if skus & set(_skus(line["text"])):
            return True

        if _similar(description, _description(line["text"])) >= 0.60:
            return True

    return False


def _recover_missing_rows(
    raw_data: dict,
    candidates_data: dict,
) -> int:
    records = _candidate_records(candidates_data)
    clusters = _cluster_missing_records(records)
    recovered = []

    for cluster in clusters:
        candidate_count = len(
            {record["candidate_id"] for record in cluster}
        )

        if candidate_count < MIN_MISSING_CANDIDATES:
            continue

        if _represented(cluster, raw_data["text"]):
            continue

        description, description_support = _cluster_description(cluster)

        if (
            not description
            or description_support < MIN_DESCRIPTION_SUPPORT
        ):
            continue

        sku_support = _component_support(cluster, "skus")
        price_support = _component_support(cluster, "prices")

        sku_ranked = sorted(
            sku_support.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        price_ranked = sorted(
            price_support.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        sku = (
            sku_ranked[0][0]
            if sku_ranked
            and sku_ranked[0][1] >= MIN_SKU_SUPPORT
            else None
        )

        price = (
            price_ranked[0][0]
            if price_ranked
            and price_ranked[0][1] >= MIN_PRICE_SUPPORT
            else None
        )

        if sku is None and price is None:
            continue

        tax_support = _component_support(cluster, "tax_codes")
        tax_ranked = sorted(
            tax_support.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        tax_code = (
            tax_ranked[0][0]
            if tax_ranked
            and tax_ranked[0][1] >= 2
            else None
        )

        anchor = max(
            cluster,
            key=lambda record: float(record["confidence"]),
        )
        y = median(float(record["normalized_y"]) for record in cluster)

        parts = []
        if sku:
            parts.append(sku)
        parts.append(description)
        if not sku and tax_code:
            parts.append(tax_code)
        if price:
            parts.append(price)

        recovered.append(
            {
                "line_number": 0,
                "candidate_id": anchor["candidate_id"],
                "text": " ".join(parts),
                "confidence": anchor["confidence"],
                "source_candidate": anchor["candidate_id"],
                "image_variant": anchor["image_variant"],
                "psm": anchor["psm"],
                "support_count": candidate_count,
                "match_method": "recovered_missing_row",
                "line_quality_score": None,
                "consensus_score": None,
                "normalized_y": y,
                "bbox": anchor.get("bbox"),
                "reconstructed": True,
                "recovered_missing_row": True,
                "numeric_refined": False,
                "original_consensus_text": None,
                "reconstruction_method": (
                    "safe missing-row recovery from at least three "
                    "independent full-receipt OCR observations at the "
                    "same physical y-position with repeated description "
                    "and repeated exact SKU or price evidence"
                ),
                "row_classification": {
                    "is_merchandise": True,
                    "reason": "recovered non-backbone merchandise row",
                    "family_candidate_count": candidate_count,
                },
                "component_support": {
                    "sku": {
                        "value": sku,
                        "support_count": sku_support.get(sku, 0) if sku else 0,
                    },
                    "description": {
                        "value": description,
                        "support_count": description_support,
                    },
                    "price": {
                        "value": price,
                        "support_count": price_support.get(price, 0) if price else 0,
                    },
                    "tax_code": {
                        "value": tax_code,
                        "support_count": tax_support.get(tax_code, 0)
                        if tax_code
                        else 0,
                    },
                },
            }
        )

    if not recovered:
        return 0

    raw_data["text"].extend(recovered)
    raw_data["text"].sort(
        key=lambda line: float(
            line.get("normalized_y")
            if line.get("normalized_y") is not None
            else 999.0
        )
    )

    for index, line in enumerate(raw_data["text"], start=1):
        line["line_number"] = index

    return len(recovered)


def refine_raw_ocr(
    raw_ocr_path: str | Path,
) -> Path:
    raw_path = Path(raw_ocr_path).expanduser().resolve()
    raw_data = _load(raw_path)

    candidates_path = Path(
        raw_data["provenance"]["candidates_file"]
    ).expanduser().resolve()

    candidates_data = _load(candidates_path)

    numeric_changes = _refine_existing_prices(
        raw_data,
        candidates_data,
    )
    recovered_count = _recover_missing_rows(
        raw_data,
        candidates_data,
    )

    summary = raw_data.setdefault("consensus_summary", {})
    summary["recovered_missing_row_count"] = recovered_count
    summary["numeric_refinement_count"] = numeric_changes
    summary["consensus_line_count"] = len(raw_data.get("text", []))
    summary["merchandise_line_count"] = sum(
        1
        for line in raw_data.get("text", [])
        if line.get("row_classification", {}).get("is_merchandise")
    )

    raw_data["selection_method"] = (
        raw_data.get("selection_method", "")
        + "; post-processed with safe missing-row recovery and "
        "targeted numeric-token refinement"
    )

    raw_data["raw_text"] = "\n".join(
        line["text"]
        for line in raw_data.get("text", [])
    )

    raw_data.setdefault("provenance", {})["post_refinement_rule"] = (
        "Numeric refinement OCRs only a narrow right-side strip at the "
        "same y-position and replaces a price only when alternate evidence "
        "materially outvotes the existing value. Missing rows require at "
        "least three independent full-receipt candidates at the same "
        "physical y-position plus repeated description and repeated exact "
        "SKU or price support. Existing conservative row safeguards remain "
        "unchanged."
    )

    _save(raw_path, raw_data)
    return raw_path
