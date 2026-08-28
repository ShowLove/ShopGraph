ShopGraph - PDF to JPG Utility
==================================

PURPOSE
-------
Adds a new standalone utility to ShopGraph that converts PDF files from:

    data/pdf_files/

into JPG images in:

    data/current_pic/

The menu flow remains:

    === ShopGraph ===
    1. Utilities

    === ShopGraph Utilities ===
    3. Utilities

    === ShopGraph Utilities ===
    1. Export Clean Codebase
    2. Clean OCR Acquisition Pipeline Data
    3. Evaluate OCR Against Benchmarks
    4. Convert PDF Files to JPG
    0. Return to Utilities Menu

USER FLOW
---------
After selecting:

    4. Convert PDF Files to JPG

ShopGraph lists every PDF in data/pdf_files.

The user may enter:

    A
        Convert every PDF.

    N
        Convert the first N PDFs in the displayed list.

    1,3,5
        Convert specific PDF numbers.

    0
        Cancel.

OUTPUT
------
Single-page PDF:

    receipt.pdf
        ->
    data/current_pic/receipt.jpg

Multi-page PDF:

    receipt.pdf
        ->
    data/current_pic/receipt_page_001.jpg
    data/current_pic/receipt_page_002.jpg
    data/current_pic/receipt_page_003.jpg
    ...

QUALITY
-------
Conversion uses:

    300 DPI
    JPEG quality 95

300 DPI is intentionally chosen because these images are expected to feed the
existing receipt/OCR workflow.

EXISTING FILES
--------------
If the generated JPG filename already exists, it is replaced with the newly
converted page. The source PDF is never modified or deleted.

DEPENDENCY
----------
Adds:

    PyMuPDF

to:

    data/requirements.txt

After installing/replacing this update, if PyMuPDF is not already installed:

    pip install -r data/requirements.txt

or:

    pip install PyMuPDF

FILES ADDED / REPLACED
----------------------
NEW:
    utils/pdf_to_jpg.py

REPLACED:
    utils/utils_main.py
    utils/constants.py
    data/requirements.txt

TEST
----
1. Place one or more PDF files in:

       data/pdf_files/

2. Run:

       python3 main.py

3. Select:

       1. Utilities
       3. Utilities
       4. Convert PDF Files to JPG

4. Try:
       A
   or:
       2
   or:
       1,3

5. Verify JPG images are created in:

       data/current_pic/

6. Run the normal OCR Acquisition Pipeline on one of the resulting images.
