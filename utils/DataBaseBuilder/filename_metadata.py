from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


FILENAME_METADATA_PATTERN = re.compile(
    r"^(?P<date>\d{6}|\d{8})_"
    r"(?P<store>[^_]+)_"
    r"(?P<store_number>[^_]+)"
    r"(?:_|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReceiptFilenameMetadata:
    receipt_date: str
    store_name: str
    store_number: str
    parser_option: str


def _normalize_store_name(value: str) -> str:
    cleaned = re.sub(r"[-]+", " ", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    lowered = cleaned.lower().replace("'", "")

    if lowered == "publix":
        return "Publix"
    if lowered in {"trader joes", "trader joe", "traderjoes", "traderjoe"}:
        return "Trader Joe's"
    if lowered == "aldi":
        return "Aldi"
    if lowered == "walmart":
        return "Walmart"
    return cleaned.title() if cleaned.islower() else cleaned


def _parser_option_for_store(store_name: str) -> str:
    lowered = store_name.lower()
    if lowered == "publix":
        return "1"
    if lowered == "trader joe's":
        return "2"
    if lowered == "aldi":
        return "3"
    return "4"


def _parse_filename_date(value: str) -> str | None:
    for format_string, expected_length in (("%m%d%y", 6), ("%m%d%Y", 8)):
        if len(value) != expected_length:
            continue
        try:
            parsed = datetime.strptime(value, format_string)
        except ValueError:
            continue
        return parsed.strftime("%m/%d/%Y")
    return None


def parse_receipt_filename_metadata(path: str | Path) -> ReceiptFilenameMetadata | None:
    """
    Recognize only filenames beginning with:
        MMDDYY_Store_StoreNumber...
        MMDDYYYY_Store_StoreNumber...

    If recognition fails, return None so DataBaseBuilder keeps its original
    manual Receipt Type / Store Number / Receipt Date prompts.
    """
    match = FILENAME_METADATA_PATTERN.match(Path(path).name)
    if match is None:
        return None

    receipt_date = _parse_filename_date(match.group("date"))
    if receipt_date is None:
        return None

    store_name = _normalize_store_name(match.group("store"))
    store_number = match.group("store_number").strip()

    if not store_name or not store_number:
        return None

    return ReceiptFilenameMetadata(
        receipt_date=receipt_date,
        store_name=store_name,
        store_number=store_number,
        parser_option=_parser_option_for_store(store_name),
    )
