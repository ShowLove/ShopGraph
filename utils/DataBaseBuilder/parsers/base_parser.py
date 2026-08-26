from __future__ import annotations

import re
from abc import ABC, abstractmethod

from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


class BaseReceiptParser(ABC):
    receipt_type = "Other"
    display_fields = (
        "six_digit_sku",
        "product",
        "tax_code",
        "price",
        "store_number",
        "date",
    )

    field_labels = {
        "six_digit_sku": "Six-Digit SKU",
        "product": "Product",
        "tax_code": "Tax Code",
        "price": "Price",
        "store_number": "Store Number",
        "date": "Date",
    }

    @abstractmethod
    def parse_line(
        self,
        text: str,
        store_number: str,
        receipt_date: str,
    ) -> PurchaseRecord:
        raise NotImplementedError

    def extract_price(self, text: str) -> str:
        matches = PRICE_PATTERN.findall(text)

        if len(matches) != 1:
            return NA

        return matches[0].replace(",", ".")

    def extract_sku(self, text: str) -> str:
        matches = SKU_PATTERN.findall(text)

        if len(matches) != 1:
            return NA

        return matches[0]

    def clean_product_text(
        self,
        text: str,
        remove_sku: bool = False,
        tax_pattern: re.Pattern | None = None,
    ) -> str:
        working = text.strip()
        working = PRICE_PATTERN.sub(" ", working)

        if remove_sku:
            working = SKU_PATTERN.sub(" ", working)

        if tax_pattern is not None:
            working = tax_pattern.sub(" ", working)

        working = re.sub(r"\s+", " ", working).strip()
        working = working.strip(" -:;,.|_~'\"()[]{}")

        return working or NA

    def format_record(self, record: PurchaseRecord) -> str:
        lines = []

        for index, field_name in enumerate(
            self.display_fields,
            start=1,
        ):
            label = self.field_labels[field_name]
            value = getattr(record, field_name)
            lines.append(f'{index}. {label}: "{value}"')

        return "\n".join(lines)
