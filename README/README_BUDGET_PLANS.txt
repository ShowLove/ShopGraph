ShopGraph - Budget Plans + Budget Burndown
===========================================

PURPOSE
-------
Adds reusable Budget Plans derived from the existing Purchase History and
Category Manager data.

A Budget Plan stores only:
- Plan id and name
- Start Date
- End Date
- Category Scope (All or Selected)
- Selected Categories when applicable
- Total Budget
- Stable worksheet name

Purchase totals and chart data are never stored in the plan configuration.
They are regenerated from Purchase History whenever a plan is refreshed.

MENU
----
Main -> Utilities -> Data Base Builder -> Budget Plans

1. Create New Budget Plan
2. Refresh Budget Plan
3. Refresh All Budget Plans
4. View Budget Plans
5. Delete Budget Plan
0. Return to Data Base Builder

The existing global -1 exit behavior remains active for every input() prompt.

CATEGORY SCOPE
--------------
ALL:
    Dynamically uses every current valid broad Category from Category Manager.
    The Category list is NOT frozen in the plan config. If a new Category is
    added later, an All Categories plan includes it on the next refresh.

SELECTED:
    Stores only the Categories explicitly selected when the plan is created.
    A refresh validates that every saved Category still exists. Missing or
    invalid Categories produce a clear error instead of being silently ignored.

DATA FLOW
---------
Purchase History Date N / Price N observations
    -> Purchase History Sub-Category
    -> Category Manager Sub-Category -> Category
    -> Budget Plan date/category filtering
    -> Budget Plan worksheet + burndown chart

DATE FILTERING
--------------
Start Date and End Date are inclusive.
Each historical Date N / Price N pair counts as its own purchase observation.

BUDGET BURNDOWN
---------------
The chart uses Remaining Budget on the Y axis and calendar date on the X axis.

Ideal Remaining Budget:
    Moves linearly from the configured budget toward $0 by the End Date.

Actual Remaining Budget:
    Budget minus cumulative qualifying spending.

Actual Remaining above Ideal Remaining means spending is below the planned
burn rate. Actual Remaining below Ideal Remaining means spending is above the
planned burn rate. Overspending is not clamped at zero.

A one-day plan is treated as having its complete ideal budget burn due on that
single day so the calculation remains defined without division by zero.

WORKSHEETS
----------
Each Budget Plan owns exactly one visible worksheet in:

    data/database/shopgraph_purchase_history.xlsx

Helper chart data is stored on that same worksheet. No hidden helper sheet is
created for a Budget Plan.

Budget Plan worksheets are derived data. Refresh replaces only that plan's
worksheet. Delete removes only the selected plan's worksheet and configuration.
Purchase History and Category Manager data are never deleted by Budget Plans.

CONFIGURATION
-------------
Runtime Budget Plan files are created under:

    utils/config/budget_plans/

Each plan is stored as its own JSON file.

The Code Update Importer now uses:

    utils/config/settings.txt

for its runtime settings. Existing values from:

    utils/config.txt

are migrated automatically when the updated importer module is loaded. The old
file remains a readable fallback; it is not destructively deleted.

The Code Update Importer protects both:

    utils/config.txt
    utils/config/

from future update ZIP overlays. Runtime settings and Budget Plan definitions
therefore cannot be overwritten by a normal ShopGraph update package.

WORKSHEET NAMES
---------------
The user-facing Plan Name, internal Plan ID, and Excel worksheet name are
separate concepts. Worksheet names are shortened to Excel's 31-character limit,
invalid Excel characters are removed, and collisions receive a short numeric
suffix. The chosen worksheet name is saved in the plan config so it stays stable
on refresh.

DEPENDENCIES
------------
No new dependency is required. Budget Plans use the existing openpyxl dependency
already used by ShopGraph analytics.

FILES
-----
NEW:
    utils/DataBaseBuilder/budget_plans/__init__.py
    utils/DataBaseBuilder/budget_plans/budget_plan_config.py
    utils/DataBaseBuilder/budget_plans/budget_plan_analytics.py
    utils/DataBaseBuilder/budget_plans/budget_plan_menu.py
    README/README_BUDGET_PLANS.txt

UPDATED:
    utils/DataBaseBuilder/data_base_builder_main.py
    utils/code_update_importer.py

RUNTIME ONLY (not included in this ZIP):
    utils/config/settings.txt
    utils/config/budget_plans/*.json

SAFETY
------
Budget Plan actions never modify Purchase History purchase cells or Category
Manager mappings. Workbook writes use ShopGraph's existing atomic-save helper.
All outputs can be regenerated from existing source data plus the small plan
configuration files.
