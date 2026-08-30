from __future__ import annotations

import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from utils.DataBaseBuilder.excel.purchase_history import (
    CATEGORY_COLUMN,
    COMMON_NAME_COLUMN,
    FIXED_HEADERS,
    PURCHASE_SHEET,
    WORKBOOK_PATH,
)
from utils.DataBaseBuilder.purchase_record import NA


CATEGORY_MANAGER_SHEET = "Category Manager"
CATEGORY_HEADER = "Category"
PRODUCT_HEADER_PREFIX = "Product"

HEADER_FILL = "1F4E78"
HEADER_FONT = "FFFFFF"
CATEGORY_FILLS = (
    "D9EAF7",
    "E2F0D9",
    "FFF2CC",
    "FCE4D6",
    "E4DFEC",
    "DDEBF7",
)
BORDER_COLOR = "B7C9D6"


# ---------------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------------

def _text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _normalized(value) -> str:
    return _text(value).casefold()


def _required_purchase_headers_are_valid(sheet) -> bool:
    actual = [
        _text(
            sheet.cell(
                row=1,
                column=column,
            ).value
        )
        for column in range(
            1,
            len(FIXED_HEADERS) + 1,
        )
    ]

    return actual == FIXED_HEADERS


def _load_existing_workbook(
    workbook_path: Path = WORKBOOK_PATH,
):
    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook was not found:"
            f"\n{workbook_path.resolve()}"
        )

    workbook = load_workbook(
        workbook_path
    )

    if PURCHASE_SHEET not in workbook.sheetnames:
        raise ValueError(
            f'Workbook is missing required sheet: "{PURCHASE_SHEET}".'
        )

    purchase_sheet = workbook[
        PURCHASE_SHEET
    ]

    if not _required_purchase_headers_are_valid(
        purchase_sheet
    ):
        raise ValueError(
            "Purchase History has an unrecognized column layout. "
            "Category Manager requires the current ShopGraph Purchase "
            "History schema."
        )

    return workbook


# ---------------------------------------------------------------------------
# PURCHASE HISTORY READING
# ---------------------------------------------------------------------------

def _read_purchase_history(
    purchase_sheet,
) -> dict:
    """
    Read Common Name -> Category from Purchase History.

    Common Name is the Category Manager identity. Multiple Purchase History
    rows may share one Common Name. They must agree on Category when Create /
    Refresh is rebuilding the manager from Purchase History.
    """
    categories_by_common_name: dict[str, set[str]] = defaultdict(set)
    rows_by_common_name: dict[str, list[int]] = defaultdict(list)
    invalid_common_name_rows = []

    for row in range(
        2,
        purchase_sheet.max_row + 1,
    ):
        common_name = _text(
            purchase_sheet.cell(
                row=row,
                column=COMMON_NAME_COLUMN,
            ).value
        )

        category = _text(
            purchase_sheet.cell(
                row=row,
                column=CATEGORY_COLUMN,
            ).value
        )

        # Formula-only / structurally empty trailing rows are ignored.
        product_value = _text(
            purchase_sheet.cell(
                row=row,
                column=5,
            ).value
        )

        if not common_name:
            if product_value:
                invalid_common_name_rows.append(row)
            continue

        if _normalized(common_name) == _normalized(NA):
            invalid_common_name_rows.append(row)
            continue

        if not category:
            category = NA

        categories_by_common_name[
            common_name
        ].add(
            category
        )
        rows_by_common_name[
            common_name
        ].append(
            row
        )

    conflicts = {}

    for common_name, categories in (
        categories_by_common_name.items()
    ):
        if len(categories) > 1:
            conflicts[common_name] = {
                "categories": sorted(
                    categories,
                    key=str.casefold,
                ),
                "rows": rows_by_common_name[
                    common_name
                ],
            }

    mapping = {
        common_name: next(
            iter(categories)
        )
        for common_name, categories
        in categories_by_common_name.items()
        if len(categories) == 1
    }

    return {
        "mapping": mapping,
        "rows_by_common_name": dict(
            rows_by_common_name
        ),
        "invalid_common_name_rows": (
            invalid_common_name_rows
        ),
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------
# CATEGORY MANAGER BUILD / FORMAT
# ---------------------------------------------------------------------------

def _category_groups(
    mapping: dict[str, str],
) -> list[tuple[str, list[str]]]:
    groups: dict[str, list[str]] = defaultdict(list)

    for common_name, category in mapping.items():
        groups[category].append(
            common_name
        )

    return [
        (
            category,
            sorted(
                common_names,
                key=str.casefold,
            ),
        )
        for category, common_names
        in sorted(
            groups.items(),
            key=lambda item: item[0].casefold(),
        )
    ]


def _delete_manager_if_present(
    workbook,
) -> None:
    if CATEGORY_MANAGER_SHEET in workbook.sheetnames:
        workbook.remove(
            workbook[
                CATEGORY_MANAGER_SHEET
            ]
        )


def _create_manager_sheet(
    workbook,
    mapping: dict[str, str],
):
    _delete_manager_if_present(
        workbook
    )

    purchase_index = workbook.sheetnames.index(
        PURCHASE_SHEET
    )

    sheet = workbook.create_sheet(
        CATEGORY_MANAGER_SHEET,
        purchase_index + 1,
    )

    groups = _category_groups(
        mapping
    )

    max_products = max(
        (
            len(common_names)
            for _, common_names in groups
        ),
        default=1,
    )

    sheet.cell(
        row=1,
        column=1,
        value=CATEGORY_HEADER,
    )

    for product_number in range(
        1,
        max_products + 1,
    ):
        sheet.cell(
            row=1,
            column=product_number + 1,
            value=(
                f"{PRODUCT_HEADER_PREFIX} "
                f"{product_number}"
            ),
        )

    for row, (
        category,
        common_names,
    ) in enumerate(
        groups,
        start=2,
    ):
        sheet.cell(
            row=row,
            column=1,
            value=category,
        )

        for column, common_name in enumerate(
            common_names,
            start=2,
        ):
            sheet.cell(
                row=row,
                column=column,
                value=common_name,
            )

    _format_category_manager(
        sheet
    )

    return sheet


def _format_category_manager(
    sheet,
) -> None:
    sheet.freeze_panes = "B2"
    sheet.sheet_view.showGridLines = False

    thin = Side(
        style="thin",
        color=BORDER_COLOR,
    )
    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )

    for cell in sheet[1]:
        cell.font = Font(
            bold=True,
            color=HEADER_FONT,
        )
        cell.fill = PatternFill(
            "solid",
            fgColor=HEADER_FILL,
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        cell.border = border

    for row in range(
        2,
        sheet.max_row + 1,
    ):
        fill = PatternFill(
            "solid",
            fgColor=CATEGORY_FILLS[
                (row - 2) % len(
                    CATEGORY_FILLS
                )
            ],
        )

        for column in range(
            1,
            sheet.max_column + 1,
        ):
            cell = sheet.cell(
                row=row,
                column=column,
            )
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

        sheet.cell(
            row=row,
            column=1,
        ).font = Font(
            bold=True
        )

    sheet.column_dimensions[
        "A"
    ].width = 28

    for column in range(
        2,
        sheet.max_column + 1,
    ):
        sheet.column_dimensions[
            get_column_letter(column)
        ].width = 34

    sheet.row_dimensions[1].height = 24

    for row in range(
        2,
        sheet.max_row + 1,
    ):
        sheet.row_dimensions[
            row
        ].height = 36

    sheet.auto_filter.ref = (
        sheet.dimensions
    )


# ---------------------------------------------------------------------------
# CATEGORY MANAGER PARSING / VALIDATION
# ---------------------------------------------------------------------------

def _manager_structure_errors(
    sheet,
) -> list[str]:
    errors = []

    if _text(
        sheet.cell(
            row=1,
            column=1,
        ).value
    ) != CATEGORY_HEADER:
        errors.append(
            'Cell A1 must contain "Category".'
        )

    if sheet.max_column < 2:
        errors.append(
            "Category Manager must contain at least one product column."
        )

    else:
        first_product_header = _text(
            sheet.cell(
                row=1,
                column=2,
            ).value
        )

        if not first_product_header.startswith(
            PRODUCT_HEADER_PREFIX
        ):
            errors.append(
                'Cell B1 must be a Product heading such as "Product 1".'
            )

    return errors


def _parse_manager(
    sheet,
) -> dict:
    assignments = []
    blank_category_products = []
    category_rows: dict[str, list[int]] = defaultdict(list)

    for row in range(
        2,
        sheet.max_row + 1,
    ):
        category = _text(
            sheet.cell(
                row=row,
                column=1,
            ).value
        )

        products = []

        for column in range(
            2,
            sheet.max_column + 1,
        ):
            common_name = _text(
                sheet.cell(
                    row=row,
                    column=column,
                ).value
            )

            if not common_name:
                continue

            products.append(
                (
                    common_name,
                    column,
                )
            )

        # Empty category rows are intentionally ignored.
        if not products:
            continue

        if not category:
            for common_name, column in products:
                blank_category_products.append(
                    {
                        "common_name": common_name,
                        "row": row,
                        "column": column,
                    }
                )
            continue

        category_rows[
            _normalized(category)
        ].append(
            row
        )

        for common_name, column in products:
            assignments.append(
                {
                    "common_name": common_name,
                    "category": category,
                    "row": row,
                    "column": column,
                }
            )

    return {
        "assignments": assignments,
        "blank_category_products": (
            blank_category_products
        ),
        "category_rows": dict(
            category_rows
        ),
    }


def _validate_manager(
    purchase_data: dict,
    manager_data: dict,
    structure_errors: list[str],
) -> dict:
    errors = {
        "structure": list(
            structure_errors
        ),
        "invalid_purchase_common_names": [],
        "purchase_conflicts": {},
        "missing": [],
        "unknown": [],
        "duplicates": {},
        "blank_category_products": [],
        "duplicate_categories": {},
    }

    errors[
        "invalid_purchase_common_names"
    ] = purchase_data[
        "invalid_common_name_rows"
    ]

    errors[
        "purchase_conflicts"
    ] = purchase_data[
        "conflicts"
    ]

    assignments = manager_data[
        "assignments"
    ]

    occurrences: dict[str, list[dict]] = defaultdict(list)

    for assignment in assignments:
        occurrences[
            assignment["common_name"]
        ].append(
            assignment
        )

    expected = set(
        purchase_data[
            "mapping"
        ]
    )
    found = set(
        occurrences
    )

    errors["missing"] = sorted(
        expected - found,
        key=str.casefold,
    )
    errors["unknown"] = sorted(
        found - expected,
        key=str.casefold,
    )

    errors["duplicates"] = {
        common_name: locations
        for common_name, locations
        in occurrences.items()
        if len(locations) > 1
    }

    errors[
        "blank_category_products"
    ] = manager_data[
        "blank_category_products"
    ]

    duplicate_categories = {}

    for normalized_category, rows in (
        manager_data[
            "category_rows"
        ].items()
    ):
        if len(rows) <= 1:
            continue

        display_name = ""

        for assignment in assignments:
            if (
                _normalized(
                    assignment["category"]
                )
                == normalized_category
            ):
                display_name = assignment[
                    "category"
                ]
                break

        duplicate_categories[
            display_name or normalized_category
        ] = rows

    errors[
        "duplicate_categories"
    ] = duplicate_categories

    has_errors = any(
        bool(value)
        for value in errors.values()
    )

    mapping = {}

    if not has_errors:
        mapping = {
            assignment["common_name"]: (
                assignment["category"]
            )
            for assignment in assignments
        }

    return {
        "valid": not has_errors,
        "errors": errors,
        "mapping": mapping,
    }


def _format_validation_report(
    validation: dict,
) -> str:
    errors = validation[
        "errors"
    ]
    lines = [
        "[ERROR] Category Manager validation failed.",
    ]

    if errors["structure"]:
        lines.append(
            "\nStructure errors:"
        )
        for message in errors[
            "structure"
        ]:
            lines.append(
                f"- {message}"
            )

    if errors[
        "invalid_purchase_common_names"
    ]:
        lines.append(
            "\nPurchase History rows with blank/NA Common Name:"
        )
        for row in errors[
            "invalid_purchase_common_names"
        ]:
            lines.append(
                f"- Row {row}"
            )

    if errors[
        "purchase_conflicts"
    ]:
        lines.append(
            "\nConflicting Purchase History categories for one Common Name:"
        )
        for common_name, info in errors[
            "purchase_conflicts"
        ].items():
            lines.append(
                f'- "{common_name}"'
            )
            lines.append(
                "  Categories: "
                + ", ".join(
                    info["categories"]
                )
            )
            lines.append(
                "  Purchase History rows: "
                + ", ".join(
                    str(row)
                    for row in info[
                        "rows"
                    ]
                )
            )

    if errors["missing"]:
        lines.append(
            "\nMissing Common Names:"
        )
        for index, common_name in enumerate(
            errors["missing"],
            start=1,
        ):
            lines.append(
                f"{index}. {common_name}"
            )

    if errors["unknown"]:
        lines.append(
            "\nUnknown Common Names:"
        )
        for index, common_name in enumerate(
            errors["unknown"],
            start=1,
        ):
            lines.append(
                f"{index}. {common_name}"
            )

    if errors["duplicates"]:
        lines.append(
            "\nDuplicate assignments:"
        )
        for common_name, locations in errors[
            "duplicates"
        ].items():
            lines.append(
                f'\n"{common_name}"'
            )
            for location in locations:
                lines.append(
                    "    Row "
                    f"{location['row']}: "
                    f"{location['category']}"
                )

    if errors[
        "blank_category_products"
    ]:
        lines.append(
            "\nProducts assigned to a blank category:"
        )
        for location in errors[
            "blank_category_products"
        ]:
            lines.append(
                f"- {location['common_name']} "
                f"(row {location['row']})"
            )

    if errors[
        "duplicate_categories"
    ]:
        lines.append(
            "\nDuplicate category rows:"
        )
        for category, rows in errors[
            "duplicate_categories"
        ].items():
            lines.append(
                f'- "{category}" appears on rows: '
                + ", ".join(
                    str(row)
                    for row in rows
                )
            )

    lines.extend(
        [
            "",
            "Purchase History was NOT modified.",
        ]
    )

    return "\n".join(
        lines
    )


# ---------------------------------------------------------------------------
# VERIFIED ATOMIC SAVE
# ---------------------------------------------------------------------------

def _verified_atomic_save(
    workbook,
    workbook_path: Path = WORKBOOK_PATH,
) -> None:
    workbook_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        file_descriptor,
        temporary_name,
    ) = tempfile.mkstemp(
        suffix=".xlsx",
        dir=workbook_path.parent,
    )

    os.close(
        file_descriptor
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        workbook.save(
            temporary_path
        )

        verification = load_workbook(
            temporary_path,
            read_only=True,
            data_only=False,
        )

        try:
            required = {
                PURCHASE_SHEET,
                CATEGORY_MANAGER_SHEET,
            }

            missing = required - set(
                verification.sheetnames
            )

            if missing:
                raise ValueError(
                    "Temporary workbook verification failed. Missing sheet(s): "
                    + ", ".join(
                        sorted(missing)
                    )
                )

        finally:
            verification.close()

        os.replace(
            temporary_path,
            workbook_path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


# ---------------------------------------------------------------------------
# CREATE / REFRESH
# ---------------------------------------------------------------------------

def create_or_refresh_category_manager(
    workbook_path: Path = WORKBOOK_PATH,
) -> dict:
    workbook = _load_existing_workbook(
        workbook_path
    )

    try:
        purchase_sheet = workbook[
            PURCHASE_SHEET
        ]
        purchase_data = _read_purchase_history(
            purchase_sheet
        )

        if purchase_data[
            "invalid_common_name_rows"
        ]:
            rows = ", ".join(
                str(row)
                for row in purchase_data[
                    "invalid_common_name_rows"
                ]
            )
            raise ValueError(
                "Category Manager cannot be created because Purchase History "
                "contains populated rows with blank/NA Common Name. "
                f"Rows: {rows}"
            )

        if purchase_data[
            "conflicts"
        ]:
            details = []

            for common_name, info in purchase_data[
                "conflicts"
            ].items():
                details.append(
                    f"{common_name}: "
                    + ", ".join(
                        info["categories"]
                    )
                )

            raise ValueError(
                "Category Manager cannot be created because the same Common "
                "Name has conflicting Categories in Purchase History:\n- "
                + "\n- ".join(
                    details
                )
            )

        _create_manager_sheet(
            workbook,
            purchase_data[
                "mapping"
            ],
        )

        _verified_atomic_save(
            workbook,
            workbook_path,
        )

        return {
            "workbook_path": workbook_path.resolve(),
            "category_count": len(
                set(
                    purchase_data[
                        "mapping"
                    ].values()
                )
            ),
            "product_count": len(
                purchase_data[
                    "mapping"
                ]
            ),
        }

    finally:
        workbook.close()


def run_create_or_refresh_category_manager() -> None:
    print(
        "\n=== Create / Refresh Category Manager ===\n"
    )
    print(
        "[INFO] Category Manager will be rebuilt from the current "
        "Purchase History. Unapplied manual Category Manager edits "
        "may be discarded."
    )

    try:
        result = create_or_refresh_category_manager()

    except (
        OSError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return

    print(
        "\n[OK] Category Manager created / refreshed."
    )
    print(
        f"Categories: {result['category_count']}"
    )
    print(
        f"Common Names: {result['product_count']}"
    )
    print(
        f"Workbook:\n{result['workbook_path']}"
    )


# ---------------------------------------------------------------------------
# APPLY
# ---------------------------------------------------------------------------

def apply_category_manager(
    workbook_path: Path = WORKBOOK_PATH,
) -> dict:
    workbook = _load_existing_workbook(
        workbook_path
    )

    try:
        if CATEGORY_MANAGER_SHEET not in workbook.sheetnames:
            return {
                "success": False,
                "report": (
                    "[ERROR] Category Manager validation failed.\n\n"
                    'Worksheet "Category Manager" was not found.\n\n'
                    "Purchase History was NOT modified."
                ),
            }

        purchase_sheet = workbook[
            PURCHASE_SHEET
        ]
        manager_sheet = workbook[
            CATEGORY_MANAGER_SHEET
        ]

        purchase_data = _read_purchase_history(
            purchase_sheet
        )
        structure_errors = (
            _manager_structure_errors(
                manager_sheet
            )
        )
        manager_data = _parse_manager(
            manager_sheet
        )
        validation = _validate_manager(
            purchase_data,
            manager_data,
            structure_errors,
        )

        if not validation[
            "valid"
        ]:
            return {
                "success": False,
                "report": _format_validation_report(
                    validation
                ),
            }

        mapping = validation[
            "mapping"
        ]
        changed_rows = 0

        # Validation is complete. Only Category cells may now change.
        for row in range(
            2,
            purchase_sheet.max_row + 1,
        ):
            common_name = _text(
                purchase_sheet.cell(
                    row=row,
                    column=COMMON_NAME_COLUMN,
                ).value
            )

            if common_name not in mapping:
                continue

            category_cell = purchase_sheet.cell(
                row=row,
                column=CATEGORY_COLUMN,
            )
            selected_category = mapping[
                common_name
            ]

            if _text(
                category_cell.value
            ) != selected_category:
                category_cell.value = (
                    selected_category
                )
                changed_rows += 1

        # Compact/reformat Category Manager only after successful validation.
        _create_manager_sheet(
            workbook,
            mapping,
        )

        _verified_atomic_save(
            workbook,
            workbook_path,
        )

        return {
            "success": True,
            "workbook_path": workbook_path.resolve(),
            "changed_rows": changed_rows,
            "category_count": len(
                set(
                    mapping.values()
                )
            ),
            "product_count": len(
                mapping
            ),
        }

    finally:
        workbook.close()


def run_apply_category_manager() -> None:
    print(
        "\n=== Apply Category Manager to Purchase History ===\n"
    )

    try:
        result = apply_category_manager()

    except (
        OSError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        print(
            "\nPurchase History was NOT modified."
        )
        return

    if not result[
        "success"
    ]:
        print(
            "\n" + result[
                "report"
            ]
        )
        return

    print(
        "\n[OK] Purchase History categories updated successfully."
    )
    print(
        "Category Manager cleaned and synchronized."
    )
    print(
        f"Purchase History rows changed: {result['changed_rows']}"
    )
    print(
        f"Categories: {result['category_count']}"
    )
    print(
        f"Common Names: {result['product_count']}"
    )
    print(
        "\nRun:\nGenerate / Refresh Purchase Analytics\n"
        "to rebuild Analytics using the updated categories."
    )


def display_category_manager_menu() -> None:
    print(
        "\n=== ShopGraph Category Manager ===\n"
    )
    print(
        "1. Create / Refresh Category Manager"
    )
    print(
        "2. Apply Category Manager to Purchase History"
    )
    print(
        "0. Return to Data Base Builder"
    )


def run_category_manager_menu() -> None:
    while True:
        display_category_manager_menu()
        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_create_or_refresh_category_manager()

        elif option == "2":
            run_apply_category_manager()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )
