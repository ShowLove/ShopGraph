from __future__ import annotations

from pathlib import Path


_selected_source_image: Path | None = None
_selected_cropped_image: Path | None = None
_selected_perspective_image: Path | None = None
_selected_enlarged_image: Path | None = None
_selected_grayscale_image: Path | None = None
_selected_threshold_image: Path | None = None
_selected_ocr_candidates_file: Path | None = None
_selected_raw_ocr_file: Path | None = None
_selected_refined_json_file: Path | None = None


def _clear_after_raw() -> None:
    global _selected_refined_json_file
    _selected_refined_json_file = None


def set_selected_cropped_image(
    source_image: Path,
    cropped_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_enlarged_image
    global _selected_grayscale_image
    global _selected_threshold_image
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = None
    _selected_enlarged_image = None
    _selected_grayscale_image = None
    _selected_threshold_image = None
    _selected_ocr_candidates_file = None
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None


def set_selected_perspective_image(
    source_image: Path,
    cropped_image: Path,
    perspective_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_enlarged_image
    global _selected_grayscale_image
    global _selected_threshold_image
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = perspective_image.resolve()
    _selected_enlarged_image = None
    _selected_grayscale_image = None
    _selected_threshold_image = None
    _selected_ocr_candidates_file = None
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None


def set_selected_enlarged_image(
    source_image: Path,
    cropped_image: Path,
    perspective_image: Path,
    enlarged_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_enlarged_image
    global _selected_grayscale_image
    global _selected_threshold_image
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = perspective_image.resolve()
    _selected_enlarged_image = enlarged_image.resolve()
    _selected_grayscale_image = None
    _selected_threshold_image = None
    _selected_ocr_candidates_file = None
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None


def set_selected_ocr_variants(
    source_image: Path,
    cropped_image: Path,
    perspective_image: Path,
    enlarged_image: Path,
    grayscale_image: Path,
    threshold_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_enlarged_image
    global _selected_grayscale_image
    global _selected_threshold_image
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = perspective_image.resolve()
    _selected_enlarged_image = enlarged_image.resolve()
    _selected_grayscale_image = grayscale_image.resolve()
    _selected_threshold_image = threshold_image.resolve()
    _selected_ocr_candidates_file = None
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None


def set_selected_ocr_candidates_file(path: Path) -> None:
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_ocr_candidates_file = path.resolve()
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None


def set_selected_raw_ocr_file(path: Path) -> None:
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_raw_ocr_file = path.resolve()
    _selected_refined_json_file = None


def set_selected_refined_json_file(path: Path) -> None:
    global _selected_refined_json_file
    _selected_refined_json_file = path.resolve()


def get_selected_source_image() -> Path | None:
    return _selected_source_image


def get_selected_cropped_image() -> Path | None:
    return _selected_cropped_image


def get_selected_perspective_image() -> Path | None:
    return _selected_perspective_image


def get_selected_enlarged_image() -> Path | None:
    return _selected_enlarged_image


def get_selected_grayscale_image() -> Path | None:
    return _selected_grayscale_image


def get_selected_threshold_image() -> Path | None:
    return _selected_threshold_image


def get_selected_ocr_candidates_file() -> Path | None:
    return _selected_ocr_candidates_file


def get_selected_raw_ocr_file() -> Path | None:
    return _selected_raw_ocr_file


def get_selected_refined_json_file() -> Path | None:
    return _selected_refined_json_file


def clear_selected_receipt() -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_enlarged_image
    global _selected_grayscale_image
    global _selected_threshold_image
    global _selected_ocr_candidates_file
    global _selected_raw_ocr_file
    global _selected_refined_json_file

    _selected_source_image = None
    _selected_cropped_image = None
    _selected_perspective_image = None
    _selected_enlarged_image = None
    _selected_grayscale_image = None
    _selected_threshold_image = None
    _selected_ocr_candidates_file = None
    _selected_raw_ocr_file = None
    _selected_refined_json_file = None
