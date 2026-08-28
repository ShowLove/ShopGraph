ShopGraph - Store-Specific Persistent Skip Rules
==================================================

BUILT AGAINST
-------------
shopgraph_codebase(20260828-192944).txt

PURPOSE
-------
Adds two options to the existing DataBaseBuilder line-review menu without
removing any existing capabilities or utilities:

    1. Accept Line
    2. Correct Columns
    3. Accept With NAs / Skip Corrections
    4. Skip Line
    5. Skip Term Forever
    6. Skip Sub-String Forever
    7. Finish Receipt
    8. Accept Remaining Lines
    0. Cancel Receipt Import

PRODUCT HIGHLIGHT
-----------------
The Product row in Proposed interpretation is visually separated:

    1. Total: "3.48"
    2. Store: "Walmart"
    3. Six-Digit SKU: "NA"
    --------------------------------
    4. Product: "Unavailable"
    --------------------------------
    5. Tax Code: "NA"
    ...

The Product field remains in exactly the same field order. Only the divider
lines are new.

SKIP TERM FOREVER
-----------------
Selecting:

    5. Skip Term Forever

stores the CURRENT Product as an exact, store-specific skip term.

Example:

    Store: Walmart
    Product: Unavailable

creates a Walmart rule for:

    Unavailable

From then on, a Walmart line whose Product is exactly "Unavailable"
(case-insensitive, with whitespace normalized) is automatically skipped.

The same Product at another store is NOT skipped unless that store has its own
rule.

SKIP SUB-STRING FOREVER
-----------------------
Selecting:

    6. Skip Sub-String Forever

opens an editable prompt pre-populated with the current Product.

Example current Product:

    Qty 1

The prompt begins with:

    Enter sub-string to skip forever: Qty 1

The user can edit that to:

    Qty

After saving, any future Walmart Product containing "Qty" is skipped, e.g.:

    Qty
    Qty 1
    Item Qty 2

The rule remains Walmart-specific.

CONFIG FILE
-----------
Rules are stored in:

    data/config/skip_terms.txt

Example:

    [STORE:Walmart]
    TERMS:
    Unavailable
    SUBSTRINGS:
    Qty

    [STORE:Publix]
    TERMS:
    Coupon
    SUBSTRINGS:
    Saving

The file is created automatically the first time the feature is used.

AUTO-SKIP DISPLAY
-----------------
Automatically skipped lines are still shown in the terminal, for example:

    [AUTO-SKIP] OCR Line 11 skipped.
    Store: "Walmart"
    Product: "Unavailable"
    Matched exact term: "Unavailable"

This keeps the behavior visible instead of silently dropping lines.

ACCEPT REMAINING LINES
----------------------
"Accept Remaining Lines" also respects persistent skip rules. A line matching
a store-specific term or substring is skipped instead of being bulk-accepted.

MATCHING RULES
--------------
Exact Terms:
    Product must equal the saved term after case/whitespace normalization.

Sub-Strings:
    Saved value may appear anywhere inside Product after case/whitespace
    normalization.

Both types are STORE-SPECIFIC.

NO OTHER WORKFLOW CHANGES
-------------------------
No capabilities or utilities are removed.
No OCR behavior is changed.
No analytics behavior is changed.
No Excel schema is changed.
The existing DataBaseBuilder correction, accept, skip, finish, and bulk-accept
flows remain in place.

FILES
-----
NEW:
    utils/DataBaseBuilder/skip_terms.py

REPLACED:
    utils/DataBaseBuilder/data_base_builder_main.py
    utils/DataBaseBuilder/parsers/base_parser.py

TEST
----
1. Run DataBaseBuilder and reach a Walmart line with:
       Product = Unavailable

2. Choose:
       5. Skip Term Forever

3. Confirm:
       data/config/skip_terms.txt
   now has:
       [STORE:Walmart]
       TERMS:
       Unavailable

4. Encounter another Walmart Product "Unavailable".
   Confirm it auto-skips and prints the skip reason.

5. Encounter Product "Unavailable" at another store.
   Confirm it is NOT auto-skipped.

6. On a Walmart Product like "Qty 1", choose:
       6. Skip Sub-String Forever

7. Edit the pre-populated value to:
       Qty

8. Confirm future Walmart Products containing Qty auto-skip.

9. Test Accept Remaining Lines and verify matching persistent rules are still
   skipped.
