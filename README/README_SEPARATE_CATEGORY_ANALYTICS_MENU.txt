ShopGraph - Separate Sub-Category and Category Analytics Menu
==============================================================

PURPOSE
-------
The Data Base Builder now exposes the two analytics levels as separate actions.

MENU
----
=== ShopGraph Data Base Builder ===

1. Add Receipt to Purchase History
2. Generate / Refresh Purchase Analytics - Sub-Categories
3. Generate / Refresh Purchase Analytics - Categories
4. Category Manager
0. Return to Main

OPTION 2 - SUB-CATEGORIES
-------------------------
Refreshes only the existing detailed Sub Analytics dashboard.

Source:
    Purchase History -> Sub-Category

It preserves the existing dashboard machinery, chart layout, calculations,
keys, explanations, and Sub-Category grouping behavior.

Worksheets refreshed:
    Sub Analytics
    _SubAnalyticsData

It does not refresh or overwrite the broad Category Analytics sheets.

OPTION 3 - CATEGORIES
---------------------
Refreshes only the broad Category Analytics dashboard using the same analytics
machinery and presentation as Sub Analytics, but groups purchases by Category.

Source:
    Purchase History.Sub-Category
        +
    Category Manager.Sub-Category -> Category
        ->
    Analytics grouped by Category

Worksheets refreshed:
    Analytics
    _AnalyticsData

Category Manager must contain a valid Category for every current Sub-Category.
If that hierarchy is incomplete or invalid, Option 3 reports an error and does
not guess Category assignments.

OPTION 4 - CATEGORY MANAGER
---------------------------
Category Manager moves from menu option 3 to menu option 4. Its internal
behavior is unchanged by this update.

BACKWARD COMPATIBILITY
----------------------
The existing generate_purchase_analytics() function is retained as a combined
wrapper so unrelated code that imports it will continue to work. The new menu
uses dedicated functions for Sub-Category and Category analytics separately.

INSTALL
-------
Overlay this ZIP onto the ShopGraph project root, replacing matching files.
No new Python package installation is required.
