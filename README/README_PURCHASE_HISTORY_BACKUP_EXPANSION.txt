ShopGraph - Expanded Purchase History Backup Menu
=================================================

PURPOSE
-------
Expands the existing:

    Utilities
        -> 8. Update Purchase History Copy

submenu into a fuller Purchase History backup/archive manager.

The top-level Utilities option remains unchanged.

MENU
----
The Purchase History Backup menu is now:

    1. Update Purchase History Copy
    2. Restore Purchase History from Copy
    3. Update Purchase History Archive
    4. Update Purchase History Archive with Date
    5. Restore Purchase History from Archive
    6. Delete Purchase History
    7. Update all from Purchase History
    0. Return to Utilities

OPTIONS 1-3
-----------
Options 1 and 2 preserve their existing behavior.

Option 3 is only renamed from:

    Store Purchase History Archive

to:

    Update Purchase History Archive

Its underlying store_purchase_history_archive() behavior is unchanged:

    - the newest normal archive remains:
        data/database/archive/shopgraph_purchase_history.xlsx

    - if that file already exists, it is first preserved under the existing
      timestamp naming behavior;

    - the live workbook is copied into the normal archive path.

OPTION 4 - DATED ARCHIVE
------------------------
Creates a separate dated archive.

The user may:

    - press Enter to use the current date; or
    - enter a chosen date using:
        YYYY-MM-DD
        MM/DD/YYYY

Normal dated filename:

    shopgraph_purchase_history_YYYY-MM-DD.xlsx

If a dated file with the same name already exists, a time suffix is added so
an existing dated snapshot is not silently overwritten.

This option does NOT change the normal Option 3 archive.

OPTION 5 - RESTORE FROM ARCHIVE
-------------------------------
Lists available Purchase History .xlsx archives in:

    data/database/archive/

The user chooses the archive to restore.

Before the selected archive replaces the live Purchase History workbook,
ShopGraph asks for confirmation.

OPTION 6 - DELETE PURCHASE HISTORY
----------------------------------
Opens:

    1. Delete Purchase History Copy
    2. Delete Purchase History Archive
    0. Return to Purchase History Backup

Delete Purchase History Copy:
    Deletes only:
        data/database/shopgraph_purchase_history copy.xlsx

Delete Purchase History Archive:
    Lists existing archive files and lets the user choose exactly one archive
    to delete.

Both delete operations require confirmation.

The live Purchase History workbook is NOT an option in this Delete submenu.

OPTION 7 - UPDATE ALL
---------------------
Runs, in order:

    1. Update Purchase History Copy
    2. Update Purchase History Archive

It reuses the same underlying functions as menu Options 1 and 3.

If the copy update fails, the archive update does not run.

If the copy succeeds but the archive update fails, ShopGraph reports the
partial success clearly.

COMPATIBILITY
-------------
The existing reusable function:

    update_purchase_history_copy()

is preserved unchanged for Pipeline Part 1 and any other existing imports.

The existing functions:

    restore_purchase_history_from_copy()
    store_purchase_history_archive()

are also retained.

No existing Pipeline, Database Builder, OCR, Analytics, Category Manager,
Budget Plan, or Utilities functionality is removed.

FILES
-----
UPDATED:
    utils/purchase_history_backup.py

NEW:
    README/README_PURCHASE_HISTORY_BACKUP_EXPANSION.txt

No runtime database, archive, copy, config, or generated files are packaged.
