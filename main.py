from __future__ import annotations

import json
from pathlib import Path

from extractors.tesseract import extract_receipt
from utils.codebase_bundler import export_codebase_bundle


DEFAULT_OUTPUT_DIR = Path("data/raw_ocr")


def save_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def run_ocr() -> None:
    print("\n=== Run OCR ===\n")

    raw_path = input("Receipt image path: ").strip()

    if not raw_path:
        print("[ERROR] No image path provided.")
        return

    image_path = Path(raw_path).expanduser().resolve()

    if not image_path.exists():
        print(f"[ERROR] Receipt image does not exist: {image_path}")
        return

    if not image_path.is_file():
        print(f"[ERROR] Receipt image path is not a file: {image_path}")
        return

    output_path = (
        DEFAULT_OUTPUT_DIR
        / f"{image_path.stem}_raw_ocr.json"
    )

    result = extract_receipt(image_path)

    save_json(
        data=result,
        output_path=output_path,
    )

    print(
        f"\n[OK] OCR JSON created:\n"
        f"{output_path.resolve()}"
    )


def export_codebase() -> None:
    print("\n=== Export Clean Codebase ===\n")

    output_path = export_codebase_bundle()

    print(
        f"\n[OK] Codebase bundle created:\n"
        f"{output_path}"
    )


def display_menu() -> None:
    print("\n=== ShopGraph ===\n")
    print("1. Run OCR")
    print("2. Export Clean Codebase")
    print("0. Exit")


def main() -> None:
    while True:
        display_menu()

        option = input("\nSelect option: ").strip()

        if option == "1":
            run_ocr()

        elif option == "2":
            export_codebase()

        elif option == "0":
            print("\nGoodbye.")
            break

        else:
            print("\n[ERROR] Invalid option.")


if __name__ == "__main__":
    main()
