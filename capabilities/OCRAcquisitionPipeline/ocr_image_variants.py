from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from capabilities.OCRAcquisitionPipeline.constants import OCR_VARIANTS_DIR
from capabilities.OCRAcquisitionPipeline.image_enlargement import ensure_enlarged_receipt
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_grayscale_image,
    get_selected_threshold_image,
    set_selected_ocr_variants,
)


def _variant_path(source_path: str | Path, suffix: str) -> Path:
    source = Path(source_path)
    return OCR_VARIANTS_DIR / f"{source.stem}_{suffix}.png"


def get_grayscale_path(source_path: str | Path) -> Path:
    return _variant_path(source_path, "grayscale")


def get_threshold_path(source_path: str | Path) -> Path:
    return _variant_path(source_path, "threshold")


def get_ocr_variant_paths(source_path: str | Path) -> dict[str, Path]:
    """
    Deterministic paths for every OCR variant. The first two names are retained
    for compatibility with the existing session-state flow.
    """
    return {
        "grayscale": get_grayscale_path(source_path),
        "threshold": get_threshold_path(source_path),
        "sharpened": _variant_path(source_path, "sharpened"),
        "otsu": _variant_path(source_path, "otsu"),
        "illumination": _variant_path(source_path, "illumination"),
    }


def _illumination_normalize(gray: np.ndarray) -> np.ndarray:
    """
    Remove slow-changing paper/shadow illumination while retaining print.
    """
    background = cv2.GaussianBlur(gray, (0, 0), sigmaX=31, sigmaY=31)
    normalized = cv2.divide(gray, background, scale=255)
    normalized = cv2.normalize(
        normalized,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
    )
    return normalized.astype(np.uint8)


def generate_variants(
    enlarged_image_path: str | Path,
    source_image_path: str | Path,
) -> tuple[Path, Path]:
    enlarged_path = Path(enlarged_image_path).expanduser().resolve()
    source_path = Path(source_image_path).expanduser().resolve()

    image = cv2.imread(str(enlarged_path))
    if image is None:
        raise ValueError(
            "OpenCV could not read normalized image: "
            f"{enlarged_path}"
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )
    grayscale_enhanced = clahe.apply(gray)
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

    blurred = cv2.GaussianBlur(
        grayscale_enhanced,
        (0, 0),
        sigmaX=1.2,
    )
    sharpened = cv2.addWeighted(
        grayscale_enhanced,
        1.8,
        blurred,
        -0.8,
        0,
    )

    _, otsu = cv2.threshold(
        grayscale_enhanced,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    illumination_gray = _illumination_normalize(gray)
    illumination = cv2.adaptiveThreshold(
        illumination_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        51,
        11,
    )

    variants = {
        "grayscale": grayscale_enhanced,
        "threshold": thresholded,
        "sharpened": sharpened,
        "otsu": otsu,
        "illumination": illumination,
    }

    paths = get_ocr_variant_paths(source_path)
    OCR_VARIANTS_DIR.mkdir(parents=True, exist_ok=True)

    for name, variant in variants.items():
        path = paths[name]
        if not cv2.imwrite(str(path), variant):
            raise RuntimeError(
                f"Could not save {name} OCR variant."
            )

    return (
        paths["grayscale"].resolve(),
        paths["threshold"].resolve(),
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
    all_paths = get_ocr_variant_paths(source_path)

    all_exist = all(path.exists() for path in all_paths.values())

    if (
        grayscale_path is not None
        and grayscale_path.exists()
        and threshold_path is not None
        and threshold_path.exists()
        and all_exist
    ):
        return (
            source_path,
            cropped_path,
            perspective_path,
            enlarged_path,
            grayscale_path,
            threshold_path,
        )

    grayscale_path, threshold_path = generate_variants(
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
    print("\n=== OCR Image Variants ===\n")

    try:
        selected = ensure_ocr_variants()
        if selected is None:
            return

        paths = get_ocr_variant_paths(selected[0])

        print("\n[OK] OCR variants created:")
        for name, path in paths.items():
            print(f"- {name}: {path}")

        print(
            "\nThese variants are now selected "
            "for multi-PSM OCR."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"\n[ERROR] {error}")
