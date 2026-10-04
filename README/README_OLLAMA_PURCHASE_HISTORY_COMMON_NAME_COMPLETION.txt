ShopGraph - Ollama Purchase History Blank/NA Common Name Completion
==================================================================

PURPOSE
Adds a local Ollama-assisted repair step between Pipeline Export 1 and Category Manager Completion. It repairs only populated Purchase History rows whose Common Name is blank or NA.

PIPELINE
1. Pipeline Part 1
2. Pipeline Part 1 - Ollama Receipt Acquisition
3. Pipeline Export 1
4. Ollama Purchase History Blank/NA Completion
5. Category Manager Completion
6. Pipeline Export 2
7. Finalize Taxonomy + Budgets

BEHAVIOR
- Uses the live data/database/shopgraph_purchase_history.xlsx workbook.
- Shares Category Manager's missing-Common-Name row definition.
- First reuses an exact Product -> Common Name mapping when historical data has exactly one unambiguous value.
- Sends remaining rows to the existing local Ollama text JSON helper in batches of 25.
- Provides compact existing Product -> Common Name examples as normalization context.
- Requires strict JSON and validates requested row coverage, duplicates, row IDs, values, and current target state.
- Writes only Common Name cells.
- Existing nonblank Common Names remain authoritative and are never overwritten.
- Ollama may return NA for uncertainty; unresolved rows remain blocked by normal Category Manager validation.
- Makes a pre-update workbook backup and performs a temporary-file verified atomic save.
- Re-scans the workbook after writing and reports any remaining invalid rows.

FILES
NEW:
capabilities/OllamaPurchaseHistoryCompletion/__init__.py
capabilities/OllamaPurchaseHistoryCompletion/main_ollama_purchase_history_completion.py
data/prompts/dev_prompts/shopgraph_ollama_common_name_completion_prompt.txt
README/README_OLLAMA_PURCHASE_HISTORY_COMMON_NAME_COMPLETION.txt

UPDATED:
capabilities/pipelines.py
utils/DataBaseBuilder/excel/category_manager.py

No runtime database, config, Purchase History workbook, or export files are included.
