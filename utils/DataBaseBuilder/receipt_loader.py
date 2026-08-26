from __future__ import annotations

import json
from pathlib import Path

from utils.constants import RAW_OCR_DIR


def list_raw_ocr_files() -> list[Path]:
    if not RAW_OCR_DIR.exists():
        return []

    return sorted(
        RAW_OCR_DIR.glob("*_raw_ocr.json"),
        key=lambda path: path.name.lower(),
    )


def choose_raw_ocr_file() -> Path | None:
    files = list_raw_ocr_files()

    if not files:
        print(
            "\n[INFO] No raw OCR JSON files were found in:"
            f"\n{RAW_OCR_DIR}"
        )
        return None

    print("\nSelect raw OCR file:\n")

    for index, path in enumerate(files, start=1):
        print(f"{index}. {path.name}")

    print("0. Cancel")

    while True:
        choice = input("\nSelect option: ").strip()

        if choice == "0":
            return None

        if choice.isdigit():
            index = int(choice)

            if 1 <= index <= len(files):
                return files[index - 1]

        print("\n[ERROR] Invalid option.")


def load_ocr_lines(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    lines = data.get("text")

    if not isinstance(lines, list):
        raise ValueError(
            "Raw OCR JSON must contain a top-level 'text' list."
        )

    validated = []

    for line in lines:
        if not isinstance(line, dict):
            continue

        line_number = line.get("line_number")
        text = line.get("text")

        if not isinstance(line_number, int):
            continue

        if not isinstance(text, str):
            continue

        if not text.strip():
            continue

        validated.append(line)

    validated.sort(key=lambda item: item["line_number"])

    if not validated:
        raise ValueError(
            "Raw OCR JSON contains no usable line_number/text records."
        )

    return validated
