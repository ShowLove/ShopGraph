from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from capabilities.OllamaReceiptAcquisitionPipeline.receipt_prompt import (
    RECEIPT_TRANSCRIPTION_PROMPT,
)


MODEL_ENV = "SHOPGRAPH_OLLAMA_MODEL"
BASE_URL_ENV = "SHOPGRAPH_OLLAMA_BASE_URL"
NUM_CTX_ENV = "SHOPGRAPH_OLLAMA_NUM_CTX"

DEFAULT_MODEL = "qwen2.5vl:7b"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_NUM_CTX = 8192
REQUEST_TIMEOUT_SECONDS = 180


class OllamaReceiptAcquisitionError(RuntimeError):
    pass


def get_configured_model() -> str:
    return (
        os.environ.get(MODEL_ENV, "").strip()
        or DEFAULT_MODEL
    )


def get_configured_base_url() -> str:
    value = (
        os.environ.get(BASE_URL_ENV, "").strip()
        or DEFAULT_BASE_URL
    )
    return value.rstrip("/")


def get_configured_num_ctx() -> int:
    raw_value = os.environ.get(
        NUM_CTX_ENV,
        "",
    ).strip()

    if not raw_value:
        return DEFAULT_NUM_CTX

    try:
        value = int(raw_value)
    except ValueError as error:
        raise OllamaReceiptAcquisitionError(
            f"{NUM_CTX_ENV} must be a whole number. "
            f"Current value: {raw_value!r}"
        ) from error

    if value < 4096:
        raise OllamaReceiptAcquisitionError(
            f"{NUM_CTX_ENV} must be at least 4096. "
            f"Current value: {value}"
        )

    return value


def _image_bytes(image_path: Path) -> bytes:
    suffix = image_path.suffix.lower()

    if suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        return image_path.read_bytes()

    if suffix in {
        ".heic",
        ".heif",
        ".tif",
        ".tiff",
    }:
        try:
            from PIL import Image
        except ImportError as error:
            raise OllamaReceiptAcquisitionError(
                "Pillow is required to convert this receipt image "
                "for Ollama vision input."
            ) from error

        if suffix in {
            ".heic",
            ".heif",
        }:
            try:
                from pillow_heif import register_heif_opener
            except ImportError as error:
                raise OllamaReceiptAcquisitionError(
                    "pillow-heif is required for HEIC/HEIF "
                    "Ollama receipt input."
                ) from error

            register_heif_opener()

        try:
            with Image.open(image_path) as image:
                converted = image.convert("RGB")
                buffer = io.BytesIO()
                converted.save(
                    buffer,
                    format="JPEG",
                    quality=95,
                )
                return buffer.getvalue()
        except OSError as error:
            raise OllamaReceiptAcquisitionError(
                f"Could not decode receipt image: {image_path.name}"
            ) from error

    raise OllamaReceiptAcquisitionError(
        f"Unsupported receipt image format: "
        f"{image_path.suffix or '(none)'}"
    )


def _request_json(
    url: str,
    *,
    payload: dict | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> dict:
    data = None
    method = "GET"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        try:
            details = (
                error.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
                .strip()
            )
        except OSError:
            details = ""

        message = (
            f"Ollama request failed with HTTP {error.code}."
        )
        if details:
            message += f"\n{details[:1000]}"

        raise OllamaReceiptAcquisitionError(
            message
        ) from error

    except urllib.error.URLError as error:
        raise OllamaReceiptAcquisitionError(
            "Could not reach the local Ollama service at "
            f"{get_configured_base_url()}.\n"
            "Install/start Ollama, then try again. "
            "You can verify installed models with: ollama list"
        ) from error

    except TimeoutError as error:
        raise OllamaReceiptAcquisitionError(
            "The local Ollama request timed out."
        ) from error

    except json.JSONDecodeError as error:
        raise OllamaReceiptAcquisitionError(
            "The local Ollama service returned invalid JSON."
        ) from error


def _installed_model_names() -> set[str]:
    payload = _request_json(
        f"{get_configured_base_url()}/api/tags",
        timeout=15,
    )

    models = payload.get("models", [])
    names = set()

    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue

            for key in ("name", "model"):
                value = model.get(key)
                if isinstance(value, str) and value.strip():
                    names.add(value.strip())

    return names


def _model_is_installed(
    configured_model: str,
    installed_names: set[str],
) -> bool:
    if configured_model in installed_names:
        return True

    if ":" not in configured_model:
        return any(
            name == configured_model
            or name.startswith(
                f"{configured_model}:"
            )
            for name in installed_names
        )

    return False


def verify_ollama_ready() -> dict:
    model = get_configured_model()
    base_url = get_configured_base_url()
    num_ctx = get_configured_num_ctx()

    installed_names = _installed_model_names()

    if not _model_is_installed(
        model,
        installed_names,
    ):
        raise OllamaReceiptAcquisitionError(
            f'Ollama is running, but model "{model}" is not installed.\n'
            f"Install it with:\n\n"
            f"    ollama pull {model}\n\n"
            f"Then run ShopGraph again."
        )

    return {
        "provider": "Ollama",
        "model": model,
        "base_url": base_url,
        "num_ctx": num_ctx,
        "local_only": True,
    }



def run_local_json_prompt(
    prompt: str,
) -> tuple[dict, dict]:
    """
    Send a text-only JSON task to the same local Ollama model already used by
    ShopGraph receipt acquisition.

    This helper is deliberately local-only. It does not use a cloud API.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise OllamaReceiptAcquisitionError(
            "Local Ollama prompt cannot be blank."
        )

    readiness = verify_ollama_ready()

    payload = {
        "model": readiness["model"],
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "user",
                "content": prompt.strip(),
            }
        ],
        "options": {
            "temperature": 0,
            "num_ctx": readiness["num_ctx"],
        },
    }

    response_payload = _request_json(
        f"{readiness['base_url']}/api/chat",
        payload=payload,
    )

    message = response_payload.get("message")
    if not isinstance(message, dict):
        raise OllamaReceiptAcquisitionError(
            "Ollama response did not contain a message object."
        )

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OllamaReceiptAcquisitionError(
            "Ollama response did not contain JSON content."
        )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise OllamaReceiptAcquisitionError(
            "Ollama returned invalid JSON for the local interpretation task."
        ) from error

    if not isinstance(parsed, dict):
        raise OllamaReceiptAcquisitionError(
            "Ollama interpretation response must be a JSON object."
        )

    metadata = {
        "provider": "Ollama",
        "model": readiness["model"],
        "base_url": readiness["base_url"],
        "num_ctx": readiness["num_ctx"],
        "local_only": True,
        "done_reason": response_payload.get("done_reason"),
        "total_duration": response_payload.get("total_duration"),
    }

    return parsed, metadata

def transcribe_receipt_image(
    image_path: str | Path,
) -> tuple[str, dict]:
    source = (
        Path(image_path)
        .expanduser()
        .resolve()
    )

    if not source.is_file():
        raise OllamaReceiptAcquisitionError(
            f"Receipt image was not found: {source}"
        )

    readiness = verify_ollama_ready()
    model = readiness["model"]
    image_base64 = base64.b64encode(
        _image_bytes(source)
    ).decode("ascii")

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "user",
                "content": RECEIPT_TRANSCRIPTION_PROMPT,
                "images": [
                    image_base64,
                ],
            }
        ],
        "options": {
            "temperature": 0,
            "num_ctx": readiness["num_ctx"],
        },
    }

    response_payload = _request_json(
        f"{readiness['base_url']}/api/chat",
        payload=payload,
    )

    message = response_payload.get("message")
    if not isinstance(message, dict):
        raise OllamaReceiptAcquisitionError(
            "Ollama response did not contain a message object."
        )

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OllamaReceiptAcquisitionError(
            "Ollama response did not contain receipt transcription text."
        )

    provider_metadata = {
        "provider": "Ollama",
        "model": model,
        "base_url": readiness["base_url"],
        "num_ctx": readiness["num_ctx"],
        "local_only": True,
        "done_reason": response_payload.get(
            "done_reason"
        ),
        "total_duration": response_payload.get(
            "total_duration"
        ),
    }

    return (
        content.strip(),
        provider_metadata,
    )

