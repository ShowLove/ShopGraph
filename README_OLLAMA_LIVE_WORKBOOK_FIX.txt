ShopGraph - Ollama Live Workbook Fix

PURPOSE
Both Ollama completion workflows now update the single authoritative workbook:
    data/database/shopgraph_purchase_history.xlsx

CHANGES
1. Ollama Purchase History Blank/NA Completion
   - Still edits Common Name in the Purchase History sheet.
   - Still uses its verified atomic-save workflow to replace the live workbook safely.
   - No longer creates shopgraph_purchase_history.pre_ollama_common_name_completion.xlsx.

2. Ollama Category Manager Completion
   - Still edits Category in the Category Manager sheet inside the same live workbook.
   - Still uses _verified_atomic_save() to replace the live workbook safely.
   - No longer creates shopgraph_purchase_history.pre_ollama_category_completion.xlsx.

The temporary files used internally for atomic saves are still created and removed automatically.
Those are safety implementation details, not persistent database copies.

INSTALL
Overlay the included capabilities/ folder onto the ShopGraph project root, preserving paths.

OLD FILES
After confirming they are not needed as recovery copies, the two old .pre_ollama_*.xlsx files may be deleted manually.

EXPECTED RESULT
After pipeline option 4 or 6 succeeds, reopen:
    data/database/shopgraph_purchase_history.xlsx
The changes should be present in that workbook.
