ShopGraph - Remove Receipt Item Interpreter
=================================================

This update removes the rule-based receipt item interpreter from the active
Data Base Builder workflow.

Changed behavior
----------------
- data_base_builder_main.py no longer imports receipt_item_interpreter.
- No build_rule_based_line_interpretations() pass is run.
- No rule-interpreter auto-skip behavior is run.
- No Product/SKU/Price fields are protected because of the old interpreter.
- Each OCR/Ollama receipt row starts with the existing store-specific parser's
  parse_line() result, followed by the existing refined-JSON merge and normal
  interactive review.
- Existing user-configured skip terms/sub-strings remain unchanged.

Why receipt_item_interpreter.py still exists as a tiny file
-----------------------------------------------------------
ShopGraph's existing Code Update Importer overlays files but does not delete
files that are absent from an update ZIP. Therefore this update replaces the
former module with a tiny retired placeholder containing no interpreter logic.

If you want the physical file gone after importing this update, it is safe to
delete:
    utils/DataBaseBuilder/receipt_item_interpreter.py

No active ShopGraph code in this update imports it.
