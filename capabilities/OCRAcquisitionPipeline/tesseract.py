from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
import pytesseract
from pytesseract import Output


OCR_ENGINE = "tesseract"


def get_tesseract_version() -> str:
    version = str(pytesseract.get_tesseract_version())
    return version.splitlines()[0].strip()


def _average_confidence(values: list[float]) -> float | None:
    valid_values = [value for value in values if value >= 0]
    if not valid_values:
        return None
    return round(sum(valid_values) / len(valid_values), 2)


def extract_receipt(
    image_path: str | Path,
    psm: int,
    crop_fraction: tuple[float, float, float, float] | None = None,
    region_name: str = "full",
) -> dict:
    """
    OCR a receipt while retaining word and line geometry.

    crop_fraction is (left, top, right, bottom), each in [0, 1].
    Geometry returned in normalized_x/y coordinates is relative to the
    FULL input image, even when a region is OCR'd separately.
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Receipt image does not exist: {path}"
        )

    config = f"--psm {psm}"

    with Image.open(path) as original:
        original = original.convert("RGB")
        full_width, full_height = original.size

        if crop_fraction is None:
            left = 0
            top = 0
            right = full_width
            bottom = full_height
        else:
            lf, tf, rf, bf = crop_fraction
            left = int(round(full_width * lf))
            top = int(round(full_height * tf))
            right = int(round(full_width * rf))
            bottom = int(round(full_height * bf))

        image = original.crop((left, top, right, bottom))
        width, height = image.size

        data = pytesseract.image_to_data(
            image,
            config=config,
            output_type=Output.DICT,
        )

    grouped: dict[
        tuple[int, int, int, int],
        list[dict],
    ] = {}

    confidences: list[float] = []

    for index, raw_text in enumerate(data["text"]):
        if raw_text is None:
            continue

        text = raw_text.strip()
        if not text:
            continue

        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0

        word_left = int(data["left"][index]) + left
        word_top = int(data["top"][index]) + top
        word_width = int(data["width"][index])
        word_height = int(data["height"][index])

        key = (
            int(data["page_num"][index]),
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )

        grouped.setdefault(key, []).append(
            {
                "text": text,
                "confidence": confidence,
                "left": word_left,
                "top": word_top,
                "width": word_width,
                "height": word_height,
                "right": word_left + word_width,
                "bottom": word_top + word_height,
                "center_x": word_left + word_width / 2.0,
                "center_y": word_top + word_height / 2.0,
                "normalized_x": (
                    (word_left + word_width / 2.0) / full_width
                    if full_width else 0.0
                ),
                "normalized_y": (
                    (word_top + word_height / 2.0) / full_height
                    if full_height else 0.0
                ),
            }
        )

        if confidence >= 0:
            confidences.append(confidence)

    text_lines = []
    raw_lines = []

    for line_number, words in enumerate(
        grouped.values(),
        start=1,
    ):
        words = sorted(words, key=lambda word: word["left"])

        line_text = " ".join(word["text"] for word in words)
        line_confidence = _average_confidence(
            [word["confidence"] for word in words]
        )

        line_left = min(word["left"] for word in words)
        line_top = min(word["top"] for word in words)
        line_right = max(word["right"] for word in words)
        line_bottom = max(word["bottom"] for word in words)

        center_x = (line_left + line_right) / 2.0
        center_y = (line_top + line_bottom) / 2.0

        raw_lines.append(line_text)
        text_lines.append(
            {
                "line_number": line_number,
                "text": line_text,
                "confidence": line_confidence,
                "bbox": {
                    "left": line_left,
                    "top": line_top,
                    "right": line_right,
                    "bottom": line_bottom,
                    "width": line_right - line_left,
                    "height": line_bottom - line_top,
                },
                "center_x": round(center_x, 2),
                "center_y": round(center_y, 2),
                "normalized_x": round(
                    center_x / full_width if full_width else 0.0,
                    6,
                ),
                "normalized_y": round(
                    center_y / full_height if full_height else 0.0,
                    6,
                ),
                "words": words,
            }
        )

    raw_text = "\n".join(raw_lines)
    mean_confidence = _average_confidence(confidences)

    low_confidence_count = sum(
        1 for confidence in confidences
        if confidence < 50
    )
    recognized_word_count = len(confidences)
    low_confidence_rate = (
        round(
            low_confidence_count / recognized_word_count,
            4,
        )
        if recognized_word_count
        else 1.0
    )

    return {
        "source_image": str(path),
        "ocr_engine": OCR_ENGINE,
        "ocr_version": get_tesseract_version(),
        "ocr_config": config,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "region": {
            "name": region_name,
            "crop_fraction": crop_fraction,
        },
        "image": {
            "width": full_width,
            "height": full_height,
            "ocr_region_width": width,
            "ocr_region_height": height,
        },
        "metrics": {
            "mean_word_confidence": mean_confidence,
            "recognized_word_count": recognized_word_count,
            "low_confidence_word_count": low_confidence_count,
            "low_confidence_rate": low_confidence_rate,
        },
        "raw_text": raw_text,
        "text": text_lines,
    }
