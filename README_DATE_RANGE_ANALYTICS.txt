ShopGraph - Analytics Date Range Update

PURPOSE
Adds a Budget Plans menu option that refreshes BOTH existing analytics worksheets for an inclusive date range.

Menu:
1. Create New Budget Plan
2. Refresh Budget Plan
3. Refresh All Budget Plans
4. View Budget Plans
5. Delete Budget Plan
6. Refresh Analytics + Sub Analytics by Date Range
0. Return to Data Base Builder

Behavior:
- Prompts for Start Date and End Date in MM/DD/YYYY.
- Date range is inclusive.
- Filters individual Date N / Price N purchase observations, not product rows.
- Overwrites the current Analytics worksheet.
- Overwrites the current Sub Analytics worksheet.
- Also replaces their hidden helper sheets (_AnalyticsData and _SubAnalyticsData) through the existing analytics machinery.
- Does not modify Purchase History, Category Manager, Budget Plan configurations, or Budget Plan worksheets.
- Existing Data Base Builder analytics options 2 and 3 retain their original all-history behavior.

FILES CHANGED
utils/DataBaseBuilder/excel/purchase_analytics.py
utils/DataBaseBuilder/budget_plans/budget_plan_menu.py

INSTALL
Use the existing ShopGraph Code Update Importer / overlay workflow, or replace the two files while preserving the directory structure.
