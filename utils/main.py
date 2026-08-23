from utils.run_ocr import run_ocr
from utils.export_codebase import run_codebase_export


def display_utils_menu() -> None:
    print("\n=== ShopGraph Utilities ===\n")
    print("1. Run OCR")
    print("2. Export Clean Codebase")
    print("0. Return to Main")


def run_utils_menu() -> None:
    while True:
        display_utils_menu()

        option = input("\nSelect option: ").strip()

        if option == "1":
            run_ocr()

        elif option == "2":
            run_codebase_export()

        elif option == "0":
            return

        else:
            print("\n[ERROR] Invalid option.")


if __name__ == "__main__":
    run_utils_menu()