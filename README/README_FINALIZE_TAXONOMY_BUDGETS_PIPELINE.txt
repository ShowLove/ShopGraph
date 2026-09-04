ShopGraph - Finalize Taxonomy + Budgets Pipeline
================================================

PURPOSE
-------
Adds one new ShopGraph Pipelines option:

    5. Finalize Taxonomy + Budgets

The new workflow reproduces the user's current manual sequence:

    Category Manager
        -> Apply Category Manager to Purchase History
        -> Budget Plans
            -> Refresh All Budget Plans

PIPELINES MENU
--------------
The menu becomes:

    1. Pipeline Part 1
    2. Pipeline Export 1
    3. Category Manager Completion
    4. Pipeline Export 2
    5. Finalize Taxonomy + Budgets
    0. Return to Capabilities Menu

WORKFLOW
--------
Option 5 performs:

    [1/2] Apply Category Manager to Purchase History
    [2/2] Refresh All Budget Plans

The workflow calls the existing reusable Category Manager business logic:

    apply_category_manager()

and the existing Budget Plans action:

    refresh_all_budget_plans()

No Category Manager validation logic, Purchase History update logic, Budget
Plan generation logic, or budget calculations are duplicated.

FAILURE BEHAVIOR
----------------
If Category Manager validation/application fails:

    - the error/validation report is shown;
    - Purchase History remains protected by the existing Category Manager logic;
    - Budget Plans are NOT refreshed.

If Category Manager succeeds, ShopGraph proceeds to the existing Refresh All
Budget Plans function, which already reports each plan's success/failure and a
final successful/failed count.

UNCHANGED
---------
This update preserves all existing functionality, including:

    Pipeline Part 1
    Pipeline Export 1
    Category Manager Completion
    Pipeline Export 2
    Category Manager menus
    Budget Plans menus
    OCR workflows
    Analytics
    Utilities
    Code Update Importer
    global -1 exit behavior

FILES
-----
UPDATED:
    capabilities/pipelines.py

NEW:
    README/README_FINALIZE_TAXONOMY_BUDGETS_PIPELINE.txt

No runtime database, config, budget plan JSON, prompt, or export files are
included.
