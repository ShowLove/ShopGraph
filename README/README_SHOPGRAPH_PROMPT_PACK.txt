ShopGraph Prompt Pack
=====================

This update adds two reusable prompts under:

    data/prompts/dev_prompts/

1. shopgraph_common_name_subcategory_completion_prompt.txt
   Analyzes the Purchase History CSV TXT export, preserves every existing
   Common Name and Sub-Category, and proposes values only for missing rows.
   Output is organized into safe Excel H:I copy/paste blocks.

2. shopgraph_code_update_zip_output_prompt.txt
   Tells ChatGPT how ShopGraph code updates must be packaged so they can be
   installed by the ShopGraph Code Update Importer.

No Python code is changed by this ZIP.
No dependency installation is required.

This ZIP is intentionally formatted as a normal ShopGraph project-relative
overlay so it can also be used to test the Code Update Importer.
