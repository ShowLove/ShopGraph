"""
Backward-compatibility aliases for the former cloud AI receipt package.

ShopGraph now uses the local Ollama receipt-acquisition implementation only.
"""
from capabilities.OllamaReceiptAcquisitionPipeline.main_OllamaReceiptAcquisitionPipeline import (
    run_ollama_receipt_acquisition_pipeline as run_ai_receipt_acquisition_pipeline,
    run_ollama_receipt_acquisition_pipeline_for_image as run_ai_receipt_acquisition_pipeline_for_image,
    run_ollama_receipt_acquisition_test_mode as run_ai_receipt_acquisition_test_mode,
)
