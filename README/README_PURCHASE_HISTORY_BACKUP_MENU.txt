ShopGraph - Purchase History Backup Menu Update
================================================

The standalone Utilities menu keeps:

    8. Update Purchase History Copy

Selecting option 8 now opens:

    === ShopGraph Purchase History Backup ===

    1. Update Purchase History Copy
    2. Restore Purchase History from Copy
    3. Store Purchase History Archive
    0. Return to Utilities

OPTION 1
--------
Copies:

    data/database/shopgraph_purchase_history.xlsx

to:

    data/database/shopgraph_purchase_history copy.xlsx

The destination copy is overwritten with the current live workbook.

OPTION 2
--------
Copies:

    data/database/shopgraph_purchase_history copy.xlsx

back to:

    data/database/shopgraph_purchase_history.xlsx

The live Purchase History workbook is therefore restored from the saved copy.

OPTION 3
--------
Copies the current live workbook into:

    data/database/archive/shopgraph_purchase_history.xlsx

The archive directory is created automatically if necessary.

Archive safety:
If archive/shopgraph_purchase_history.xlsx already exists, the previous archive
is first renamed with a timestamp and preserved. The newest archive always has:

    archive/shopgraph_purchase_history.xlsx

This avoids silently destroying the previous archive while keeping the exact
current archive path requested.

PIPELINE COMPATIBILITY
----------------------
The existing update_purchase_history_copy() function is retained unchanged in
purpose, so Pipeline Part 1 can continue making its automatic Purchase History
copy without opening this submenu.

FILES
-----
UPDATED:
    utils/purchase_history_backup.py
    utils/utils_main.py

NEW:
    README/README_PURCHASE_HISTORY_BACKUP_MENU.txt

No database workbook, runtime config file, or archive file is included.
No new dependency is required.
