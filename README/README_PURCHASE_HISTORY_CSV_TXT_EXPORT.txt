ShopGraph - Purchase History CSV TXT Export
==========================================

PURPOSE

Adds a new standalone utility that converts:

    data/database/shopgraph_purchase_history.xlsx

to:

    data/database/shopgraph_purchase_history.txt

The output is a normal UTF-8 text file containing standard CSV-formatted data.

MENU

The existing ShopGraph Utilities menu becomes:

    1. Export Clean Codebase
    2. Clean Generated Processing Data
    3. Evaluate OCR Against Benchmarks
    4. Convert PDF Files to JPG
    5. Clean Source Data
    6. Export Purchase History as CSV TXT
    0. Return to Utilities Menu

No existing utility or capability is removed.

EXPORT RULES

- Reads only the "Purchase History" worksheet.
- Does not export Analytics.
- Does not export Imported Receipts.
- Preserves row/column order.
- Uses commas as separators.
- Uses standard CSV quoting and escaping.
- Writes UTF-8 text.
- Writes one spreadsheet row per text line.
- Overwrites the previous shopgraph_purchase_history.txt each time.

FORMULAS

The workbook is opened with data_only=False.

This means formula cells are preserved as formula text rather than becoming
blank if openpyxl does not have a cached Excel-calculated value.

FILES

NEW:
    utils/export_purchase_history_txt.py

UPDATED:
    utils/utils_main.py

No new dependency is required. ShopGraph already uses openpyxl.
