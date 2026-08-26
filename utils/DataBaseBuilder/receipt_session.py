from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from utils.DataBaseBuilder.purchase_record import PurchaseRecord


@dataclass
class ReceiptSession:
    source_path: Path
    receipt_type: str
    store_number: str
    receipt_date: str
    starting_line_number: int
    accepted_purchases: list[PurchaseRecord] = field(default_factory=list)
    skipped_line_numbers: list[int] = field(default_factory=list)

    def accept(self, purchase: PurchaseRecord) -> None:
        self.accepted_purchases.append(purchase)

    def skip(self, line_number: int) -> None:
        self.skipped_line_numbers.append(line_number)
