from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from utils.constants import DATA_DIR


RAW_OCR_DIR = DATA_DIR / "raw_ocr"
BENCHMARK_DIR = DATA_DIR / "benchmarks"

SKU_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
PRICE_PATTERN = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")


def _normalize(value: str) -> str:
    value = value.lower().replace(",", ".")
    value = re.sub(r"[^a-z0-9.]+", " ", value)
    return " ".join(value.split())


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _benchmark_files() -> list[Path]:
    if not BENCHMARK_DIR.exists():
        return []

    return sorted(
        path
        for path in BENCHMARK_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".json"
    )


def _ground_truth_rows(data: dict) -> list[dict]:
    rows = []

    for line in data.get("text", []):
        review = line.get("human_review")
        if not isinstance(review, dict):
            continue

        rows.append(
            {
                "line_number": line.get("line_number"),
                "sku": review.get("six_digit_sku", "NA"),
                "product": review.get("product", "NA"),
                "tax_code": review.get("tax_code", "NA"),
                "price": review.get("price", "NA"),
                "text": line.get("text", ""),
            }
        )

    return rows


def _predicted_rows(data: dict) -> list[dict]:
    rows = []

    for line in data.get("text", []):
        text = line.get("text", "")
        rows.append(
            {
                "line_number": line.get("line_number"),
                "text": text,
                "normalized": _normalize(text),
                "sku": (
                    SKU_PATTERN.findall(text)[0]
                    if SKU_PATTERN.findall(text)
                    else None
                ),
                "prices": [
                    price.replace(",", ".")
                    for price in PRICE_PATTERN.findall(text)
                ],
            }
        )

    return rows


def _best_prediction(
    truth: dict,
    predictions: list[dict],
) -> dict | None:
    if truth["sku"] != "NA":
        for prediction in predictions:
            if prediction["sku"] == truth["sku"]:
                return prediction

    product_norm = _normalize(truth["product"])
    best = None
    best_score = 0.0

    for prediction in predictions:
        score = SequenceMatcher(
            None,
            product_norm,
            prediction["normalized"],
        ).ratio()

        if score > best_score:
            best = prediction
            best_score = score

    if best_score < 0.35:
        return None

    return best


def evaluate_pair(
    benchmark_path: Path,
    raw_path: Path,
) -> dict:
    benchmark = _load_json(benchmark_path)
    raw = _load_json(raw_path)

    truth_rows = _ground_truth_rows(benchmark)
    predictions = _predicted_rows(raw)

    product_exact = 0
    product_close = 0
    sku_exact = 0
    sku_total = 0
    price_exact = 0
    price_total = 0
    matched_rows = 0

    details = []

    for truth in truth_rows:
        prediction = _best_prediction(
            truth,
            predictions,
        )

        if prediction is None:
            details.append(
                {
                    "truth": truth,
                    "prediction": None,
                }
            )
            continue

        matched_rows += 1

        truth_product = _normalize(truth["product"])
        prediction_text = prediction["normalized"]

        if truth_product in prediction_text:
            product_exact += 1

        product_similarity = SequenceMatcher(
            None,
            truth_product,
            prediction_text,
        ).ratio()

        if product_similarity >= 0.70:
            product_close += 1

        if truth["sku"] != "NA":
            sku_total += 1
            if prediction["sku"] == truth["sku"]:
                sku_exact += 1

        if truth["price"] != "NA":
            price_total += 1
            if truth["price"] in prediction["prices"]:
                price_exact += 1

        details.append(
            {
                "truth": truth,
                "prediction": prediction,
                "product_similarity": round(
                    product_similarity,
                    4,
                ),
            }
        )

    total = len(truth_rows)

    return {
        "benchmark": benchmark_path.name,
        "raw_ocr": raw_path.name,
        "receipt_type": benchmark.get(
            "benchmark",
            {},
        ).get(
            "receipt_type",
            "Unknown",
        ),
        "ground_truth_rows": total,
        "matched_rows": matched_rows,
        "matched_row_rate": (
            round(matched_rows / total, 4)
            if total else 0.0
        ),
        "product_exact": product_exact,
        "product_exact_rate": (
            round(product_exact / total, 4)
            if total else 0.0
        ),
        "product_close": product_close,
        "product_close_rate": (
            round(product_close / total, 4)
            if total else 0.0
        ),
        "sku_exact": sku_exact,
        "sku_total": sku_total,
        "sku_exact_rate": (
            round(sku_exact / sku_total, 4)
            if sku_total else None
        ),
        "price_exact": price_exact,
        "price_total": price_total,
        "price_exact_rate": (
            round(price_exact / price_total, 4)
            if price_total else None
        ),
        "details": details,
    }


def run_benchmark_evaluator() -> None:
    print("\n=== OCR Benchmark Evaluator ===\n")

    benchmarks = _benchmark_files()

    if not benchmarks:
        print(
            "[ERROR] No JSON benchmarks found in:"
            f"\n{BENCHMARK_DIR}"
        )
        return

    results = []

    for benchmark_path in benchmarks:
        raw_path = RAW_OCR_DIR / benchmark_path.name

        if not raw_path.exists():
            print(
                "[SKIP] No matching raw OCR file:"
                f"\n{raw_path.name}"
            )
            continue

        result = evaluate_pair(
            benchmark_path,
            raw_path,
        )
        results.append(result)

        print(
            "\n"
            + "-" * 60
            + f"\n{result['receipt_type']} - "
            f"{benchmark_path.name}"
        )
        print(
            f"Rows matched: "
            f"{result['matched_rows']}/"
            f"{result['ground_truth_rows']} "
            f"({result['matched_row_rate']:.1%})"
        )
        print(
            f"Product exact: "
            f"{result['product_exact']}/"
            f"{result['ground_truth_rows']} "
            f"({result['product_exact_rate']:.1%})"
        )
        print(
            f"Product close >= 70%: "
            f"{result['product_close']}/"
            f"{result['ground_truth_rows']} "
            f"({result['product_close_rate']:.1%})"
        )

        if result["sku_total"]:
            print(
                f"SKU exact: "
                f"{result['sku_exact']}/"
                f"{result['sku_total']} "
                f"({result['sku_exact_rate']:.1%})"
            )

        if result["price_total"]:
            print(
                f"Price exact: "
                f"{result['price_exact']}/"
                f"{result['price_total']} "
                f"({result['price_exact_rate']:.1%})"
            )

    if not results:
        print(
            "\n[ERROR] No benchmark/raw OCR filename pairs "
            "were available to compare."
        )
        return

    output_path = DATA_DIR / "benchmark_results.json"

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "results": results,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    print(
        "\n[OK] Detailed benchmark results created:"
        f"\n{output_path.resolve()}"
    )
