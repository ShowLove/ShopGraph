from utils.reliable_receipt_crop import run_reliable_receipt_crop
from utils.perspective_correction import run_perspective_correction
from utils.image_enlargement import run_image_enlargement
from utils.ocr_image_variants import run_ocr_image_variants
from utils.run_ocr import run_ocr
from utils.compare_ocr import run_compare_ocr
from utils.export_codebase import run_codebase_export


def display_utils_menu() -> None:
    print(
        "\n=== ShopGraph Utilities ===\n"
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
        "7. Export Clean Codebase"
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
            run_codebase_export()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


if __name__ == "__main__":
    run_utils_menu()
