"""
Compatibility aliases for the local Ollama response parser.
"""
from capabilities.OllamaReceiptAcquisitionPipeline.response_parser import (
    OllamaReceiptResponseError as AIReceiptResponseError,
    parse_ollama_receipt_response as parse_ai_receipt_response,
)
