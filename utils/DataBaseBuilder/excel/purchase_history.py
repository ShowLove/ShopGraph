from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from utils.constants import DATA_DIR
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord
from utils.DataBaseBuilder.receipt_session import ReceiptSession


DATABASE_DIR = DATA_DIR / "database"
WORKBOOK_PATH = DATABASE_DIR / "shopgraph_purchase_history.xlsx"
PURCHASE_SHEET = "Purchase History"
IMPORT_SHEET = "Imported Receipts"
FIXED_HEADERS = [
    "Six-Digit SKU",
    "Product",
    "Tax Code",
    "Store Number",
]
IMPORT_HEADERS = [
    "Source OCR JSON",
    "Store Number",
    "Receipt Date",
    "Imported Timestamp",
]


def _create_workbook():
    workbook = Workbook()
    purchase_sheet = workbook.active
    purchase_sheet.title = PURCHASE_SHEET

    for column, header in enumerate(FIXED_HEADERS, start=1):
        purchase_sheet.cell(row=1, column=column, value=header)

    _ensure_history_pair(purchase_sheet, 1)

    import_sheet = workbook.create_sheet(IMPORT_SHEET)

    for column, header in enumerate(IMPORT_HEADERS, start=1):
        import_sheet.cell(row=1, column=column, value=header)

    import_sheet.sheet_state = "hidden"
    _format_workbook(workbook)
    return workbook


def _load_or_create_workbook():
    if WORKBOOK_PATH.exists():
        workbook = load_workbook(WORKBOOK_PATH)

        if PURCHASE_SHEET not in workbook.sheetnames:
            raise ValueError(
                f"Workbook is missing required sheet: {PURCHASE_SHEET}"
            )

        if IMPORT_SHEET not in workbook.sheetnames:
            import_sheet = workbook.create_sheet(IMPORT_SHEET)

            for column, header in enumerate(IMPORT_HEADERS, start=1):
                import_sheet.cell(row=1, column=column, value=header)

            import_sheet.sheet_state = "hidden"

        return workbook

    return _create_workbook()


def _ensure_history_pair(sheet, pair_number: int) -> tuple[int, int]:
    date_column = 5 + (pair_number - 1) * 2
    price_column = date_column + 1

    sheet.cell(
        row=1,
        column=date_column,
        value=f"Date {pair_number}",
    )
    sheet.cell(
        row=1,
        column=price_column,
        value=f"Price {pair_number}",
    )

    return date_column, price_column


def _format_workbook(workbook) -> None:
    purchase_sheet = workbook[PURCHASE_SHEET]
    purchase_sheet.freeze_panes = "A2"
    purchase_sheet.auto_filter.ref = purchase_sheet.dimensions

    for cell in purchase_sheet[1]:
        cell.font = Font(bold=True)

    import_sheet = workbook[IMPORT_SHEET]
    import_sheet.freeze_panes = "A2"

    for cell in import_sheet[1]:
        cell.font = Font(bold=True)

    widths = {
        1: 18,
        2: 34,
        3: 14,
        4: 16,
    }

    for column, width in widths.items():
        purchase_sheet.column_dimensions[
            get_column_letter(column)
        ].width = width

    for column in range(5, purchase_sheet.max_column + 1):
        purchase_sheet.column_dimensions[
            get_column_letter(column)
        ].width = 14

    import_widths = [32, 16, 16, 22]

    for column, width in enumerate(import_widths, start=1):
        import_sheet.column_dimensions[
            get_column_letter(column)
        ].width = width


def _normalized(value) -> str:
    if value is None:
        return ""

    return str(value).strip().casefold()


def _find_matching_row(sheet, record: PurchaseRecord) -> int | None:
    sku = _normalized(record.six_digit_sku)
    product = _normalized(record.product)
    store = _normalized(record.store_number)

    for row in range(2, sheet.max_row + 1):
        row_sku = _normalized(sheet.cell(row=row, column=1).value)
        row_product = _normalized(sheet.cell(row=row, column=2).value)
        row_store = _normalized(sheet.cell(row=row, column=4).value)

        if record.six_digit_sku != NA:
            if row_sku == sku and row_store == store:
                return row
        elif row_product == product and row_store == store:
            return row

    return None


def _next_history_pair(sheet, row: int) -> tuple[int, int]:
    pair_number = 1

    while True:
        date_column, price_column = _ensure_history_pair(
            sheet,
            pair_number,
        )

        date_value = sheet.cell(row=row, column=date_column).value
        price_value = sheet.cell(row=row, column=price_column).value

        if date_value in (None, "") and price_value in (None, ""):
            return date_column, price_column

        pair_number += 1


def _excel_date(value: str):
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return value


def _excel_price(value: str):
    if value == NA:
        return NA

    try:
        return float(value)
    except ValueError:
        return value


def _resolve_tax_code_conflict(
    existing: str,
    incoming: str,
    product: str,
) -> str:
    if existing == NA and incoming != NA:
        return incoming

    if incoming == NA or existing == incoming:
        return existing

    print(
        "\n[WARNING] Tax Code conflict for product:"
        f"\n{product}"
        f"\n1. Keep existing Tax Code: {existing}"
        f"\n2. Use incoming Tax Code: {incoming}"
    )

    while True:
        option = input("\nSelect option: ").strip()

        if option == "1":
            return existing

        if option == "2":
            return incoming

        print("\n[ERROR] Invalid option.")


def _append_purchase(sheet, record: PurchaseRecord) -> bool:
    row = _find_matching_row(sheet, record)
    created = row is None

    if created:
        row = sheet.max_row + 1
        sheet.cell(row=row, column=1, value=record.six_digit_sku)
        sheet.cell(row=row, column=2, value=record.product)
        sheet.cell(row=row, column=3, value=record.tax_code)
        sheet.cell(row=row, column=4, value=record.store_number)
    else:
        existing_tax = str(
            sheet.cell(row=row, column=3).value or NA
        )
        selected_tax = _resolve_tax_code_conflict(
            existing=existing_tax,
            incoming=record.tax_code,
            product=record.product,
        )
        sheet.cell(row=row, column=3, value=selected_tax)

    date_column, price_column = _next_history_pair(sheet, row)
    date_cell = sheet.cell(row=row, column=date_column)
    price_cell = sheet.cell(row=row, column=price_column)

    date_cell.value = _excel_date(record.date)
    date_cell.number_format = "mm/dd/yyyy"

    price_cell.value = _excel_price(record.price)

    if record.price != NA:
        price_cell.number_format = "$0.00"

    return created


def _source_already_imported(workbook, source_name: str) -> bool:
    sheet = workbook[IMPORT_SHEET]
    normalized_source = _normalized(source_name)

    for row in range(2, sheet.max_row + 1):
        existing = sheet.cell(row=row, column=1).value

        if _normalized(existing) == normalized_source:
            return True

    return False


def source_already_imported(source_path: Path) -> bool:
    if not WORKBOOK_PATH.exists():
        return False

    workbook = _load_or_create_workbook()
    return _source_already_imported(workbook, source_path.name)


def _record_import(workbook, session: ReceiptSession) -> None:
    sheet = workbook[IMPORT_SHEET]
    row = sheet.max_row + 1

    sheet.cell(row=row, column=1, value=session.source_path.name)
    sheet.cell(row=row, column=2, value=session.store_number)
    sheet.cell(
        row=row,
        column=3,
        value=_excel_date(session.receipt_date),
    )
    sheet.cell(row=row, column=3).number_format = "mm/dd/yyyy"
    sheet.cell(
        row=row,
        column=4,
        value=datetime.now(),
    )
    sheet.cell(row=row, column=4).number_format = "mm/dd/yyyy hh:mm"


def _atomic_save(workbook) -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        suffix=".xlsx",
        dir=DATABASE_DIR,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        workbook.save(temporary_path)
        os.replace(temporary_path, WORKBOOK_PATH)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def commit_receipt(session: ReceiptSession) -> dict:
    workbook = _load_or_create_workbook()
    sheet = workbook[PURCHASE_SHEET]

    new_rows = 0
    updated_rows = 0

    for record in session.accepted_purchases:
        created = _append_purchase(sheet, record)

        if created:
            new_rows += 1
        else:
            updated_rows += 1

    _record_import(workbook, session)
    _format_workbook(workbook)
    _atomic_save(workbook)

    return {
        "workbook_path": WORKBOOK_PATH.resolve(),
        "purchases_added": len(session.accepted_purchases),
        "existing_histories_updated": updated_rows,
        "new_product_rows": new_rows,
    }
