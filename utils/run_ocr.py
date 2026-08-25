from __future__ import annotations

import json
from pathlib import Path

from extractors.tesseract import extract_receipt
from utils.constants import RAW_OCR_DIR
from utils.image_preprocessing import preprocess_selected_receipt
from utils.perspective_correction import correct_selected_receipt
from utils.receipt_picker import choose_receipt_image
from utils.reliable_receipt_crop import crop_selected_receipt
from utils.session_state import (
    get_selected_cropped_image,
    get_selected_perspective_image,
    get_selected_preprocessed_image,
    get_selected_source_image,
)


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
    preprocessed_path = (
        get_selected_preprocessed_image()
    )

    if (
        preprocessed_path is not None
        and preprocessed_path.exists()
    ):
        print(
            "[INFO] Using selected preprocessed image:"
            f"\n{preprocessed_path}"
        )

        return preprocessed_path

    source_path = (
        get_selected_source_image()
    )

    cropped_path = (
        get_selected_cropped_image()
    )

    perspective_path = (
        get_selected_perspective_image()
    )

    # Selected receipt has reached perspective correction.
    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
        and perspective_path is not None
        and perspective_path.exists()
    ):
        try:
            preprocessed_path = (
                preprocess_selected_receipt(
                    source_path=source_path,
                    cropped_path=cropped_path,
                    perspective_path=perspective_path,
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

    # Selected receipt has only been cropped.
    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
    ):
        try:
            perspective_path = (
                correct_selected_receipt(
                    source_path=source_path,
                    cropped_path=cropped_path,
                )
            )

            print(
                "\n[OK] Perspective-corrected receipt created:"
                f"\n{perspective_path}"
            )

            preprocessed_path = (
                preprocess_selected_receipt(
                    source_path=source_path,
                    cropped_path=cropped_path,
                    perspective_path=perspective_path,
                )
            )

            print(
                "\n[OK] Preprocessed receipt created:"
                f"\n{preprocessed_path}"
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

        return preprocessed_path

    # Simplified workflow:
    # Nothing has been selected. Prompt once and automatically run
    # crop -> perspective correction -> preprocessing.
    print(
        "[INFO] No receipt has been prepared "
        "in this session yet."
    )

    source_path = choose_receipt_image()

    if source_path is None:
        return None

    try:
        cropped_path = (
            crop_selected_receipt(
                source_path
            )
        )

        print(
            "\n[OK] Cropped receipt created:"
            f"\n{cropped_path}"
        )

        perspective_path = (
            correct_selected_receipt(
                source_path=source_path,
                cropped_path=cropped_path,
            )
        )

        print(
            "\n[OK] Perspective-corrected receipt created:"
            f"\n{perspective_path}"
        )

        preprocessed_path = (
            preprocess_selected_receipt(
                source_path=source_path,
                cropped_path=cropped_path,
                perspective_path=perspective_path,
            )
        )

        print(
            "\n[OK] Preprocessed receipt created:"
            f"\n{preprocessed_path}"
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

    return preprocessed_path


def run_ocr() -> None:
    print(
        "\n=== Run OCR ===\n"
    )

    image_path = (
        _get_ocr_input_image()
    )

    if image_path is None:
        return

    source_path = (
        get_selected_source_image()
    )

    if source_path is not None:
        output_stem = (
            source_path.stem
        )
    else:
        output_stem = (
            image_path.stem
            .removesuffix(
                "_preprocessed"
            )
        )

    output_path = (
        RAW_OCR_DIR
        / f"{output_stem}_raw_ocr.json"
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
