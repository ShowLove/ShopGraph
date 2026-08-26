from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from utils.DataBaseBuilder.purchase_record import PurchaseRecord


@dataclass(frozen=True)
class ReviewedLine:
    line_number: int
    status: str
    purchase: PurchaseRecord | None = None


@dataclass
class ReceiptSession:
    source_path: Path
    receipt_type: str
    store_number: str
    receipt_date: str
    starting_line_number: int
    accepted_purchases: list[PurchaseRecord] = field(default_factory=list)
    skipped_line_numbers: list[int] = field(default_factory=list)
    reviewed_lines: list[ReviewedLine] = field(default_factory=list)

    def accept(
        self,
        line_number: int,
        purchase: PurchaseRecord,
        status: str = "accepted",
    ) -> None:
        self.accepted_purchases.append(purchase)
        self.reviewed_lines.append(
            ReviewedLine(
                line_number=line_number,
                status=status,
                purchase=purchase,
            )
        )

    def skip(self, line_number: int) -> None:
        self.skipped_line_numbers.append(line_number)
        self.reviewed_lines.append(
            ReviewedLine(
                line_number=line_number,
                status="skipped",
            )
        )
