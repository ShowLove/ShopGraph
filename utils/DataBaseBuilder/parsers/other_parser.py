from __future__ import annotations

from utils.DataBaseBuilder.parsers.base_parser import BaseReceiptParser
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord


class OtherParser(BaseReceiptParser):
    receipt_type = "Other"

    def parse_line(
        self,
        text: str,
        store_number: str,
        receipt_date: str,
    ) -> PurchaseRecord:
        return PurchaseRecord(
            six_digit_sku=self.extract_sku(text),
            product=self.clean_product_text(
                text,
                remove_sku=True,
            ),
            tax_code=NA,
            price=self.extract_price(text),
            store_number=store_number,
            date=receipt_date,
        )
