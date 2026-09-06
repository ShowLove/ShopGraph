ShopGraph - HEIC / HEIF Image Support
========================================

PURPOSE
-------
Adds working HEIC/HEIF receipt-image support to ShopGraph.

ShopGraph already listed .heic as a selectable image type, but the first OCR
image-processing stage used cv2.imread() directly. Standard OpenCV builds often
cannot decode Apple's HEIC/HEIF format, so the file could be selected/imported
but processing failed when receipt cropping began.

IMPLEMENTATION
--------------
This update uses a central image loader:

    capabilities/OCRAcquisitionPipeline/image_loader.py

Normal image formats still use OpenCV exactly as before:

    JPG / JPEG
    PNG
    WEBP
    TIFF

HEIC and HEIF use:

    Pillow + pillow-heif

The image is decoded directly into memory, EXIF orientation is applied, then
the RGB image is converted to an OpenCV-compatible BGR array.

This is preferable to permanently converting every HEIC to JPG because:

    - no extra lossy JPEG recompression is introduced;
    - the original HEIC remains intact;
    - no duplicate source image needs to be managed;
    - downstream ShopGraph behavior remains unchanged;
    - the receipt crop stage already writes a PNG, so after source ingestion
      the rest of the OCR pipeline continues using its existing PNG workflow.

SUPPORTED SOURCE SUFFIXES
-------------------------
    .jpg
    .jpeg
    .png
    .heic
    .heif
    .webp
    .tif
    .tiff

DEPENDENCY
----------
Added:

    pillow-heif

to:

    data/requirements.txt

After importing this ShopGraph code update, install/update requirements:

    pip install -r data/requirements.txt

FILES
-----
NEW:
    capabilities/OCRAcquisitionPipeline/image_loader.py
    README/README_HEIC_IMAGE_SUPPORT.txt

UPDATED:
    capabilities/OCRAcquisitionPipeline/reliable_receipt_crop.py
    capabilities/OCRAcquisitionPipeline/receipt_picker.py
    utils/picture_importer.py
    data/requirements.txt

UNCHANGED
---------
No OCR logic, crop detection algorithm, perspective correction, image
normalization, OCR variants, database logic, menus, pipelines, backup logic,
analytics, or budget behavior was removed or redesigned.
