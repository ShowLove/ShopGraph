ShopGraph - Source Data Cleanup Utility

Adds a new standalone utility:

5. Clean Source Data

It prompts the user to delete the contents of:
1. data/current_pic/
2. data/pdf_files/
3. data/benchmarks/
4. all three

Each deletion requires confirmation. Only folder contents are deleted;
the folders themselves remain.

No existing capabilities or utilities are removed or changed.

Files:
NEW: utils/clean_source_data.py
UPDATED: utils/utils_main.py
