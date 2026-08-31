from __future__ import annotations

from pathlib import Path

from capabilities.OCRAcquisitionPipeline.reliable_receipt_crop import run_reliable_receipt_crop
from capabilities.OCRAcquisitionPipeline.perspective_correction import run_perspective_correction
from capabilities.OCRAcquisitionPipeline.image_enlargement import run_image_enlargement
from capabilities.OCRAcquisitionPipeline.ocr_image_variants import run_ocr_image_variants
from capabilities.OCRAcquisitionPipeline.run_ocr import run_ocr
from capabilities.OCRAcquisitionPipeline.compare_ocr import run_compare_ocr
from capabilities.OCRAcquisitionPipeline.refine_json import run_refine_json
from capabilities.OCRAcquisitionPipeline.receipt_picker import get_available_receipts
from capabilities.OCRAcquisitionPipeline.session_state import get_selected_raw_ocr_file


def _run_stages_for_receipt(source_path: Path | None = None) -> Path | None:
    print("\n[1/7] Reliable Receipt Detection / Crop")
    cropped = run_reliable_receipt_crop(source_path)
    if cropped is None:
        return None

    print("\n[2/7] Perspective Correction")
    run_perspective_correction()

    print("\n[3/7] Receipt Size Normalization")
    run_image_enlargement()

    print("\n[4/7] Generate OCR Image Variants")
    run_ocr_image_variants()

    print("\n[5/7] Run Multi-Variant / Multi-PSM OCR")
    run_ocr()

    print("\n[6/7] Compare OCR Results / Build Raw OCR JSON")
    run_compare_ocr()

    raw_path = get_selected_raw_ocr_file()
    if raw_path is None or not raw_path.exists():
        print("\n[ERROR] Stage 6 did not produce a raw OCR JSON.")
        return None

    print("\n[7/7] Refine Json File")
    run_refine_json()
    return raw_path.resolve()


def run_ocr_acquisition_pipeline() -> list[Path]:
    """Original behavior: choose ONE image and run Stages 1-7."""
    print("\n=== OCR Acquisition Pipeline ===\n")
    raw_path = _run_stages_for_receipt(None)
    if raw_path is None:
        return []
    print("\n[OK] OCR Acquisition Pipeline complete.")
    return [raw_path]



def run_ocr_acquisition_pipeline_for_image(
    source_path: str | Path,
) -> list[Path]:
    """
    Run Stages 1-7 for one explicit receipt image without showing the receipt
    picker. This is used by higher-level automated Pipelines.
    """
    source = (
        Path(source_path)
        .expanduser()
        .resolve()
    )

    print(
        "\n=== OCR Acquisition Pipeline - Saved Picture ===\n"
    )
    print(
        "[INFO] Using saved receipt image:"
        f"\n{source}"
    )

    raw_path = _run_stages_for_receipt(
        source
    )

    if raw_path is None:
        return []

    print(
        "\n[OK] OCR Acquisition Pipeline complete."
    )

    return [raw_path]


def run_ocr_acquisition_pipeline_all_images() -> list[Path]:
    """New behavior: process every supported image in data/current_pic/."""
    print("\n=== OCR Acquisition Pipeline - All Images ===\n")
    receipts = get_available_receipts()

    if not receipts:
        print("\n[ERROR] No receipt images were found in data/current_pic/.")
        return []

    print("\nAvailable receipt images:\n")
    for index, receipt in enumerate(receipts, start=1):
        print(f"{index}. {receipt.name}")

    print(f"\n[INFO] Processing all {len(receipts)} image(s).")
    outputs = []

    for index, source_path in enumerate(receipts, start=1):
        print("\n" + "=" * 70)
        print(f"Receipt {index}/{len(receipts)}: {source_path.name}")
        print("=" * 70)

        try:
            raw_path = _run_stages_for_receipt(source_path)
        except Exception as error:
            print(
                "\n[ERROR] Receipt pipeline failed for "
                f"{source_path.name}: {error}"
            )
            continue

        if raw_path is not None:
            outputs.append(raw_path)
            print(f"\n[OK] Receipt {index}/{len(receipts)} complete.")

    print("\n[OK] OCR Acquisition Pipeline - All Images complete.")
    print(f"Images found: {len(receipts)}")
    print(f"Raw OCR files completed: {len(outputs)}")
    return outputs


def main() -> None:
    run_ocr_acquisition_pipeline()


if __name__ == "__main__":
    main()
