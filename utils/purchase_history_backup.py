from __future__ import annotations

import shutil
from datetime import datetime
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

ARCHIVE_DIR = (
    DATABASE_DIR
    / "archive"
)


def update_purchase_history_copy() -> Path:
    """
    Replace the Purchase History copy with an exact file copy of the live
    Purchase History workbook.
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


def restore_purchase_history_from_copy() -> Path:
    """
    Replace the live Purchase History workbook with the saved copy.
    """
    if not COPY_PATH.exists():
        raise FileNotFoundError(
            "Purchase History copy was not found:"
            f"\n{COPY_PATH.resolve()}"
        )

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        COPY_PATH,
        SOURCE_PATH,
    )

    return SOURCE_PATH.resolve()


def store_purchase_history_archive() -> Path:
    """
    Store a snapshot of the live Purchase History workbook in archive/.

    The newest archive uses the normal workbook filename. If an older archive
    already exists, it is preserved under a timestamped filename first.
    """
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            "Purchase History workbook was not found:"
            f"\n{SOURCE_PATH.resolve()}"
        )

    ARCHIVE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    archive_path = (
        ARCHIVE_DIR
        / SOURCE_PATH.name
    )

    if archive_path.exists():
        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S-%f"
        )
        preserved_path = (
            ARCHIVE_DIR
            / (
                f"{SOURCE_PATH.stem}_"
                f"{timestamp}"
                f"{SOURCE_PATH.suffix}"
            )
        )
        archive_path.replace(
            preserved_path
        )

    shutil.copy2(
        SOURCE_PATH,
        archive_path,
    )

    return archive_path.resolve()


def run_update_purchase_history_copy() -> None:
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


def run_restore_purchase_history_from_copy() -> None:
    print(
        "\n=== Restore Purchase History from Copy ===\n"
    )

    try:
        restored_path = (
            restore_purchase_history_from_copy()
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
        "\nSource:"
        f"\n{COPY_PATH.resolve()}"
    )

    print(
        "\nFile Restored from Copy:"
        f"\n{restored_path}"
    )


def run_store_purchase_history_archive() -> None:
    print(
        "\n=== Store Purchase History Archive ===\n"
    )

    try:
        archive_path = (
            store_purchase_history_archive()
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
        "\nSource:"
        f"\n{SOURCE_PATH.resolve()}"
    )

    print(
        "\nArchive File:"
        f"\n{archive_path}"
    )


def display_purchase_history_backup_menu() -> None:
    print(
        "\n=== ShopGraph Purchase History Backup ===\n"
    )
    print(
        "1. Update Purchase History Copy"
    )
    print(
        "2. Restore Purchase History from Copy"
    )
    print(
        "3. Store Purchase History Archive"
    )
    print(
        "0. Return to Utilities"
    )


def run_purchase_history_backup_menu() -> None:
    while True:
        display_purchase_history_backup_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_update_purchase_history_copy()
        elif option == "2":
            run_restore_purchase_history_from_copy()
        elif option == "3":
            run_store_purchase_history_archive()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )


# Backward-compatible entry point retained for any older imports/scripts.
def run_purchase_history_backup() -> None:
    run_purchase_history_backup_menu()


if __name__ == "__main__":
    run_purchase_history_backup_menu()
