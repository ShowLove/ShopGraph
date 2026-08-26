from __future__ import annotations

import shutil
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.constants import (
    CROPPED_DIR,
    PERSPECTIVE_DIR,
    ENLARGED_DIR,
    OCR_VARIANTS_DIR,
    OCR_CANDIDATES_DIR,
    RAW_OCR_DIR,
)
from capabilities.OCRAcquisitionPipeline.session_state import (
    clear_selected_receipt,
)


# ---------------------------------------------------------------------------
# OCR ACQUISITION PIPELINE GENERATED DATA
# ---------------------------------------------------------------------------

GENERATED_DIRECTORIES = (
    CROPPED_DIR,
    PERSPECTIVE_DIR,
    ENLARGED_DIR,
    OCR_VARIANTS_DIR,
    OCR_CANDIDATES_DIR,
    RAW_OCR_DIR,
)


def _clear_directory_contents(
    directory: Path,
) -> tuple[int, int]:
    """
    Delete everything inside a generated-data directory while preserving
    the directory itself.

    Returns:
        (files_deleted, directories_deleted)
    """
    files_deleted = 0
    directories_deleted = 0

    if not directory.exists():
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        return (
            files_deleted,
            directories_deleted,
        )

    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(
                item
            )
            directories_deleted += 1

        else:
            item.unlink()
            files_deleted += 1

    return (
        files_deleted,
        directories_deleted,
    )


def clean_ocr_acquisition_pipeline_data() -> dict:
    """
    Remove all generated files produced by the OCR Acquisition Pipeline.

    IMPORTANT:
    data/current_pic/ is intentionally NOT touched.

    The generated output directories themselves are preserved so the
    pipeline can immediately be run again.
    """
    total_files_deleted = 0
    total_directories_deleted = 0
    cleaned_directories = []

    for directory in GENERATED_DIRECTORIES:
        (
            files_deleted,
            directories_deleted,
        ) = _clear_directory_contents(
            directory
        )

        total_files_deleted += (
            files_deleted
        )

        total_directories_deleted += (
            directories_deleted
        )

        cleaned_directories.append(
            str(
                directory.resolve()
            )
        )

    # Prevent stale session paths from pointing to files that were deleted.
    clear_selected_receipt()

    return {
        "cleaned_directories": cleaned_directories,
        "files_deleted": total_files_deleted,
        "directories_deleted": total_directories_deleted,
        "current_pic_unchanged": True,
    }


def run_ocr_acquisition_pipeline_cleanup() -> None:
    print(
        "\n=== Clean OCR Acquisition Pipeline Data ===\n"
    )

    print(
        "This removes generated OCR Acquisition Pipeline files."
    )

    print(
        "data/current_pic/ will NOT be changed.\n"
    )

    result = (
        clean_ocr_acquisition_pipeline_data()
    )

    print(
        "[OK] OCR Acquisition Pipeline generated data cleaned."
    )

    print(
        f"Files deleted: {result['files_deleted']}"
    )

    print(
        "Nested directories deleted: "
        f"{result['directories_deleted']}"
    )

    print(
        "Current receipt images preserved: YES"
    )


if __name__ == "__main__":
    run_ocr_acquisition_pipeline_cleanup()
