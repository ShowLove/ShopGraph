ShopGraph - Category Manager
============================

PURPOSE
-------
Category Manager gives the user direct control over the Common Name -> Category
taxonomy used by Purchase History and therefore by ShopGraph's category-based
Analytics.

MENU
----
Data Base Builder now contains:

    1. Add Receipt to Purchase History
    2. Generate / Refresh Purchase Analytics
    3. Category Manager
    0. Return to Main

Category Manager contains:

    1. Create / Refresh Category Manager
    2. Apply Category Manager to Purchase History
    0. Return to Data Base Builder

CREATE / REFRESH
----------------
Create / Refresh treats Purchase History as authoritative and completely
rebuilds the "Category Manager" worksheet from the CURRENT Purchase History.

Column A contains one category per row. Starting in column B, every unique
Common Name assigned to that category is written across the row.

Example:

    Category      Product 1      Product 2      Product 3
    Fresh Fruit   Bananas        Apples         Kiwi
    Yogurt        Chobani        YoBaby

Create / Refresh may destroy unapplied manual edits in Category Manager. This
is intentional. Newly imported Common Names automatically appear the next time
Create / Refresh is run.

COMMON NAME IDENTITY
--------------------
Category Manager uses Common Name as its product identity. Raw Product text is
not used for category assignment.

Do not rename Common Names in Category Manager. If "Bananas" is changed to
"Banana", Apply treats that as one missing known Common Name and one unknown
Common Name and refuses to update Purchase History.

MANUAL EDITING
--------------
The user may:

- move Common Names between categories;
- reorder products;
- reorder category rows;
- rename categories;
- create new categories;
- eliminate old categories after moving their products;
- leave blank cells between products;
- place products in different product columns.

Blank cells, product order, category order, and original product column position
do not matter.

EXACT-ONCE ACCOUNTING
---------------------
Before Apply may change Purchase History, every unique valid Common Name in
Purchase History must appear exactly once in Category Manager and belong to one
nonblank category.

Apply detects:

- missing Common Names;
- duplicate Common Names;
- unknown Common Names;
- products under blank categories;
- duplicate category rows;
- blank/NA Purchase History Common Names;
- conflicting Purchase History categories for the same Common Name;
- malformed required worksheet structure.

If validation fails, Purchase History is not modified, the workbook is not
saved, and Category Manager is not cleaned/rebuilt.

APPLY
-----
After successful validation, Apply builds:

    Common Name -> Category

and updates ONLY the Category column in Purchase History.

It does not recreate Purchase History and does not alter Store, SKU, Product,
Tax Code, Store Number, Common Name, Total formulas, Date N / Price N history,
Imported Receipts, Analytics, or other unrelated workbook data.

If the same Common Name appears on multiple Purchase History rows, every row is
assigned the selected Category.

CATEGORY MANAGER CLEANUP
------------------------
After a successful Apply, Category Manager is rebuilt from the newly applied
mapping. Each category has one row, Common Names are contiguous beginning in
column B, empty rows/gaps are removed, and formatting is restored.

DATA SAFETY
-----------
Category Manager uses a verified atomic-save process:

1. Load workbook.
2. Parse Purchase History and Category Manager.
3. Validate everything.
4. On any validation failure: modify nothing and save nothing.
5. On success: change only Category values in memory.
6. Rebuild Category Manager in memory.
7. Save to a temporary XLSX.
8. Reopen the temporary XLSX and verify required worksheets exist.
9. Atomically replace the original workbook only after verification succeeds.

This version intentionally does NOT create audit backups, timestamped backups,
version history, or backup-retention files.

ANALYTICS
---------
Analytics continues to read Category from Purchase History exactly as before.
After a successful Apply, run the existing:

    Generate / Refresh Purchase Analytics

to rebuild Analytics using the new taxonomy.

FILES
-----
NEW:
    utils/DataBaseBuilder/excel/category_manager.py
    README/README_CATEGORY_MANAGER.txt

UPDATED:
    utils/DataBaseBuilder/data_base_builder_main.py
    utils/DataBaseBuilder/excel/__init__.py
