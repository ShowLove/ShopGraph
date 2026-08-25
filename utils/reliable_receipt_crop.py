from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from utils.constants import CROPPED_DIR
from utils.receipt_picker import choose_receipt_image
from utils.session_state import set_selected_cropped_image


def _order_points(
    points: np.ndarray,
) -> np.ndarray:
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


def _four_point_transform(
    image: np.ndarray,
    points: np.ndarray,
) -> np.ndarray:
    rect = _order_points(
        points
    )

    (
        top_left,
        top_right,
        bottom_right,
        bottom_left,
    ) = rect

    width_a = np.linalg.norm(
        bottom_right - bottom_left
    )

    width_b = np.linalg.norm(
        top_right - top_left
    )

    max_width = max(
        int(max(width_a, width_b)),
        1,
    )

    height_a = np.linalg.norm(
        top_right - bottom_right
    )

    height_b = np.linalg.norm(
        top_left - bottom_left
    )

    max_height = max(
        int(max(height_a, height_b)),
        1,
    )

    destination = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype="float32",
    )

    transform_matrix = (
        cv2.getPerspectiveTransform(
            rect,
            destination,
        )
    )

    return cv2.warpPerspective(
        image,
        transform_matrix,
        (max_width, max_height),
    )


def _resize_for_detection(
    image: np.ndarray,
    target_height: int = 1000,
) -> tuple[np.ndarray, float]:
    height = image.shape[0]

    if height <= target_height:
        return image.copy(), 1.0

    scale = (
        target_height
        / float(height)
    )

    resized = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_AREA,
    )

    return resized, scale


def _build_paper_mask(
    image: np.ndarray,
) -> np.ndarray:
    """
    Detect light, relatively low-saturation paper against a darker
    background.

    This is intentionally different from edge-only contour detection.
    Receipts photographed on wood often have incomplete paper edges,
    but the receipt itself is still a large bright region.
    """
    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV,
    )

    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    # Receipt paper is usually bright. Saturation is allowed to be
    # moderately high because warm indoor lighting can tint the paper.
    bright_mask = cv2.inRange(
        value,
        115,
        255,
    )

    low_saturation_mask = cv2.inRange(
        saturation,
        0,
        125,
    )

    mask = cv2.bitwise_and(
        bright_mask,
        low_saturation_mask,
    )

    kernel_large = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (19, 19),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel_large,
        iterations=2,
    )

    kernel_small = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (7, 7),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel_small,
        iterations=1,
    )

    return mask


def _find_receipt_corners_from_paper(
    image: np.ndarray,
) -> np.ndarray | None:
    resized, scale = _resize_for_detection(
        image
    )

    mask = _build_paper_mask(
        resized
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    image_area = (
        resized.shape[0]
        * resized.shape[1]
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

        # A receipt should occupy a meaningful part of the photo.
        if area < image_area * 0.18:
            continue

        rectangle = cv2.minAreaRect(
            contour
        )

        box = cv2.boxPoints(
            rectangle
        ).astype(
            "float32"
        )

        width, height = rectangle[1]

        if width <= 0 or height <= 0:
            continue

        long_side = max(
            width,
            height,
        )

        short_side = min(
            width,
            height,
        )

        aspect_ratio = (
            long_side
            / short_side
        )

        # Grocery receipts are generally tall rectangles.
        if aspect_ratio < 1.35:
            continue

        if scale != 1.0:
            box /= scale

        return box

    return None


def _find_receipt_corners_from_edges(
    image: np.ndarray,
) -> np.ndarray | None:
    """
    Secondary fallback.

    If bright-paper segmentation fails, try traditional edge detection.
    """
    resized, scale = _resize_for_detection(
        image
    )

    gray = cv2.cvtColor(
        resized,
        cv2.COLOR_BGR2GRAY,
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0,
    )

    edges = cv2.Canny(
        blurred,
        50,
        150,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (7, 7),
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    image_area = (
        resized.shape[0]
        * resized.shape[1]
    )

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True,
    )[:30]

    for contour in contours:
        area = cv2.contourArea(
            contour
        )

        if area < image_area * 0.18:
            continue

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        for epsilon in (
            0.02,
            0.03,
            0.04,
            0.05,
        ):
            approximation = (
                cv2.approxPolyDP(
                    contour,
                    epsilon * perimeter,
                    True,
                )
            )

            if len(approximation) != 4:
                continue

            points = (
                approximation
                .reshape(4, 2)
                .astype("float32")
            )

            if scale != 1.0:
                points /= scale

            return points

    return None


def _add_small_margin(
    image: np.ndarray,
    margin: int = 8,
) -> np.ndarray:
    """
    Add a small white border so OCR does not start directly on the
    paper edge.
    """
    return cv2.copyMakeBorder(
        image,
        margin,
        margin,
        margin,
        margin,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )


def get_cropped_path(
    source_path: str | Path,
) -> Path:
    source = Path(
        source_path
    )

    return (
        CROPPED_DIR
        / f"{source.stem}_cropped.png"
    )


def crop_receipt(
    image_path: str | Path,
) -> Path:
    """
    Detect and crop the receipt from the original image.

    The original image is never modified.

    A source image always maps to one deterministic output path:
        data/cropped/<source_stem>_cropped.png

    Re-running the crop overwrites that same file.
    """
    source_path = (
        Path(image_path)
        .expanduser()
        .resolve()
    )

    if not source_path.exists():
        raise FileNotFoundError(
            "Receipt image does not exist: "
            f"{source_path}"
        )

    if not source_path.is_file():
        raise ValueError(
            "Receipt image path is not a file: "
            f"{source_path}"
        )

    image = cv2.imread(
        str(source_path)
    )

    if image is None:
        raise ValueError(
            "OpenCV could not read image: "
            f"{source_path}"
        )

    corners = (
        _find_receipt_corners_from_paper(
            image
        )
    )

    detection_method = (
        "bright-paper detection"
    )

    if corners is None:
        corners = (
            _find_receipt_corners_from_edges(
                image
            )
        )

        detection_method = (
            "edge detection fallback"
        )

    if corners is None:
        raise RuntimeError(
            "Receipt boundary could not be detected reliably. "
            "No cropped image was written."
        )

    cropped = _four_point_transform(
        image,
        corners,
    )

    cropped = _add_small_margin(
        cropped
    )

    destination = get_cropped_path(
        source_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # cv2.imwrite overwrites an existing file with the same name.
    saved = cv2.imwrite(
        str(destination),
        cropped,
    )

    if not saved:
        raise RuntimeError(
            "OpenCV could not save cropped image: "
            f"{destination}"
        )

    print(
        "[INFO] Receipt crop method: "
        f"{detection_method}"
    )

    print(
        "[INFO] Cropped dimensions: "
        f"{cropped.shape[1]} x {cropped.shape[0]}"
    )

    return destination.resolve()


def crop_selected_receipt(
    source_path: Path,
) -> Path:
    cropped_path = crop_receipt(
        source_path
    )

    set_selected_cropped_image(
        source_image=source_path,
        cropped_image=cropped_path,
    )

    return cropped_path


def run_reliable_receipt_crop() -> None:
    print(
        "\n=== Reliable Receipt Detection / Crop ===\n"
    )

    source_path = choose_receipt_image()

    if source_path is None:
        return

    try:
        output_path = crop_selected_receipt(
            source_path
        )

        print(
            "\n[OK] Cropped receipt created:"
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
