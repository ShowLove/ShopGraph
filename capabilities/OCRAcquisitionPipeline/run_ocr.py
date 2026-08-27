from __future__ import annotations

import json
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.tesseract import extract_receipt
from capabilities.OCRAcquisitionPipeline.constants import OCR_CANDIDATES_DIR
from capabilities.OCRAcquisitionPipeline.ocr_image_variants import (
    ensure_ocr_variants,
    get_ocr_variant_paths,
)
from capabilities.OCRAcquisitionPipeline.session_state import (
    set_selected_ocr_candidates_file,
)


PSM_MODES = (4, 6, 11)

# Right-column OCR gives prices/tax markers another chance to be recognized.
RIGHT_COLUMN_CROP = (0.68, 0.0, 1.0, 1.0)
RIGHT_COLUMN_PSMS = (6, 11)


def _save_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
    source = Path(source_path)
    return (
        OCR_CANDIDATES_DIR
        / f"{source.stem}_ocr_candidates.json"
    )


def run_all_ocr_candidates() -> Path | None:
    selected = ensure_ocr_variants()
    if selected is None:
        return None

    source_path = selected[0]
    variants = get_ocr_variant_paths(source_path)

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
                region_name="full",
            )

            candidates.append(
                {
                    "candidate_id": (
                        f"{variant_name}_psm{psm}"
                    ),
                    "image_variant": variant_name,
                    "psm": psm,
                    "candidate_scope": "full",
                    "eligible_for_backbone": True,
                    "result": result,
                }
            )

        for psm in RIGHT_COLUMN_PSMS:
            print(
                "[INFO] OCR "
                f"{variant_name} / right column / PSM {psm}"
            )

            result = extract_receipt(
                image_path=image_path,
                psm=psm,
                crop_fraction=RIGHT_COLUMN_CROP,
                region_name="right_column",
            )

            candidates.append(
                {
                    "candidate_id": (
                        f"{variant_name}_right_psm{psm}"
                    ),
                    "image_variant": variant_name,
                    "psm": psm,
                    "candidate_scope": "right_column",
                    "eligible_for_backbone": False,
                    "result": result,
                }
            )

    output = {
        "source_receipt": str(source_path),
        "candidate_count": len(candidates),
        "full_candidate_count": sum(
            1 for candidate in candidates
            if candidate["candidate_scope"] == "full"
        ),
        "right_column_candidate_count": sum(
            1 for candidate in candidates
            if candidate["candidate_scope"] == "right_column"
        ),
        "candidates": candidates,
    }

    output_path = get_ocr_candidates_path(source_path)
    _save_json(output, output_path)

    set_selected_ocr_candidates_file(output_path)

    return output_path.resolve()


def run_ocr() -> None:
    print("\n=== Multi-Variant / Multi-PSM OCR ===\n")

    try:
        output_path = run_all_ocr_candidates()
        if output_path is None:
            return

        with output_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        print(
            "\n[OK] OCR candidates created:"
            f"\n{output_path}"
        )
        print(
            "\nGenerated "
            f"{data['candidate_count']} OCR candidates:"
            f"\n- {data['full_candidate_count']} full-receipt candidates"
            f"\n- {data['right_column_candidate_count']} right-column candidates"
        )
        print(
            "\nNext step: Compare OCR Results."
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"\n[ERROR] {error}")
