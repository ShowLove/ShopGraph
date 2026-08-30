from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from utils.DataBaseBuilder.budget_plans.budget_plan_analytics import (
    current_worksheet_names,
    delete_budget_plan_worksheet,
    generate_budget_plan,
    get_current_categories,
)
from utils.DataBaseBuilder.budget_plans.budget_plan_config import (
    CATEGORY_SCOPE_ALL,
    CATEGORY_SCOPE_SELECTED,
    BudgetPlanConfigError,
    delete_plan_config,
    generate_plan_id,
    generate_worksheet_name,
    list_plans,
    parse_budget,
    save_plan,
)


DATE_FORMAT = "%m/%d/%Y"


def _format_date(iso_value: str) -> str:
    return datetime.strptime(iso_value, "%Y-%m-%d").strftime(DATE_FORMAT)


def _format_budget(value) -> str:
    return f"${Decimal(str(value)):,.2f}"


def _prompt_date(label: str):
    while True:
        value = input(f"\n{label} (MM/DD/YYYY, or 0 to cancel): ").strip()
        if value == "0":
            return None
        try:
            return datetime.strptime(value, DATE_FORMAT).date()
        except ValueError:
            print("\n[ERROR] Enter the date as MM/DD/YYYY.")


def _prompt_budget():
    while True:
        value = input("\nBudget (or 0 to cancel): ").strip()
        if value == "0":
            return None
        try:
            amount = parse_budget(value)
        except BudgetPlanConfigError as error:
            print(f"\n[ERROR] {error}")
            continue
        return amount


def _prompt_category_scope():
    while True:
        print("\nCategory Scope:\n")
        print("A. All Categories")
        print("S. Select Categories")
        print("0. Cancel")
        option = input("\nSelect Category Scope: ").strip().casefold()
        if option == "a":
            return CATEGORY_SCOPE_ALL
        if option == "s":
            return CATEGORY_SCOPE_SELECTED
        if option == "0":
            return None
        print("\n[ERROR] Select A, S, or 0.")


def _prompt_selected_categories(categories: list[str]):
    if not categories:
        print("\n[ERROR] Category Manager contains no valid broad Categories.")
        return None

    print("\nAvailable Categories:\n")
    for index, category in enumerate(categories, start=1):
        print(f"{index}. {category}")

    while True:
        value = input("\nSelect Categories (example: 1,2,5; 0 to cancel): ").strip()
        if value == "0":
            return None

        raw_parts = [part.strip() for part in value.split(",") if part.strip()]
        if not raw_parts or any(not part.isdigit() for part in raw_parts):
            print("\n[ERROR] Enter one or more Category numbers separated by commas.")
            continue

        indexes = []
        seen = set()
        invalid = False
        for part in raw_parts:
            index = int(part)
            if index < 1 or index > len(categories):
                invalid = True
                break
            if index not in seen:
                indexes.append(index)
                seen.add(index)

        if invalid:
            print("\n[ERROR] One or more Category numbers are invalid.")
            continue

        return [categories[index - 1] for index in indexes]


def _confirm_create(plan: dict) -> bool:
    print("\n=== Confirm Budget Plan ===\n")
    print(f"Name: {plan['name']}")
    print(f"Date Range: {_format_date(plan['start_date'])} - {_format_date(plan['end_date'])}")
    if plan["category_scope"] == CATEGORY_SCOPE_ALL:
        print("Category Scope: All Categories")
        print("Categories: All current Categories")
    else:
        print("Category Scope: Selected Categories")
        print("Categories: " + ", ".join(plan["categories"]))
    print(f"Budget: {_format_budget(plan['budget'])}")
    print(f"Worksheet: {plan['worksheet_name']}")
    print("\n1. Create")
    print("0. Cancel")

    while True:
        option = input("\nSelect option: ").strip()
        if option == "1":
            return True
        if option == "0":
            return False
        print("\n[ERROR] Invalid option.")


def _plan_scope_text(plan: dict) -> str:
    if plan["category_scope"] == CATEGORY_SCOPE_ALL:
        return "All Categories"
    return "Selected: " + ", ".join(plan["categories"])


def _display_plan_list(plans: list[dict]) -> None:
    for index, plan in enumerate(plans, start=1):
        print(f"{index}. {plan['name']}")
        print(f"   {_format_date(plan['start_date'])} - {_format_date(plan['end_date'])}")
        print(f"   {_format_budget(plan['budget'])}")
        print(f"   {_plan_scope_text(plan)}")
        print(f"   Worksheet: {plan['worksheet_name']}")


def _select_plan(prompt: str = "Select Budget Plan"):
    try:
        plans = list_plans()
    except (OSError, BudgetPlanConfigError) as error:
        print(f"\n[ERROR] {error}")
        return None

    if not plans:
        print("\n[INFO] No Budget Plans have been created yet.")
        return None

    print()
    _display_plan_list(plans)
    while True:
        value = input(f"\n{prompt} (0 to cancel): ").strip()
        if value == "0":
            return None
        if not value.isdigit():
            print("\n[ERROR] Enter a Budget Plan number.")
            continue
        index = int(value)
        if 1 <= index <= len(plans):
            return plans[index - 1]
        print("\n[ERROR] Invalid Budget Plan number.")


def create_new_budget_plan() -> None:
    print("\n=== Create New Budget Plan ===\n")

    while True:
        name = input("Plan Name (or 0 to cancel): ").strip()
        if name == "0":
            return
        if name:
            break
        print("\n[ERROR] Plan Name cannot be blank.\n")

    start_date = _prompt_date("Start Date")
    if start_date is None:
        return
    end_date = _prompt_date("End Date")
    if end_date is None:
        return
    if end_date < start_date:
        print("\n[ERROR] End Date cannot be before Start Date.")
        return

    try:
        categories = get_current_categories()
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"\n[ERROR] Could not read current Categories: {error}")
        return

    category_scope = _prompt_category_scope()
    if category_scope is None:
        return

    selected_categories = []
    if category_scope == CATEGORY_SCOPE_SELECTED:
        selected_categories = _prompt_selected_categories(categories)
        if selected_categories is None:
            return

    budget = _prompt_budget()
    if budget is None:
        return

    try:
        existing_plans = list_plans()
        existing_plan_sheet_names = {plan["worksheet_name"] for plan in existing_plans}
        sheet_names = current_worksheet_names()
        plan_id = generate_plan_id(name, start_date, end_date)
        worksheet_name = generate_worksheet_name(
            name,
            end_date,
            sheet_names,
            existing_plan_sheet_names,
        )
    except (FileNotFoundError, OSError, ValueError, BudgetPlanConfigError) as error:
        print(f"\n[ERROR] Could not prepare Budget Plan: {error}")
        return

    plan = {
        "id": plan_id,
        "name": name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "category_scope": category_scope,
        "categories": selected_categories,
        "budget": f"{budget:.2f}",
        "worksheet_name": worksheet_name,
    }

    if not _confirm_create(plan):
        print("\n[INFO] Budget Plan creation cancelled.")
        return

    try:
        summary = generate_budget_plan(plan)
        config_path = save_plan(plan)
    except (FileNotFoundError, OSError, ValueError, BudgetPlanConfigError) as error:
        print(f"\n[ERROR] Budget Plan could not be created: {error}")
        return

    print("\n[OK] Budget Plan created.")
    print(f"Worksheet: {summary['worksheet_name']}")
    print(f"Spent: {_format_budget(summary['total_spent'])}")
    print(f"Remaining: {_format_budget(summary['remaining_budget'])}")
    print(f"Status: {summary['ahead_behind']}")
    print(f"Configuration:\n{config_path}")
    print(f"Workbook:\n{summary['workbook_path']}")


def refresh_budget_plan() -> None:
    print("\n=== Refresh Budget Plan ===")
    plan = _select_plan()
    if plan is None:
        return
    try:
        summary = generate_budget_plan(plan)
    except (FileNotFoundError, OSError, ValueError, BudgetPlanConfigError) as error:
        print(f"\n[ERROR] Could not refresh {plan['name']}: {error}")
        return

    print(f"\n[OK] Budget Plan refreshed: {plan['name']}")
    print(f"Spent: {_format_budget(summary['total_spent'])}")
    print(f"Remaining: {_format_budget(summary['remaining_budget'])}")
    print(f"Status: {summary['ahead_behind']}")
    print(f"Workbook:\n{summary['workbook_path']}")


def refresh_all_budget_plans() -> None:
    print("\n=== Refresh All Budget Plans ===\n")
    try:
        plans = list_plans()
    except (OSError, BudgetPlanConfigError) as error:
        print(f"[ERROR] {error}")
        return

    if not plans:
        print("[INFO] No Budget Plans have been created yet.")
        return

    successes = 0
    failures = 0
    for plan in plans:
        try:
            generate_budget_plan(plan)
        except (FileNotFoundError, OSError, ValueError, BudgetPlanConfigError) as error:
            failures += 1
            print(f"[ERROR] {plan['name']}: {error}")
        else:
            successes += 1
            print(f"[OK] {plan['name']}")

    print(f"\nRefresh complete. Successful: {successes}; Failed: {failures}")


def view_budget_plans() -> None:
    print("\n=== Budget Plans ===\n")
    try:
        plans = list_plans()
    except (OSError, BudgetPlanConfigError) as error:
        print(f"[ERROR] {error}")
        return
    if not plans:
        print("[INFO] No Budget Plans have been created yet.")
        return
    _display_plan_list(plans)


def delete_budget_plan() -> None:
    print("\n=== Delete Budget Plan ===")
    plan = _select_plan("Select Budget Plan to delete")
    if plan is None:
        return

    print("\nThis deletes only the derived Budget Plan configuration and worksheet.")
    print("Purchase History and Category Manager data are not deleted.\n")
    print(f"Plan: {plan['name']}")
    print(f"Date Range: {_format_date(plan['start_date'])} - {_format_date(plan['end_date'])}")
    print(f"Category Scope: {_plan_scope_text(plan)}")
    print(f"Budget: {_format_budget(plan['budget'])}")
    print(f"Worksheet: {plan['worksheet_name']}")

    answer = input("\nDelete this Budget Plan? [y/N]: ").strip().casefold()
    if answer not in {"y", "yes"}:
        print("\n[INFO] Delete cancelled.")
        return

    try:
        worksheet_deleted = delete_budget_plan_worksheet(plan["worksheet_name"])
        config_deleted = delete_plan_config(plan["id"])
    except (FileNotFoundError, OSError, ValueError, BudgetPlanConfigError) as error:
        print(f"\n[ERROR] Could not delete Budget Plan safely: {error}")
        return

    if worksheet_deleted:
        print("\n[OK] Derived worksheet deleted.")
    else:
        print("\n[WARNING] Derived worksheet was already missing.")

    if config_deleted:
        print("[OK] Budget Plan configuration deleted.")
    else:
        print("[WARNING] Budget Plan configuration was already missing.")


def display_budget_plans_menu() -> None:
    print("\n=== ShopGraph Budget Plans ===\n")
    print("1. Create New Budget Plan")
    print("2. Refresh Budget Plan")
    print("3. Refresh All Budget Plans")
    print("4. View Budget Plans")
    print("5. Delete Budget Plan")
    print("0. Return to Data Base Builder")


def run_budget_plans_menu() -> None:
    while True:
        display_budget_plans_menu()
        option = input("\nSelect option: ").strip()
        if option == "1":
            create_new_budget_plan()
        elif option == "2":
            refresh_budget_plan()
        elif option == "3":
            refresh_all_budget_plans()
        elif option == "4":
            view_budget_plans()
        elif option == "5":
            delete_budget_plan()
        elif option == "0":
            return
        else:
            print("\n[ERROR] Invalid option.")
