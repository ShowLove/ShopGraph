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

    This function intentionally retains the original Option 3 behavior.
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


def _parse_archive_date(value: str):
    """
    Parse the date used by a dated archive.

    Accepted input:
        YYYY-MM-DD
        MM/DD/YYYY
    """
    value = value.strip()

    for date_format in (
        "%Y-%m-%d",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(
                value,
                date_format,
            ).date()
        except ValueError:
            pass

    raise ValueError(
        "Invalid date. Use YYYY-MM-DD or MM/DD/YYYY."
    )


def store_purchase_history_archive_with_date(
    archive_date=None,
) -> Path:
    """
    Store a separate dated snapshot without changing the normal Option 3
    archive.

    Example:
        shopgraph_purchase_history_2026-09-06.xlsx

    If that dated filename already exists, a time suffix is added so an older
    dated snapshot is never silently overwritten.
    """
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            "Purchase History workbook was not found:"
            f"\n{SOURCE_PATH.resolve()}"
        )

    if archive_date is None:
        archive_date = datetime.now().date()

    ARCHIVE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    date_text = archive_date.strftime(
        "%Y-%m-%d"
    )

    archive_path = (
        ARCHIVE_DIR
        / (
            f"{SOURCE_PATH.stem}_"
            f"{date_text}"
            f"{SOURCE_PATH.suffix}"
        )
    )

    if archive_path.exists():
        time_text = datetime.now().strftime(
            "%H%M%S-%f"
        )
        archive_path = (
            ARCHIVE_DIR
            / (
                f"{SOURCE_PATH.stem}_"
                f"{date_text}_"
                f"{time_text}"
                f"{SOURCE_PATH.suffix}"
            )
        )

    shutil.copy2(
        SOURCE_PATH,
        archive_path,
    )

    return archive_path.resolve()


def _archive_files() -> list[Path]:
    """
    Return available Purchase History archive workbooks, newest modified first.
    """
    if not ARCHIVE_DIR.exists():
        return []

    candidates = [
        path
        for path in ARCHIVE_DIR.iterdir()
        if (
            path.is_file()
            and path.suffix.casefold() == ".xlsx"
            and path.name.startswith(
                SOURCE_PATH.stem
            )
        )
    ]

    candidates.sort(
        key=lambda path: (
            path.stat().st_mtime,
            path.name.casefold(),
        ),
        reverse=True,
    )

    return candidates


def _select_archive(
    prompt: str,
) -> Path | None:
    archives = _archive_files()

    if not archives:
        print(
            "\n[INFO] No Purchase History archives were found."
        )
        return None

    print(
        "\nAvailable Purchase History Archives:\n"
    )

    for index, archive_path in enumerate(
        archives,
        start=1,
    ):
        modified = datetime.fromtimestamp(
            archive_path.stat().st_mtime
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(
            f"{index}. {archive_path.name} "
            f"(modified {modified})"
        )

    print(
        "0. Cancel"
    )

    while True:
        choice = input(
            f"\n{prompt}: "
        ).strip()

        if choice == "0":
            return None

        try:
            index = int(choice)
        except ValueError:
            print(
                "\n[ERROR] Enter one of the archive numbers shown."
            )
            continue

        if 1 <= index <= len(archives):
            return archives[index - 1]

        print(
            "\n[ERROR] Invalid archive selection."
        )


def restore_purchase_history_from_archive(
    archive_path: Path,
) -> Path:
    """
    Replace the live Purchase History workbook with the selected archive.
    """
    archive_path = Path(
        archive_path
    )

    if not archive_path.exists():
        raise FileNotFoundError(
            "Purchase History archive was not found:"
            f"\n{archive_path.resolve()}"
        )

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        archive_path,
        SOURCE_PATH,
    )

    return SOURCE_PATH.resolve()


def delete_purchase_history_copy() -> Path:
    """
    Delete only the saved Purchase History copy.
    """
    if not COPY_PATH.exists():
        raise FileNotFoundError(
            "Purchase History copy was not found:"
            f"\n{COPY_PATH.resolve()}"
        )

    deleted_path = COPY_PATH.resolve()
    COPY_PATH.unlink()

    return deleted_path


def delete_purchase_history_archive(
    archive_path: Path,
) -> Path:
    """
    Delete one selected Purchase History archive.
    """
    archive_path = Path(
        archive_path
    )

    if not archive_path.exists():
        raise FileNotFoundError(
            "Purchase History archive was not found:"
            f"\n{archive_path.resolve()}"
        )

    deleted_path = archive_path.resolve()
    archive_path.unlink()

    return deleted_path


def update_all_from_purchase_history() -> tuple[Path, Path]:
    """
    Update both normal backup targets from the current live Purchase History:

        1. Purchase History copy
        2. Normal Purchase History archive

    The existing Option 1 and Option 3 implementations are reused directly.
    """
    copy_path = (
        update_purchase_history_copy()
    )

    archive_path = (
        store_purchase_history_archive()
    )

    return (
        copy_path,
        archive_path,
    )


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
        "\n=== Update Purchase History Archive ===\n"
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


def run_store_purchase_history_archive_with_date() -> None:
    print(
        "\n=== Update Purchase History Archive with Date ===\n"
    )

    print(
        "Press Enter to use today's date, "
        "or enter a date."
    )
    print(
        "Accepted formats: YYYY-MM-DD or MM/DD/YYYY"
    )

    date_input = input(
        "\nArchive date: "
    ).strip()

    try:
        archive_date = (
            datetime.now().date()
            if not date_input
            else _parse_archive_date(
                date_input
            )
        )

        archive_path = (
            store_purchase_history_archive_with_date(
                archive_date
            )
        )

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return

    print(
        "\n[OK] Dated Purchase History archive updated."
    )

    print(
        "\nSource:"
        f"\n{SOURCE_PATH.resolve()}"
    )

    print(
        "\nArchive File:"
        f"\n{archive_path}"
    )


def run_restore_purchase_history_from_archive() -> None:
    print(
        "\n=== Restore Purchase History from Archive ==="
    )

    archive_path = _select_archive(
        "Select archive to restore"
    )

    if archive_path is None:
        print(
            "\n[INFO] Restore cancelled."
        )
        return

    print(
        "\nSelected Archive:"
        f"\n{archive_path.resolve()}"
    )

    confirmation = input(
        "\nRestore the live Purchase History from this archive? [y/N]: "
    ).strip().casefold()

    if confirmation not in {
        "y",
        "yes",
    }:
        print(
            "\n[INFO] Restore cancelled."
        )
        return

    try:
        restored_path = (
            restore_purchase_history_from_archive(
                archive_path
            )
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return

    print(
        "\n[OK] Purchase History restored from archive."
    )

    print(
        "\nSource Archive:"
        f"\n{archive_path.resolve()}"
    )

    print(
        "\nRestored Purchase History:"
        f"\n{restored_path}"
    )


def run_delete_purchase_history_copy() -> None:
    print(
        "\n=== Delete Purchase History Copy ===\n"
    )

    if not COPY_PATH.exists():
        print(
            "[INFO] Purchase History copy does not exist."
        )
        return

    print(
        "File:"
        f"\n{COPY_PATH.resolve()}"
    )

    confirmation = input(
        "\nDelete this Purchase History copy? [y/N]: "
    ).strip().casefold()

    if confirmation not in {
        "y",
        "yes",
    }:
        print(
            "\n[INFO] Delete cancelled."
        )
        return

    try:
        deleted_path = (
            delete_purchase_history_copy()
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return

    print(
        "\n[OK] Purchase History copy deleted."
    )
    print(
        "Deleted:"
        f"\n{deleted_path}"
    )


def run_delete_purchase_history_archive() -> None:
    print(
        "\n=== Delete Purchase History Archive ==="
    )

    archive_path = _select_archive(
        "Select archive to delete"
    )

    if archive_path is None:
        print(
            "\n[INFO] Delete cancelled."
        )
        return

    print(
        "\nSelected Archive:"
        f"\n{archive_path.resolve()}"
    )

    confirmation = input(
        "\nDelete this archive permanently? [y/N]: "
    ).strip().casefold()

    if confirmation not in {
        "y",
        "yes",
    }:
        print(
            "\n[INFO] Delete cancelled."
        )
        return

    try:
        deleted_path = (
            delete_purchase_history_archive(
                archive_path
            )
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return

    print(
        "\n[OK] Purchase History archive deleted."
    )
    print(
        "Deleted:"
        f"\n{deleted_path}"
    )


def display_delete_purchase_history_menu() -> None:
    print(
        "\n=== Delete Purchase History ===\n"
    )
    print(
        "1. Delete Purchase History Copy"
    )
    print(
        "2. Delete Purchase History Archive"
    )
    print(
        "0. Return to Purchase History Backup"
    )


def run_delete_purchase_history_menu() -> None:
    while True:
        display_delete_purchase_history_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_delete_purchase_history_copy()
        elif option == "2":
            run_delete_purchase_history_archive()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )


def run_update_all_from_purchase_history() -> None:
    print(
        "\n=== Update All from Purchase History ===\n"
    )

    print(
        "[1/2] Update Purchase History Copy"
    )

    try:
        copy_path = (
            update_purchase_history_copy()
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            f"\n[ERROR] Purchase History copy update failed:"
            f"\n{error}"
        )
        print(
            "\n[INFO] Purchase History Archive was not updated."
        )
        return

    print(
        "[OK] Purchase History copy updated:"
        f"\n{copy_path}"
    )

    print(
        "\n[2/2] Update Purchase History Archive"
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
            f"\n[ERROR] Purchase History archive update failed:"
            f"\n{error}"
        )
        print(
            "\n[WARNING] Purchase History copy was updated successfully, "
            "but the archive was not."
        )
        return

    print(
        "[OK] Purchase History archive updated:"
        f"\n{archive_path}"
    )

    print(
        "\n[OK] All Purchase History backups updated."
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
        "3. Update Purchase History Archive"
    )
    print(
        "4. Update Purchase History Archive with Date"
    )
    print(
        "5. Restore Purchase History from Archive"
    )
    print(
        "6. Delete Purchase History"
    )
    print(
        "7. Update all from Purchase History"
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
        elif option == "4":
            run_store_purchase_history_archive_with_date()
        elif option == "5":
            run_restore_purchase_history_from_archive()
        elif option == "6":
            run_delete_purchase_history_menu()
        elif option == "7":
            run_update_all_from_purchase_history()
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
