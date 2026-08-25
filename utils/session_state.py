from __future__ import annotations

from pathlib import Path


_selected_source_image: Path | None = None
_selected_preprocessed_image: Path | None = None


def set_selected_receipt(
    source_image: Path,
    preprocessed_image: Path,
) -> None:
    global _selected_source_image
    global _selected_preprocessed_image

    _selected_source_image = source_image.resolve()
    _selected_preprocessed_image = preprocessed_image.resolve()


def get_selected_source_image() -> Path | None:
    return _selected_source_image


def get_selected_preprocessed_image() -> Path | None:
    return _selected_preprocessed_image


def clear_selected_receipt() -> None:
    global _selected_source_image
    global _selected_preprocessed_image

    _selected_source_image = None
    _selected_preprocessed_image = None
