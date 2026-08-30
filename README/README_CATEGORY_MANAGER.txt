ShopGraph Category Manager - Hierarchical Category / Sub-Category Update

PURPOSE
-------
ShopGraph now uses a three-level product taxonomy:

    Common Name -> Sub-Category -> Category

Purchase History stores the detailed Sub-Category only.
Category Manager stores the broad Sub-Category -> Category relationship.

PURCHASE HISTORY
----------------
The existing Purchase History column formerly labeled "Category" is now
"Sub-Category". It remains in the same physical column (I). Date 1 remains J,
Price 1 remains K, and all later Date/Price history stays in place.

Existing workbooks using the old "Category" header are migrated by renaming
that header only. No Purchase History columns are inserted or shifted.

CATEGORY MANAGER LAYOUT
-----------------------
    Category | Sub-Category | Product 1 | Product 2 | ...

Products are Common Name values.

CREATE / REFRESH
----------------
Create / Refresh rebuilds Common Name -> Sub-Category membership from the
current Purchase History.

Existing valid Sub-Category -> Category mappings are preserved because
Category Manager is the authoritative storage location for broad Category.
Product placement, gaps, order, and other unapplied layout edits do not need
to survive refresh.

New Sub-Categories appear with Category = NA until the user assigns them.

APPLY
-----
Apply validates the entire manager before changing Purchase History.

Required integrity includes:
- every current Common Name exactly once;
- no unknown Common Names;
- no duplicate Common Names;
- every product assigned to a valid Sub-Category;
- every Sub-Category represented by one row;
- every Sub-Category assigned to exactly one non-NA Category.

Multiple Sub-Categories may share the same Category.

After successful validation, only Purchase History Sub-Category values may be
changed. Broad Category is never written to Purchase History.

The manager is then compacted and reformatted.

DATA SAFETY
-----------
Validation failure saves nothing and leaves Purchase History unchanged.

Successful Apply uses a temporary workbook, reopens it for verification, and
only then atomically replaces the live workbook.

No audit/version backup system is added by this update.

ANALYTICS
---------
Sub Analytics is the existing detailed analytics system, now driven by
Purchase History Sub-Category.

Analytics is the broad dashboard. It joins Purchase History Sub-Category to
Category Manager's Sub-Category -> Category mapping.

Sub Analytics can still refresh if broad Analytics cannot be generated because
Category Manager is incomplete.
