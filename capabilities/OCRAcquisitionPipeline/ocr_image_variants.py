from __future__ import annotations

from pathlib import Path

import cv2

from capabilities.OCRAcquisitionPipeline.constants import OCR_VARIANTS_DIR
from capabilities.OCRAcquisitionPipeline.image_enlargement import ensure_enlarged_receipt
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_grayscale_image,
    get_selected_threshold_image,
    set_selected_ocr_variants,
)


def get_grayscale_path(
    source_path: str | Path,
) -> Path:
    source = Path(source_path)

    return (
        OCR_VARIANTS_DIR
        / f"{source.stem}_grayscale.png"
    )


def get_threshold_path(
    source_path: str | Path,
) -> Path:
    source = Path(source_path)

    return (
        OCR_VARIANTS_DIR
        / f"{source.stem}_threshold.png"
    )


def generate_variants(
    enlarged_image_path: str | Path,
    source_image_path: str | Path,
) -> tuple[Path, Path]:
    enlarged_path = (
        Path(enlarged_image_path)
        .expanduser()
        .resolve()
    )

    source_path = (
        Path(source_image_path)
        .expanduser()
        .resolve()
    )

    image = cv2.imread(
        str(enlarged_path)
    )

    if image is None:
        raise ValueError(
            "OpenCV could not read enlarged image: "
            f"{enlarged_path}"
        )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    grayscale_enhanced = clahe.apply(
        gray
    )

    grayscale_enhanced = cv2.fastNlMeansDenoising(
        grayscale_enhanced,
        None,
        h=5,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    thresholded = cv2.adaptiveThreshold(
        grayscale_enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        15,
    )

    grayscale_path = get_grayscale_path(
        source_path
    )

    threshold_path = get_threshold_path(
        source_path
    )

    OCR_VARIANTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not cv2.imwrite(
        str(grayscale_path),
        grayscale_enhanced,
    ):
        raise RuntimeError(
            "Could not save grayscale OCR variant."
        )

    if not cv2.imwrite(
        str(threshold_path),
        thresholded,
    ):
        raise RuntimeError(
            "Could not save threshold OCR variant."
        )

    return (
        grayscale_path.resolve(),
        threshold_path.resolve(),
    )


def ensure_ocr_variants() -> tuple[Path, Path, Path, Path, Path, Path] | None:
    selected = ensure_enlarged_receipt()

    if selected is None:
        return None

    (
        source_path,
        cropped_path,
        perspective_path,
        enlarged_path,
    ) = selected

    grayscale_path = get_selected_grayscale_image()
    threshold_path = get_selected_threshold_image()

    if (
        grayscale_path is not None
        and grayscale_path.exists()
        and threshold_path is not None
        and threshold_path.exists()
    ):
        return (
            source_path,
            cropped_path,
            perspective_path,
            enlarged_path,
            grayscale_path,
            threshold_path,
        )

    (
        grayscale_path,
        threshold_path,
    ) = generate_variants(
        enlarged_image_path=enlarged_path,
        source_image_path=source_path,
    )

    set_selected_ocr_variants(
        source_image=source_path,
        cropped_image=cropped_path,
        perspective_image=perspective_path,
        enlarged_image=enlarged_path,
        grayscale_image=grayscale_path,
        threshold_image=threshold_path,
    )

    return (
        source_path,
        cropped_path,
        perspective_path,
        enlarged_path,
        grayscale_path,
        threshold_path,
    )


def run_ocr_image_variants() -> None:
    print(
        "\n=== OCR Image Variants ===\n"
    )

    try:
        selected = ensure_ocr_variants()

        if selected is None:
            return

        grayscale_path = selected[4]
        threshold_path = selected[5]

        print(
            "\n[OK] Grayscale enhanced variant:"
            f"\n{grayscale_path}"
        )

        print(
            "\n[OK] Thresholded variant:"
            f"\n{threshold_path}"
        )

        print(
            "\nThese variants are now selected "
            "for multi-PSM OCR."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
