from __future__ import annotations

from utils.DataBaseBuilder.parsers.base_parser import BaseReceiptParser
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


class AldiParser(BaseReceiptParser):
    receipt_type = "Aldi"
    display_fields = (
        "total",
        "store",
        "six_digit_sku",
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
            six_digit_sku=self.extract_sku(text),
            product=self.clean_product_text(
                text,
                remove_sku=True,
            ),
            tax_code=NA,
            price=price,
            store_number=store_number,
            date=receipt_date,
        )
