ShopGraph - Receipt-Level Contributions Update

PURPOSE
Adds a receipt-level Contribution concept without changing the Purchase History column schema and without adding any AI prompt.

BEHAVIOR
- After receipt item review, Data Base Builder asks:
    Did someone else contribute toward the total receipt? [y/N]
- No/blank preserves the existing workflow.
- Yes asks for one positive contribution amount.
- ShopGraph stores the contribution as a negative Purchase History observation:
    Product: Contribution
    Common Name: Contribution
    Sub-Category: Contributions
    Price: negative contribution amount
    Store / Store Number / Date: inherited from the confirmed receipt metadata
- The contribution is receipt-level only. It is not allocated to individual items.
- Normal merchandise price validation is unchanged and still rejects negative prices.
- Contribution rows use the existing Date N / Price N history structure.
- Contribution identity additionally checks Store so different stores with Store Number=NA do not collapse into one history row.
- Category Manager has a deterministic built-in default:
    Contributions -> Adjustments
  Existing user-authored Category Manager mappings remain authoritative.
- Purchase Analytics accepts negative observations so Contributions reduce net spending totals.
- Budget Plan analytics reuses Purchase Analytics observations, so all-category plans naturally include Contributions; category-scoped plans include them only when Adjustments is in scope.
- No new AI prompt is added.
- No Purchase History schema migration is added.

FILES CHANGED
utils/DataBaseBuilder/data_base_builder_main.py
utils/DataBaseBuilder/excel/purchase_history.py
utils/DataBaseBuilder/excel/category_manager.py
utils/DataBaseBuilder/excel/purchase_analytics.py

INSTALL
Use ShopGraph's existing Code Update Importer / overlay workflow, or replace the four files while preserving the directory structure.

RECOMMENDED FIRST USE
1. Import this overlay.
2. Add a receipt normally.
3. At the new contribution question, answer y and enter an amount such as 50.00.
4. Refresh Category Manager once so Contributions appears as Adjustments.
5. Apply Category Manager / run the normal taxonomy pipeline as usual.
6. Refresh Analytics/Budget Plans normally.
