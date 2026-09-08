
from __future__ import annotations

import json


class OllamaReceiptResponseError(ValueError):
    pass


def _strip_code_fence(value: str) -> str:
    text = value.strip()

    if not text.startswith("```"):
        return text

    lines = text.splitlines()

    if lines:
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def parse_ollama_receipt_response(raw_text: str) -> list[dict]:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise OllamaReceiptResponseError(
            "Ollama response did not contain receipt transcription text."
        )

    cleaned = _strip_code_fence(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise OllamaReceiptResponseError(
            "Ollama response was not valid JSON."
        ) from error

    receipt_lines = payload.get("receipt_lines")

    if not isinstance(receipt_lines, list):
        raise OllamaReceiptResponseError(
            "Ollama response must contain a 'receipt_lines' list."
        )

    normalized = []

    for index, item in enumerate(receipt_lines, start=1):
        if isinstance(item, str):
            text = item.strip()
            uncertain = False
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            uncertain = bool(item.get("uncertain", False))
        else:
            continue

        if not text:
            continue

        normalized.append(
            {
                "line_number": index,
                "text": text,
                "uncertain": uncertain,
            }
        )

    if not normalized:
        raise OllamaReceiptResponseError(
            "Ollama response contained no usable receipt lines."
        )

    return normalized
