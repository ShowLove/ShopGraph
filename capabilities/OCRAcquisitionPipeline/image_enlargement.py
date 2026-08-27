from __future__ import annotations

from pathlib import Path

import cv2

from capabilities.OCRAcquisitionPipeline.constants import ENLARGED_DIR
from capabilities.OCRAcquisitionPipeline.perspective_correction import correct_selected_receipt
from capabilities.OCRAcquisitionPipeline.receipt_picker import choose_receipt_image
from capabilities.OCRAcquisitionPipeline.reliable_receipt_crop import crop_selected_receipt
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_cropped_image,
    get_selected_enlarged_image,
    get_selected_perspective_image,
    get_selected_source_image,
    set_selected_enlarged_image,
)


# Normalize every perspective-corrected receipt to approximately the same
# physical OCR scale instead of blindly enlarging every photo by 2x.
TARGET_RECEIPT_WIDTH = 2000
MIN_TARGET_WIDTH = 1600
MAX_TARGET_WIDTH = 2200


def get_enlarged_path(source_path: str | Path) -> Path:
    source = Path(source_path)
    return ENLARGED_DIR / f"{source.stem}_normalized.png"


def _target_width_for(image) -> int:
    """
    Use a stable OCR width while avoiding needless enlargement of already
    high-resolution receipts.
    """
    width = image.shape[1]

    if width < MIN_TARGET_WIDTH:
        return TARGET_RECEIPT_WIDTH

    if width > MAX_TARGET_WIDTH:
        return TARGET_RECEIPT_WIDTH

    return width


def enlarge_receipt(
    perspective_image_path: str | Path,
    source_image_path: str | Path,
) -> Path:
    perspective_path = Path(perspective_image_path).expanduser().resolve()
    source_path = Path(source_image_path).expanduser().resolve()

    if not perspective_path.exists():
        raise FileNotFoundError(
            "Perspective-corrected receipt does not exist: "
            f"{perspective_path}"
        )

    image = cv2.imread(str(perspective_path))
    if image is None:
        raise ValueError(
            "OpenCV could not read perspective-corrected receipt: "
            f"{perspective_path}"
        )

    original_height, original_width = image.shape[:2]
    target_width = _target_width_for(image)
    scale = target_width / float(original_width)
    target_height = max(1, int(round(original_height * scale)))

    interpolation = (
        cv2.INTER_CUBIC
        if scale >= 1.0
        else cv2.INTER_AREA
    )

    normalized = cv2.resize(
        image,
        (target_width, target_height),
        interpolation=interpolation,
    )

    destination = get_enlarged_path(source_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(destination), normalized):
        raise RuntimeError(
            "OpenCV could not save normalized receipt: "
            f"{destination}"
        )

    print(
        "[INFO] Receipt size normalization: "
        f"{original_width}x{original_height} -> "
        f"{target_width}x{target_height} "
        f"(scale {scale:.3f}x)"
    )

    return destination.resolve()


def ensure_enlarged_receipt() -> tuple[Path, Path, Path, Path] | None:
    source_path = get_selected_source_image()
    cropped_path = get_selected_cropped_image()
    perspective_path = get_selected_perspective_image()
    enlarged_path = get_selected_enlarged_image()

    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
        and perspective_path is not None
        and perspective_path.exists()
        and enlarged_path is not None
        and enlarged_path.exists()
    ):
        return (
            source_path,
            cropped_path,
            perspective_path,
            enlarged_path,
        )

    if source_path is None or not source_path.exists():
        source_path = choose_receipt_image()
        if source_path is None:
            return None

    if cropped_path is None or not cropped_path.exists():
        cropped_path = crop_selected_receipt(source_path)
        print(
            "\n[OK] Cropped receipt created:"
            f"\n{cropped_path}"
        )

    if perspective_path is None or not perspective_path.exists():
        perspective_path = correct_selected_receipt(
            source_path=source_path,
            cropped_path=cropped_path,
        )
        print(
            "\n[OK] Perspective-corrected receipt created:"
            f"\n{perspective_path}"
        )

    enlarged_path = enlarge_receipt(
        perspective_image_path=perspective_path,
        source_image_path=source_path,
    )

    set_selected_enlarged_image(
        source_image=source_path,
        cropped_image=cropped_path,
        perspective_image=perspective_path,
        enlarged_image=enlarged_path,
    )

    return (
        source_path,
        cropped_path,
        perspective_path,
        enlarged_path,
    )


def run_image_enlargement() -> None:
    print("\n=== Receipt Size Normalization ===\n")

    try:
        selected = ensure_enlarged_receipt()
        if selected is None:
            return

        enlarged_path = selected[3]

        print(
            "\n[OK] Normalized receipt created:"
            f"\n{enlarged_path}"
        )
        print(
            "\nThis receipt is now selected "
            "for OCR Image Variants."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"\n[ERROR] {error}")
