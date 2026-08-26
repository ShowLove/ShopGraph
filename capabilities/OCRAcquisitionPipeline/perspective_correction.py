from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from capabilities.OCRAcquisitionPipeline.constants import PERSPECTIVE_DIR
from capabilities.OCRAcquisitionPipeline.receipt_picker import choose_receipt_image
from capabilities.OCRAcquisitionPipeline.reliable_receipt_crop import crop_selected_receipt
from capabilities.OCRAcquisitionPipeline.session_state import (
    get_selected_cropped_image,
    get_selected_source_image,
    set_selected_perspective_image,
)


def _order_points(
    points: np.ndarray,
) -> np.ndarray:
    """
    Order four points:
    top-left, top-right, bottom-right, bottom-left.
    """
    rectangle = np.zeros(
        (4, 2),
        dtype="float32",
    )

    point_sum = points.sum(axis=1)

    point_diff = np.diff(
        points,
        axis=1,
    ).reshape(-1)

    rectangle[0] = points[
        np.argmin(point_sum)
    ]

    rectangle[2] = points[
        np.argmax(point_sum)
    ]

    rectangle[1] = points[
        np.argmin(point_diff)
    ]

    rectangle[3] = points[
        np.argmax(point_diff)
    ]

    return rectangle


def _find_document_corners(
    image: np.ndarray,
) -> np.ndarray | None:
    """
    Detect the four outer corners of the already-cropped receipt.

    This stage intentionally operates on the cropped receipt rather
    than the original photograph. That makes perspective estimation
    less vulnerable to the table/background.
    """
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0,
    )

    # Use both thresholding and edges to make the outer paper boundary
    # easier to recover from unevenly lit thermal-paper photos.
    _, thresholded = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    edges = cv2.Canny(
        thresholded,
        40,
        120,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (9, 9),
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    image_area = (
        image.shape[0]
        * image.shape[1]
    )

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True,
    )

    for contour in contours:
        area = cv2.contourArea(
            contour
        )

        if area < image_area * 0.30:
            continue

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        for epsilon in (
            0.015,
            0.02,
            0.025,
            0.03,
            0.04,
            0.05,
        ):
            approximation = cv2.approxPolyDP(
                contour,
                epsilon * perimeter,
                True,
            )

            if len(approximation) == 4:
                return (
                    approximation
                    .reshape(4, 2)
                    .astype("float32")
                )

    # Final fallback: use the minimum-area rectangle around the
    # largest substantial contour.
    for contour in contours:
        area = cv2.contourArea(
            contour
        )

        if area < image_area * 0.30:
            continue

        rectangle = cv2.minAreaRect(
            contour
        )

        return cv2.boxPoints(
            rectangle
        ).astype(
            "float32"
        )

    return None


def _warp_receipt(
    image: np.ndarray,
    corners: np.ndarray,
) -> np.ndarray:
    rectangle = _order_points(
        corners
    )

    (
        top_left,
        top_right,
        bottom_right,
        bottom_left,
    ) = rectangle

    width_bottom = np.linalg.norm(
        bottom_right - bottom_left
    )

    width_top = np.linalg.norm(
        top_right - top_left
    )

    output_width = max(
        int(
            round(
                max(
                    width_bottom,
                    width_top,
                )
            )
        ),
        1,
    )

    height_right = np.linalg.norm(
        top_right - bottom_right
    )

    height_left = np.linalg.norm(
        top_left - bottom_left
    )

    output_height = max(
        int(
            round(
                max(
                    height_right,
                    height_left,
                )
            )
        ),
        1,
    )

    destination = np.array(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ],
        dtype="float32",
    )

    transform = cv2.getPerspectiveTransform(
        rectangle,
        destination,
    )

    corrected = cv2.warpPerspective(
        image,
        transform,
        (
            output_width,
            output_height,
        ),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    return cv2.copyMakeBorder(
        corrected,
        8,
        8,
        8,
        8,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )


def get_perspective_corrected_path(
    source_path: str | Path,
) -> Path:
    source = Path(
        source_path
    )

    return (
        PERSPECTIVE_DIR
        / f"{source.stem}_perspective.png"
    )


def correct_perspective(
    cropped_image_path: str | Path,
    source_image_path: str | Path,
) -> Path:
    """
    Perspective-correct an already-cropped receipt.

    The cropped image is never modified.

    One original source receipt maps to exactly one perspective output.
    Re-running overwrites that same output.
    """
    cropped_path = (
        Path(cropped_image_path)
        .expanduser()
        .resolve()
    )

    source_path = (
        Path(source_image_path)
        .expanduser()
        .resolve()
    )

    if not cropped_path.exists():
        raise FileNotFoundError(
            "Cropped receipt image does not exist: "
            f"{cropped_path}"
        )

    if not cropped_path.is_file():
        raise ValueError(
            "Cropped receipt path is not a file: "
            f"{cropped_path}"
        )

    image = cv2.imread(
        str(cropped_path)
    )

    if image is None:
        raise ValueError(
            "OpenCV could not read cropped image: "
            f"{cropped_path}"
        )

    corners = _find_document_corners(
        image
    )

    if corners is None:
        # The crop stage may already have produced a good rectangular
        # receipt. In that case, keep the image rather than failing the
        # streamlined pipeline.
        corrected = image.copy()

        correction_status = (
            "no additional perspective distortion detected; "
            "using cropped image as-is"
        )

    else:
        corrected = _warp_receipt(
            image,
            corners,
        )

        correction_status = (
            "perspective correction applied"
        )

    destination = (
        get_perspective_corrected_path(
            source_path
        )
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    saved = cv2.imwrite(
        str(destination),
        corrected,
    )

    if not saved:
        raise RuntimeError(
            "OpenCV could not save perspective-corrected image: "
            f"{destination}"
        )

    print(
        "[INFO] Perspective result: "
        f"{correction_status}"
    )

    print(
        "[INFO] Perspective-corrected dimensions: "
        f"{corrected.shape[1]} x {corrected.shape[0]}"
    )

    return destination.resolve()


def correct_selected_receipt(
    source_path: Path,
    cropped_path: Path,
) -> Path:
    perspective_path = (
        correct_perspective(
            cropped_image_path=cropped_path,
            source_image_path=source_path,
        )
    )

    set_selected_perspective_image(
        source_image=source_path,
        cropped_image=cropped_path,
        perspective_image=perspective_path,
    )

    return perspective_path


def _get_or_create_cropped_receipt() -> tuple[Path, Path] | None:
    source_path = (
        get_selected_source_image()
    )

    cropped_path = (
        get_selected_cropped_image()
    )

    if (
        source_path is not None
        and source_path.exists()
        and cropped_path is not None
        and cropped_path.exists()
    ):
        print(
            "[INFO] Using selected cropped receipt:"
            f"\n{cropped_path}"
        )

        return (
            source_path,
            cropped_path,
        )

    print(
        "[INFO] No receipt has been cropped "
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
        "\n[OK] Cropped receipt created:"
        f"\n{cropped_path}"
    )

    return (
        source_path,
        cropped_path,
    )


def run_perspective_correction() -> None:
    print(
        "\n=== Perspective Correction ===\n"
    )

    selected = (
        _get_or_create_cropped_receipt()
    )

    if selected is None:
        return

    source_path, cropped_path = (
        selected
    )

    try:
        output_path = (
            correct_selected_receipt(
                source_path=source_path,
                cropped_path=cropped_path,
            )
        )

        print(
            "\n[OK] Perspective-corrected receipt created:"
            f"\n{output_path}"
        )

        print(
            "\nThis receipt is now selected "
            "for Image Preprocessing."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
