from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from utils.constants import PREPROCESSED_DIR
from utils.perspective_correction import correct_selected_receipt
from utils.receipt_picker import choose_receipt_image
from utils.reliable_receipt_crop import crop_selected_receipt
from utils.session_state import (
    get_selected_cropped_image,
    get_selected_perspective_image,
    get_selected_source_image,
    set_selected_preprocessed_image,
)


def _enhance_for_ocr(
    image: np.ndarray,
) -> np.ndarray:
    """
    Current preprocessing stage:

    Perspective-corrected receipt
        -> 2x enlargement
        -> grayscale
        -> CLAHE contrast enhancement
        -> light denoising

    Thresholded variants will be added as a later pipeline stage.
    """
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    gray = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(
        gray
    )

    enhanced = cv2.fastNlMeansDenoising(
        enhanced,
        None,
        h=5,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    return enhanced


def get_preprocessed_path(
    source_path: str | Path,
) -> Path:
    source = Path(
        source_path
    )

    return (
        PREPROCESSED_DIR
        / f"{source.stem}_preprocessed.png"
    )


def preprocess_receipt(
    perspective_image_path: str | Path,
    source_image_path: str | Path,
) -> Path:
    perspective_path = (
        Path(perspective_image_path)
        .expanduser()
        .resolve()
    )

    source_path = (
        Path(source_image_path)
        .expanduser()
        .resolve()
    )

    if not perspective_path.exists():
        raise FileNotFoundError(
            "Perspective-corrected receipt does not exist: "
            f"{perspective_path}"
        )

    image = cv2.imread(
        str(perspective_path)
    )

    if image is None:
        raise ValueError(
            "OpenCV could not read perspective-corrected image: "
            f"{perspective_path}"
        )

    processed = _enhance_for_ocr(
        image
    )

    destination = (
        get_preprocessed_path(
            source_path
        )
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved = cv2.imwrite(
        str(destination),
        processed,
    )

    if not saved:
        raise RuntimeError(
            "OpenCV could not save preprocessed image: "
            f"{destination}"
        )

    return destination.resolve()


def _get_or_create_perspective_image() -> tuple[Path, Path, Path] | None:
    source_path = (
        get_selected_source_image()
    )

    cropped_path = (
        get_selected_cropped_image()
    )

    perspective_path = (
        get_selected_perspective_image()
    )

    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
        and perspective_path is not None
        and perspective_path.exists()
    ):
        print(
            "[INFO] Using selected perspective-corrected receipt:"
            f"\n{perspective_path}"
        )

        return (
            source_path,
            cropped_path,
            perspective_path,
        )

    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
    ):
        print(
            "[INFO] Perspective correction has not been run yet. "
            "Running it automatically."
        )

        try:
            perspective_path = (
                correct_selected_receipt(
                    source_path=source_path,
                    cropped_path=cropped_path,
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
            "\n[OK] Perspective-corrected receipt created:"
            f"\n{perspective_path}"
        )

        return (
            source_path,
            cropped_path,
            perspective_path,
        )

    print(
        "[INFO] No receipt has been selected "
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

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
        return None

    return (
        source_path,
        cropped_path,
        perspective_path,
    )


def preprocess_selected_receipt(
    source_path: Path,
    cropped_path: Path,
    perspective_path: Path,
) -> Path:
    preprocessed_path = (
        preprocess_receipt(
            perspective_image_path=perspective_path,
            source_image_path=source_path,
        )
    )

    set_selected_preprocessed_image(
        source_image=source_path,
        cropped_image=cropped_path,
        perspective_image=perspective_path,
        preprocessed_image=preprocessed_path,
    )

    return preprocessed_path


def run_image_preprocessing() -> None:
    print(
        "\n=== Image Preprocessing ===\n"
    )

    selected = (
        _get_or_create_perspective_image()
    )

    if selected is None:
        return

    (
        source_path,
        cropped_path,
        perspective_path,
    ) = selected

    try:
        output_path = (
            preprocess_selected_receipt(
                source_path=source_path,
                cropped_path=cropped_path,
                perspective_path=perspective_path,
            )
        )

        print(
            "\n[OK] Preprocessed receipt created:"
            f"\n{output_path}"
        )

        print(
            "\nThis receipt is now selected "
            "for Run OCR."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
