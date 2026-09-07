SHOPGRAPH — DATA BASE BUILDER TEST MODE
===========================================

PURPOSE
-------
Adds a Test Mode to ShopGraph Data Base Builder without changing existing
production behavior.

DATA BASE BUILDER MENU
----------------------
1. Add Receipt to Purchase History
2. Generate / Refresh Purchase Analytics - Sub-Categories
3. Generate / Refresh Purchase Analytics - Categories
4. Category Manager
5. Budget Plans
6. Test Mode
0. Return to Main

TEST MODE MENU
--------------
1. Add Receipt to Purchase History - Test Mode
0. Return to Main Data Base Builder

TEST WORKBOOK
-------------
Test Mode writes Purchase History data to:

    data/exports/test_shopgraph_purchase_history.xlsx

IMPLEMENTATION
--------------
The normal Add Receipt to Purchase History workflow is reused directly.

The Purchase History workbook path is now a parameter with the existing
production workbook as its default:

    data/database/shopgraph_purchase_history.xlsx

Normal mode therefore behaves exactly as before.

Test Mode calls the same run_receipt_import() and commit_receipt() code path,
but passes:

    data/exports/test_shopgraph_purchase_history.xlsx

Duplicate-import checking also uses the selected workbook, so Test Mode tracks
its own Imported Receipts history independently from the production workbook.

If the test workbook does not yet exist, the existing Purchase History workbook
creation logic creates it automatically. If it already exists, subsequent Test
Mode imports append/update it using the same matching/history logic as normal
Purchase History.

No test workbook is shipped in this update ZIP.
