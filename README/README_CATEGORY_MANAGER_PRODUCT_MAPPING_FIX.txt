ShopGraph - Category Manager Product Mapping Fix
===============================================

PURPOSE
-------
Restores the intended hierarchical Category Manager layout:

    A = Category
    B = Sub-Category
    C+ = Products / Common Names belonging to that Sub-Category

Column B is rebuilt from Purchase History Sub-Category values.
Column A remains the broad Category manually controlled by the user.
Existing valid Sub-Category -> Category mappings are preserved on refresh.
New Sub-Categories receive Category = NA until the user assigns one.

Products are the Purchase History Common Name values and are grouped across
Product 1, Product 2, Product 3, ... for the corresponding Sub-Category.

INSTALL
-------
Copy the ZIP contents over the ShopGraph project root, preserving directories.
No new package installation is required.

REPLACED FILE
-------------
    utils/DataBaseBuilder/excel/category_manager.py

The included excel/__init__.py is unchanged-compatible and is included so the
overlay is self-contained.
