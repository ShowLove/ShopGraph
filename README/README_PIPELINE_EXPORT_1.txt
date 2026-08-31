ShopGraph - Pipeline Export 1 Update
====================================

MENU
----
The Pipelines menu is now:

    === ShopGraph Pipelines ===

    1. Pipeline Part 1
    2. Pipeline Export 1
    0. Return to Capabilities Menu

PIPELINE EXPORT 1
-----------------
Pipeline Export 1 uses ShopGraph's configured import location and creates:

    PipelineExports/Export_1/

inside that location if it does not already exist.

It exports:

    data/prompts/dev_prompts/
        shopgraph_common_name_subcategory_completion_prompt.txt

    data/database/
        shopgraph_purchase_history.txt

to:

    PipelineExports/Export_1/
        shopgraph_common_name_subcategory_completion_prompt.txt
        shopgraph_purchase_history.txt

Before copying shopgraph_purchase_history.txt, the existing ShopGraph Purchase
History TXT exporter is run so the TXT reflects the current Purchase History
workbook.

If either destination file already exists, it is overwritten.

The source files remain in the ShopGraph project. "Export" means copy to the
external PipelineExports folder; it does not delete or relocate ShopGraph's
working files.

PIPELINE PART 1
---------------
After Pipeline Part 1 successfully finishes OCR + Data Base Builder, it now
automatically runs Pipeline Export 1 as its final step.

Therefore:

    Pipeline Part 1
        -> OCR / Data Base Builder
        -> Pipeline Export 1
        -> latest prompt + latest Purchase History TXT in Export_1

CONFIGURATION
-------------
The destination root is the same import location returned by ShopGraph's
existing get_import_location() configuration logic.

No runtime config file is included in this update ZIP.

FILES
-----
UPDATED:
    capabilities/pipelines.py

NEW:
    README/README_PIPELINE_EXPORT_1.txt

No new dependency is required.
