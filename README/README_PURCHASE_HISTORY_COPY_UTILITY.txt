ShopGraph - Purchase History Copy Utility
=========================================

PURPOSE
-------
Adds a simple standalone utility that copies:

    data/database/shopgraph_purchase_history.xlsx

to:

    data/database/shopgraph_purchase_history copy.xlsx

Each run replaces the previous copy with the current live workbook.

Because this is a direct file copy, the entire XLSX workbook is copied,
including Purchase History, Category Manager, Analytics, Sub Analytics,
hidden sheets, formulas, formatting, and workbook metadata contained in
the source file.

MENU
----
Main -> Utilities -> Utilities

    8. Update Purchase History Copy

FILES
-----
NEW:
    utils/purchase_history_backup.py

UPDATED:
    utils/utils_main.py

DEPENDENCIES
------------
No new dependency is required. The utility uses Python's standard library.

SAFETY
------
The source workbook is never modified by this utility.
Only "shopgraph_purchase_history copy.xlsx" is created/replaced.
