from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from utils.constants import REFINED_JSON_DIR
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


REQUIRED_FIELDS = (
    "Total",
    "Store",
    "Six-Digit SKU",
    "Product",
    "Tax Code",
    "Store Number",
    "Common Name",
    "Category",
    "Date 1",
    "Price 1",
)

FIELD_MAP = {
    "Total": "total",
    "Store": "store",
    "Six-Digit SKU": "six_digit_sku",
    "Product": "product",
    "Tax Code": "tax_code",
    "Store Number": "store_number",
    "Common Name": "common_name",
    "Category": "category",
    "Date 1": "date",
    "Price 1": "price",
}


def refined_path_for_raw(
    raw_ocr_path: str | Path,
) -> Path:
    raw_path = Path(raw_ocr_path)
    stem = raw_path.stem

    if stem.endswith("_raw_ocr"):
        stem = stem[:-8]

    return REFINED_JSON_DIR / f"{stem}_refined.json"


def load_matching_refined_json(
    raw_ocr_path: str | Path,
) -> dict | None:
    raw_path = Path(raw_ocr_path).expanduser().resolve()
    refined_path = refined_path_for_raw(raw_path)

    if not refined_path.exists():
        return None

    try:
        with refined_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    source_raw = data.get("source_raw_ocr")
    if not isinstance(source_raw, str):
        return None

    if Path(source_raw).name != raw_path.name:
        return None

    lines = data.get("lines")
    if not isinstance(lines, list):
        return None

    line_map = {}

    for line in lines:
        if not isinstance(line, dict):
            return None

        line_number = line.get("line_number")
        fields = line.get("fields")

        if not isinstance(line_number, int):
            return None

        if not isinstance(fields, dict):
            return None

        if not all(
            field in fields
            for field in REQUIRED_FIELDS
        ):
            return None

        line_map[line_number] = line

    return {
        "path": refined_path.resolve(),
        "data": data,
        "line_map": line_map,
        "receipt_context": data.get(
            "receipt_context",
            {},
        ),
    }


def merge_refined_guess(
    parser_record: PurchaseRecord,
    refined_line: dict | None,
    protected_fields: set[str] | None = None,
) -> PurchaseRecord:
    if refined_line is None:
        return parser_record

    fields = refined_line.get("fields")
    if not isinstance(fields, dict):
        return parser_record

    protected = protected_fields or set()
    values = {}

    for refined_name, record_name in FIELD_MAP.items():
        if record_name in protected:
            continue

        value = fields.get(refined_name, NA)

        if (
            isinstance(value, str)
            and value.strip()
            and value.strip() != NA
        ):
            values[record_name] = value.strip()

    if not values:
        return parser_record

    return replace(
        parser_record,
        **values,
    )
