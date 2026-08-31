ShopGraph - Picture Importer Utility
=========================================

PURPOSE
-------
Adds a standalone utility that copies a user-selected picture from ShopGraph's
configured import folder into:

    data/current_pic/

The utility uses the SAME import location already used by the Code Update ZIP
Importer.

Current ShopGraph config behavior is preserved:
- legacy setting: utils/config.txt
- current runtime setting: utils/config/settings.txt
- key: code_update_import_location

The existing Code Update Importer already reads the legacy file first and the
current runtime settings second, so existing installations continue to work.

MENU
----
Main -> Utilities -> Utilities

    9. Import Picture to Current Folder

Submenu:

    === ShopGraph Picture Importer ===

    1. Import Picture
    2. Change Default Import Location
    0. Return to Utilities

IMPORT FLOW
-----------
1. ShopGraph reads the configured import location.
2. Every normal file in that directory is listed, newest first.
3. The user selects one file.
4. ShopGraph validates that the selected file is actually a supported image.
5. If valid, the file is copied into data/current_pic/.
6. The original source file is never moved or deleted.

IMAGE VALIDATION
----------------
Supported image types:

    JPG / JPEG
    PNG
    GIF
    BMP
    TIFF
    WEBP

Validation checks BOTH:
- the filename extension; and
- the file's binary image signature.

This means a non-picture file renamed to something such as fake.jpg is rejected.

If the selected item is not a supported picture, ShopGraph reports an error and
does not copy it.

EXISTING DESTINATION FILE
-------------------------
If data/current_pic/ already contains a file with the same name, ShopGraph asks
before replacing it.

IMPORT LOCATION
---------------
Option 2 uses ShopGraph's existing shared import-location setting. Changing it
also changes where the Code Update ZIP Importer looks, because both utilities
intentionally use the same configured import directory.

FILES
-----
NEW:
    utils/picture_importer.py
    README/README_PICTURE_IMPORTER.txt

UPDATED:
    utils/utils_main.py

No runtime config file is included in this update ZIP.

DEPENDENCIES
------------
No new package installation is required. The utility uses Python's standard
library only.

INSTALL
-------
Install this ZIP with ShopGraph's existing:

    Utilities -> Import Code Update ZIP

Then restart ShopGraph so the updated menu/module imports are loaded.
