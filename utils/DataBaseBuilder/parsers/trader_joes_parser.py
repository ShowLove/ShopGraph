from __future__ import annotations

from utils.DataBaseBuilder.parsers.base_parser import BaseReceiptParser
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


class TraderJoesParser(BaseReceiptParser):
    receipt_type = "Trader Joe's"
    display_fields = (
        "total",
        "store",
        "product",
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
        price = self.extract_price(text)

        return self.build_record(
            six_digit_sku=NA,
            product=self.clean_product_text(text),
            tax_code=NA,
            price=price,
            store_number=store_number,
            date=receipt_date,
        )
