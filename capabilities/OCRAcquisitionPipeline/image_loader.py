from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


HEIC_SUFFIXES = {
    ".heic",
    ".heif",
}


def _load_heic_with_pillow(
    image_path: Path,
) -> np.ndarray:
    """
    Decode an HEIC/HEIF image with Pillow + pillow-heif and return an OpenCV
    BGR ndarray.

    HEIC is decoded in memory. ShopGraph does not need to create a permanent
    JPG copy because the next OCR stage already writes a PNG crop.

    EXIF orientation is applied before conversion so iPhone photos arrive
    upright for receipt detection.
    """
    try:
        from pillow_heif import register_heif_opener
    except ImportError as error:
        raise RuntimeError(
            "HEIC support requires pillow-heif. "
            "Install ShopGraph requirements with:\n"
            "pip install -r data/requirements.txt"
        ) from error

    register_heif_opener()

    try:
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            rgb_image = image.convert("RGB")
            rgb_array = np.asarray(rgb_image)
    except Exception as error:
        raise ValueError(
            "Could not decode HEIC/HEIF image: "
            f"{image_path}\n\n{error}"
        ) from error

    # Pillow uses RGB; OpenCV processing expects BGR.
    return cv2.cvtColor(
        rgb_array,
        cv2.COLOR_RGB2BGR,
    )


def load_image_for_opencv(
    image_path: str | Path,
) -> np.ndarray:
    """
    Read a ShopGraph source image into OpenCV-compatible BGR form.

    Normal formats continue through OpenCV exactly as before.
    HEIC/HEIF uses pillow-heif because OpenCV builds commonly do not include
    HEIF decoding support.
    """
    path = (
        Path(image_path)
        .expanduser()
        .resolve()
    )

    if not path.exists():
        raise FileNotFoundError(
            "Image does not exist: "
            f"{path}"
        )

    if not path.is_file():
        raise ValueError(
            "Image path is not a file: "
            f"{path}"
        )

    if path.suffix.casefold() in HEIC_SUFFIXES:
        return _load_heic_with_pillow(
            path
        )

    image = cv2.imread(
        str(path)
    )

    if image is None:
        raise ValueError(
            "OpenCV could not read image: "
            f"{path}"
        )

    return image
