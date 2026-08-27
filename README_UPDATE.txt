ShopGraph - Accessible Vertical Purchase Analytics Dashboard
================================================================

BUILT AGAINST
-------------
shopgraph_codebase(20260827-222252).txt

PURPOSE
-------
This update replaces the current Purchase Analytics dashboard layout.

The previous dashboard placed several charts side-by-side and put long category
names directly in or around charts. That becomes cluttered quickly, especially
for the doughnut chart.

The new layout is intentionally long and vertical:

    LARGE GRAPH        NUMBER/COLOR KEY        EXPLANATION
    LARGE GRAPH        NUMBER/COLOR KEY        EXPLANATION
    LARGE GRAPH        NUMBER/COLOR KEY        EXPLANATION
    ...

Each chart is approximately twice the size of the earlier chart.

ACCESSIBILITY
-------------
The dashboard no longer relies on color alone.

Each category, store, product, or month receives a NUMBER in addition to a
color.

The graph uses compact numeric labels/codes.

To the right of each graph is a key containing:

    colored box
    number
    full description
    dollar amount / count / percent

Farther to the right is a written explanation containing:

    What it represents
    How to read it
    What it is useful for
    Notes when helpful

Colors may repeat when there are more items than available palette colors.
The number remains the unambiguous identifier, which makes the charts more
usable for people with color-vision differences.

NO "OTHER" CATEGORY
-------------------
The category graphs no longer combine small categories into a large "Other"
slice/bar.

Every category is retained and receives its own numeric code.

The same principle is used for stores in Monthly Spending by Store.

TOP PRODUCTS
------------
Top 10 Products by Spending remains intentionally limited to the ten largest
product spending totals because "Top 10" is the purpose of that graph. No
"Other" product bar is created.

THE SEVEN GRAPHS
----------------
1. Monthly Spending
2. Spending by Category
3. Spending by Store
4. Spending Share by Category
5. Top 10 Products by Spending
6. Monthly Spending by Store
7. Purchase Frequency by Category

LAYOUT
------
The visible Analytics sheet uses:

    A:O   large graph
    Q:W   numbered/color definition key
    Y:AG  detailed explanation

The dashboard extends vertically as necessary.

The hidden _AnalyticsData worksheet remains the chart-data source.

GRAPH LABELING
--------------
Descriptions such as full category/product/store names are deliberately kept
OUT of the graphs.

Examples:

    Doughnut slice label:
        4

    Key:
        [color] 4  Plant-Based Milk   $18.57 (8.0%)

Bar charts use numeric category labels.

Monthly Spending uses numeric month codes on the x-axis.

Monthly Spending by Store uses:
    numbered store series
    numbered months on the x-axis

The key explains both.

DATA RULES
----------
The existing reliable analytics rules are preserved:

- Purchase History is the source.
- Date N / Price N pairs are discovered dynamically.
- Analytics does not depend on the workbook Total formula.
- Invalid date/price pairs are skipped safely.
- Existing Analytics and _AnalyticsData sheets are rebuilt from scratch.
- Purchase History and Imported Receipts are not modified.
- _AnalyticsData remains hidden.
- Workbook saving remains atomic.

MENU
----
The existing DataBaseBuilder menu remains:

    1. Add Receipt to Purchase History
    2. Generate / Refresh Purchase Analytics
    0. Return to Main

No menu change is required for this update.

FILES
-----
FUNCTIONALLY REPLACED:

    utils/DataBaseBuilder/excel/purchase_analytics.py

INCLUDED AS MATCHING INTEGRATION FILES:

    utils/DataBaseBuilder/data_base_builder_main.py
    utils/DataBaseBuilder/excel/__init__.py

TEST
----
1. Extract the ZIP over the ShopGraph project root.
2. Run:

       python3 main.py

3. Go to:

       Utilities
       -> Data Base Builder
       -> 2. Generate / Refresh Purchase Analytics

4. Open:

       data/database/shopgraph_purchase_history.xlsx

5. Open the Analytics worksheet.

Verify:

- charts are stacked vertically;
- charts are much larger;
- the graph itself uses compact numbers rather than long descriptions;
- every graph has a numbered/color key on the right;
- every graph has a written explanation farther right;
- category-share does not create a large "Other" slice;
- each category has its own doughnut segment and numbered key entry;
- _AnalyticsData is hidden;
- Purchase History remains unchanged.
