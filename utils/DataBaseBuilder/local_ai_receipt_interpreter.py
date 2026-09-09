from __future__ import annotations

from capabilities.OllamaReceiptAcquisitionPipeline.ollama_client import (
    OllamaReceiptAcquisitionError,
    run_local_json_prompt,
)
from utils.DataBaseBuilder.purchase_record import NA


class LocalAIReceiptInterpretationError(RuntimeError):
    pass


def _build_prompt(
    lines: list[dict],
    receipt_type: str,
) -> str:
    numbered_lines = "\n".join(
        f'{line["line_number"]}: {line["text"]}'
        for line in lines
    )

    return f"""
You are ShopGraph's local receipt-line interpretation engine.

Store: {receipt_type}

Your task is NOT OCR. The text below has already been transcribed.
Use the whole receipt context to make conservative initial guesses for only:
- whether each source line contains a purchased product,
- the printed product name,
- the final item price actually charged.

Return JSON only with exactly this shape:

{{
  "lines": [
    {{
      "line_number": 1,
      "is_product": true,
      "product": "printed merchandise name only",
      "price": "0.00"
    }}
  ]
}}

Critical rules:

1. Return exactly one interpretation object for every numbered input line.
2. line_number must match the original input line_number.
3. Product must contain the merchandise description only.
4. Remove tax codes, SKU/PLU codes, quantities, promotion math, unit-price math,
   savings text, and final-price numbers from Product.
5. Price means the FINAL amount charged for that item.
6. Do not choose a reference/promotion amount merely because it is larger.
7. In text such as:
      Chobani Fab 0% Blck Chry F 1 @ 10 for $10.00 1.00 You saved: $0.62
   interpret:
      product = "Chobani Fab 0% Blck Chry"
      price = "1.00"
   The $10.00 is promotion/reference math and $0.62 is savings, not item price.
8. For "3 for $10.00 3.33", final item price is 3.33, not 10.00.
9. For weight pricing, distinguish weight/unit price from the final extended charge.
10. Preserve 0.00 as a legitimate item price.
11. Use surrounding receipt lines for context when needed.
12. If the line is receipt metadata, subtotal, tax, total, payment information,
    savings-only text, promotion-only text, address/header/footer text, or otherwise
    not a purchased product, return:
      is_product = false
      product = "NA"
      price = "NA"
13. If a product is visible but its final item price cannot be determined safely,
    keep the product and return price = "NA".
14. If a final item price is visible but a product cannot be identified safely,
    return product = "NA".
15. Never invent a brand, flavor, size, product, or price not supported by the text.
16. Do not create Common Name, Sub-Category, Category, Store, Store Number, or Date.
17. Do not add commentary outside the JSON.

Receipt lines:
{numbered_lines}
""".strip()


def build_local_ai_line_interpretations(
    lines: list[dict],
    receipt_type: str,
) -> dict[int, dict]:
    """
    Interpret the full ordered receipt once with local Ollama.

    Returned mapping is intentionally limited to Product / Price semantics.
    Filename/store metadata remains owned by the existing Data Base Builder.
    """
    if not lines:
        return {}

    try:
        payload, _metadata = run_local_json_prompt(
            _build_prompt(
                lines,
                receipt_type,
            )
        )
    except OllamaReceiptAcquisitionError as error:
        raise LocalAIReceiptInterpretationError(
            str(error)
        ) from error

    raw_lines = payload.get("lines")
    if not isinstance(raw_lines, list):
        raise LocalAIReceiptInterpretationError(
            "Local Ollama interpretation response did not contain a 'lines' list."
        )

    valid_line_numbers = {
        int(line["line_number"])
        for line in lines
    }
    result: dict[int, dict] = {}

    for item in raw_lines:
        if not isinstance(item, dict):
            continue

        line_number = item.get("line_number")
        if not isinstance(line_number, int):
            continue
        if line_number not in valid_line_numbers:
            continue
        if line_number in result:
            continue

        is_product = bool(item.get("is_product", False))

        product_value = item.get("product", NA)
        product = (
            product_value.strip()
            if isinstance(product_value, str)
            else NA
        )
        if not product or product.upper() == NA:
            product = NA

        price_value = item.get("price", NA)
        price = (
            price_value.strip()
            if isinstance(price_value, str)
            else NA
        )
        if not price or price.upper() == NA:
            price = NA

        if price != NA:
            try:
                amount = float(
                    price.replace("$", "").replace(",", "")
                )
            except ValueError:
                price = NA
            else:
                if amount < 0:
                    price = NA
                else:
                    price = f"{amount:.2f}"

        if not is_product:
            product = NA
            price = NA

        result[line_number] = {
            "is_product": is_product,
            "product": product,
            "price": price,
        }

    return result
