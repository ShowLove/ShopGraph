ShopGraph Category Manager - Category / Sub-Category A:B Fix

PURPOSE
-------
Category Manager is the broad taxonomy mapping table.

The intended layout is exactly:

    Column A: Category
    Column B: Sub-Category

Column B is rebuilt from the distinct Sub-Category values currently found in
Purchase History. Column A is the broad Category filled in by the user.

Example:

    Category       Sub-Category
    Food           Fresh Fruit
    Food           Fresh Vegetables
    Food           Yogurt
    Personal Care  Body Wash
    NA             New Sub-Category

CREATE / REFRESH
----------------
Create / Refresh uses Purchase History as the authority for the list of
Sub-Categories.

- Every distinct Purchase History Sub-Category appears once in column B.
- Existing valid Sub-Category -> Category mappings are preserved in column A.
- A newly encountered Sub-Category has no known broad Category, so column A is
  set to NA.
- Category is never inferred from the Sub-Category name, Common Name, Product,
  OCR, or Purchase History.
- A legacy Category Manager layout is rebuilt into this A:B taxonomy layout.

APPLY / VALIDATE
----------------
Apply validates the taxonomy and saves a clean two-column Category Manager.
It does not rewrite Purchase History. Purchase History remains authoritative
for Sub-Category; Category Manager remains authoritative for the broad parent
Category.

ANALYTICS
---------
Broad Analytics resolves:

    Purchase History Sub-Category
        -> Category Manager column B
        -> Category Manager column A

Sub Analytics continues to use Purchase History Sub-Category directly.

DATA SAFETY
-----------
Workbook saves use a temporary .xlsx file, verify it can be reopened, and only
then atomically replace the live workbook.
