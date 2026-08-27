from __future__ import annotations

from dataclasses import dataclass, replace


NA = "NA"


@dataclass(frozen=True)
class PurchaseRecord:
    total: str = NA
    store: str = NA
    six_digit_sku: str = NA
    product: str = NA
    tax_code: str = NA
    store_number: str = NA
    common_name: str = NA
    category: str = NA
    date: str = NA
    price: str = NA

    def with_value(
        self,
        field_name: str,
        value: str,
    ) -> "PurchaseRecord":
        cleaned = str(value).strip() or NA
        return replace(
            self,
            **{field_name: cleaned},
        )
