SHOPGRAPH — BUDGET VS STACKED CATEGORY SPENDING UPDATE
=======================================================

PURPOSE
-------
Changes each Budget Plan worksheet to show exactly TWO vertical bars:

1. Budget
   - One solid bar equal to the full configured Budget Plan amount.

2. Spent
   - One stacked bar equal to total spending through the plan's Relevant Date.
   - Every colored segment is spending from one broad Category.

CATEGORY NUMBERS + KEY
----------------------
Each Category receives a number (1, 2, 3, ...).

That number is displayed inside the Category's colored segment on the Spent bar.
A color-matched key is placed to the right of the chart and shows:

    # | Category | Spent

This makes it possible to compare Total Budget versus Total Spent immediately,
while still seeing what makes up the Spent bar.

EXAMPLE CONCEPT
---------------

    Budget              Spent
    ██████              ██████  4
    ██████              ██████  3
    ██████              ██████  2
    ██████              ██████  1

                         Key:
                         1  Food
                         2  Household
                         3  Personal Care
                         4  Other Category

DATA RULES
----------
- Uses broad Categories from Category Manager.
- Uses Purchase History observations already mapped through ShopGraph's existing
  Category analytics architecture.
- Respects ALL versus SELECTED Budget Plan scope.
- Uses only purchases inside the Budget Plan date range.
- Uses spending through the plan's Relevant Date so the stacked bar agrees with
  the worksheet's Total Spent summary value.
- A Category with $0 spending remains in the key but has no visible segment.
- If spending exceeds the budget, the Spent bar can be taller than the Budget bar.

UNCHANGED
---------
- Budget Plan creation.
- Refresh Budget Plan.
- Refresh All Budget Plans.
- View Budget Plans.
- Delete Budget Plan.
- Budget Plan JSON configuration.
- Purchase History.
- Category Manager.
- Existing summary metrics and daily calculations.
- Global -1 exit behavior.

FILES
-----
Replaces:
    utils/DataBaseBuilder/budget_plans/budget_plan_analytics.py

INSTALLATION
------------
Import this ZIP through ShopGraph's existing Code Update Importer, then run:

    Data Base Builder
        -> Budget Plans
            -> Refresh Budget Plan

or:

    Data Base Builder
        -> Budget Plans
            -> Refresh All Budget Plans

DEPENDENCIES
------------
No new dependencies. Uses the project's existing openpyxl dependency.
