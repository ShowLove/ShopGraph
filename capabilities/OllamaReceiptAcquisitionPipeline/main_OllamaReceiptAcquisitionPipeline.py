from __future__ import annotations

from pathlib import Path

from capabilities.OllamaReceiptAcquisitionPipeline.ollama_client import (
    OllamaReceiptAcquisitionError,
    get_configured_base_url,
    get_configured_model,
    transcribe_receipt_image,
)
from capabilities.OllamaReceiptAcquisitionPipeline.response_parser import (
    OllamaReceiptResponseError,
    parse_ollama_receipt_response,
)
from capabilities.OllamaReceiptAcquisitionPipeline.raw_receipt_writer import (
    write_shopgraph_raw_receipt,
)
from capabilities.OCRAcquisitionPipeline.receipt_picker import (
    choose_receipt_image,
)
from utils.DataBaseBuilder.data_base_builder_main import (
    TEST_WORKBOOK_PATH,
    run_receipt_import,
)


def run_ollama_receipt_acquisition_pipeline_for_image(
    source_path: str | Path,
) -> list[Path]:
    source = (
        Path(source_path)
        .expanduser()
        .resolve()
    )

    print(
        "\n=== Ollama Receipt Acquisition Pipeline ===\n"
    )
    print(
        "[INFO] Using receipt image:"
        f"\n{source}"
    )
    print(
        "[INFO] Local Ollama model:"
        f"\n{get_configured_model()}"
    )
    print(
        "[INFO] Ollama service:"
        f"\n{get_configured_base_url()}"
    )
    print(
        "[INFO] Receipt image processing is local-only."
    )

    try:
        raw_response, provider_metadata = (
            transcribe_receipt_image(
                source
            )
        )

        receipt_lines = (
            parse_ollama_receipt_response(
                raw_response
            )
        )

        raw_path = (
            write_shopgraph_raw_receipt(
                source_path=source,
                receipt_lines=receipt_lines,
                provider_metadata=(
                    provider_metadata
                ),
            )
        )

    except (
        OllamaReceiptAcquisitionError,
        OllamaReceiptResponseError,
        OSError,
        ValueError,
    ) as error:
        print(
            "\n[ERROR] Ollama Receipt Acquisition Pipeline failed:"
            f"\n{error}"
        )
        return []

    print(
        "\n[OK] Ollama receipt transcription complete."
    )
    print(
        f"Receipt lines: {len(receipt_lines)}"
    )
    print(
        "Raw ShopGraph receipt JSON:"
        f"\n{raw_path}"
    )

    return [raw_path]


def run_ollama_receipt_acquisition_pipeline() -> list[Path]:
    source = choose_receipt_image()

    if source is None:
        return []

    return (
        run_ollama_receipt_acquisition_pipeline_for_image(
            source
        )
    )


def _run_ollama_test_acquisition_only() -> None:
    outputs = (
        run_ollama_receipt_acquisition_pipeline()
    )

    if not outputs:
        return

    print(
        "\n[TEST OK] Ollama acquisition finished."
        "\nLive Purchase History was not opened or modified."
    )


def _run_ollama_test_with_database_builder() -> None:
    outputs = (
        run_ollama_receipt_acquisition_pipeline()
    )

    if not outputs:
        return

    print(
        "\n=== Data Base Builder - Test Mode ==="
    )
    print(
        "[INFO] Ollama raw receipt will be reviewed against:"
        f"\n{TEST_WORKBOOK_PATH.resolve()}"
    )
    print(
        "[INFO] Live Purchase History will not be used."
    )

    for raw_path in outputs:
        run_receipt_import(
            source_path=raw_path,
            workbook_path=TEST_WORKBOOK_PATH,
        )


def display_ollama_receipt_acquisition_test_mode() -> None:
    print(
        "\n=== Ollama Receipt Acquisition Pipeline - Test Mode ===\n"
    )
    print(
        "1. Run Ollama Receipt Acquisition Only"
    )
    print(
        "2. Run Ollama Receipt Acquisition + Data Base Builder Test Mode"
    )
    print(
        "0. Return to Capabilities Menu"
    )


def run_ollama_receipt_acquisition_test_mode() -> None:
    while True:
        display_ollama_receipt_acquisition_test_mode()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "1":
            _run_ollama_test_acquisition_only()

        elif option == "2":
            _run_ollama_test_with_database_builder()

        elif option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


def main() -> None:
    run_ollama_receipt_acquisition_pipeline()


if __name__ == "__main__":
    main()
