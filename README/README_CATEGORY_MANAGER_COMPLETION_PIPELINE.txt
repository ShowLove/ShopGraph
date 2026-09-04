ShopGraph - Category Manager Completion Pipeline
================================================

PURPOSE
-------
Adds the second ShopGraph taxonomy-completion stage:

    Common Name
        -> Sub-Category
        -> Category

This update preserves the existing Common Name/Sub-Category workflow and adds
a separate broad-Category completion workflow.

UTILITIES
---------
The standalone Utilities menu now includes:

    10. Export Category Manager as CSV TXT

It exports the live "Category Manager" worksheet from:

    data/database/shopgraph_purchase_history.xlsx

to:

    data/database/shopgraph_category_manager.txt

PIPELINES
---------
The Pipelines menu becomes:

    1. Pipeline Part 1
    2. Pipeline Export 1
    3. Category Manager Completion
    4. Pipeline Export 2
    0. Return to Capabilities Menu

Category Manager Completion runs:

    1. Create / Refresh Category Manager
    2. Pipeline Export 2

The existing reusable Category Manager create/refresh function is used
directly. If Category Manager refresh fails, Export_2 is not created.

PIPELINE EXPORT 2
-----------------
Pipeline Export 2 uses the same configured import location as Pipeline Export 1
and creates:

    PipelineExports/Export_2/

containing:

    shopgraph_category_manager.txt
    shopgraph_category_completion_prompt.txt
    shopgraph_purchase_history.txt

Both TXT exports are refreshed from the live workbook immediately before being
copied to Export_2. Existing destination files are overwritten.

NEW PROMPT
----------
Added:

    data/prompts/dev_prompts/shopgraph_category_completion_prompt.txt

The prompt analyzes ONLY Category Manager rows where:

    Category = NA

Existing non-NA Category assignments are authoritative and are never targets
for modification. Purchase History is used as supporting evidence.

COMPATIBILITY / PRESERVATION
----------------------------
Existing functionality is retained, including:

    Pipeline Part 1
    Pipeline Export 1
    Category Manager menu
    Apply Category Manager to Purchase History
    Purchase History TXT export
    OCR workflows
    Analytics
    Budget Plans
    Picture Importer
    Code Update Importer
    global -1 exit behavior

FILES
-----
NEW:
    utils/export_category_manager_txt.py
    data/prompts/dev_prompts/shopgraph_category_completion_prompt.txt
    README/README_CATEGORY_MANAGER_COMPLETION_PIPELINE.txt

UPDATED:
    capabilities/pipelines.py
    utils/utils_main.py

No runtime database, runtime config, archive, or PipelineExports files are
included in this update.
