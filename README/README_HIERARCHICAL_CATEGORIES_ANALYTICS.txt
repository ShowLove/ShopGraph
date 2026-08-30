ShopGraph Hierarchical Categories and Analytics

FINAL MODEL
-----------
Receipt/refinement:
    Product -> Common Name -> Sub-Category

Category Manager:
    Category -> Sub-Category -> Common Names

Sub Analytics:
    Purchase History -> Sub-Category -> detailed dashboard

Analytics:
    Purchase History + Category Manager -> Category -> broad dashboard

SUB ANALYTICS
-------------
The prior Analytics implementation is preserved as closely as practical and
renamed "Sub Analytics".

Its category-oriented charts are now:
- Spending by Sub-Category
- Spending Share by Sub-Category
- Purchase Frequency by Sub-Category

Monthly, store, product, key, explanation, accessible chart layout, and
no-"Other"-bucket behavior remain consistent with the existing dashboard.

ANALYTICS
---------
The new "Analytics" sheet provides the broad Category view using Category
Manager's Sub-Category -> Category mapping.

If Category Manager is missing or incomplete, ShopGraph still refreshes
Sub Analytics and reports why broad Analytics could not be refreshed.
A stale broad Analytics sheet is removed rather than left behind.

COMPATIBILITY
-------------
Internal receipt records may continue using the existing Python attribute name
"category" where changing it would add regression risk. User-facing detailed
classification is Sub-Category.

Stage-7 refined JSON now uses "Sub-Category"; the Data Base Builder loader also
accepts older refined JSON containing "Category".

The Purchase History TXT/CSV export needs no new broad Category field because
broad Category is not stored in Purchase History.
