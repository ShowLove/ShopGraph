from __future__ import annotations

import re

from utils.DataBaseBuilder.parsers.base_parser import BaseReceiptParser
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


PUBLIX_TAX_PATTERN = re.compile(
    r"(?<![A-Za-z])(TLF|TF|LF|F|T)(?![A-Za-z])",
    re.IGNORECASE,
)


class PublixParser(BaseReceiptParser):
    receipt_type = "Publix"
    display_fields = (
        "total",
        "store",
        "product",
        "tax_code",
        "store_number",
        "common_name",
        "category",
        "date",
        "price",
    )

    def parse_line(
        self,
        text: str,
        store_number: str,
        receipt_date: str,
    ) -> PurchaseRecord:
        tax_matches = [
            match.upper()
            for match in PUBLIX_TAX_PATTERN.findall(text)
        ]

        tax_code = (
            tax_matches[0]
            if len(tax_matches) == 1
            else NA
        )

        price = self.extract_price(text)

        return self.build_record(
            six_digit_sku=NA,
            product=self.clean_product_text(
                text,
                tax_pattern=PUBLIX_TAX_PATTERN,
            ),
            tax_code=tax_code,
            price=price,
            store_number=store_number,
            date=receipt_date,
        )
