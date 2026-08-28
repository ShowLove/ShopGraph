from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from utils.constants import DATA_DIR


CONFIG_DIR = DATA_DIR / "config"
SKIP_TERMS_FILE = CONFIG_DIR / "skip_terms.txt"

NA = "NA"

SECTION_PREFIX = "[STORE:"
SECTION_SUFFIX = "]"
TERMS_HEADER = "TERMS:"
SUBSTRINGS_HEADER = "SUBSTRINGS:"


@dataclass(frozen=True)
class SkipMatch:
    matched: bool
    match_type: str | None = None
    matched_value: str | None = None


def _normalize(value: str) -> str:
    return " ".join(
        str(value)
        .strip()
        .casefold()
        .split()
    )


def _display_store(store: str) -> str:
    cleaned = " ".join(str(store).strip().split())
    return cleaned or "Other"


def _empty_rules() -> dict[str, dict[str, list[str]]]:
    return {}


def _ensure_file() -> None:
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if SKIP_TERMS_FILE.exists():
        return

    SKIP_TERMS_FILE.write_text(
        (
            "# ShopGraph store-specific automatic skip rules\n"
            "#\n"
            "# TERMS are exact Product matches for a store.\n"
            "# SUBSTRINGS match anywhere inside Product for a store.\n"
            "# Matching is case-insensitive and whitespace-normalized.\n"
            "#\n"
            "# Example:\n"
            "# [STORE:Walmart]\n"
            "# TERMS:\n"
            "# Unavailable\n"
            "# SUBSTRINGS:\n"
            "# Qty\n"
            "\n"
        ),
        encoding="utf-8",
    )


def load_skip_rules() -> dict[str, dict[str, list[str]]]:
    """
    Load store-specific rules from data/config/skip_terms.txt.

    File format:

        [STORE:Walmart]
        TERMS:
        Unavailable
        SUBSTRINGS:
        Qty

        [STORE:Publix]
        TERMS:
        Some Exact Product
        SUBSTRINGS:
        Coupon
    """
    _ensure_file()

    rules = _empty_rules()
    current_store: str | None = None
    current_mode: str | None = None

    for raw_line in SKIP_TERMS_FILE.read_text(
        encoding="utf-8",
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if (
            line.startswith(SECTION_PREFIX)
            and line.endswith(SECTION_SUFFIX)
        ):
            current_store = line[
                len(SECTION_PREFIX):-len(SECTION_SUFFIX)
            ].strip()

            if current_store:
                rules.setdefault(
                    _normalize(current_store),
                    {
                        "store": current_store,
                        "terms": [],
                        "substrings": [],
                    },
                )

            current_mode = None
            continue

        if line.upper() == TERMS_HEADER:
            current_mode = "terms"
            continue

        if line.upper() == SUBSTRINGS_HEADER:
            current_mode = "substrings"
            continue

        if (
            current_store is None
            or current_mode is None
        ):
            continue

        store_key = _normalize(current_store)

        if store_key not in rules:
            continue

        existing = rules[store_key][current_mode]

        if not any(
            _normalize(item) == _normalize(line)
            for item in existing
        ):
            existing.append(line)

    return rules


def _write_skip_rules(
    rules: dict[str, dict[str, list[str]]],
) -> Path:
    _ensure_file()

    lines = [
        "# ShopGraph store-specific automatic skip rules",
        "#",
        "# TERMS are exact Product matches for a store.",
        "# SUBSTRINGS match anywhere inside Product for a store.",
        "# Matching is case-insensitive and whitespace-normalized.",
        "",
    ]

    ordered = sorted(
        rules.values(),
        key=lambda entry: entry["store"].casefold(),
    )

    for index, entry in enumerate(ordered):
        if index:
            lines.append("")

        lines.append(
            f"[STORE:{entry['store']}]"
        )
        lines.append(TERMS_HEADER)

        for term in entry["terms"]:
            lines.append(term)

        lines.append(SUBSTRINGS_HEADER)

        for substring in entry["substrings"]:
            lines.append(substring)

    lines.append("")

    SKIP_TERMS_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return SKIP_TERMS_FILE.resolve()


def _add_rule(
    store: str,
    value: str,
    rule_type: str,
) -> tuple[bool, Path]:
    cleaned_store = _display_store(store)
    cleaned_value = " ".join(
        str(value).strip().split()
    )

    if (
        not cleaned_value
        or _normalize(cleaned_value) == _normalize(NA)
    ):
        raise ValueError(
            "A skip rule cannot be blank or NA."
        )

    rules = load_skip_rules()
    store_key = _normalize(cleaned_store)

    entry = rules.setdefault(
        store_key,
        {
            "store": cleaned_store,
            "terms": [],
            "substrings": [],
        },
    )

    existing = entry[rule_type]

    if any(
        _normalize(item) == _normalize(cleaned_value)
        for item in existing
    ):
        return False, SKIP_TERMS_FILE.resolve()

    existing.append(cleaned_value)

    return True, _write_skip_rules(rules)


def add_skip_term(
    store: str,
    product: str,
) -> tuple[bool, Path]:
    """
    Add an exact Product match for this store.
    """
    return _add_rule(
        store=store,
        value=product,
        rule_type="terms",
    )


def add_skip_substring(
    store: str,
    substring: str,
) -> tuple[bool, Path]:
    """
    Add a Product substring match for this store.
    """
    return _add_rule(
        store=store,
        value=substring,
        rule_type="substrings",
    )


def match_product(
    store: str,
    product: str,
) -> SkipMatch:
    """
    Store-specific matching.

    TERMS:
        exact Product match after case/whitespace normalization.

    SUBSTRINGS:
        normalized substring appears anywhere in normalized Product.
    """
    product_normalized = _normalize(product)

    if (
        not product_normalized
        or product_normalized == _normalize(NA)
    ):
        return SkipMatch(False)

    rules = load_skip_rules()
    entry = rules.get(
        _normalize(store)
    )

    if entry is None:
        return SkipMatch(False)

    for term in entry["terms"]:
        if product_normalized == _normalize(term):
            return SkipMatch(
                matched=True,
                match_type="term",
                matched_value=term,
            )

    for substring in entry["substrings"]:
        substring_normalized = _normalize(
            substring
        )

        if (
            substring_normalized
            and substring_normalized
            in product_normalized
        ):
            return SkipMatch(
                matched=True,
                match_type="substring",
                matched_value=substring,
            )

    return SkipMatch(False)


def get_skip_terms_file() -> Path:
    _ensure_file()
    return SKIP_TERMS_FILE.resolve()
