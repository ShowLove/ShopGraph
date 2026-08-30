from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from utils.constants import PROJECT_ROOT


CONFIG_DIR = PROJECT_ROOT / "utils" / "config"
BUDGET_PLANS_DIR = CONFIG_DIR / "budget_plans"

CATEGORY_SCOPE_ALL = "all"
CATEGORY_SCOPE_SELECTED = "selected"
VALID_CATEGORY_SCOPES = {
    CATEGORY_SCOPE_ALL,
    CATEGORY_SCOPE_SELECTED,
}

INVALID_WORKSHEET_CHARS = re.compile(r"[\\/*?:\[\]]")
NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


class BudgetPlanConfigError(ValueError):
    """Raised when a Budget Plan configuration is invalid."""


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def parse_iso_date(value) -> date:
    if isinstance(value, date):
        return value

    text = _text(value)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise BudgetPlanConfigError(
            f'Invalid ISO date "{text}". Expected YYYY-MM-DD.'
        ) from error


def parse_budget(value) -> Decimal:
    text = _text(value).replace("$", "").replace(",", "")
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as error:
        raise BudgetPlanConfigError(
            f'Invalid budget amount "{value}".'
        ) from error

    if not amount.is_finite() or amount <= 0:
        raise BudgetPlanConfigError("Budget must be greater than zero.")

    return amount.quantize(Decimal("0.01"))


def validate_plan(plan: dict) -> dict:
    plan_id = _text(plan.get("id"))
    name = _text(plan.get("name"))
    worksheet_name = _text(plan.get("worksheet_name"))
    category_scope = _text(plan.get("category_scope")).casefold()

    if not plan_id:
        raise BudgetPlanConfigError("Budget Plan id is missing.")
    if not name:
        raise BudgetPlanConfigError("Budget Plan name is missing.")
    if category_scope not in VALID_CATEGORY_SCOPES:
        raise BudgetPlanConfigError(
            'category_scope must be either "all" or "selected".'
        )
    if not worksheet_name:
        raise BudgetPlanConfigError("Budget Plan worksheet name is missing.")
    if len(worksheet_name) > 31 or INVALID_WORKSHEET_CHARS.search(worksheet_name):
        raise BudgetPlanConfigError(
            f'Invalid Excel worksheet name "{worksheet_name}".'
        )

    start_date = parse_iso_date(plan.get("start_date"))
    end_date = parse_iso_date(plan.get("end_date"))
    if end_date < start_date:
        raise BudgetPlanConfigError(
            "Budget Plan End Date cannot be before Start Date."
        )

    budget = parse_budget(plan.get("budget"))

    raw_categories = plan.get("categories", [])
    if raw_categories is None:
        raw_categories = []
    if not isinstance(raw_categories, list):
        raise BudgetPlanConfigError("categories must be a list.")

    categories = []
    seen = set()
    for value in raw_categories:
        category = _text(value)
        if not category:
            continue
        normalized = category.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        categories.append(category)

    if category_scope == CATEGORY_SCOPE_SELECTED and not categories:
        raise BudgetPlanConfigError(
            "Selected Category Scope requires at least one Category."
        )

    if category_scope == CATEGORY_SCOPE_ALL:
        categories = []

    return {
        "id": plan_id,
        "name": name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "category_scope": category_scope,
        "categories": categories,
        "budget": f"{budget:.2f}",
        "worksheet_name": worksheet_name,
    }


def _plan_path(plan_id: str) -> Path:
    safe_id = _text(plan_id)
    if not safe_id or Path(safe_id).name != safe_id or safe_id in {".", ".."}:
        raise BudgetPlanConfigError("Invalid Budget Plan id.")
    return BUDGET_PLANS_DIR / f"{safe_id}.json"


def _atomic_json_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}_",
        suffix=".json",
        dir=path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def save_plan(plan: dict) -> Path:
    validated = validate_plan(plan)
    path = _plan_path(validated["id"])
    _atomic_json_write(path, validated)
    return path.resolve()


def load_plan(plan_id: str) -> dict:
    path = _plan_path(plan_id)
    if not path.exists():
        raise FileNotFoundError(f"Budget Plan configuration was not found:\n{path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BudgetPlanConfigError(
            f"Budget Plan configuration is invalid JSON:\n{path}\n\n{error}"
        ) from error

    return validate_plan(data)


def list_plans() -> list[dict]:
    if not BUDGET_PLANS_DIR.exists():
        return []

    plans = []
    errors = []
    for path in sorted(BUDGET_PLANS_DIR.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            plans.append(validate_plan(data))
        except (OSError, json.JSONDecodeError, BudgetPlanConfigError) as error:
            errors.append(f"{path.name}: {error}")

    if errors:
        raise BudgetPlanConfigError(
            "One or more Budget Plan configuration files are invalid:\n"
            + "\n".join(f"- {item}" for item in errors)
        )

    return sorted(plans, key=lambda item: (item["name"].casefold(), item["start_date"], item["id"]))


def delete_plan_config(plan_id: str) -> bool:
    path = _plan_path(plan_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def _slug(value: str, max_length: int = 28) -> str:
    normalized = NON_SLUG_CHARS.sub("-", value.casefold()).strip("-")
    normalized = normalized or "budget-plan"
    return normalized[:max_length].rstrip("-") or "budget-plan"


def generate_plan_id(name: str, start_date: date, end_date: date) -> str:
    base = _slug(name)
    digest = hashlib.sha1(
        f"{name}|{start_date.isoformat()}|{end_date.isoformat()}".encode("utf-8")
    ).hexdigest()[:6]
    candidate = f"{base}-{digest}"

    BUDGET_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    if not _plan_path(candidate).exists():
        return candidate

    counter = 2
    while _plan_path(f"{candidate}-{counter}").exists():
        counter += 1
    return f"{candidate}-{counter}"


def _worksheet_base(name: str, end_date: date) -> str:
    cleaned = INVALID_WORKSHEET_CHARS.sub(" ", name)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        cleaned = "Budget"

    suffix = f" {end_date:%y}"
    prefix = "BP "
    available = 31 - len(prefix) - len(suffix)
    trimmed = cleaned[:max(1, available)].rstrip()
    return f"{prefix}{trimmed}{suffix}"[:31].rstrip()


def generate_worksheet_name(
    name: str,
    end_date: date,
    existing_sheet_names: set[str],
    existing_plan_names: set[str],
) -> str:
    base = _worksheet_base(name, end_date)
    used = {item.casefold() for item in existing_sheet_names | existing_plan_names}
    if base.casefold() not in used:
        return base

    counter = 2
    while True:
        suffix = f" {counter}"
        candidate = f"{base[:31 - len(suffix)].rstrip()}{suffix}"
        if candidate.casefold() not in used:
            return candidate
        counter += 1
