from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

from capabilities.OllamaReceiptAcquisitionPipeline.ollama_client import (
    OllamaReceiptAcquisitionError,
    run_local_json_prompt,
)
from utils.constants import DATA_DIR
from utils.DataBaseBuilder.excel.category_manager import (
    find_populated_rows_with_missing_common_name,
)
from utils.DataBaseBuilder.excel.purchase_history import (
    CATEGORY_COLUMN,
    COMMON_NAME_COLUMN,
    FIXED_HEADERS,
    PRODUCT_COLUMN,
    PURCHASE_SHEET,
    STORE_COLUMN,
    WORKBOOK_PATH,
    _ensure_purchase_schema,
)
from utils.DataBaseBuilder.purchase_record import NA

PROMPT_PATH = DATA_DIR / "prompts" / "dev_prompts" / "shopgraph_ollama_common_name_completion_prompt.txt"
BATCH_SIZE = 25


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _is_na(value) -> bool:
    return _text(value).casefold() == _text(NA).casefold()


def _headers_are_valid(sheet) -> bool:
    actual = [_text(sheet.cell(1, c).value) for c in range(1, len(FIXED_HEADERS) + 1)]
    return actual == FIXED_HEADERS


def _load_workbook_for_completion():
    path = Path(WORKBOOK_PATH).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Purchase History workbook was not found:\n{path}")
    workbook = load_workbook(path)
    if PURCHASE_SHEET not in workbook.sheetnames:
        workbook.close()
        raise ValueError(f'Workbook is missing required sheet: "{PURCHASE_SHEET}".')
    sheet = workbook[PURCHASE_SHEET]
    _ensure_purchase_schema(sheet)
    if not _headers_are_valid(sheet):
        workbook.close()
        raise ValueError("Purchase History has an unrecognized column layout.")
    return path, workbook, sheet


def _historical_product_mappings(sheet) -> dict[str, set[str]]:
    mappings: dict[str, set[str]] = defaultdict(set)
    for row in range(2, sheet.max_row + 1):
        product = _text(sheet.cell(row, PRODUCT_COLUMN).value)
        common_name = _text(sheet.cell(row, COMMON_NAME_COLUMN).value)
        if product and common_name and not _is_na(common_name):
            mappings[product.casefold()].add(common_name)
    return mappings


def _row_payload(sheet, row: int) -> dict:
    return {
        "excel_row": row,
        "product": _text(sheet.cell(row, PRODUCT_COLUMN).value),
        "store": _text(sheet.cell(row, STORE_COLUMN).value),
        "sub_category": _text(sheet.cell(row, CATEGORY_COLUMN).value),
    }


def _reference_examples(sheet, limit: int = 120) -> list[dict]:
    examples = []
    seen = set()
    for row in range(2, sheet.max_row + 1):
        product = _text(sheet.cell(row, PRODUCT_COLUMN).value)
        common_name = _text(sheet.cell(row, COMMON_NAME_COLUMN).value)
        if not product or not common_name or _is_na(common_name):
            continue
        key = (product.casefold(), common_name.casefold())
        if key in seen:
            continue
        seen.add(key)
        examples.append({"product": product, "common_name": common_name})
        if len(examples) >= limit:
            break
    return examples


def _build_prompt(rows: list[dict], examples: list[dict]) -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Ollama completion prompt was not found:\n{PROMPT_PATH.resolve()}")
    base = PROMPT_PATH.read_text(encoding="utf-8").strip()
    payload = {"rows_to_complete": rows, "reference_examples": examples}
    return base + "\n\nINPUT JSON:\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def _validate_response(response: dict, requested: list[dict]) -> dict[int, str]:
    rows = response.get("rows")
    if not isinstance(rows, list):
        raise ValueError('Ollama response must contain a "rows" list.')
    expected = {item["excel_row"]: item["product"] for item in requested}
    results: dict[int, str] = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Every Ollama rows entry must be an object.")
        row = item.get("excel_row")
        common_name = item.get("common_name")
        if not isinstance(row, int) or row not in expected:
            raise ValueError(f"Ollama returned an unexpected Excel row: {row!r}")
        if row in results:
            raise ValueError(f"Ollama returned duplicate Excel row {row}.")
        if not isinstance(common_name, str) or not common_name.strip():
            raise ValueError(f"Ollama returned an invalid Common Name for row {row}.")
        results[row] = common_name.strip()
    missing = sorted(set(expected) - set(results))
    if missing:
        raise ValueError(f"Ollama omitted requested Excel rows: {missing}")
    return results


def _atomic_save(workbook, workbook_path: Path) -> None:
    fd, temp_name = tempfile.mkstemp(prefix="shopgraph_common_name_", suffix=".xlsx", dir=str(workbook_path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        workbook.save(temp_path)
        verify = load_workbook(temp_path, read_only=True)
        verify.close()
        os.replace(temp_path, workbook_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def run_ollama_purchase_history_completion() -> dict:
    print("\n=== Ollama Purchase History Blank/NA Completion ===\n")
    print("[1/4] Scan Purchase History")
    workbook_path, workbook, sheet = _load_workbook_for_completion()
    try:
        invalid_rows = find_populated_rows_with_missing_common_name(sheet)
        if not invalid_rows:
            print("\n[OK] No populated Purchase History rows contain blank/NA Common Name.")
            print("\nNo changes were required.")
            return {"updated_rows": 0, "unresolved_rows": [], "remaining_rows": []}

        print(f"\nFound {len(invalid_rows)} populated rows with blank/NA Common Name:")
        print(", ".join(str(row) for row in invalid_rows))

        historical = _historical_product_mappings(sheet)
        proposed: dict[int, str] = {}
        ai_rows = []
        for row in invalid_rows:
            payload = _row_payload(sheet, row)
            matches = historical.get(payload["product"].casefold(), set())
            if len(matches) == 1:
                proposed[row] = next(iter(matches))
            else:
                ai_rows.append(payload)

        print("\n[2/4] Analyze Missing Common Names with Ollama")
        if proposed:
            print(f"\n[INFO] Reused {len(proposed)} unambiguous existing Product -> Common Name mappings.")

        examples = _reference_examples(sheet)
        for start in range(0, len(ai_rows), BATCH_SIZE):
            batch = ai_rows[start:start + BATCH_SIZE]
            response, _metadata = run_local_json_prompt(_build_prompt(batch, examples))
            proposed.update(_validate_response(response, batch))

        for row in invalid_rows:
            value = proposed.get(row, NA)
            print(f"Row {row} -> {value}")

        print("\n[3/4] Validate Ollama Results")
        unresolved = [row for row in invalid_rows if _is_na(proposed.get(row, NA))]
        writable = {row: value for row, value in proposed.items() if not _is_na(value)}

        # Re-check identity and target state immediately before writing.
        original_products = {row: _text(sheet.cell(row, PRODUCT_COLUMN).value) for row in invalid_rows}
        for row in writable:
            if row not in invalid_rows:
                raise ValueError(f"Refusing unexpected row update: {row}")
            current_common = _text(sheet.cell(row, COMMON_NAME_COLUMN).value)
            if current_common and not _is_na(current_common):
                raise ValueError(f"Row {row} no longer has a blank/NA Common Name.")
            if _text(sheet.cell(row, PRODUCT_COLUMN).value) != original_products[row]:
                raise ValueError(f"Product identity changed before write for row {row}.")

        print(f"\n[OK] {len(proposed)}/{len(invalid_rows)} results validated.")
        print("\n[4/4] Update Purchase History")

        if writable:
            for row, common_name in writable.items():
                sheet.cell(row, COMMON_NAME_COLUMN, value=common_name)
            _atomic_save(workbook, workbook_path)
            print("\n[OK] Purchase History updated.")
            print(f"\nRows updated: {len(writable)}")
            print(f"Workbook:\n{workbook_path}")
        else:
            print("\n[INFO] Ollama did not produce any writable Common Names.")
    finally:
        workbook.close()

    verify_workbook = load_workbook(workbook_path, read_only=False)
    try:
        verify_sheet = verify_workbook[PURCHASE_SHEET]
        remaining = find_populated_rows_with_missing_common_name(verify_sheet)
    finally:
        verify_workbook.close()

    if remaining:
        print("\n[WARNING] Purchase History still contains populated rows with blank/NA Common Name.")
        print("Rows: " + ", ".join(str(row) for row in remaining))
        print("\nCategory Manager Completion will continue to reject Purchase History until these rows are resolved.")
    else:
        print("\n[OK] Purchase History Common Name validation passed.")
        print("Populated rows with blank/NA Common Name: 0")

    return {"updated_rows": len(writable), "unresolved_rows": unresolved, "remaining_rows": remaining}


def main() -> None:
    try:
        run_ollama_purchase_history_completion()
    except (FileNotFoundError, PermissionError, OSError, ValueError, OllamaReceiptAcquisitionError) as error:
        print(f"\n[ERROR] Ollama Purchase History completion failed:\n{error}")


if __name__ == "__main__":
    main()

