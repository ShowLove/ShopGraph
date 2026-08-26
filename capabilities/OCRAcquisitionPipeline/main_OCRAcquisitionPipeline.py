from capabilities.OCRAcquisitionPipeline.reliable_receipt_crop import (
    run_reliable_receipt_crop,
)
from capabilities.OCRAcquisitionPipeline.perspective_correction import (
    run_perspective_correction,
)
from capabilities.OCRAcquisitionPipeline.image_enlargement import (
    run_image_enlargement,
)
from capabilities.OCRAcquisitionPipeline.ocr_image_variants import (
    run_ocr_image_variants,
)
from capabilities.OCRAcquisitionPipeline.run_ocr import (
    run_ocr,
)
from capabilities.OCRAcquisitionPipeline.compare_ocr import (
    run_compare_ocr,
)


def run_ocr_acquisition_pipeline() -> None:
    """
    Run the complete OCR Acquisition Pipeline in order.

    From the user's point of view, this behaves exactly like the current
    capability option: the receipt is selected once and downstream stages
    reuse the same session state and generated artifacts.
    """
    print(
        "\n=== OCR Acquisition Pipeline ===\n"
    )

    print(
        "[1/6] Reliable Receipt Detection / Crop"
    )
    run_reliable_receipt_crop()

    print(
        "\n[2/6] Perspective Correction"
    )
    run_perspective_correction()

    print(
        "\n[3/6] 2x Enlargement"
    )
    run_image_enlargement()

    print(
        "\n[4/6] Generate OCR Image Variants"
    )
    run_ocr_image_variants()

    print(
        "\n[5/6] Run OCR - PSM 4 / 6 / 11"
    )
    run_ocr()

    print(
        "\n[6/6] Compare OCR Results / Build Raw OCR JSON"
    )
    run_compare_ocr()

    print(
        "\n[OK] OCR Acquisition Pipeline complete."
    )


def main() -> None:
    run_ocr_acquisition_pipeline()


if __name__ == "__main__":
    main()
