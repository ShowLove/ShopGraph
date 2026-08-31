from capabilities.OCRAcquisitionPipeline.main_OCRAcquisitionPipeline import (
    run_ocr_acquisition_pipeline,
    run_ocr_acquisition_pipeline_all_images,
)
from capabilities.OCRAcquisitionPipeline.reliable_receipt_crop import (
    run_reliable_receipt_crop,
)
from capabilities.OCRAcquisitionPipeline.perspective_correction import (
    run_perspective_correction,
)
from capabilities.OCRAcquisitionPipeline.image_enlargement import (
    run_image_enlargement,
)
from capabilities.OCRAcquisitionPipeline.ocr_image_variants import (
    run_ocr_image_variants,
)
from capabilities.OCRAcquisitionPipeline.run_ocr import (
    run_ocr,
)
from capabilities.OCRAcquisitionPipeline.compare_ocr import (
    run_compare_ocr,
)
from capabilities.OCRAcquisitionPipeline.refine_json import (
    run_refine_json,
)

from utils.export_codebase import (
    run_codebase_export,
)
from utils.clean_ocr_acquisition_pipeline import (
    run_ocr_acquisition_pipeline_cleanup,
)
from utils.DataBaseBuilder.data_base_builder_main import (
    run_data_base_builder_menu,
    run_receipt_import,
)
from utils.ocr_benchmark_evaluator import (
    run_benchmark_evaluator,
)
from utils.pdf_to_jpg import (
    run_pdf_to_jpg_converter,
)
from utils.clean_source_data import (
    run_source_data_cleanup,
)
from utils.export_purchase_history_txt import (
    run_purchase_history_txt_export,
)
from utils.code_update_importer import (
    run_code_update_importer_menu,
)
from utils.purchase_history_backup import (
    run_purchase_history_backup,
)
from utils.picture_importer import (
    run_picture_importer_menu,
)


def display_capabilities_menu() -> None:
    print("\n=== ShopGraph Capabilities ===\n")
    print("1. OCR Acquisition Pipeline")
    print("2. OCR Acquisition Pipeline - All Images")
    print("3. OCR Acquisition Pipeline + Data Base Builder")
    print("4. OCR Acquisition Pipeline - All Images + Data Base Builder")
    print("0. Return to Utilities Menu")


def _run_database_builder_for_outputs(raw_ocr_files) -> None:
    if not raw_ocr_files:
        return

    print("\n=== Data Base Builder ===")
    print(
        "\n[INFO] OCR processing complete. "
        "Continuing directly into Add Receipt to Purchase History."
    )

    for index, raw_ocr_file in enumerate(raw_ocr_files, start=1):
        print("\n" + "=" * 70)
        print(
            f"Database Review {index}/{len(raw_ocr_files)}: "
            f"{raw_ocr_file.name}"
        )
        print("=" * 70)
        run_receipt_import(raw_ocr_file)


def run_capabilities_menu() -> None:
    while True:
        display_capabilities_menu()
        option = input("\nSelect option: ").strip()

        if option == "1":
            run_ocr_acquisition_pipeline()
        elif option == "2":
            run_ocr_acquisition_pipeline_all_images()
        elif option == "3":
            raw_ocr_files = run_ocr_acquisition_pipeline()
            _run_database_builder_for_outputs(raw_ocr_files)
        elif option == "4":
            raw_ocr_files = run_ocr_acquisition_pipeline_all_images()
            _run_database_builder_for_outputs(raw_ocr_files)
        elif option == "0":
            return
        else:
            print("\n[ERROR] Invalid option.")


def display_capability_sub_tasks_menu() -> None:
    print(
        "\n=== ShopGraph Capability Sub Tasks ===\n"
    )
    print(
        "1. OCR Acquisition Pipeline"
    )
    print(
        "0. Return to Utilities Menu"
    )


def display_ocr_acquisition_sub_tasks_menu() -> None:
    print(
        "\n=== OCR Acquisition Pipeline - Sub Tasks ===\n"
    )
    print(
        "1. Reliable Receipt Detection / Crop"
    )
    print(
        "2. Perspective Correction"
    )
    print(
        "3. Receipt Size Normalization"
    )
    print(
        "4. Generate OCR Image Variants"
    )
    print(
        "5. Run Multi-Variant / Multi-PSM OCR"
    )
    print(
        "6. Compare OCR Results / Build Raw OCR JSON"
    )
    print(
        "7. Refine Json File"
    )
    print(
        "0. Return to Capability Sub Tasks"
    )


def run_ocr_acquisition_sub_tasks_menu() -> None:
    while True:
        display_ocr_acquisition_sub_tasks_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_reliable_receipt_crop()
        elif option == "2":
            run_perspective_correction()
        elif option == "3":
            run_image_enlargement()
        elif option == "4":
            run_ocr_image_variants()
        elif option == "5":
            run_ocr()
        elif option == "6":
            run_compare_ocr()
        elif option == "7":
            run_refine_json()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )


def run_capability_sub_tasks_menu() -> None:
    while True:
        display_capability_sub_tasks_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_ocr_acquisition_sub_tasks_menu()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )


def display_standalone_utilities_menu() -> None:
    print(
        "\n=== ShopGraph Utilities ===\n"
    )
    print(
        "1. Export Clean Codebase"
    )
    print(
        "2. Clean Generated Processing Data"
    )
    print(
        "3. Evaluate OCR Against Benchmarks"
    )
    print(
        "4. Convert PDF Files to JPG"
    )
    print(
        "5. Clean Source Data"
    )
    print(
        "6. Export Purchase History as CSV TXT"
    )
    print(
        "7. Import Code Update ZIP"
    )
    print(
        "8. Update Purchase History Copy"
    )
    print(
        "9. Import Picture to Current Folder"
    )
    print(
        "0. Return to Utilities Menu"
    )


def run_standalone_utilities_menu() -> None:
    while True:
        display_standalone_utilities_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_codebase_export()
        elif option == "2":
            run_ocr_acquisition_pipeline_cleanup()
        elif option == "3":
            run_benchmark_evaluator()
        elif option == "4":
            run_pdf_to_jpg_converter()
        elif option == "5":
            run_source_data_cleanup()
        elif option == "6":
            run_purchase_history_txt_export()
        elif option == "7":
            run_code_update_importer_menu()
        elif option == "8":
            run_purchase_history_backup()
        elif option == "9":
            run_picture_importer_menu()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )


def display_utils_menu() -> None:
    print(
        "\n=== ShopGraph Utilities ===\n"
    )
    print(
        "1. Capabilities"
    )
    print(
        "2. Capability Sub Tasks"
    )
    print(
        "3. Utilities"
    )
    print(
        "4. Data Base Builder"
    )
    print(
        "0. Return to Main"
    )


def run_utils_menu() -> None:
    while True:
        display_utils_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_capabilities_menu()
        elif option == "2":
            run_capability_sub_tasks_menu()
        elif option == "3":
            run_standalone_utilities_menu()
        elif option == "4":
            run_data_base_builder_menu()
        elif option == "0":
            return
        else:
            print(
                "\n[ERROR] Invalid option."
            )
