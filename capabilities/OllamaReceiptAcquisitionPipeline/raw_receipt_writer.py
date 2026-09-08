
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from utils.constants import RAW_OCR_DIR


def _safe_output_name(
    source_path: Path,
) -> str:
    return (
        f"{source_path.stem}_ollama_raw_ocr.json"
    )


def build_shopgraph_raw_receipt(
    source_path: str | Path,
    receipt_lines: list[dict],
    provider_metadata: dict,
) -> dict:
    source = (
        Path(source_path)
        .expanduser()
        .resolve()
    )

    normalized_lines = []

    for index, line in enumerate(
        receipt_lines,
        start=1,
    ):
        text = str(
            line.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        normalized_lines.append(
            {
                "line_number": index,
                "candidate_id": "ollama_vision",
                "candidate_line_index": index - 1,
                "candidate_scope": "full",
                "text": text,
                "confidence": None,
                "source_candidate": "ollama_vision",
                "image_variant": "original",
                "psm": "OLLAMA",
                "support_count": 1,
                "match_method": "ollama_vision",
                "line_quality_score": None,
                "consensus_score": None,
                "normalized_y": None,
                "bbox": None,
                "ai_uncertain": bool(
                    line.get(
                        "uncertain",
                        False,
                    )
                ),
            }
        )

    raw_text = "\n".join(
        line["text"]
        for line in normalized_lines
    )

    model = str(
        provider_metadata.get(
            "model",
            "unknown",
        )
    )

    return {
        "source_receipt": str(source),
        "selection_method": (
            "local Ollama vision receipt transcription; "
            "visual rows preserved in reading order; "
            "downstream ShopGraph review remains authoritative"
        ),
        "backbone_candidate": {
            "candidate_id": "ollama_vision",
            "image_variant": "original",
            "psm": "OLLAMA",
            "comparison_metrics": {},
        },
        "consensus_summary": {
            "backbone_line_count": len(
                normalized_lines
            ),
            "consensus_line_count": len(
                normalized_lines
            ),
            "merchandise_line_count": 0,
            "component_reconstruction_count": 0,
            "candidate_count": 1,
            "full_candidate_count": 1,
            "right_column_candidate_count": 0,
        },
        "raw_text": raw_text,
        "text": normalized_lines,
        "candidate_ranking": [],
        "provenance": {
            "engine": (
                "Ollama Receipt Acquisition Pipeline"
            ),
            "provider": provider_metadata.get(
                "provider",
                "Ollama",
            ),
            "model": model,
            "response_id": provider_metadata.get(
                "response_id"
            ),
            "rule": (
                "Receipt text was transcribed by an local Ollama vision model. "
                "No Common Name, Sub-Category, or broad Category was "
                "generated here. The existing Data Base Builder remains "
                "the downstream review authority."
            ),
        },
    }


def write_shopgraph_raw_receipt(
    source_path: str | Path,
    receipt_lines: list[dict],
    provider_metadata: dict,
) -> Path:
    source = (
        Path(source_path)
        .expanduser()
        .resolve()
    )

    output = build_shopgraph_raw_receipt(
        source,
        receipt_lines,
        provider_metadata,
    )

    RAW_OCR_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        RAW_OCR_DIR
        / _safe_output_name(
            source
        )
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            suffix=".json",
            dir=RAW_OCR_DIR,
        )
    )
    os.close(descriptor)

    temporary_path = Path(
        temporary_name
    )

    try:
        with temporary_path.open(
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

        os.replace(
            temporary_path,
            destination,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return destination.resolve()
