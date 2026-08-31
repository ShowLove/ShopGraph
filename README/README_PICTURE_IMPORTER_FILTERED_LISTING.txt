ShopGraph - Picture Importer Filtered Listing Update
===================================================

PURPOSE
-------
Refines the existing Picture Importer so the selection menu shows ONLY picture
files that ShopGraph's receipt/OCR workflow supports.

Non-picture files in the configured import directory are silently ignored and
never appear as numbered choices.

SUPPORTED FORMATS
-----------------
The utility no longer maintains its own independent extension list.

Instead, it imports:

    SUPPORTED_IMAGE_SUFFIXES

directly from:

    capabilities/OCRAcquisitionPipeline/receipt_picker.py

Therefore the Picture Importer stays synchronized with the receipt picker.

At the time of this update ShopGraph accepts:

    .jpg
    .jpeg
    .png
    .heic
    .webp
    .tif
    .tiff

VALIDATION
----------
A file must pass BOTH checks before it appears in the menu:

1. Its extension must be in ShopGraph's SUPPORTED_IMAGE_SUFFIXES.
2. Its binary file signature must match the corresponding image format.

For example:

    receipt.jpg       -> shown if it is really a JPEG
    receipt.png       -> shown if it is really a PNG
    notes.txt         -> ignored
    update.zip        -> ignored
    spreadsheet.xlsx  -> ignored
    fake.jpg          -> ignored if it is not actually a JPEG

This means invalid files are filtered out before the user chooses anything,
rather than being displayed and rejected afterward.

MENU
----
The existing menu remains unchanged:

    === ShopGraph Picture Importer ===

    1. Import Picture
    2. Change Default Import Location
    0. Return to Utilities

DESTINATION
-----------
Selected pictures are still copied to:

    data/current_pic/

The original source file is never moved or deleted.

FILES
-----
UPDATED:
    utils/picture_importer.py

No runtime config files are included.
No other ShopGraph behavior is changed.

DEPENDENCIES
------------
No new dependency is required.
