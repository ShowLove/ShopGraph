from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill

from utils.DataBaseBuilder.budget_plans.budget_plan_config import (
    CATEGORY_SCOPE_ALL,
    CATEGORY_SCOPE_SELECTED,
    parse_budget,
    parse_iso_date,
    validate_plan,
)
from utils.DataBaseBuilder.excel.category_manager import (
    load_category_mapping_for_analytics,
)
from utils.DataBaseBuilder.excel.purchase_analytics import (
    CURRENCY_FORMAT,
    DATE_FORMAT,
    _atomic_save,
    _broad_category_observations,
    _flatten_purchase_history,
)
from utils.DataBaseBuilder.excel.purchase_history import (
    PURCHASE_SHEET,
    WORKBOOK_PATH,
    _ensure_purchase_schema,
)


CHART_WIDTH = 24
CHART_HEIGHT = 13
HELPER_START_COLUMN = 12  # L
HEADER_FILL = "D9EAF7"
SECTION_FILL = "E2F0D9"


class BudgetPlanAnalyticsError(ValueError):
    """Raised when a Budget Plan worksheet cannot be generated safely."""


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _ideal_remaining(
    budget: float,
    start_date: date,
    end_date: date,
    current_date: date,
) -> float:
    total_elapsed_days = (end_date - start_date).days

    # A one-day plan has only its deadline point. Treat the ideal budget as fully
    # burned by the end of that day rather than divide by zero.
    if total_elapsed_days == 0:
        return 0.0

    elapsed_days = (current_date - start_date).days
    fraction = min(max(elapsed_days / total_elapsed_days, 0.0), 1.0)
    return budget * (1.0 - fraction)


def _relevant_date(start_date: date, end_date: date, today: date | None = None) -> date:
    today = today or date.today()
    if today < start_date:
        return start_date
    if today > end_date:
        return end_date
    return today


def _resolve_category_scope(plan: dict, current_categories: set[str]) -> set[str]:
    if plan["category_scope"] == CATEGORY_SCOPE_ALL:
        if not current_categories:
            raise BudgetPlanAnalyticsError(
                "Category Manager contains no valid broad Categories."
            )
        return set(current_categories)

    missing = [
        category
        for category in plan["categories"]
        if category not in current_categories
    ]
    if missing:
        raise BudgetPlanAnalyticsError(
            "This Budget Plan references Categories that are no longer valid:\n"
            + "\n".join(f'- "{item}"' for item in missing)
        )

    return set(plan["categories"])


def _filtered_observations(
    observations: list[dict],
    start_date: date,
    end_date: date,
    selected_categories: set[str],
) -> list[dict]:
    return sorted(
        [
            item
            for item in observations
            if start_date <= item["date"] <= end_date
            and item["category"] in selected_categories
        ],
        key=lambda item: (
            item["date"],
            item.get("source_row", 0),
            item.get("history_number", 0),
        ),
    )


def _daily_rows(
    observations: list[dict],
    budget: float,
    start_date: date,
    end_date: date,
) -> list[tuple[date, float, float, float]]:
    spending_by_day = defaultdict(float)
    for item in observations:
        spending_by_day[item["date"]] += float(item["price"])

    cumulative = 0.0
    rows = []
    for day in _date_range(start_date, end_date):
        cumulative += spending_by_day.get(day, 0.0)
        rows.append(
            (
                day,
                _ideal_remaining(budget, start_date, end_date, day),
                budget - cumulative,
                cumulative,
            )
        )
    return rows


def _display_categories(plan: dict, selected_categories: set[str]) -> str:
    if plan["category_scope"] == CATEGORY_SCOPE_ALL:
        return "All Categories"
    return ", ".join(sorted(selected_categories, key=str.casefold))


def _ahead_behind_text(expected_spending: float, actual_spending: float) -> str:
    difference = expected_spending - actual_spending
    if abs(difference) < 0.005:
        return "On pace"
    if difference > 0:
        return f"Ahead by ${difference:,.2f}"
    return f"Behind by ${abs(difference):,.2f}"


def _write_budget_plan_sheet(
    workbook,
    plan: dict,
    rows: list[tuple[date, float, float, float]],
    selected_categories: set[str],
    diagnostics: dict,
    purchase_observation_count: int,
) -> dict:
    sheet_name = plan["worksheet_name"]
    if sheet_name in workbook.sheetnames:
        workbook.remove(workbook[sheet_name])

    sheet = workbook.create_sheet(sheet_name)
    sheet.sheet_view.showGridLines = False

    start_date = parse_iso_date(plan["start_date"])
    end_date = parse_iso_date(plan["end_date"])
    budget = float(parse_budget(plan["budget"]))
    relevant = _relevant_date(start_date, end_date)

    row_by_date = {row[0]: row for row in rows}
    relevant_row = row_by_date[relevant]
    ideal_remaining = relevant_row[1]
    actual_remaining = relevant_row[2]
    actual_spending = relevant_row[3]
    expected_spending = budget - ideal_remaining

    sheet["A1"] = plan["name"]
    sheet["A1"].font = Font(size=18, bold=True)
    sheet["A1"].fill = PatternFill("solid", fgColor=HEADER_FILL)
    sheet.merge_cells("A1:H1")

    metrics = [
        ("Budget Plan", plan["name"]),
        ("Start Date", start_date),
        ("End Date", end_date),
        (
            "Category Scope",
            "All Categories"
            if plan["category_scope"] == CATEGORY_SCOPE_ALL
            else "Selected Categories",
        ),
        ("Categories", _display_categories(plan, selected_categories)),
        ("Budget", budget),
        ("Total Spent", actual_spending),
        ("Remaining Budget", budget - actual_spending),
        ("Relevant Date", relevant),
        ("Ideal Spending Through Relevant Date", expected_spending),
        ("Actual Spending Through Relevant Date", actual_spending),
        ("Ahead / Behind Budget", _ahead_behind_text(expected_spending, actual_spending)),
    ]

    for index, (label, value) in enumerate(metrics, start=3):
        sheet.cell(index, 1, label)
        sheet.cell(index, 1).font = Font(bold=True)
        sheet.cell(index, 1).fill = PatternFill("solid", fgColor=SECTION_FILL)
        sheet.cell(index, 2, value)

    for row_index in (4, 5, 11):
        sheet.cell(row_index, 2).number_format = DATE_FORMAT
    for row_index in (8, 9, 12, 13):
        sheet.cell(row_index, 2).number_format = CURRENCY_FORMAT

    sheet["A16"] = "Budget Burndown"
    sheet["A16"].font = Font(size=14, bold=True)

    helper_col = HELPER_START_COLUMN
    helper_headers = (
        "Date",
        "Ideal Remaining Budget",
        "Actual Remaining Budget",
        "Cumulative Spending",
    )
    for offset, header in enumerate(helper_headers):
        cell = sheet.cell(1, helper_col + offset, header)
        cell.font = Font(bold=True)

    for row_number, data in enumerate(rows, start=2):
        for offset, value in enumerate(data):
            cell = sheet.cell(row_number, helper_col + offset, value)
            if offset == 0:
                cell.number_format = DATE_FORMAT
            else:
                cell.number_format = CURRENCY_FORMAT

    chart = LineChart()
    chart.title = "Budget Burndown"
    chart.y_axis.title = "Remaining Budget"
    chart.x_axis.title = "Date"
    chart.style = 10
    chart.width = CHART_WIDTH
    chart.height = CHART_HEIGHT

    data = Reference(
        sheet,
        min_col=helper_col + 1,
        max_col=helper_col + 2,
        min_row=1,
        max_row=len(rows) + 1,
    )
    dates = Reference(
        sheet,
        min_col=helper_col,
        min_row=2,
        max_row=len(rows) + 1,
    )
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(dates)
    chart.legend.position = "b"
    sheet.add_chart(chart, "A18")

    sheet.column_dimensions["A"].width = 38
    sheet.column_dimensions["B"].width = 48
    for column in range(helper_col, helper_col + 4):
        sheet.column_dimensions[
            __import__("openpyxl").utils.get_column_letter(column)
        ].width = 22

    sheet["A47"] = (
        "Interpretation: Actual Remaining above Ideal Remaining means spending "
        "is running below the planned burn rate. Below the ideal line means "
        "spending is running above the planned burn rate."
    )
    sheet["A47"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.merge_cells("A47:H49")

    return {
        "worksheet_name": sheet_name,
        "budget": budget,
        "total_spent": actual_spending,
        "remaining_budget": actual_remaining,
        "relevant_date": relevant,
        "expected_spending": expected_spending,
        "actual_spending": actual_spending,
        "ahead_behind": _ahead_behind_text(expected_spending, actual_spending),
        "purchase_observations": purchase_observation_count,
        "skipped_pairs": diagnostics.get("skipped_pairs", 0),
        "resolved_categories": sorted(selected_categories, key=str.casefold),
    }


def generate_budget_plan(
    plan: dict,
    workbook_path: Path = WORKBOOK_PATH,
) -> dict:
    plan = validate_plan(plan)
    workbook_path = Path(workbook_path).expanduser().resolve()

    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook does not exist:\n"
            f"{workbook_path}"
        )

    workbook = load_workbook(workbook_path, data_only=False)
    try:
        if PURCHASE_SHEET not in workbook.sheetnames:
            raise BudgetPlanAnalyticsError(
                f'Workbook does not contain "{PURCHASE_SHEET}".'
            )

        purchase_sheet = workbook[PURCHASE_SHEET]
        _ensure_purchase_schema(purchase_sheet)
        observations, diagnostics = _flatten_purchase_history(purchase_sheet)

        mapping = load_category_mapping_for_analytics(workbook)
        broad_observations = _broad_category_observations(observations, mapping)
        current_categories = set(mapping.values())
        selected_categories = _resolve_category_scope(plan, current_categories)

        start_date = parse_iso_date(plan["start_date"])
        end_date = parse_iso_date(plan["end_date"])
        budget = float(parse_budget(plan["budget"]))
        qualifying = _filtered_observations(
            broad_observations,
            start_date,
            end_date,
            selected_categories,
        )
        rows = _daily_rows(qualifying, budget, start_date, end_date)
        summary = _write_budget_plan_sheet(
            workbook,
            plan,
            rows,
            selected_categories,
            diagnostics,
            len(qualifying),
        )
        _atomic_save(workbook, workbook_path)
        return {
            "success": True,
            "workbook_path": workbook_path,
            **summary,
        }
    finally:
        workbook.close()


def delete_budget_plan_worksheet(
    worksheet_name: str,
    workbook_path: Path = WORKBOOK_PATH,
) -> bool:
    workbook_path = Path(workbook_path).expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook does not exist:\n"
            f"{workbook_path}"
        )

    workbook = load_workbook(workbook_path, data_only=False)
    try:
        if worksheet_name not in workbook.sheetnames:
            return False
        workbook.remove(workbook[worksheet_name])
        _atomic_save(workbook, workbook_path)
        return True
    finally:
        workbook.close()


def get_current_categories(
    workbook_path: Path = WORKBOOK_PATH,
) -> list[str]:
    workbook_path = Path(workbook_path).expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook does not exist:\n"
            f"{workbook_path}"
        )

    workbook = load_workbook(workbook_path, data_only=False)
    try:
        mapping = load_category_mapping_for_analytics(workbook)
        return sorted(set(mapping.values()), key=str.casefold)
    finally:
        workbook.close()


def current_worksheet_names(
    workbook_path: Path = WORKBOOK_PATH,
) -> set[str]:
    workbook_path = Path(workbook_path).expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(
            "Purchase History workbook does not exist:\n"
            f"{workbook_path}"
        )
    workbook = load_workbook(workbook_path, read_only=True, data_only=False)
    try:
        return set(workbook.sheetnames)
    finally:
        workbook.close()
