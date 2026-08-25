from __future__ import annotations

import json
from pathlib import Path

from extractors.tesseract import extract_receipt
from utils.constants import RAW_OCR_DIR
from utils.image_preprocessing import preprocess_selected_receipt
from utils.receipt_picker import choose_receipt_image
from utils.session_state import get_selected_preprocessed_image


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def _get_ocr_input_image() -> Path | None:
    selected_preprocessed = (
        get_selected_preprocessed_image()
    )

    if (
        selected_preprocessed is not None
        and selected_preprocessed.exists()
    ):
        print(
            "[INFO] Using selected preprocessed image:"
            f"\n{selected_preprocessed}"
        )
        return selected_preprocessed

    print(
        "[INFO] No receipt has been preprocessed "
        "in this session yet."
    )

    source_path = choose_receipt_image()

    if source_path is None:
        return None

    try:
        preprocessed_path = (
            preprocess_selected_receipt(
                source_path
            )
        )
    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return None

    print(
        "\n[OK] Preprocessed receipt created:"
        f"\n{preprocessed_path}"
    )

    return preprocessed_path


def run_ocr() -> None:
    print("\n=== Run OCR ===\n")

    image_path = _get_ocr_input_image()

    if image_path is None:
        return

    output_path = (
        RAW_OCR_DIR
        / f"{image_path.stem}_raw_ocr.json"
    )

    result = extract_receipt(
        image_path
    )

    save_json(
        data=result,
        output_path=output_path,
    )

    print(
        "\n[OK] OCR JSON created:"
        f"\n{output_path.resolve()}"
    )
