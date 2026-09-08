"""
Backward-compatible aliases to ShopGraph's local Ollama client.

No cloud AI provider is used by this module.
"""
from capabilities.OllamaReceiptAcquisitionPipeline.ollama_client import (
    BASE_URL_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    MODEL_ENV,
    REQUEST_TIMEOUT_SECONDS,
    OllamaReceiptAcquisitionError as AIReceiptAcquisitionError,
    get_configured_base_url,
    get_configured_model,
    transcribe_receipt_image,
    verify_ollama_ready,
)
