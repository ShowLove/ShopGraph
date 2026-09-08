"""
Backward-compatible public names for the former AI receipt package.

All calls are routed to the local Ollama implementation.
"""
from capabilities.OllamaReceiptAcquisitionPipeline.main_OllamaReceiptAcquisitionPipeline import (
    display_ollama_receipt_acquisition_test_mode as display_ai_receipt_acquisition_test_mode,
    main,
    run_ollama_receipt_acquisition_pipeline as run_ai_receipt_acquisition_pipeline,
    run_ollama_receipt_acquisition_pipeline_for_image as run_ai_receipt_acquisition_pipeline_for_image,
    run_ollama_receipt_acquisition_test_mode as run_ai_receipt_acquisition_test_mode,
)


if __name__ == "__main__":
    main()
