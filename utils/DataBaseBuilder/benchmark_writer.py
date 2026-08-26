from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from utils.constants import DATA_DIR
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord
from utils.DataBaseBuilder.receipt_session import ReceiptSession


BENCHMARK_DIR = DATA_DIR / "benchmarks"


def _record_fields(record: PurchaseRecord) -> dict[str, str]:
    return {
        "six_digit_sku": record.six_digit_sku,
        "product": record.product,
        "tax_code": record.tax_code,
        "price": record.price,
        "store_number": record.store_number,
        "date": record.date,
    }


def _corrected_text(record: PurchaseRecord, receipt_type: str) -> str:
    if receipt_type == "Publix":
        values = [record.product, record.tax_code, record.price]
    elif receipt_type == "Trader Joe's":
        values = [record.product, record.price]
    elif receipt_type == "Aldi":
        values = [record.six_digit_sku, record.product, record.price]
    else:
        values = [
            record.six_digit_sku,
            record.product,
            record.tax_code,
            record.price,
        ]

    meaningful = [value for value in values if value != NA]
    return " ".join(meaningful) if meaningful else NA


def _prompt_existing_benchmark(path: Path) -> bool:
    if not path.exists():
        return True

    print(
        "\nA benchmark already exists for this receipt:"
        f"\n\n{path.name}"
        "\n\n1. Replace benchmark with this newly reviewed version"
        "\n0. Keep existing benchmark"
    )

    while True:
        option = input("\nSelect option: ").strip()

        if option == "1":
            return True

        if option == "0":
            return False

        print("\n[ERROR] Invalid option.")


def _atomic_json_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        suffix=".json",
        dir=path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_corrected_benchmark(session: ReceiptSession) -> Path | None:
    """
    Create a corrected counterpart of the immutable raw OCR JSON.

    The benchmark keeps the original top-level structure and line metadata.
    Reviewed lines retain their OCR text in ``original_ocr_text`` while the
    ordinary ``text`` field becomes the final human-reviewed interpretation.
    """
    destination = BENCHMARK_DIR / session.source_path.name

    if not _prompt_existing_benchmark(destination):
        return None

    with session.source_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    lines = data.get("text")
    if not isinstance(lines, list):
        raise ValueError("Raw OCR JSON must contain a top-level 'text' list.")

    reviews = {
        review.line_number: review
        for review in session.reviewed_lines
    }

    for line in lines:
        if not isinstance(line, dict):
            continue

        line_number = line.get("line_number")
        review = reviews.get(line_number)

        if review is None:
            continue

        line["review_status"] = review.status

        if review.purchase is None:
            continue

        original_text = line.get("text", "")
        corrected_text = _corrected_text(
            review.purchase,
            session.receipt_type,
        )

        line["original_ocr_text"] = original_text
        line["text"] = corrected_text
        line["human_review"] = _record_fields(review.purchase)

    data["benchmark"] = {
        "source_raw_ocr": session.source_path.name,
        "receipt_type": session.receipt_type,
        "store_number": session.store_number,
        "receipt_date": session.receipt_date,
        "starting_line_number": session.starting_line_number,
        "reviewed_line_count": len(session.reviewed_lines),
        "accepted_purchase_count": len(session.accepted_purchases),
        "skipped_line_count": len(session.skipped_line_numbers),
        "ground_truth": True,
    }

    _atomic_json_write(destination, data)
    return destination.resolve()
