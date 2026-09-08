SHOPGRAPH — RULE-BASED RECEIPT ITEM INTERPRETATION
===================================================

PURPOSE
-------
This update improves:

    Data Base Builder
        1. Add Receipt to Purchase History

The existing Store, Store Number, and Receipt Date workflow is intentionally
unchanged.

The new logic focuses on the mature receipt rules for:

    Product
    Six-Digit SKU
    Final Item Price
    Total

Common Name and Sub-Category remain unchanged by this rule engine.

ARCHITECTURE
------------
New module:

    utils/DataBaseBuilder/receipt_item_interpreter.py

The module is deterministic Python. It does not call AI.

Before the normal interactive line review begins, Data Base Builder now analyzes
the ordered OCR lines as a receipt sequence. It then feeds the resulting
Product/SKU/Final Price proposal into the SAME existing review and commit flow.

Normal Purchase History and Test Mode therefore exercise the same new logic.

RULES NOW CODED
---------------
1. Preserve original OCR line order.

2. Product and final price may occur on the same line.

3. A product without a price may remain open while immediately following lines
   are inspected.

4. A following price-only or pricing-math line may complete the open product.

5. Pricing/weight/promotion lines used to complete a product are consumed as
   metadata and are not offered as separate products.

6. Price-like tokens are candidates, not automatically final item prices.

7. Unit-price/reference amounts such as "$0.65/lb" are rejected as final prices.

8. Weight/reference values used in pricing mathematics are not treated as final
   item prices.

9. Promotional reference amounts such as "3 for $10.00" are rejected when a
   separate actual item charge is present.

10. Savings/discount lines are automatically rejected as purchased items.

11. Final charge is preferred over unit/promotional/savings reference amounts.

12. 0.00 is preserved as a valid final item price.

13. Price-column/right-side geometry may support a decision when OCR word
    coordinates are available, but the code deliberately does NOT implement a
    "rightmost decimal always wins" rule.

14. If multiple plausible final-charge amounts remain after deterministic
    filtering, Price stays NA instead of inventing an association.

15. Quantity/status metadata may share a product line without becoming part of
    the normalized Product Name.

16. Qty > 1 does not cause the displayed line price to be divided or split.

17. Explicit "unavailable" status prevents the line from being treated as a
    completed purchase.

18. SKU / item identifiers are retained in the SKU field and removed from the
    normalized Product Name.

19. Repeated identical product descriptions are preserved as separate item
    occurrences. No product-name deduplication is performed.

20. Each proposed item still contains one Product and one Final Item Price.

EXAMPLES
--------
Aldi:

    388137 Large Eggs 1.66 FA

becomes:

    SKU:     388137
    Product: Large Eggs
    Price:   1.66
    Total:   1.66

Publix weighted item:

    Bananas F
    $0.65/lb x 2.36 lb        1.53

becomes one proposed purchase:

    Product: Bananas
    Price:   1.53

The second OCR line is automatically treated as pricing detail for Bananas.

Publix promotion:

    Tf Caesar Salad Kit Chop F
    1 @ 3 for $10.00          3.34

uses 3.34 as the item price and rejects 10.00 as the promotional reference.

Walmart-style quantity/status line:

    Purina ... Cat Litter 20 shopped Qty2 $23.94

keeps one item record with:

    Product: Purina ... Cat Litter
    Price:   23.94

The code does not divide the displayed charge merely because Qty2 is present.

WHAT REMAINS INTENTIONALLY UNCHANGED / NOT CODED YET
----------------------------------------------------
- Store identification
- Store Number identification
- Receipt Date identification
- Header / Main Receipt / Footer boundary detection
- Common Name inference
- Sub-Category inference

The existing filename/manual/refined-context flow for Store, Store Number, and
Date remains in place.

Header/Main/Footer logic is intentionally not added because the current Receipt
Rules document identifies that as a future problem.

CONSERVATIVE DESIGN
-------------------
The interpreter is not intended to "force an answer."

When deterministic evidence is insufficient, it returns NA and the existing
interactive correction workflow remains available.

The existing Data Base Builder review menu, Purchase History writing logic,
duplicate tracking, Test Mode output path, benchmarks, skip-term functionality,
and analytics behavior are otherwise unchanged.
