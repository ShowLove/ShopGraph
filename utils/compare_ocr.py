from __future__ import annotations

import json
import re
from pathlib import Path

from utils.constants import RAW_OCR_DIR
from utils.run_ocr import run_all_ocr_candidates
from utils.session_state import (
    get_selected_ocr_candidates_file,
    set_selected_raw_ocr_file,
)


def _load_json(
    path: Path,
) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def _score_candidate(
    candidate: dict,
) -> dict:
    result = candidate["result"]
    metrics = result["metrics"]

    mean_confidence = (
        metrics["mean_word_confidence"]
        or 0.0
    )

    recognized_word_count = (
        metrics["recognized_word_count"]
    )

    low_confidence_rate = (
        metrics["low_confidence_rate"]
    )

    raw_text = result["raw_text"]

    # Reward receipt-like numeric structure without interpreting
    # product meaning. This simply recognizes that receipts contain
    # many digits, prices, and item identifiers.
    digit_count = len(
        re.findall(
            r"\d",
            raw_text,
        )
    )

    price_like_count = len(
        re.findall(
            r"\b\d+[.,]\d{2}\b",
            raw_text,
        )
    )

    # Confidence is primary.
    # Coverage and receipt-like structure are secondary.
    # Low-confidence output receives a penalty.
    score = (
        mean_confidence
        + min(
            recognized_word_count,
            250,
        ) * 0.03
        + min(
            digit_count,
            300,
        ) * 0.01
        + min(
            price_like_count,
            80,
        ) * 0.08
        - low_confidence_rate * 15.0
    )

    return {
        "score": round(
            score,
            4,
        ),
        "mean_word_confidence": mean_confidence,
        "recognized_word_count": recognized_word_count,
        "low_confidence_rate": low_confidence_rate,
        "digit_count": digit_count,
        "price_like_count": price_like_count,
    }


def _get_or_create_candidates_file() -> Path | None:
    candidates_path = (
        get_selected_ocr_candidates_file()
    )

    if (
        candidates_path is not None
        and candidates_path.exists()
    ):
        return candidates_path

    print(
        "[INFO] OCR candidates have not been generated "
        "in this session yet. Running the earlier pipeline "
        "automatically."
    )

    return run_all_ocr_candidates()


def compare_and_build_raw_ocr() -> Path | None:
    candidates_path = (
        _get_or_create_candidates_file()
    )

    if candidates_path is None:
        return None

    candidates_data = _load_json(
        candidates_path
    )

    scored_candidates = []

    for candidate in candidates_data[
        "candidates"
    ]:
        metrics = _score_candidate(
            candidate
        )

        scored_candidates.append(
            {
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate[
                    "psm"
                ],
                "comparison_metrics": metrics,
                "result": candidate[
                    "result"
                ],
            }
        )

    scored_candidates.sort(
        key=lambda item: item[
            "comparison_metrics"
        ]["score"],
        reverse=True,
    )

    best = scored_candidates[0]

    source_receipt = Path(
        candidates_data[
            "source_receipt"
        ]
    )

    output_path = (
        RAW_OCR_DIR
        / f"{source_receipt.stem}_raw_ocr.json"
    )

    output = {
        "source_receipt": str(
            source_receipt
        ),
        "selection_method": (
            "heuristic comparison of mean word confidence, "
            "recognized-word coverage, low-confidence rate, "
            "digit coverage, and price-like token coverage"
        ),
        "selected_candidate": {
            "candidate_id": best[
                "candidate_id"
            ],
            "image_variant": best[
                "image_variant"
            ],
            "psm": best[
                "psm"
            ],
            "comparison_metrics": best[
                "comparison_metrics"
            ],
        },
        "raw_text": best[
            "result"
        ]["raw_text"],
        "text": best[
            "result"
        ]["text"],
        "ocr_metadata": {
            "ocr_engine": best[
                "result"
            ]["ocr_engine"],
            "ocr_version": best[
                "result"
            ]["ocr_version"],
            "ocr_config": best[
                "result"
            ]["ocr_config"],
            "source_image": best[
                "result"
            ]["source_image"],
            "image": best[
                "result"
            ]["image"],
        },
        "candidate_ranking": [
            {
                "rank": rank,
                "candidate_id": candidate[
                    "candidate_id"
                ],
                "image_variant": candidate[
                    "image_variant"
                ],
                "psm": candidate[
                    "psm"
                ],
                "comparison_metrics": candidate[
                    "comparison_metrics"
                ],
            }
            for rank, candidate
            in enumerate(
                scored_candidates,
                start=1,
            )
        ],
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    set_selected_raw_ocr_file(
        output_path
    )

    return output_path.resolve()


def run_compare_ocr() -> None:
    print(
        "\n=== Compare OCR Results ===\n"
    )

    try:
        output_path = (
            compare_and_build_raw_ocr()
        )

        if output_path is None:
            return

        data = _load_json(
            output_path
        )

        selected = data[
            "selected_candidate"
        ]

        print(
            "[OK] Selected best OCR candidate:"
        )

        print(
            f"Variant: {selected['image_variant']}"
        )

        print(
            f"PSM: {selected['psm']}"
        )

        print(
            "Score: "
            f"{selected['comparison_metrics']['score']}"
        )

        print(
            "\n[OK] Final raw OCR JSON created:"
            f"\n{output_path}"
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
