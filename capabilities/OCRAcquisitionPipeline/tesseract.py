from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
import pytesseract
from pytesseract import Output


OCR_ENGINE = "tesseract"


def get_tesseract_version() -> str:
    version = str(
        pytesseract.get_tesseract_version()
    )

    return version.splitlines()[0].strip()


def _average_confidence(
    values: list[float],
) -> float | None:
    valid_values = [
        value
        for value in values
        if value >= 0
    ]

    if not valid_values:
        return None

    return round(
        sum(valid_values)
        / len(valid_values),
        2,
    )


def extract_receipt(
    image_path: str | Path,
    psm: int,
) -> dict:
    path = (
        Path(image_path)
        .expanduser()
        .resolve()
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Receipt image does not exist: {path}"
        )

    config = f"--psm {psm}"

    with Image.open(path) as image:
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

    for index, raw_text in enumerate(
        data["text"]
    ):
        if raw_text is None:
            continue

        text = raw_text.strip()

        if not text:
            continue

        key = (
            int(data["page_num"][index]),
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )

        try:
            confidence = float(
                data["conf"][index]
            )
        except (
            TypeError,
            ValueError,
        ):
            confidence = -1.0

        grouped.setdefault(
            key,
            [],
        ).append(
            {
                "text": text,
                "confidence": confidence,
            }
        )

        if confidence >= 0:
            confidences.append(
                confidence
            )

    text_lines = []
    raw_lines = []

    for line_number, words in enumerate(
        grouped.values(),
        start=1,
    ):
        line_text = " ".join(
            word["text"]
            for word in words
        )

        line_confidence = (
            _average_confidence(
                [
                    word["confidence"]
                    for word in words
                ]
            )
        )

        raw_lines.append(
            line_text
        )

        text_lines.append(
            {
                "line_number": line_number,
                "text": line_text,
                "confidence": line_confidence,
            }
        )

    raw_text = "\n".join(
        raw_lines
    )

    mean_confidence = (
        _average_confidence(
            confidences
        )
    )

    low_confidence_count = sum(
        1
        for confidence in confidences
        if confidence < 50
    )

    recognized_word_count = len(
        confidences
    )

    low_confidence_rate = (
        round(
            low_confidence_count
            / recognized_word_count,
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
        "image": {
            "width": width,
            "height": height,
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
