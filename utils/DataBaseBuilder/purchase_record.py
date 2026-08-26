from __future__ import annotations

from dataclasses import dataclass, replace


NA = "NA"


@dataclass(frozen=True)
class PurchaseRecord:
    six_digit_sku: str = NA
    product: str = NA
    tax_code: str = NA
    price: str = NA
    store_number: str = NA
    date: str = NA

    def with_value(self, field_name: str, value: str) -> "PurchaseRecord":
        cleaned = value.strip() or NA
        return replace(self, **{field_name: cleaned})
