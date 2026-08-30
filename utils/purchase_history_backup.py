from __future__ import annotations

import shutil
from pathlib import Path

from utils.constants import DATA_DIR


DATABASE_DIR = DATA_DIR / "database"

SOURCE_PATH = (
    DATABASE_DIR
    / "shopgraph_purchase_history.xlsx"
)

COPY_PATH = (
    DATABASE_DIR
    / "shopgraph_purchase_history copy.xlsx"
)


def update_purchase_history_copy() -> Path:
    """
    Replace the Purchase History copy with an exact file copy of the live
    Purchase History workbook.

    Source:
        data/database/shopgraph_purchase_history.xlsx

    Destination:
        data/database/shopgraph_purchase_history copy.xlsx
    """
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            "Purchase History workbook was not found:"
            f"\n{SOURCE_PATH.resolve()}"
        )

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        SOURCE_PATH,
        COPY_PATH,
    )

    return COPY_PATH.resolve()


def run_purchase_history_backup() -> None:
    print(
        "\n=== Update Purchase History Copy ===\n"
    )

    try:
        output_path = (
            update_purchase_history_copy()
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            f"[ERROR] {error}"
        )
        return

    print(
        "[OK] Purchase History copy updated."
    )

    print(
        "\nSource:"
        f"\n{SOURCE_PATH.resolve()}"
    )

    print(
        "\nCopy:"
        f"\n{output_path}"
    )


if __name__ == "__main__":
    run_purchase_history_backup()
