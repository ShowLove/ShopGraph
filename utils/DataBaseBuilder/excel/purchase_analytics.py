from __future__ import annotations

import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.chart import BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel

from utils.DataBaseBuilder.excel.purchase_history import (
    PURCHASE_SHEET,
    WORKBOOK_PATH,
)


ANALYTICS_SHEET = "Analytics"
ANALYTICS_DATA_SHEET = "_AnalyticsData"
NA = "NA"

DATE_HEADER_PATTERN = re.compile(r"^Date\s+(\d+)$", re.IGNORECASE)
PRICE_HEADER_PATTERN = re.compile(r"^Price\s+(\d+)$", re.IGNORECASE)

CURRENCY_FORMAT = '$#,##0.00'
DATE_FORMAT = 'mm/dd/yyyy'
MONTH_FORMAT = 'mmm yyyy'


class PurchaseAnalyticsError(ValueError):
    """Raised when Purchase Analytics cannot be generated safely."""


def _normalized_text(value) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    if not text or text.upper() == NA:
        return ""

    return text


def _parse_date(value) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value <= 0:
            return None

        try:
            converted = from_excel(value)
        except (TypeError, ValueError, OverflowError):
            return None

        if isinstance(converted, datetime):
            return converted.date()

        if isinstance(converted, date):
            return converted

        return None

    text = str(value).strip()

    if not text or text.upper() == NA or text.startswith("="):
        return None

    formats = (
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m-%d-%Y",
        "%m-%d-%y",
        "%Y-%m-%d",
    )

    for format_string in formats:
        try:
            return datetime.strptime(
                text,
                format_string,
            ).date()
        except ValueError:
            continue

    return None


def _parse_price(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float, Decimal)):
        try:
            amount = float(value)
        except (TypeError, ValueError, OverflowError):
            return None

        return amount if amount >= 0 else None

    text = str(value).strip()

    if not text or text.upper() == NA or text.startswith("="):
        return None

    text = text.replace("$", "").replace(",", "").strip()

    try:
        amount = float(text)
    except ValueError:
        return None

    return amount if amount >= 0 else None


def _header_map(sheet) -> dict[str, int]:
    headers = {}

    for cell in sheet[1]:
        value = _normalized_text(cell.value)

        if value:
            headers[value] = cell.column

    return headers


def _history_pairs(sheet) -> list[tuple[int, int, int]]:
    dates = {}
    prices = {}

    for cell in sheet[1]:
        header = _normalized_text(cell.value)

        date_match = DATE_HEADER_PATTERN.fullmatch(header)
        if date_match:
            dates[int(date_match.group(1))] = cell.column
            continue

        price_match = PRICE_HEADER_PATTERN.fullmatch(header)
        if price_match:
            prices[int(price_match.group(1))] = cell.column

    pair_numbers = sorted(set(dates) & set(prices))

    return [
        (number, dates[number], prices[number])
        for number in pair_numbers
    ]


def _flatten_purchase_history(sheet) -> tuple[list[dict], dict]:
    headers = _header_map(sheet)
    pairs = _history_pairs(sheet)

    if not pairs:
        return [], {
            "skipped_pairs": 0,
            "history_pairs_found": 0,
        }

    fixed_columns = {
        "store": headers.get("Store"),
        "six_digit_sku": headers.get("Six-Digit SKU"),
        "product": headers.get("Product"),
        "store_number": headers.get("Store Number"),
        "common_name": headers.get("Common Name"),
        "category": headers.get("Category"),
    }

    observations = []
    skipped_pairs = 0

    for row in range(2, sheet.max_row + 1):
        def value_for(name: str):
            column = fixed_columns.get(name)
            return sheet.cell(row=row, column=column).value if column else None

        store = _normalized_text(value_for("store")) or "Unknown"
        store_number = _normalized_text(value_for("store_number")) or NA
        product = _normalized_text(value_for("product")) or "Unknown Product"
        common_name = _normalized_text(value_for("common_name")) or product
        category = _normalized_text(value_for("category")) or "Uncategorized"
        sku = _normalized_text(value_for("six_digit_sku")) or NA

        for pair_number, date_column, price_column in pairs:
            raw_date = sheet.cell(
                row=row,
                column=date_column,
            ).value
            raw_price = sheet.cell(
                row=row,
                column=price_column,
            ).value

            has_any_value = (
                _normalized_text(raw_date)
                or _normalized_text(raw_price)
            )

            if not has_any_value:
                continue

            purchase_date = _parse_date(raw_date)
            price = _parse_price(raw_price)

            if purchase_date is None or price is None:
                skipped_pairs += 1
                continue

            observations.append(
                {
                    "date": purchase_date,
                    "price": price,
                    "store": store,
                    "store_number": store_number,
                    "product": product,
                    "common_name": common_name,
                    "category": category,
                    "six_digit_sku": sku,
                    "history_number": pair_number,
                    "source_row": row,
                }
            )

    return observations, {
        "skipped_pairs": skipped_pairs,
        "history_pairs_found": len(pairs),
    }


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)

    return date(value.year, value.month + 1, 1)


def _month_range(start: date, end: date) -> list[date]:
    months = []
    current = _month_start(start)
    final = _month_start(end)

    while current <= final:
        months.append(current)
        current = _next_month(current)

    return months


def _collapse_top(
    values: dict[str, float | int],
    *,
    maximum_rows: int,
    top_when_collapsing: int,
) -> list[tuple[str, float | int]]:
    ranked = sorted(
        values.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )

    if len(ranked) <= maximum_rows:
        return ranked

    kept = ranked[:top_when_collapsing]
    other_value = sum(
        item[1]
        for item in ranked[top_when_collapsing:]
    )

    if other_value:
        kept.append(("Other", other_value))

    return kept


def _aggregate(observations: list[dict]) -> dict:
    total_spending = sum(item["price"] for item in observations)
    earliest = min(item["date"] for item in observations)
    latest = max(item["date"] for item in observations)

    monthly_spending = defaultdict(float)
    category_spending = defaultdict(float)
    store_spending = defaultdict(float)
    product_spending = defaultdict(float)
    category_frequency = Counter()
    monthly_store = defaultdict(lambda: defaultdict(float))

    for item in observations:
        month = _month_start(item["date"])
        price = item["price"]
        category = item["category"]
        store = item["store"]
        product_identity = item["common_name"] or item["product"] or "Unknown Product"

        monthly_spending[month] += price
        category_spending[category] += price
        store_spending[store] += price
        product_spending[product_identity] += price
        category_frequency[category] += 1
        monthly_store[month][store] += price

    months = _month_range(earliest, latest)

    monthly_rows = [
        (month, monthly_spending.get(month, 0.0))
        for month in months
    ]

    category_rows = _collapse_top(
        category_spending,
        maximum_rows=15,
        top_when_collapsing=14,
    )

    store_rows = sorted(
        store_spending.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )

    share_rows = _collapse_top(
        category_spending,
        maximum_rows=8,
        top_when_collapsing=7,
    )

    product_rows = sorted(
        product_spending.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )[:10]

    frequency_rows = _collapse_top(
        dict(category_frequency),
        maximum_rows=15,
        top_when_collapsing=14,
    )

    ranked_stores = [name for name, _ in store_rows]

    if len(ranked_stores) > 6:
        monthly_store_names = ranked_stores[:5] + ["Other"]
        kept_stores = set(ranked_stores[:5])
    else:
        monthly_store_names = ranked_stores
        kept_stores = set(ranked_stores)

    monthly_store_rows = []

    for month in months:
        values = []

        for store in monthly_store_names:
            if store == "Other" and len(ranked_stores) > 6:
                value = sum(
                    amount
                    for actual_store, amount
                    in monthly_store.get(month, {}).items()
                    if actual_store not in kept_stores
                )
            else:
                value = monthly_store.get(month, {}).get(store, 0.0)

            values.append(value)

        monthly_store_rows.append((month, values))

    known_stores = {
        item["store"]
        for item in observations
        if item["store"] != "Unknown"
    }

    known_categories = {
        item["category"]
        for item in observations
        if item["category"] != "Uncategorized"
    }

    if not known_categories:
        known_categories = {
            item["category"]
            for item in observations
        }

    return {
        "total_spending": total_spending,
        "observation_count": len(observations),
        "earliest": earliest,
        "latest": latest,
        "store_count": len(known_stores),
        "category_count": len(known_categories),
        "monthly_spending": monthly_rows,
        "category_spending": category_rows,
        "store_spending": store_rows,
        "category_share": share_rows,
        "product_spending": product_rows,
        "category_frequency": frequency_rows,
        "monthly_store_names": monthly_store_names,
        "monthly_store": monthly_store_rows,
    }


def _delete_sheet_if_present(workbook, name: str) -> None:
    if name in workbook.sheetnames:
        workbook.remove(workbook[name])


def _create_output_sheets(workbook):
    _delete_sheet_if_present(workbook, ANALYTICS_SHEET)
    _delete_sheet_if_present(workbook, ANALYTICS_DATA_SHEET)

    purchase_index = workbook.sheetnames.index(PURCHASE_SHEET)

    analytics = workbook.create_sheet(
        ANALYTICS_SHEET,
        purchase_index + 1,
    )
    data_sheet = workbook.create_sheet(
        ANALYTICS_DATA_SHEET,
        purchase_index + 2,
    )

    data_sheet.sheet_state = "hidden"
    analytics.sheet_view.showGridLines = False
    analytics.freeze_panes = "A6"

    return analytics, data_sheet


def _style_dashboard_header(analytics, aggregates: dict) -> None:
    analytics.merge_cells("A1:N2")
    title = analytics["A1"]
    title.value = "ShopGraph Spending Analytics"
    title.font = Font(
        bold=True,
        size=20,
        color="FFFFFF",
    )
    title.alignment = Alignment(
        horizontal="center",
        vertical="center",
    )
    title.fill = PatternFill(
        "solid",
        fgColor="1F4E78",
    )

    summary = (
        ("Total Spending", aggregates["total_spending"]),
        ("Purchase Observations", aggregates["observation_count"]),
        (
            "Date Range",
            (
                f"{aggregates['earliest'].strftime('%m/%d/%Y')} - "
                f"{aggregates['latest'].strftime('%m/%d/%Y')}"
            ),
        ),
        ("Stores", aggregates["store_count"]),
        ("Categories", aggregates["category_count"]),
    )

    start_columns = (1, 4, 7, 10, 13)

    for (label, value), column in zip(summary, start_columns):
        label_cell = analytics.cell(row=4, column=column)
        value_cell = analytics.cell(row=5, column=column)

        label_cell.value = label
        label_cell.font = Font(bold=True, color="404040")
        label_cell.alignment = Alignment(horizontal="center")

        value_cell.value = value
        value_cell.font = Font(bold=True, size=12)
        value_cell.alignment = Alignment(horizontal="center")

        if label == "Total Spending":
            value_cell.number_format = CURRENCY_FORMAT

    for column in range(1, 15):
        analytics.column_dimensions[get_column_letter(column)].width = 12

    analytics.row_dimensions[1].height = 26
    analytics.row_dimensions[2].height = 26


def _write_table(
    sheet,
    *,
    start_column: int,
    start_row: int,
    title: str,
    headers: list[str],
    rows: list[tuple | list],
    currency_columns: set[int] | None = None,
    date_columns: set[int] | None = None,
) -> dict:
    currency_columns = currency_columns or set()
    date_columns = date_columns or set()

    sheet.cell(
        row=start_row,
        column=start_column,
        value=title,
    ).font = Font(bold=True)

    header_row = start_row + 1

    for offset, header in enumerate(headers):
        cell = sheet.cell(
            row=header_row,
            column=start_column + offset,
            value=header,
        )
        cell.font = Font(bold=True)

    data_start = header_row + 1

    for row_offset, values in enumerate(rows):
        row_number = data_start + row_offset

        for column_offset, value in enumerate(values):
            cell = sheet.cell(
                row=row_number,
                column=start_column + column_offset,
                value=value,
            )

            if column_offset in currency_columns:
                cell.number_format = CURRENCY_FORMAT

            if column_offset in date_columns:
                cell.number_format = MONTH_FORMAT

    return {
        "start_column": start_column,
        "header_row": header_row,
        "data_start": data_start,
        "data_end": data_start + len(rows) - 1,
        "column_count": len(headers),
        "row_count": len(rows),
    }


def _line_chart(data_sheet, table: dict) -> LineChart:
    chart = LineChart()
    chart.title = "Monthly Spending"
    chart.y_axis.title = "Spending ($)"
    chart.x_axis.title = "Month"
    chart.style = 13
    chart.height = 7.3
    chart.width = 13.2
    chart.legend = None

    data = Reference(
        data_sheet,
        min_col=table["start_column"] + 1,
        min_row=table["header_row"],
        max_row=table["data_end"],
    )
    categories = Reference(
        data_sheet,
        min_col=table["start_column"],
        min_row=table["data_start"],
        max_row=table["data_end"],
    )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)

    return chart


def _horizontal_bar_chart(
    data_sheet,
    table: dict,
    *,
    title: str,
    x_axis_title: str,
) -> BarChart:
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = title
    chart.x_axis.title = x_axis_title
    chart.y_axis.title = ""
    chart.height = 7.3
    chart.width = 13.2
    chart.legend = None

    data = Reference(
        data_sheet,
        min_col=table["start_column"] + 1,
        min_row=table["header_row"],
        max_row=table["data_end"],
    )
    categories = Reference(
        data_sheet,
        min_col=table["start_column"],
        min_row=table["data_start"],
        max_row=table["data_end"],
    )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)

    return chart


def _doughnut_chart(data_sheet, table: dict) -> DoughnutChart:
    chart = DoughnutChart()
    chart.title = "Spending Share by Category"
    chart.holeSize = 55
    chart.style = 10
    chart.height = 7.3
    chart.width = 13.2

    data = Reference(
        data_sheet,
        min_col=table["start_column"] + 1,
        min_row=table["header_row"],
        max_row=table["data_end"],
    )
    labels = Reference(
        data_sheet,
        min_col=table["start_column"],
        min_row=table["data_start"],
        max_row=table["data_end"],
    )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)

    labels_options = DataLabelList()
    labels_options.showPercent = True
    labels_options.showLeaderLines = True
    chart.dataLabels = labels_options

    return chart


def _stacked_store_chart(data_sheet, table: dict) -> BarChart:
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.style = 12
    chart.title = "Monthly Spending by Store"
    chart.y_axis.title = "Spending ($)"
    chart.x_axis.title = "Month"
    chart.height = 9.0
    chart.width = 27.0

    data = Reference(
        data_sheet,
        min_col=table["start_column"] + 1,
        max_col=(
            table["start_column"]
            + table["column_count"]
            - 1
        ),
        min_row=table["header_row"],
        max_row=table["data_end"],
    )
    categories = Reference(
        data_sheet,
        min_col=table["start_column"],
        min_row=table["data_start"],
        max_row=table["data_end"],
    )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)

    return chart


def _add_insufficient_note(
    analytics,
    cell: str,
    message: str,
) -> None:
    analytics[cell] = message
    analytics[cell].font = Font(
        italic=True,
        color="666666",
    )


def _atomic_save(workbook, workbook_path: Path) -> None:
    workbook_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        suffix=".xlsx",
        dir=workbook_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)

    try:
        workbook.save(temporary_path)
        os.replace(temporary_path, workbook_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def generate_purchase_analytics(
    workbook_path: Path = WORKBOOK_PATH,
) -> dict:
    workbook_path = Path(workbook_path).expanduser().resolve()

    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook does not exist: "
            f"{workbook_path}"
        )

    workbook = load_workbook(
        workbook_path,
        data_only=False,
    )

    if PURCHASE_SHEET not in workbook.sheetnames:
        raise PurchaseAnalyticsError(
            f"Workbook does not contain '{PURCHASE_SHEET}'."
        )

    purchase_sheet = workbook[PURCHASE_SHEET]
    observations, diagnostics = _flatten_purchase_history(
        purchase_sheet
    )

    analytics, data_sheet = _create_output_sheets(
        workbook
    )

    if not observations:
        analytics.merge_cells("A1:N2")
        analytics["A1"] = "ShopGraph Spending Analytics"
        analytics["A1"].font = Font(
            bold=True,
            size=20,
            color="FFFFFF",
        )
        analytics["A1"].fill = PatternFill(
            "solid",
            fgColor="1F4E78",
        )
        analytics["A1"].alignment = Alignment(
            horizontal="center",
            vertical="center",
        )
        analytics["A4"] = "No purchase history is available yet."
        analytics["A4"].font = Font(
            italic=True,
            size=12,
            color="666666",
        )
        analytics.sheet_view.showGridLines = False

        data_sheet["A1"] = "No valid purchase observations."
        data_sheet.sheet_state = "hidden"

        _atomic_save(workbook, workbook_path)

        return {
            "workbook_path": workbook_path,
            "charts_created": 0,
            "purchase_observations": 0,
            "skipped_pairs": diagnostics["skipped_pairs"],
            "history_pairs_found": diagnostics["history_pairs_found"],
        }

    aggregates = _aggregate(observations)
    _style_dashboard_header(
        analytics,
        aggregates,
    )

    # Helper tables are deliberately separated by columns so each chart has a
    # simple, inspectable source range.
    monthly_table = _write_table(
        data_sheet,
        start_column=1,
        start_row=1,
        title="Monthly Spending",
        headers=["Month", "Spending"],
        rows=aggregates["monthly_spending"],
        currency_columns={1},
        date_columns={0},
    )

    category_table = _write_table(
        data_sheet,
        start_column=4,
        start_row=1,
        title="Spending by Category",
        headers=["Category", "Spending"],
        rows=aggregates["category_spending"],
        currency_columns={1},
    )

    store_table = _write_table(
        data_sheet,
        start_column=7,
        start_row=1,
        title="Spending by Store",
        headers=["Store", "Spending"],
        rows=aggregates["store_spending"],
        currency_columns={1},
    )

    share_table = _write_table(
        data_sheet,
        start_column=10,
        start_row=1,
        title="Spending Share by Category",
        headers=["Category", "Spending"],
        rows=aggregates["category_share"],
        currency_columns={1},
    )

    product_table = _write_table(
        data_sheet,
        start_column=13,
        start_row=1,
        title="Top Products by Spending",
        headers=["Product", "Spending"],
        rows=aggregates["product_spending"],
        currency_columns={1},
    )

    frequency_table = _write_table(
        data_sheet,
        start_column=16,
        start_row=1,
        title="Purchase Frequency by Category",
        headers=["Category", "Purchases"],
        rows=aggregates["category_frequency"],
    )

    monthly_store_headers = [
        "Month",
        *aggregates["monthly_store_names"],
    ]
    monthly_store_rows = [
        [month, *values]
        for month, values in aggregates["monthly_store"]
    ]
    monthly_store_table = _write_table(
        data_sheet,
        start_column=19,
        start_row=1,
        title="Monthly Spending by Store",
        headers=monthly_store_headers,
        rows=monthly_store_rows,
        currency_columns=set(
            range(1, len(monthly_store_headers))
        ),
        date_columns={0},
    )

    charts_created = 0

    chart_specs = (
        (monthly_table, "A7", lambda table: _line_chart(data_sheet, table)),
        (share_table, "H7", lambda table: _doughnut_chart(data_sheet, table)),
        (
            category_table,
            "A24",
            lambda table: _horizontal_bar_chart(
                data_sheet,
                table,
                title="Spending by Category",
                x_axis_title="Spending ($)",
            ),
        ),
        (
            store_table,
            "H24",
            lambda table: _horizontal_bar_chart(
                data_sheet,
                table,
                title="Spending by Store",
                x_axis_title="Spending ($)",
            ),
        ),
        (
            product_table,
            "A42",
            lambda table: _horizontal_bar_chart(
                data_sheet,
                table,
                title="Top 10 Products by Spending",
                x_axis_title="Spending ($)",
            ),
        ),
        (
            frequency_table,
            "H42",
            lambda table: _horizontal_bar_chart(
                data_sheet,
                table,
                title="Purchase Frequency by Category",
                x_axis_title="Purchases",
            ),
        ),
    )

    for table, anchor, builder in chart_specs:
        if table["row_count"] <= 0:
            _add_insufficient_note(
                analytics,
                anchor,
                "Not enough data for this chart.",
            )
            continue

        chart = builder(table)
        analytics.add_chart(chart, anchor)
        charts_created += 1

    if (
        monthly_store_table["row_count"] > 0
        and len(aggregates["monthly_store_names"]) > 0
    ):
        analytics.add_chart(
            _stacked_store_chart(
                data_sheet,
                monthly_store_table,
            ),
            "A60",
        )
        charts_created += 1
    else:
        _add_insufficient_note(
            analytics,
            "A60",
            "Not enough data for Monthly Spending by Store.",
        )

    # Hidden helper data is useful for debugging but stays out of the shopper's
    # normal dashboard view.
    data_sheet.sheet_state = "hidden"

    _atomic_save(workbook, workbook_path)

    return {
        "workbook_path": workbook_path,
        "charts_created": charts_created,
        "purchase_observations": aggregates["observation_count"],
        "total_spending": aggregates["total_spending"],
        "skipped_pairs": diagnostics["skipped_pairs"],
        "history_pairs_found": diagnostics["history_pairs_found"],
    }
