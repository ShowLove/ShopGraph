from __future__ import annotations

import shutil
from pathlib import Path

from utils.constants import DATA_DIR, EXPORT_DIR
from capabilities.OCRAcquisitionPipeline.constants import (
    CROPPED_DIR,
    PERSPECTIVE_DIR,
    ENLARGED_DIR,
    OCR_VARIANTS_DIR,
    OCR_CANDIDATES_DIR,
    RAW_OCR_DIR,
    REFINED_JSON_DIR,
)
from capabilities.OCRAcquisitionPipeline.session_state import clear_selected_receipt


GENERATED_DIRECTORIES = (
    CROPPED_DIR,
    PERSPECTIVE_DIR,
    ENLARGED_DIR,
    OCR_VARIANTS_DIR,
    OCR_CANDIDATES_DIR,
    RAW_OCR_DIR,
    REFINED_JSON_DIR,
    DATA_DIR / "preprocessed",
    EXPORT_DIR,
)

PRESERVED_DIRECTORIES = (
    DATA_DIR / "current_pic",
    DATA_DIR / "benchmarks",
    DATA_DIR / "pdf_files",
    DATA_DIR / "database",
    DATA_DIR / "prompts",
)


def _clear_directory_contents(directory: Path) -> tuple[int, int]:
    files_deleted = 0
    directories_deleted = 0

    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        return files_deleted, directories_deleted

    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
            directories_deleted += 1
        else:
            item.unlink()
            files_deleted += 1

    return files_deleted, directories_deleted


def clean_ocr_acquisition_pipeline_data() -> dict:
    total_files_deleted = 0
    total_directories_deleted = 0

    for directory in GENERATED_DIRECTORIES:
        files_deleted, directories_deleted = _clear_directory_contents(directory)
        total_files_deleted += files_deleted
        total_directories_deleted += directories_deleted

    clear_selected_receipt()

    return {
        "files_deleted": total_files_deleted,
        "directories_deleted": total_directories_deleted,
    }


def run_ocr_acquisition_pipeline_cleanup() -> None:
    print("\n=== Clean Generated Processing Data ===\n")
    print("This removes disposable/generated ShopGraph processing files.")
    print("\nThe following source/persistent data will NOT be changed:")
    print("- data/current_pic/")
    print("- data/benchmarks/")
    print("- data/pdf_files/")
    print("- data/database/")
    print("- data/prompts/\n")

    result = clean_ocr_acquisition_pipeline_data()

    print("[OK] Generated ShopGraph processing data cleaned.")
    print(f"Files deleted: {result['files_deleted']}")
    print(f"Nested directories deleted: {result['directories_deleted']}")
    print("Current receipt images preserved: YES")
    print("Benchmarks preserved: YES")
    print("Database / PDF inputs / prompts preserved: YES")


if __name__ == "__main__":
    run_ocr_acquisition_pipeline_cleanup()
