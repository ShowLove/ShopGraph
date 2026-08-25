from __future__ import annotations

from pathlib import Path


_selected_source_image: Path | None = None
_selected_cropped_image: Path | None = None
_selected_perspective_image: Path | None = None
_selected_preprocessed_image: Path | None = None


def set_selected_source_image(
    source_image: Path,
) -> None:
    global _selected_source_image

    _selected_source_image = source_image.resolve()


def set_selected_cropped_image(
    source_image: Path,
    cropped_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_preprocessed_image

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()

    # New crop invalidates downstream artifacts for this session.
    _selected_perspective_image = None
    _selected_preprocessed_image = None


def set_selected_perspective_image(
    source_image: Path,
    cropped_image: Path,
    perspective_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_preprocessed_image

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = perspective_image.resolve()

    # New perspective correction invalidates preprocessing.
    _selected_preprocessed_image = None


def set_selected_preprocessed_image(
    source_image: Path,
    cropped_image: Path,
    perspective_image: Path,
    preprocessed_image: Path,
) -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_preprocessed_image

    _selected_source_image = source_image.resolve()
    _selected_cropped_image = cropped_image.resolve()
    _selected_perspective_image = perspective_image.resolve()
    _selected_preprocessed_image = preprocessed_image.resolve()


def get_selected_source_image() -> Path | None:
    return _selected_source_image


def get_selected_cropped_image() -> Path | None:
    return _selected_cropped_image


def get_selected_perspective_image() -> Path | None:
    return _selected_perspective_image


def get_selected_preprocessed_image() -> Path | None:
    return _selected_preprocessed_image


def clear_selected_receipt() -> None:
    global _selected_source_image
    global _selected_cropped_image
    global _selected_perspective_image
    global _selected_preprocessed_image

    _selected_source_image = None
    _selected_cropped_image = None
    _selected_perspective_image = None
    _selected_preprocessed_image = None
