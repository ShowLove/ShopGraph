from utils.reliable_receipt_crop import run_reliable_receipt_crop
from utils.perspective_correction import run_perspective_correction
from utils.image_preprocessing import run_image_preprocessing
from utils.run_ocr import run_ocr
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
        "3. Image Preprocessing / 2x Enlargement"
    )

    print(
        "4. Run OCR"
    )

    print(
        "5. Export Clean Codebase"
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
            run_image_preprocessing()

        elif option == "4":
            run_ocr()

        elif option == "5":
            run_codebase_export()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


if __name__ == "__main__":
    run_utils_menu()
