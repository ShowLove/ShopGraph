from utils.reliable_receipt_crop import run_reliable_receipt_crop
from utils.perspective_correction import run_perspective_correction
from utils.image_enlargement import run_image_enlargement
from utils.ocr_image_variants import run_ocr_image_variants
from utils.run_ocr import run_ocr
from utils.compare_ocr import run_compare_ocr
from utils.export_codebase import run_codebase_export


# ---------------------------------------------------------------------------
# OCR ACQUISITION PIPELINE
# ---------------------------------------------------------------------------

def run_ocr_acquisition_pipeline() -> None:
    """
    Run the complete OCR Acquisition Pipeline in order.

    The existing smart workflow is preserved. The first stage prompts
    for the receipt image. Each later stage automatically uses the
    receipt and artifacts already selected/generated in this session.

    Pipeline:
        1. Reliable Receipt Detection / Crop
        2. Perspective Correction
        3. 2x Enlargement
        4. Generate OCR Image Variants
        5. Run OCR - PSM 4 / 6 / 11
        6. Compare OCR Results / Build Raw OCR JSON
    """
    print(
        "\n=== OCR Acquisition Pipeline ===\n"
    )

    print(
        "[1/6] Reliable Receipt Detection / Crop"
    )
    run_reliable_receipt_crop()

    print(
        "\n[2/6] Perspective Correction"
    )
    run_perspective_correction()

    print(
        "\n[3/6] 2x Enlargement"
    )
    run_image_enlargement()

    print(
        "\n[4/6] Generate OCR Image Variants"
    )
    run_ocr_image_variants()

    print(
        "\n[5/6] Run OCR - PSM 4 / 6 / 11"
    )
    run_ocr()

    print(
        "\n[6/6] Compare OCR Results / Build Raw OCR JSON"
    )
    run_compare_ocr()

    print(
        "\n[OK] OCR Acquisition Pipeline complete."
    )


# ---------------------------------------------------------------------------
# CAPABILITIES
# ---------------------------------------------------------------------------

def display_capabilities_menu() -> None:
    print(
        "\n=== ShopGraph Capabilities ===\n"
    )

    print(
        "1. OCR Acquisition Pipeline"
    )

    print(
        "0. Return to Utilities Menu"
    )


def run_capabilities_menu() -> None:
    while True:
        display_capabilities_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            run_ocr_acquisition_pipeline()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


# ---------------------------------------------------------------------------
# CAPABILITY SUB TASKS
# ---------------------------------------------------------------------------

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
        "3. 2x Enlargement"
    )

    print(
        "4. Generate OCR Image Variants"
    )

    print(
        "5. Run OCR - PSM 4 / 6 / 11"
    )

    print(
        "6. Compare OCR Results / Build Raw OCR JSON"
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


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def display_standalone_utilities_menu() -> None:
    print(
        "\n=== ShopGraph Utilities ===\n"
    )

    print(
        "1. Export Clean Codebase"
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

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


# ---------------------------------------------------------------------------
# TOP-LEVEL UTILS MENU
# ---------------------------------------------------------------------------

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

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


if __name__ == "__main__":
    run_utils_menu()
