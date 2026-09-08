from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


PRICE_PATTERN = re.compile(
    r"(?<!\d)(?P<currency>\$)?(?P<value>\d+[.,]\d{2})(?!\d)",
    re.IGNORECASE,
)

SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")

SAVINGS_TERMS = (
    "you saved",
    "savings",
    "saved:",
    "discount",
    "coupon",
)

UNAVAILABLE_TERMS = (
    "unavailable",
    "out of stock",
    "not fulfilled",
    "not available",
)

STATUS_TERMS = (
    "shopped",
    "substituted",
    "weight adjusted",
    "unavailable",
)

UNIT_PRICE_MARKERS = (
    "/lb",
    "/ lb",
    "per lb",
    "/oz",
    "/ oz",
    "per oz",
    "/kg",
    "/ kg",
    "per kg",
    "/ea",
    "/ ea",
    "per ea",
    "per each",
)

PROMO_MARKERS = (
    " for $",
    "for $",
    " @ ",
    "each when you buy",
)

CALCULATION_MARKERS = (
    " x ",
    " for $",
    "for $",
    " @ ",
)

# These are item-line metadata fragments, not part of the normalized product name.
QTY_PATTERN = re.compile(
    r"\bqty\s*\d+\b",
    re.IGNORECASE,
)
SHOPPED_PATTERN = re.compile(
    r"\b\d+\s+shopped\b",
    re.IGNORECASE,
)
WEIGHT_ADJUSTED_PATTERN = re.compile(
    r"\b\d+\s+weight\s+adjusted\b",
    re.IGNORECASE,
)
STATUS_PATTERN = re.compile(
    r"\b(?:substituted|unavailable|shopped|weight\s+adjusted)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriceCandidate:
    value: str
    start: int
    end: int
    normalized_x: float | None
    has_currency_symbol: bool
    is_unit_price: bool
    is_promotional_reference: bool
    is_savings_amount: bool


@dataclass(frozen=True)
class RuleBasedLineInterpretation:
    line_number: int
    record: PurchaseRecord | None
    source_line_numbers: tuple[int, ...] = ()
    consumed_by_line_number: int | None = None
    auto_skip_reason: str | None = None
    rule_notes: tuple[str, ...] = ()


def _normalize(text: str) -> str:
    return " ".join(str(text).lower().replace(",", ".").split())


def _decimal_string(value: str) -> str:
    return value.replace(",", ".")


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _word_price_positions(line: dict) -> dict[str, list[float]]:
    positions: dict[str, list[float]] = {}

    for word in line.get("words", []) or []:
        if not isinstance(word, dict):
            continue

        word_text = str(word.get("text", ""))
        x = _safe_float(word.get("normalized_x"))

        if x is None:
            continue

        for match in PRICE_PATTERN.finditer(word_text):
            value = _decimal_string(match.group("value"))
            positions.setdefault(value, []).append(x)

    return positions


def _is_unit_price(text: str, match: re.Match) -> bool:
    after = text[match.end(): match.end() + 16].lower()
    before = text[max(0, match.start() - 12): match.start()].lower()

    if any(marker in after for marker in UNIT_PRICE_MARKERS):
        return True

    # OCR sometimes separates the slash/unit from the price by one token.
    if re.search(r"^\s*(?:/|per)\s*(?:lb|oz|kg|ea|each)\b", after):
        return True

    # "$0.65 lb" is less explicit, so only treat it as unit pricing when
    # nearby arithmetic/weight syntax also supports that interpretation.
    if re.search(r"^\s*(?:lb|oz|kg)\b", after):
        window = (before + " " + after).lower()
        if " x " in window or "@" in window:
            return True

    return False


def _is_promotional_reference(text: str, match: re.Match) -> bool:
    """
    Mark the amount that is syntactically part of a promotion, not every amount
    appearing later on the same line.

    Example:
        "1 @ 3 for $10.00 3.34"
                    ^10.00 is reference price
                          ^3.34 remains eligible final charge
    """
    before = text[max(0, match.start() - 18): match.start()].lower()

    return bool(
        re.search(
            r"(?:\bfor|\@)\s*\$?\s*$",
            before,
        )
    )


def _is_savings_line(text: str) -> bool:
    normalized = _normalize(text)
    return any(term in normalized for term in SAVINGS_TERMS)


def _is_unavailable_line(text: str) -> bool:
    normalized = _normalize(text)
    return any(term in normalized for term in UNAVAILABLE_TERMS)


def _price_candidates(line: dict) -> list[PriceCandidate]:
    text = str(line.get("text", ""))
    positions = _word_price_positions(line)
    result: list[PriceCandidate] = []

    for match in PRICE_PATTERN.finditer(text):
        value = _decimal_string(match.group("value"))
        x_values = positions.get(value, [])
        normalized_x = max(x_values) if x_values else None

        result.append(
            PriceCandidate(
                value=value,
                start=match.start(),
                end=match.end(),
                normalized_x=normalized_x,
                has_currency_symbol=bool(match.group("currency")),
                is_unit_price=_is_unit_price(text, match),
                is_promotional_reference=_is_promotional_reference(text, match),
                is_savings_amount=_is_savings_line(text),
            )
        )

    return result


def _candidate_score(candidate: PriceCandidate, line: dict) -> float:
    """
    Rank price candidates using the receipt rules.

    Position is evidence, not proof. Reference amounts are penalized heavily.
    """
    score = 0.0

    if candidate.normalized_x is not None:
        score += candidate.normalized_x * 100.0
    else:
        text_length = max(len(str(line.get("text", ""))), 1)
        score += (candidate.end / text_length) * 55.0

    if candidate.has_currency_symbol:
        score += 2.0

    if candidate.is_unit_price:
        score -= 70.0

    if candidate.is_promotional_reference:
        score -= 60.0

    if candidate.is_savings_amount:
        score -= 100.0

    return score


def _select_final_price(line: dict) -> tuple[str, tuple[str, ...]]:
    candidates = _price_candidates(line)

    if not candidates:
        return NA, ()

    if _is_savings_line(str(line.get("text", ""))):
        return NA, ("Savings amount rejected as item price.",)

    # A single candidate is normally the final charge unless the text itself
    # explicitly identifies it as a unit/reference amount.
    if len(candidates) == 1:
        candidate = candidates[0]

        if candidate.is_unit_price or candidate.is_promotional_reference:
            return NA, (
                "Only price-like token is a unit/promotional reference amount.",
            )

        return candidate.value, (
            "Single non-reference price-like token selected as final item price.",
        )

    viable = [
        candidate
        for candidate in candidates
        if not (
            candidate.is_unit_price
            or candidate.is_promotional_reference
            or candidate.is_savings_amount
        )
    ]

    # The strongest deterministic case is when the receipt rules eliminate all
    # reference amounts and exactly one candidate remains.
    if len(viable) == 1:
        selected = viable[0]
        return selected.value, (
            "Multiple price-like values evaluated.",
            "Unit/promotional/savings/weight-reference amounts rejected.",
            "Exactly one viable final-charge candidate remained.",
        )

    if not viable:
        return NA, (
            "All price-like values were identified as reference/non-final amounts.",
        )

    # Position may support a decision but must not become an absolute
    # "rightmost decimal wins" rule. Only use geometry when one candidate is
    # clearly separated into a right-side price column.
    positioned = [
        candidate
        for candidate in viable
        if candidate.normalized_x is not None
    ]

    if len(positioned) >= 2:
        ranked = sorted(
            positioned,
            key=lambda candidate: candidate.normalized_x,
            reverse=True,
        )

        if (
            ranked[0].normalized_x is not None
            and ranked[1].normalized_x is not None
            and (
                ranked[0].normalized_x
                - ranked[1].normalized_x
            ) >= 0.12
        ):
            return ranked[0].value, (
                "Multiple viable monetary values remained.",
                "A clearly separated right-side item-price column supplied supporting evidence.",
            )

    return NA, (
        "Multiple plausible final-charge values remain; ambiguity preserved.",
    )


def _line_has_price(line: dict) -> bool:
    return bool(_price_candidates(line))


def _looks_like_pricing_math(line: dict) -> bool:
    text = _normalize(line.get("text", ""))

    if not _line_has_price(line):
        return False

    # Weight/unit arithmetic such as "$0.65/lb x 2.36 lb 1.53".
    if (
        any(marker in text for marker in UNIT_PRICE_MARKERS)
        and " x " in f" {text} "
    ):
        return True

    # Promotional calculation such as "1 @ 3 for $10.00 3.34".
    if re.search(
        r"^\s*\d+\s*@\s*\d+\s*for\s*\$?\d+[.,]\d{2}",
        str(line.get("text", "")),
        re.IGNORECASE,
    ):
        return True

    # A line made mostly of arithmetic/reference syntax is a modifier. Merely
    # containing Qty/status text is NOT enough; Walmart-style item lines may
    # legitimately contain Product + status + Qty + final price on one line.
    alphabetic_words = re.findall(r"[A-Za-z]{3,}", text)
    if (
        any(marker.strip() in text for marker in CALCULATION_MARKERS)
        and len(alphabetic_words) <= 3
    ):
        return True

    return False


def _looks_like_price_only_line(line: dict) -> bool:
    text = str(line.get("text", "")).strip()
    price, _ = _select_final_price(line)

    if price == NA:
        return False

    without_prices = PRICE_PATTERN.sub(" ", text)
    without_prices = re.sub(r"[$\s:;,.|_-]+", "", without_prices)

    return not without_prices


def _clean_item_metadata(text: str) -> str:
    working = str(text)

    # Product identifiers are metadata, not Product Name text.
    working = SKU_PATTERN.sub(" ", working)

    # All price-like values are removed from Product Name.
    working = PRICE_PATTERN.sub(" ", working)

    # Remove known status/quantity fragments that can share the item line.
    working = SHOPPED_PATTERN.sub(" ", working)
    working = WEIGHT_ADJUSTED_PATTERN.sub(" ", working)
    working = QTY_PATTERN.sub(" ", working)
    working = STATUS_PATTERN.sub(" ", working)

    # Remove common trailing tax codes without deleting ordinary words.
    working = re.sub(
        r"(?<![A-Za-z])(?:FA|FB|NA|NB|TLF|TF|LF|F|T)(?![A-Za-z])",
        " ",
        working,
        flags=re.IGNORECASE,
    )

    working = re.sub(r"\s+", " ", working).strip()
    working = working.strip(" -:;,.|_~'\"()[]{}$")

    return working or NA


def _looks_product_like(
    line: dict,
    parser_record: PurchaseRecord,
) -> bool:
    text = str(line.get("text", ""))

    if _is_savings_line(text):
        return False

    if _looks_like_pricing_math(line):
        # A modifier/calculation line is not a new item by itself.
        return False

    product = _clean_item_metadata(
        parser_record.product
        if parser_record.product != NA
        else text
    )

    if product == NA:
        return False

    alphabetic = sum(character.isalpha() for character in product)

    return alphabetic >= 3


def _with_core_fields(
    record: PurchaseRecord,
    *,
    product: str | None = None,
    price: str | None = None,
) -> PurchaseRecord:
    updated = record

    if product is not None:
        updated = updated.with_value("product", product)

    if price is not None:
        updated = updated.with_value("price", price)
        updated = updated.with_value(
            "total",
            price if price != NA else NA,
        )

    return updated


def _parse_primary_line(
    line: dict,
    parser,
    store_number: str,
    receipt_date: str,
) -> tuple[PurchaseRecord, tuple[str, ...]]:
    parser_record = parser.parse_line(
        text=str(line.get("text", "")),
        store_number=store_number,
        receipt_date=receipt_date,
    )

    product = _clean_item_metadata(parser_record.product)
    price, price_notes = _select_final_price(line)

    record = _with_core_fields(
        parser_record,
        product=product,
        price=price,
    )

    notes = [
        "Product identifiers/price/status metadata removed from Product Name.",
        *price_notes,
    ]

    return record, tuple(notes)


def _can_complete_open_product(line: dict) -> bool:
    if _is_savings_line(str(line.get("text", ""))):
        return False

    price, _ = _select_final_price(line)

    if price == NA:
        return False

    return (
        _looks_like_pricing_math(line)
        or _looks_like_price_only_line(line)
    )


def build_rule_based_line_interpretations(
    lines: list[dict],
    parser,
    store_number: str,
    receipt_date: str,
) -> dict[int, RuleBasedLineInterpretation]:
    """
    Build deterministic Product/Price/SKU guesses from ordered OCR lines.

    This intentionally does NOT infer receipt Header/Main/Footer boundaries.
    Store, Store Number, and Date remain controlled by the existing workflow.
    """
    interpretations: dict[int, RuleBasedLineInterpretation] = {}
    ordered = sorted(
        lines,
        key=lambda item: item["line_number"],
    )

    for index, line in enumerate(ordered):
        line_number = line["line_number"]
        text = str(line.get("text", ""))

        if line_number in interpretations:
            # Already consumed as a modifier/completion line.
            continue

        if _is_savings_line(text):
            interpretations[line_number] = RuleBasedLineInterpretation(
                line_number=line_number,
                record=None,
                source_line_numbers=(line_number,),
                auto_skip_reason="Savings/discount line is not a purchased item.",
                rule_notes=("Savings lines are not products.",),
            )
            continue

        if _is_unavailable_line(text):
            interpretations[line_number] = RuleBasedLineInterpretation(
                line_number=line_number,
                record=None,
                source_line_numbers=(line_number,),
                auto_skip_reason=(
                    "Explicit unavailable status means Product + displayed price "
                    "does not prove a completed purchase."
                ),
                rule_notes=(
                    "Unavailable item status rejected as completed purchase.",
                ),
            )
            continue

        parser_record, notes = _parse_primary_line(
            line,
            parser,
            store_number,
            receipt_date,
        )

        if not _looks_product_like(line, parser_record):
            # Modifier/math line that was not consumed by a preceding product.
            # Do not silently convert it into a product.
            if _looks_like_pricing_math(line):
                interpretations[line_number] = RuleBasedLineInterpretation(
                    line_number=line_number,
                    record=None,
                    source_line_numbers=(line_number,),
                    auto_skip_reason=(
                        "Pricing/quantity/weight calculation line is not "
                        "an independent product."
                    ),
                    rule_notes=(
                        "Pricing mathematics does not create a separate item.",
                    ),
                )
            continue

        source_numbers = [line_number]
        record = parser_record
        combined_notes = list(notes)

        # Product lines may remain open while immediately following related
        # pricing/calculation lines are examined.
        if record.price == NA:
            for lookahead in range(index + 1, min(index + 3, len(ordered))):
                next_line = ordered[lookahead]
                next_number = next_line["line_number"]

                if next_number in interpretations:
                    continue

                next_text = str(next_line.get("text", ""))

                if _is_savings_line(next_text):
                    # Savings is related metadata, but it cannot complete price.
                    continue

                if _can_complete_open_product(next_line):
                    final_price, final_notes = _select_final_price(next_line)

                    if final_price != NA:
                        record = _with_core_fields(
                            record,
                            price=final_price,
                        )
                        source_numbers.append(next_number)
                        combined_notes.extend(
                            (
                                "Open product completed from following related line.",
                                *final_notes,
                            )
                        )

                        interpretations[next_number] = RuleBasedLineInterpretation(
                            line_number=next_number,
                            record=None,
                            source_line_numbers=(next_number,),
                            consumed_by_line_number=line_number,
                            auto_skip_reason=(
                                f"Used as pricing/quantity/weight detail for "
                                f"OCR Line {line_number}."
                            ),
                            rule_notes=(
                                "Modifier line belongs to preceding product.",
                            ),
                        )
                        break

                # A clearly product-like next line means the open product should
                # not steal information from the next item.
                next_parser_record = parser.parse_line(
                    text=next_text,
                    store_number=store_number,
                    receipt_date=receipt_date,
                )

                if _looks_product_like(
                    next_line,
                    next_parser_record,
                ):
                    break

        interpretations[line_number] = RuleBasedLineInterpretation(
            line_number=line_number,
            record=record,
            source_line_numbers=tuple(source_numbers),
            rule_notes=tuple(dict.fromkeys(combined_notes)),
        )

    return interpretations
