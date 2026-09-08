
from __future__ import annotations

import shutil
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.main_OCRAcquisitionPipeline import (
    run_ocr_acquisition_pipeline_for_image,
)
from capabilities.OllamaReceiptAcquisitionPipeline.main_OllamaReceiptAcquisitionPipeline import (
    run_ollama_receipt_acquisition_pipeline_for_image,
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
from utils.export_category_manager_txt import (
    export_category_manager_as_csv_txt,
)
from utils.DataBaseBuilder.excel.category_manager import (
    create_or_refresh_category_manager,
    apply_category_manager,
)
from utils.DataBaseBuilder.budget_plans.budget_plan_menu import (
    refresh_all_budget_plans,
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



PIPELINE_EXPORT_2_FOLDER = (
    Path("PipelineExports")
    / "Export_2"
)

PIPELINE_EXPORT_2_PROMPT = (
    DATA_DIR
    / "prompts"
    / "dev_prompts"
    / "shopgraph_category_completion_prompt.txt"
)


def run_pipeline_export_2() -> Path | None:
    """
    Refresh and export the three files needed for broad Category completion.

    Destination:
        <configured import location>/PipelineExports/Export_2/

    Existing destination files are overwritten.
    Source ShopGraph files remain in place.
    """
    print("\n=== ShopGraph Pipeline Export 2 ===\n")

    try:
        import_location = get_import_location()
        export_folder = (
            import_location
            / PIPELINE_EXPORT_2_FOLDER
        )
        export_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not PIPELINE_EXPORT_2_PROMPT.exists():
            raise FileNotFoundError(
                "Prompt file was not found:"
                f"\n{PIPELINE_EXPORT_2_PROMPT.resolve()}"
            )

        # Always refresh both TXT files from the live workbook immediately
        # before copying them into Export_2.
        category_manager_txt = (
            export_category_manager_as_csv_txt()
        )
        purchase_history_txt = (
            export_purchase_history_as_csv_txt()
        )

        sources = (
            category_manager_txt,
            PIPELINE_EXPORT_2_PROMPT,
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
            "[OK] Pipeline Export 2 complete."
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
            f"\n[ERROR] Pipeline Export 2 failed:"
            f"\n{error}"
        )
        return None


def run_category_manager_completion() -> None:
    """
    Refresh Category Manager and, only if that succeeds, create Pipeline Export 2.
    """
    print(
        "\n=== ShopGraph Category Manager Completion ===\n"
    )

    print(
        "[1/2] Create / Refresh Category Manager"
    )

    try:
        result = (
            create_or_refresh_category_manager()
        )
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
    ) as error:
        print(
            "\n[ERROR] Category Manager refresh failed."
            f"\n\n{error}"
        )
        print(
            "\n[INFO] Pipeline Export 2 was not created."
        )
        return

    print(
        "\n[OK] Category Manager created / refreshed."
    )
    print(
        f"Categories assigned: {result['category_count']}"
    )
    print(
        f"Sub-Categories: {result['subcategory_count']}"
    )
    print(
        f"Common Names: {result['product_count']}"
    )
    print(
        "Workbook:"
        f"\n{result['workbook_path']}"
    )

    print(
        "\n[2/2] Pipeline Export 2"
    )

    export_folder = run_pipeline_export_2()

    if export_folder is None:
        print(
            "\n[WARNING] Category Manager refresh succeeded, "
            "but Pipeline Export 2 failed."
        )
        return

    print(
        "\n[OK] Category Manager Completion complete."
    )



def run_finalize_taxonomy_and_budgets() -> None:
    """
    Finalize the current ShopGraph taxonomy and refresh every Budget Plan.

    Workflow:
        1. Apply Category Manager to Purchase History.
        2. Refresh All Budget Plans.

    Category Manager validation must succeed before Budget Plans are refreshed.
    Existing Category Manager and Budget Plan business logic is reused directly.
    """
    print(
        "\n=== ShopGraph Finalize Taxonomy + Budgets ===\n"
    )

    print(
        "[1/2] Apply Category Manager to Purchase History"
    )

    try:
        result = apply_category_manager()
    except (
        OSError,
        ValueError,
    ) as error:
        print(
            "\n[ERROR] Category Manager could not be applied."
            f"\n\n{error}"
        )
        print(
            "\n[INFO] Budget Plans were not refreshed."
        )
        return

    if not result["success"]:
        print(
            "\n" + result["report"]
        )
        print(
            "\n[INFO] Budget Plans were not refreshed."
        )
        return

    print(
        "\n[OK] Purchase History Sub-Categories updated successfully."
    )
    print(
        f"Purchase History rows changed: {result['changed_rows']}"
    )
    print(
        f"Categories: {result['category_count']}"
    )
    print(
        f"Sub-Categories: {result['subcategory_count']}"
    )
    print(
        f"Common Names: {result['product_count']}"
    )
    print(
        "Category Manager cleaned and synchronized."
    )
    print(
        f"\nWorkbook:\n{result['workbook_path']}"
    )

    print(
        "\n[2/2] Refresh All Budget Plans"
    )

    # Reuse the existing Budget Plans action exactly. It already handles:
    # - no plans,
    # - individual plan failures,
    # - success/failure counts,
    # - normal ShopGraph output.
    refresh_all_budget_plans()

    print(
        "\n[OK] Finalize Taxonomy + Budgets workflow complete."
    )


def _run_pipeline_part_1_with_acquisition(
    *,
    title: str,
    acquisition_label: str,
    acquisition_function,
) -> None:
    """
    Shared Pipeline Part 1 orchestration.

    The original OCR and local Ollama variants deliberately reuse the same
    cleanup, picture import, Purchase History backup, Data Base Builder, and
    Pipeline Export 1 logic. Only the receipt-acquisition engine differs.
    """
    print(f"\n=== {title} ===\n")

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
            f"\n[INFO] {title} cancelled "
            "before receipt acquisition."
        )
        return

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
            f"{acquisition_label}/Data Base Builder will not start."
            f"\n\n{error}"
        )
        return

    print(
        "[OK] Purchase History copy updated:"
        f"\n{backup_path}"
    )

    print(
        f"\n[5/6] {acquisition_label} + Data Base Builder"
    )

    try:
        raw_receipt_files = (
            acquisition_function(
                saved_picture
            )
        )
    except Exception as error:
        print(
            f"\n[ERROR] {acquisition_label} failed:"
            f"\n{error}"
        )
        return

    if not raw_receipt_files:
        print(
            f"\n[ERROR] {acquisition_label} did not "
            "produce a compatible raw receipt file."
        )
        return

    _run_database_builder_for_outputs(
        raw_receipt_files
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
            f"\n[WARNING] {title} processing completed, "
            "but Pipeline Export 1 failed."
        )
        return

    print(
        f"\n[OK] {title} complete."
    )


def run_pipeline_part_1() -> None:
    """
    Existing Pipeline Part 1. It continues to use the original OCR engine.
    """
    _run_pipeline_part_1_with_acquisition(
        title="ShopGraph Pipeline Part 1",
        acquisition_label="OCR Acquisition Pipeline",
        acquisition_function=(
            run_ocr_acquisition_pipeline_for_image
        ),
    )


def run_pipeline_part_1_ollama() -> None:
    """
    Parallel Pipeline Part 1 using local Ollama receipt acquisition.

    Only stage 5 differs from the original workflow.
    """
    _run_pipeline_part_1_with_acquisition(
        title=(
            "ShopGraph Pipeline Part 1 - "
            "Ollama Receipt Acquisition"
        ),
        acquisition_label=(
            "Ollama Receipt Acquisition Pipeline"
        ),
        acquisition_function=(
            run_ollama_receipt_acquisition_pipeline_for_image
        ),
    )


def display_pipelines_menu() -> None:
    print("\n=== ShopGraph Pipelines ===\n")
    print("1. Pipeline Part 1")
    print("2. Pipeline Part 1 - Ollama Receipt Acquisition")
    print("3. Pipeline Export 1")
    print("4. Category Manager Completion")
    print("5. Pipeline Export 2")
    print("6. Finalize Taxonomy + Budgets")
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
            run_pipeline_part_1_ollama()

        elif option == "3":
            run_pipeline_export_1()

        elif option == "4":
            run_category_manager_completion()

        elif option == "5":
            run_pipeline_export_2()

        elif option == "6":
            run_finalize_taxonomy_and_budgets()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )
