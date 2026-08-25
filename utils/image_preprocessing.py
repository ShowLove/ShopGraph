from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from utils.constants import PREPROCESSED_DIR
from utils.receipt_picker import choose_receipt_image
from utils.session_state import set_selected_receipt


def _order_points(points: np.ndarray) -> np.ndarray:
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
    rect = _order_points(points)

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
    max_width = int(
        max(width_a, width_b)
    )

    height_a = np.linalg.norm(
        top_right - bottom_right
    )
    height_b = np.linalg.norm(
        top_left - bottom_left
    )
    max_height = int(
        max(height_a, height_b)
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


def _detect_receipt(
    image: np.ndarray,
) -> np.ndarray | None:
    height = image.shape[0]
    target_height = 900

    if height > target_height:
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
    else:
        scale = 1.0
        resized = image.copy()

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
        (5, 5),
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

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True,
    )[:20]

    image_area = (
        resized.shape[0]
        * resized.shape[1]
    )

    for contour in contours:
        area = cv2.contourArea(
            contour
        )

        if area < image_area * 0.20:
            continue

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        approximation = (
            cv2.approxPolyDP(
                contour,
                0.02 * perimeter,
                True,
            )
        )

        if len(approximation) == 4:
            points = (
                approximation
                .reshape(4, 2)
                .astype("float32")
            )

            if scale != 1.0:
                points /= scale

            return points

    return None


def _enhance_for_ocr(
    image: np.ndarray,
) -> np.ndarray:
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    gray = cv2.normalize(
        gray,
        None,
        alpha=0,
        beta=255,
        norm_type=cv2.NORM_MINMAX,
    )

    denoised = (
        cv2.fastNlMeansDenoising(
            gray,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21,
        )
    )

    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )

    cleanup_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (2, 2),
        )
    )

    return cv2.morphologyEx(
        thresholded,
        cv2.MORPH_OPEN,
        cleanup_kernel,
        iterations=1,
    )


def get_preprocessed_path(
    source_path: str | Path,
) -> Path:
    source = Path(source_path)

    return (
        PREPROCESSED_DIR
        / f"{source.stem}_preprocessed.png"
    )


def preprocess_receipt(
    image_path: str | Path,
) -> Path:
    source_path = (
        Path(image_path)
        .expanduser()
        .resolve()
    )

    if not source_path.exists():
        raise FileNotFoundError(
            f"Receipt image does not exist: "
            f"{source_path}"
        )

    if not source_path.is_file():
        raise ValueError(
            f"Receipt image path is not a file: "
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

    receipt_corners = _detect_receipt(
        image
    )

    if receipt_corners is not None:
        document = _four_point_transform(
            image,
            receipt_corners,
        )
        detection_status = (
            "receipt boundary detected"
        )
    else:
        document = image.copy()
        detection_status = (
            "receipt boundary not detected; "
            "using original image dimensions"
        )

    processed = _enhance_for_ocr(
        document
    )

    destination = get_preprocessed_path(
        source_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # cv2.imwrite overwrites an existing file with the same path.
    saved = cv2.imwrite(
        str(destination),
        processed,
    )

    if not saved:
        raise RuntimeError(
            "OpenCV could not save image: "
            f"{destination}"
        )

    print(
        "[INFO] Preprocessing result: "
        f"{detection_status}"
    )

    return destination.resolve()


def preprocess_selected_receipt(
    source_path: Path,
) -> Path:
    preprocessed_path = preprocess_receipt(
        source_path
    )

    set_selected_receipt(
        source_image=source_path,
        preprocessed_image=preprocessed_path,
    )

    return preprocessed_path


def run_image_preprocessing() -> None:
    print(
        "\n=== Image Preprocessing ===\n"
    )

    source_path = choose_receipt_image()

    if source_path is None:
        return

    try:
        output_path = (
            preprocess_selected_receipt(
                source_path
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
