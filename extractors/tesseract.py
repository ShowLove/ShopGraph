from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
import pytesseract
from pytesseract import Output


OCR_ENGINE = "tesseract"
OCR_CONFIG = "--psm 6"


def get_tesseract_version() -> str:
    """
    Return the installed Tesseract version.
    """
    version = str(pytesseract.get_tesseract_version())
    return version.splitlines()[0].strip()


def _average_confidence(values: list[float]) -> float | None:
    valid_values = [value for value in values if value >= 0]

    if not valid_values:
        return None

    return round(sum(valid_values) / len(valid_values), 2)


def _extract_line_confidences(image: Image.Image) -> dict[int, float | None]:
    """
    Read Tesseract's word-level confidence values and aggregate them
    by the text lines detected by Tesseract.

    This does not interpret or normalize receipt contents.
    """
    data = pytesseract.image_to_data(
        image,
        config=OCR_CONFIG,
        output_type=Output.DICT,
    )

    grouped: dict[tuple[int, int, int, int], list[float]] = {}

    for index, raw_text in enumerate(data["text"]):
        if raw_text is None or raw_text == "":
            continue

        key = (
            int(data["page_num"][index]),
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )

        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0

        grouped.setdefault(key, []).append(confidence)

    return {
        line_number: _average_confidence(grouped[key])
        for line_number, key in enumerate(grouped.keys(), start=1)
    }


def extract_receipt(image_path: str | Path) -> dict:
    """
    Stage 1 receipt OCR extraction.

    Input:
        Path to a receipt image.

    Output:
        JSON-serializable dictionary containing raw Tesseract output
        and OCR metadata.

    No parsing, product identification, categorization,
    normalization, or database work is performed here.
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Receipt image does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Receipt image path is not a file: {path}")

    with Image.open(path) as image:
        width, height = image.size

        raw_text = pytesseract.image_to_string(
            image,
            config=OCR_CONFIG,
        )

        confidence_by_line = _extract_line_confidences(image)

    raw_lines = raw_text.splitlines()

    text_lines = [
        {
            "line_number": line_number,
            "text": line,
            "confidence": confidence_by_line.get(line_number),
        }
        for line_number, line in enumerate(raw_lines, start=1)
    ]

    return {
        "source_image": str(path),
        "ocr_engine": OCR_ENGINE,
        "ocr_version": get_tesseract_version(),
        "ocr_config": OCR_CONFIG,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "image": {
            "width": width,
            "height": height,
        },
        "raw_text": raw_text,
        "text": text_lines,
    }
