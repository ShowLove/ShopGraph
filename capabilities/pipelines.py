from __future__ import annotations

import shutil
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.main_OCRAcquisitionPipeline import (
    run_ocr_acquisition_pipeline_for_image,
)
from utils.clean_ocr_acquisition_pipeline import (
    clean_ocr_acquisition_pipeline_data,
)
from utils.clean_source_data import (
    clean_current_receipt_images,
)
from utils.DataBaseBuilder.data_base_builder_main import (
    run_receipt_import,
)
from utils.picture_importer import (
    get_saved_picture_path,
    import_picture_to_current_folder,
)
from utils.purchase_history_backup import (
    update_purchase_history_copy,
)
from utils.code_update_importer import (
    get_import_location,
)
from utils.constants import DATA_DIR
from utils.export_purchase_history_txt import (
    export_purchase_history_as_csv_txt,
)


def _run_database_builder_for_outputs(
    raw_ocr_files,
) -> None:
    if not raw_ocr_files:
        return

    print("\n=== Data Base Builder ===")
    print(
        "\n[INFO] OCR processing complete. "
        "Continuing directly into Add Receipt to Purchase History."
    )

    for index, raw_ocr_file in enumerate(
        raw_ocr_files,
        start=1,
    ):
        print("\n" + "=" * 70)
        print(
            f"Database Review {index}/{len(raw_ocr_files)}: "
            f"{raw_ocr_file.name}"
        )
        print("=" * 70)

        run_receipt_import(
            raw_ocr_file
        )



PIPELINE_EXPORT_1_FOLDER = (
    Path("PipelineExports")
    / "Export_1"
)

PIPELINE_EXPORT_1_PROMPT = (
    DATA_DIR
    / "prompts"
    / "dev_prompts"
    / "shopgraph_common_name_subcategory_completion_prompt.txt"
)


def run_pipeline_export_1() -> Path | None:
    """
    Refresh and export the two files needed for the Common Name/Sub-Category
    completion workflow.

    Destination:
        <configured import location>/PipelineExports/Export_1/

    Existing destination files are overwritten.
    Source ShopGraph files remain in place.
    """
    print("\n=== ShopGraph Pipeline Export 1 ===\n")

    try:
        import_location = get_import_location()
        export_folder = (
            import_location
            / PIPELINE_EXPORT_1_FOLDER
        )
        export_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not PIPELINE_EXPORT_1_PROMPT.exists():
            raise FileNotFoundError(
                "Prompt file was not found:"
                f"\n{PIPELINE_EXPORT_1_PROMPT.resolve()}"
            )

        # Refresh the TXT from the live Purchase History workbook first so
        # Pipeline Export 1 always sends the latest purchase-history data.
        purchase_history_txt = (
            export_purchase_history_as_csv_txt()
        )

        sources = (
            PIPELINE_EXPORT_1_PROMPT,
            purchase_history_txt,
        )

        for source in sources:
            destination = (
                export_folder
                / source.name
            )
            shutil.copy2(
                source,
                destination,
            )

        print(
            "[OK] Pipeline Export 1 complete."
        )
        print(
            "\nExport folder:"
            f"\n{export_folder.resolve()}"
        )
        print(
            "\nExported / overwritten:"
        )
        for source in sources:
            print(
                f"- {source.name}"
            )

        return export_folder.resolve()

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] Pipeline Export 1 failed:"
            f"\n{error}"
        )
        return None


def run_pipeline_part_1() -> None:
    """
    Automated single-receipt workflow:

    1. Clean generated OCR-processing data.
    2. Clear data/current_pic/.
    3. Prompt once to choose/import a supported picture.
    4. Re-read the saved picture filename from utils/config.txt.
    5. Update the Purchase History copy.
    6. Run the equivalent of Capability 3 for that exact saved picture:
       OCR Acquisition Pipeline + Data Base Builder.

    Administrative confirmation menus are intentionally skipped to minimize
    prompting. Data Base Builder's normal review/correction prompts remain.
    """
    print("\n=== ShopGraph Pipeline Part 1 ===\n")

    print("[1/6] Clean Generated Processing Data")
    generated_result = (
        clean_ocr_acquisition_pipeline_data()
    )
    print(
        "[OK] Generated processing data cleaned. "
        f"Files: {generated_result['files_deleted']}; "
        f"Folders: {generated_result['directories_deleted']}"
    )

    print("\n[2/6] Clean Current Receipt Images")
    source_result = (
        clean_current_receipt_images()
    )
    print(
        "[OK] Current receipt images cleaned. "
        f"Files: {source_result['files_deleted']}; "
        f"Folders: {source_result['directories_deleted']}"
    )

    print("\n[3/6] Import Picture")
    try:
        imported_path = (
            import_picture_to_current_folder()
        )
    except (
        OSError,
        PermissionError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] Picture import failed: {error}"
        )
        return

    if imported_path is None:
        print(
            "\n[INFO] Pipeline Part 1 cancelled "
            "before OCR processing."
        )
        return

    # Deliberately resolve the image through the saved configuration rather
    # than relying only on the function return value. This proves the same
    # saved filename can drive the next capability step.
    saved_picture = get_saved_picture_path()

    if saved_picture is None:
        print(
            "\n[ERROR] The saved picture from utils/config.txt "
            "could not be resolved in data/current_pic/."
        )
        return

    print(
        "\n[INFO] Pipeline selected picture:"
        f"\n{saved_picture.name}"
    )

    print("\n[4/6] Update Purchase History Copy")
    try:
        backup_path = (
            update_purchase_history_copy()
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        print(
            "\n[ERROR] Purchase History backup failed. "
            "OCR/Data Base Builder will not start."
            f"\n\n{error}"
        )
        return

    print(
        "[OK] Purchase History copy updated:"
        f"\n{backup_path}"
    )

    print(
        "\n[5/6] OCR Acquisition Pipeline + Data Base Builder"
    )

    try:
        raw_ocr_files = (
            run_ocr_acquisition_pipeline_for_image(
                saved_picture
            )
        )
    except Exception as error:
        print(
            "\n[ERROR] OCR Acquisition Pipeline failed:"
            f"\n{error}"
        )
        return

    if not raw_ocr_files:
        print(
            "\n[ERROR] OCR Acquisition Pipeline did not "
            "produce a raw OCR file."
        )
        return

    _run_database_builder_for_outputs(
        raw_ocr_files
    )

    print(
        "\n[OK] Core Pipeline Part 1 processing complete."
    )

    print(
        "\n[6/6] Pipeline Export 1"
    )
    export_folder = run_pipeline_export_1()

    if export_folder is None:
        print(
            "\n[WARNING] Pipeline Part 1 processing completed, "
            "but Pipeline Export 1 failed."
        )
        return

    print(
        "\n[OK] Pipeline Part 1 complete."
    )


def display_pipelines_menu() -> None:
    print("\n=== ShopGraph Pipelines ===\n")
    print("1. Pipeline Part 1")
    print("2. Pipeline Export 1")
    print("0. Return to Capabilities Menu")


def run_pipelines_menu() -> None:
    while True:
        display_pipelines_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_pipeline_part_1()

        elif option == "2":
            run_pipeline_export_1()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )
