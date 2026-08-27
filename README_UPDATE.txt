ShopGraph - Safe Missing-Row Recovery + Numeric Refinement
===========================================================

This package is built against the attached 20260827-191453 codebase.

NEW FILE
--------
capabilities/OCRAcquisitionPipeline/refine_consensus.py

CHANGED FILE
------------
capabilities/OCRAcquisitionPipeline/compare_ocr.py

The other included Python files are matching copies from the attached codebase.

WHAT IT TRIES
-------------
1. Safe missing-row recovery:
   - at least 3 independent full-receipt candidates
   - same narrow y-position
   - repeated description
   - plus repeated exact SKU or repeated exact price
   - existing conservative rows are NOT loosened

2. Numeric token refinement:
   - OCRs a narrow right-side row strip
   - 3x enlargement
   - PSM 7 and PSM 13
   - numeric/currency whitelist
   - replaces an existing price only if alternate evidence materially wins

3. Adds diagnostics:
   - recovered_missing_row_count
   - numeric_refinement_count

INSTALL
-------
Extract over the ShopGraph project root.

No new dependency is required: Pillow and pytesseract are already in use.

TEST
----
Run the same three receipts normally, then run:
Utilities -> Utilities -> Evaluate OCR Against Benchmarks

Watch specifically for:
- IMG_0251: recovery of the missing Zucchini row
- IMG_0253: whether 7.89/9.89 improve only with strong numeric evidence
- IMG_0255: preserve all six product rows/prices without metadata contamination
