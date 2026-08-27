ShopGraph - Stage 7 Refined JSON + DataBaseBuilder Integration
==================================================================

BUILT AGAINST
-------------
shopgraph_codebase(20260827-195849).txt

NEW OCR STAGE
-------------
The OCR Acquisition Pipeline now has seven stages:

1. Reliable Receipt Detection / Crop
2. Perspective Correction
3. Receipt Size Normalization
4. Generate OCR Image Variants
5. Run Multi-Variant / Multi-PSM OCR
6. Compare OCR Results / Build Raw OCR JSON
7. Refine Json File

The complete OCR Acquisition Pipeline automatically runs Stage 7.

STAGE 7 OUTPUT
--------------
Input:
    data/raw_ocr/<receipt>_raw_ocr.json

Output:
    data/refined_json/<receipt>_refined.json

Every Stage-6 line_number receives one refined line object. No input line is
discarded.

Each refined line contains:
    Total
    Store
    Six-Digit SKU
    Product
    Tax Code
    Store Number
    Common Name
    Category
    Date 1
    Price 1

Missing/not-applicable values are "NA".

For human review, Product remains the best editable line-level guess even for
non-purchase lines. Example:

    source_text: ALDI
    Product: ALDI

DATABASEBUILDER INTEGRATION
---------------------------
When DataBaseBuilder opens a raw OCR receipt, it automatically looks for the
matching refined JSON.

If the refined file is valid:
    refined guess > parser guess

However, values explicitly confirmed by the user during the current import
(Store selection, Store Number, Receipt Date, and later Correct Columns edits)
remain authoritative.

If refined JSON is missing or invalid, DataBaseBuilder falls back to its
existing store-specific parsers.

PRE-POPULATED CORRECTIONS
-------------------------
The existing readline behavior is preserved.

Example:

    Current Product: ALDI
    Enter corrected Product: ALDI

The second ALDI is already editable in the terminal input buffer. Press Enter
to keep it, edit it, or replace it.

COMMON NAME / CATEGORY
----------------------
Stage 7 can conservatively infer Common Name and Category. It may also use an
existing shopgraph_purchase_history.xlsx as supporting evidence for known
same-store products/SKUs.

Historical prices and dates are NEVER copied into the current receipt.

EXCEL
-----
Accepted/corrected records now feed:
    Store
    Six-Digit SKU
    Product
    Tax Code
    Store Number
    Common Name
    Category
    Date 1
    Price 1

The workbook Total column remains its existing formula that sums Price 1,
Price 2, Price 3, etc. The record-level Total is used for review/refined JSON,
but does not replace the workbook formula.

FILES ADDED
-----------
capabilities/OCRAcquisitionPipeline/refine_json.py
utils/DataBaseBuilder/refined_json_loader.py

IMPORTANT FILES REPLACED
------------------------
capabilities/OCRAcquisitionPipeline/constants.py
capabilities/OCRAcquisitionPipeline/session_state.py
capabilities/OCRAcquisitionPipeline/main_OCRAcquisitionPipeline.py
utils/constants.py
utils/utils_main.py
utils/clean_ocr_acquisition_pipeline.py
utils/DataBaseBuilder/purchase_record.py
utils/DataBaseBuilder/data_base_builder_main.py
utils/DataBaseBuilder/benchmark_writer.py
utils/DataBaseBuilder/parsers/base_parser.py
utils/DataBaseBuilder/parsers/aldi_parser.py
utils/DataBaseBuilder/parsers/publix_parser.py
utils/DataBaseBuilder/parsers/trader_joes_parser.py
utils/DataBaseBuilder/parsers/other_parser.py
utils/DataBaseBuilder/excel/purchase_history.py

TEST
----
1. Run:
       python3 main.py

2. Run the complete OCR Acquisition Pipeline.
   Confirm Stage 7 creates:
       data/refined_json/<receipt>_refined.json

3. Open:
       Utilities -> Data Base Builder -> Add Receipt to Purchase History

4. Select the matching raw OCR JSON.
   DataBaseBuilder should print that refined JSON was loaded.

5. For an ALDI header line, verify the proposal can show Product = ALDI.

6. Choose:
       2. Correct Columns
   Select Product.
   Verify:
       Current Product: ALDI
       Enter corrected Product: ALDI

7. Press Enter and verify the value is retained.

8. Test a purchase item and confirm refined Common Name / Category / Price
   guesses are presented and editable.

9. Accept selected purchase lines and verify the workbook writes the corrected
   Common Name and Category while retaining the existing Total formula behavior.
