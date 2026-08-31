ShopGraph - Pipelines / Pipeline Part 1
=========================================

PURPOSE
-------
Adds a new higher-level Capabilities entry:

    5. Pipelines

Current submenu:

    === ShopGraph Pipelines ===

    1. Pipeline Part 1
    0. Return to Capabilities Menu

PIPELINE PART 1
---------------
Pipeline Part 1 automates the manual workflow that previously required moving
between Utilities and Capabilities menus.

It performs, in order:

1. Clean Generated Processing Data
   - Uses ShopGraph's existing non-interactive generated-data cleanup logic.
   - Preserves database, benchmarks, PDFs, prompts, and other persistent data.

2. Clean Current Receipt Images
   - Clears only data/current_pic/.
   - No confirmation prompt is shown inside the Pipeline.

3. Import Picture
   - Uses the existing configured import folder.
   - Shows only supported/validated pictures.
   - The user chooses the receipt picture.
   - The picture is copied to data/current_pic/.

4. Save / Re-read Selected Picture
   - The selected picture filename is saved under:

         utils/config.txt

     using:

         selected_picture_filename=<filename>

   - Existing values already in utils/config.txt are preserved.
   - The Pipeline deliberately re-reads this saved value before starting OCR.

5. Update Purchase History Copy
   - Runs the same underlying copy operation as:

         Utilities -> 8. Update Purchase History Copy

   - If the backup fails, the Pipeline STOPS before OCR/Data Base Builder.

6. OCR Acquisition Pipeline + Data Base Builder
   - Equivalent to existing Capability 3.
   - Uses the saved picture directly, so the normal receipt-image selection
     prompt is skipped.
   - Runs OCR Stages 1-7.
   - Continues directly into Data Base Builder for the resulting raw OCR file.

PROMPTING
---------
The goal is minimal prompting.

Pipeline Part 1 does NOT ask the user to:
- separately open Clean Generated Processing Data;
- separately confirm Current Receipt Images deletion;
- separately open Update Purchase History Copy;
- choose the receipt again inside OCR Acquisition Pipeline;
- separately choose Capability 3.

The unavoidable picture-choice prompt remains.

Normal Data Base Builder review/correction prompts remain unchanged because
those prompts are part of the actual receipt review workflow.

MENU
----
The Capabilities menu becomes:

    === ShopGraph Capabilities ===

    1. OCR Acquisition Pipeline
    2. OCR Acquisition Pipeline - All Images
    3. OCR Acquisition Pipeline + Data Base Builder
    4. OCR Acquisition Pipeline - All Images + Data Base Builder
    5. Pipelines
    0. Return to Utilities Menu

CONFIG SAFETY
-------------
No utils/config.txt file is shipped in this update ZIP.

At runtime, Picture Importer updates only the selected_picture_filename key in
utils/config.txt while preserving other existing legacy settings.

FILES
-----
NEW:
    capabilities/pipelines.py
    README/README_PIPELINES_PART_1.txt

UPDATED:
    capabilities/OCRAcquisitionPipeline/main_OCRAcquisitionPipeline.py
    utils/clean_source_data.py
    utils/picture_importer.py
    utils/utils_main.py

DEPENDENCIES
------------
No new dependency is introduced by this update.

INSTALL
-------
Install through ShopGraph's existing Code Update Importer and restart ShopGraph.
