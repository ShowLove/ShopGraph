from __future__ import annotations

import shutil
from pathlib import Path

from utils.constants import DATA_DIR


SOURCE_FOLDERS = {
    "1": ("Current Receipt Images", DATA_DIR / "current_pic"),
    "2": ("PDF Source Files", DATA_DIR / "pdf_files"),
    "3": ("Benchmarks", DATA_DIR / "benchmarks"),
}


def _count_contents(directory: Path) -> tuple[int, int]:
    if not directory.exists():
        return 0, 0

    files = sum(
        1
        for path in directory.rglob("*")
        if path.is_file()
    )
    directories = sum(
        1
        for path in directory.rglob("*")
        if path.is_dir()
    )
    return files, directories


def _clear_directory_contents(directory: Path) -> tuple[int, int]:
    directory.mkdir(parents=True, exist_ok=True)

    files_deleted = 0
    directories_deleted = 0

    for item in list(directory.iterdir()):
        if item.is_dir():
            files_deleted += sum(
                1
                for path in item.rglob("*")
                if path.is_file()
            )
            directories_deleted += 1 + sum(
                1
                for path in item.rglob("*")
                if path.is_dir()
            )
            shutil.rmtree(item)
        else:
            item.unlink()
            files_deleted += 1

    return files_deleted, directories_deleted



def clean_current_receipt_images() -> dict:
    """
    Non-interactive cleanup used by automated Pipelines.

    Only data/current_pic/ contents are removed. The folder itself remains.
    """
    label, directory = SOURCE_FOLDERS["1"]
    files_deleted, directories_deleted = (
        _clear_directory_contents(
            directory
        )
    )

    return {
        "label": label,
        "directory": directory.resolve(),
        "files_deleted": files_deleted,
        "directories_deleted": directories_deleted,
    }


def _display_menu() -> None:
    print("\n=== Clean Source Data ===\n")
    print("Choose which folder contents to delete:\n")

    for option, (label, directory) in SOURCE_FOLDERS.items():
        files, directories = _count_contents(directory)
        print(f"{option}. {label}")
        print(f"   {directory}")
        print(f"   Files: {files} | Nested folders: {directories}")

    print("4. Delete Contents of All 3 Source Folders")
    print("0. Return to Utilities Menu")


def _confirm(label: str, paths: list[Path]) -> bool:
    print("\nWARNING: This permanently deletes folder CONTENTS.")
    print("The folder(s) themselves will remain.\n")
    print(f"Target: {label}")

    for path in paths:
        print(f"- {path.resolve()}")

    print("\n1. Confirm Delete")
    print("0. Cancel")

    while True:
        option = input("\nSelect option: ").strip()

        if option == "1":
            return True
        if option == "0":
            return False

        print("\n[ERROR] Invalid option.")


def _delete_selection(selection: list[tuple[str, Path]], label: str) -> None:
    paths = [path for _, path in selection]

    if not _confirm(label, paths):
        print("\n[INFO] Source-data cleanup cancelled.")
        return

    total_files = 0
    total_directories = 0

    for folder_label, directory in selection:
        files_deleted, directories_deleted = _clear_directory_contents(directory)
        total_files += files_deleted
        total_directories += directories_deleted

        print(f"\n[OK] {folder_label} contents deleted.")
        print(f"Files deleted: {files_deleted}")
        print(f"Nested directories deleted: {directories_deleted}")

    print("\n[OK] Source-data cleanup complete.")
    print(f"Total files deleted: {total_files}")
    print(f"Total nested directories deleted: {total_directories}")


def run_source_data_cleanup() -> None:
    while True:
        _display_menu()
        option = input("\nSelect option: ").strip()

        if option in SOURCE_FOLDERS:
            label, directory = SOURCE_FOLDERS[option]
            _delete_selection([(label, directory)], label)

        elif option == "4":
            selection = list(SOURCE_FOLDERS.values())
            _delete_selection(selection, "All 3 Source Folders")

        elif option == "0":
            return

        else:
            print("\n[ERROR] Invalid option.")


if __name__ == "__main__":
    run_source_data_cleanup()
