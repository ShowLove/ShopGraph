from __future__ import annotations

import json
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.tesseract import extract_receipt
from capabilities.OCRAcquisitionPipeline.constants import OCR_CANDIDATES_DIR
from capabilities.OCRAcquisitionPipeline.ocr_image_variants import ensure_ocr_variants
from capabilities.OCRAcquisitionPipeline.session_state import set_selected_ocr_candidates_file


PSM_MODES = (
    4,
    6,
    11,
)


def _save_json(
    data: dict,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def get_ocr_candidates_path(
    source_path: str | Path,
) -> Path:
    source = Path(
        source_path
    )

    return (
        OCR_CANDIDATES_DIR
        / f"{source.stem}_ocr_candidates.json"
    )


def run_all_ocr_candidates() -> Path | None:
    selected = ensure_ocr_variants()

    if selected is None:
        return None

    source_path = selected[0]
    grayscale_path = selected[4]
    threshold_path = selected[5]

    variants = {
        "grayscale": grayscale_path,
        "threshold": threshold_path,
    }

    candidates = []

    for variant_name, image_path in variants.items():
        for psm in PSM_MODES:
            print(
                "[INFO] OCR "
                f"{variant_name} / PSM {psm}"
            )

            result = extract_receipt(
                image_path=image_path,
                psm=psm,
            )

            candidates.append(
                {
                    "candidate_id": (
                        f"{variant_name}_psm{psm}"
                    ),
                    "image_variant": variant_name,
                    "psm": psm,
                    "result": result,
                }
            )

    output = {
        "source_receipt": str(
            source_path
        ),
        "candidate_count": len(
            candidates
        ),
        "candidates": candidates,
    }

    output_path = (
        get_ocr_candidates_path(
            source_path
        )
    )

    _save_json(
        output,
        output_path,
    )

    set_selected_ocr_candidates_file(
        output_path
    )

    return output_path.resolve()


def run_ocr() -> None:
    print(
        "\n=== Multi-PSM OCR ===\n"
    )

    try:
        output_path = run_all_ocr_candidates()

        if output_path is None:
            return

        print(
            "\n[OK] OCR candidates created:"
            f"\n{output_path}"
        )

        print(
            "\nGenerated 6 candidates:"
            "\n- grayscale / PSM 4"
            "\n- grayscale / PSM 6"
            "\n- grayscale / PSM 11"
            "\n- threshold / PSM 4"
            "\n- threshold / PSM 6"
            "\n- threshold / PSM 11"
        )

        print(
            "\nNext step: Compare OCR Results."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
