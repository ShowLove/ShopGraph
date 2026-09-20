SHOPGRAPH UPDATE: PURCHASE HISTORY LATEST-DATE SORT
==================================================

Purpose
-------
Adds one explicit action to the existing Data Base Builder menu:

    7. Sort Purchase History by Latest Date

Behavior
--------
- Sorts only the Purchase History worksheet rows.
- Determines each product row's newest valid Date N value across Date 1, Date 2, etc.
- Places oldest product histories at the top and newest product histories at the bottom.
- Rows without a valid Date N remain at the top.
- Rows sharing the same newest date retain their existing relative order.
- Preserves the complete row, including all product identity fields, Date/Price history, formatting,
  comments, hyperlinks, and row height.
- Rebuilds ShopGraph's Total formula after rows move so the formula references the new row number.
- Uses the existing atomic workbook save path.
- Does NOT change normal receipt import behavior, product matching, history appending, Category Manager,
  analytics, Budget Plans, receipt acquisition, or test mode.

Files replaced
--------------
utils/DataBaseBuilder/data_base_builder_main.py
utils/DataBaseBuilder/excel/purchase_history.py

Installation
------------
Use ShopGraph's existing Code Update Importer and select this ZIP.
