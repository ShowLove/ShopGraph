SHOPGRAPH — OLLAMA SUB-CATEGORY COMPLETION UPDATE

Adds Pipeline options 5 and 8 for blank/NA Sub-Category completion.

Runtime persistent-write rule:
The new Ollama completion capabilities write only to data/database/shopgraph_purchase_history.xlsx. Option 5 modifies Purchase History column I only. Option 8 modifies Category Manager column B only. Atomic-save temporary files may be used and removed by the existing save helper. No alternate .xlsx database is created.

Menu:
1 Pipeline Part 1
2 Pipeline Part 1 - Ollama Receipt Acquisition
3 Pipeline Export 1
4 Ollama Purchase History Blank/NA Completion
5 Ollama Purchase History Sub-Category Blank/NA Completion
6 Category Manager Completion
7 Ollama Category Manager Completion
8 Ollama Category Manager Sub-Category Blank/NA Completion
9 Pipeline Export 2
10 Finalize Taxonomy + Budgets
11 Return to Capabilities Menu

Install with the existing Code Update Importer / overlay mechanism.
