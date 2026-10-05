ShopGraph - Ollama Category Manager Completion
===============================================

PURPOSE
-------
Adds a local-only Ollama stage that completes blank/NA broad Category values in the live Category Manager. Pipeline Export 2 remains available as the manual external-AI fallback.

MENU
----
6. Ollama Category Manager Completion
7. Pipeline Export 2
8. Finalize Taxonomy + Budgets

BEHAVIOR
--------
- Reads Category Manager and Purchase History directly from the live workbook.
- Existing non-NA Category assignments are authoritative and are never overwritten.
- Exact existing Sub-Category -> Category mappings are reused deterministically.
- Remaining targets are sent to the existing local run_local_json_prompt() Ollama client in batches.
- Product/Common Name membership and compact Purchase History examples are supplied as evidence.
- Existing Category capitalization is preserved.
- Ollama responses are strictly validated before any workbook write.
- A backup named shopgraph_purchase_history.pre_ollama_category_completion.xlsx is created before modification.
- The workbook is saved through ShopGraph's verified atomic-save helper.
- The saved workbook is reopened and checked for remaining blank/NA Categories.

SAFETY
------
Malformed JSON, omitted/duplicate/unexpected rows, changed Sub-Category identity, invalid Categories, or a target that became non-NA cause rejection before the live workbook is changed.

WORKFLOW
--------
Pipeline Part 1 -> Ollama Purchase History Blank/NA Completion -> Category Manager Completion -> Ollama Category Manager Completion -> Finalize Taxonomy + Budgets

The Ollama completion stage does NOT automatically apply Category Manager to Purchase History and does NOT refresh Budget Plans. Finalize Taxonomy + Budgets retains that responsibility.
