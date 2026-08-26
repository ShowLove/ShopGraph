from __future__ import annotations

from utils.DataBaseBuilder.parsers.base_parser import BaseReceiptParser
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


class TraderJoesParser(BaseReceiptParser):
    receipt_type = "Trader Joe's"
    display_fields = (
        "product",
        "price",
        "store_number",
        "date",
    )

    def parse_line(
        self,
        text: str,
        store_number: str,
        receipt_date: str,
    ) -> PurchaseRecord:
        return PurchaseRecord(
            six_digit_sku=NA,
            product=self.clean_product_text(text),
            tax_code=NA,
            price=self.extract_price(text),
            store_number=store_number,
            date=receipt_date,
        )
