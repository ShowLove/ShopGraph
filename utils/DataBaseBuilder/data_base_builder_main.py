from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import readline

from utils.DataBaseBuilder.benchmark_writer import write_corrected_benchmark
from utils.DataBaseBuilder.excel.purchase_history import (
    commit_receipt,
    source_already_imported,
)
from utils.DataBaseBuilder.excel.purchase_analytics import (
    generate_purchase_analytics,
)
from utils.DataBaseBuilder.excel.category_manager import (
    run_category_manager_menu,
)
from utils.DataBaseBuilder.parsers import build_parser
from utils.DataBaseBuilder.parsers.publix_parser import PUBLIX_TAX_PATTERN
from utils.DataBaseBuilder.purchase_record import NA, PurchaseRecord
from utils.DataBaseBuilder.receipt_loader import (
    choose_raw_ocr_file,
    load_ocr_lines,
)
from utils.DataBaseBuilder.receipt_session import ReceiptSession
from utils.DataBaseBuilder.refined_json_loader import (
    load_matching_refined_json,
    merge_refined_guess,
)
from utils.DataBaseBuilder.filename_metadata import (
    parse_receipt_filename_metadata,
)
from utils.DataBaseBuilder.skip_terms import (
    add_skip_substring,
    add_skip_term,
    get_skip_terms_file,
    match_product,
)


PUBLIX_TAX_OPTIONS = {
    "1": ("F", "Food item. Basic grocery/raw food category; generally non-taxable in Florida and commonly SNAP/EBT eligible."),
    "2": ("T", "Taxable item. Commonly taxable non-food or applicable prepared item."),
    "3": ("TF", "Taxable Food."),
    "4": ("LF", "Local Tax Food."),
    "5": ("TLF", "Taxable / Local Tax Food."),
    "6": (NA, "Unknown / not available."),
}


def display_data_base_builder_menu() -> None:
    print("\n=== ShopGraph Data Base Builder ===\n")
    print("1. Add Receipt to Purchase History")
    print("2. Generate / Refresh Purchase Analytics")
    print("3. Category Manager")
    print("0. Return to Main")


def _choose_receipt_parser():
    print("\nSelect receipt type:\n")
    print("1. Publix")
    print("2. Trader Joe's")
    print("3. Aldi")
    print("4. Other")
    print("0. Cancel")

    while True:
        option = input("\nSelect option: ").strip()

        if option == "0":
            return None

        parser = build_parser(option)

        if parser is not None:
            return parser

        print("\n[ERROR] Invalid option.")


def _prompt_store_number(
    receipt_type: str,
    default_value: str = NA,
) -> str | None:
    if receipt_type == "Publix":
        print("\nSelect store:\n")
        print("1. 1058 - Indian Harbour Place")
        print("2. Other")
        print("0. Cancel")

        if default_value != NA:
            print(
                f"\n[INFO] Refined JSON best guess: {default_value}"
            )

        while True:
            option = input("\nSelect option: ").strip()

            if option == "1":
                return "1058"

            if option == "2":
                break

            if option == "0":
                return None

            print("\n[ERROR] Invalid option.")

    while True:
        prompt = "\nStore Number: "
        value = (
            _input_with_current_value(
                prompt,
                default_value,
            )
            if default_value != NA
            else input(prompt).strip()
        )
        value = value.strip()

        if value:
            return value

        print("\n[ERROR] Store Number cannot be blank.")


def _prompt_receipt_date(
    default_value: str = NA,
) -> str | None:
    while True:
        prompt = "\nReceipt date (MM/DD/YYYY, or 0 to cancel): "

        value = (
            _input_with_current_value(
                prompt,
                default_value,
            )
            if default_value != NA
            else input(prompt).strip()
        )
        value = value.strip()

        if value == "0":
            return None

        try:
            datetime.strptime(value, "%m/%d/%Y")
            return value
        except ValueError:
            print("\n[ERROR] Enter the date as MM/DD/YYYY.")


def _prompt_starting_line(lines: list[dict]) -> int | None:
    available = {line["line_number"] for line in lines}
    minimum = min(available)
    maximum = max(available)

    while True:
        value = input(
            f"\nStarting OCR line number ({minimum}-{maximum}, or 0 to cancel): "
        ).strip()

        if value == "0":
            return None

        if not value.isdigit():
            print("\n[ERROR] Enter a numeric line number.")
            continue

        line_number = int(value)

        if line_number not in available:
            print(
                "\n[ERROR] That line_number does not exist in the selected JSON."
            )
            continue

        return line_number


def _confirm_duplicate_import(source_path) -> bool:
    if not source_already_imported(source_path):
        return True

    print(
        "\n[WARNING] This OCR JSON has already been imported:"
        f"\n{source_path.name}"
        "\n\n1. Cancel duplicate import"
        "\n2. Continue anyway"
    )

    while True:
        option = input("\nSelect option: ").strip()

        if option == "1":
            return False

        if option == "2":
            return True

        print("\n[ERROR] Invalid option.")


def _display_line(parser, line: dict, record: PurchaseRecord) -> None:
    print("\n" + "-" * 50)
    print(f"\nOCR Line {line['line_number']}")
    print(line["text"])
    print("\nProposed interpretation:\n")
    print(parser.format_record(record))


def _input_with_current_value(
    prompt: str,
    current_value: str,
) -> str:
    """
    Display an editable input prompt pre-populated with the current value.

    The user can:
    - press Enter to keep the current value,
    - edit part of the current value,
    - or replace it completely.

    readline is used only for the interactive pre-population behavior.
    """

    def _prefill() -> None:
        readline.insert_text(
            str(current_value)
        )
        readline.redisplay()

    readline.set_startup_hook(
        _prefill
    )

    try:
        return input(
            prompt
        ).strip()

    finally:
        readline.set_startup_hook()


def _prompt_tax_code(current_value: str) -> str:
    print(f"\nCurrent Tax Code: {current_value}")
    print("\nSelect Tax Code:\n")

    for option, (code, description) in PUBLIX_TAX_OPTIONS.items():
        print(f"{option}. {code}")
        print(f"   {description}")

    print("7. Enter custom value")

    while True:
        option = input("\nSelect option: ").strip()

        if option in PUBLIX_TAX_OPTIONS:
            return PUBLIX_TAX_OPTIONS[option][0]

        if option == "7":
            return (
                _input_with_current_value(
                    "\nEnter Tax Code: ",
                    current_value,
                )
                or NA
            )

        print("\n[ERROR] Invalid option.")


def _valid_price(value: str) -> bool:
    if value == NA:
        return True

    try:
        amount = float(value)
    except ValueError:
        return False

    return amount >= 0


def _correct_field(
    parser,
    record: PurchaseRecord,
    field_name: str,
) -> PurchaseRecord:
    label = parser.field_labels[field_name]
    current = getattr(record, field_name)

    if field_name == "tax_code" and parser.receipt_type == "Publix":
        value = _prompt_tax_code(current)
        return record.with_value(field_name, value)

    while True:
        print(f"\nCurrent {label}: {current}")
        value = _input_with_current_value(
            f"Enter corrected {label}: ",
            current,
        )
        value = value or NA

        if field_name == "six_digit_sku":
            if value != NA and (not value.isdigit() or len(value) != 6):
                print("\n[ERROR] SKU must be exactly six digits or NA.")
                continue

        if field_name in {"price", "total"} and not _valid_price(value):
            print("\n[ERROR] Value must be a non-negative number or NA.")
            continue

        if field_name == "date" and value != NA:
            try:
                datetime.strptime(value, "%m/%d/%Y")
            except ValueError:
                print("\n[ERROR] Date must use MM/DD/YYYY or NA.")
                continue

        return record.with_value(field_name, value)


def _correct_columns(parser, record: PurchaseRecord) -> PurchaseRecord:
    valid_numbers = {
        str(index): field_name
        for index, field_name in enumerate(
            parser.display_fields,
            start=1,
        )
    }

    while True:
        raw = input(
            "\nCorrect the following column numbers "
            "(separate with spaces): "
        ).strip()
        selections = raw.split()

        if selections and all(
            selection in valid_numbers
            for selection in selections
        ):
            break

        print("\n[ERROR] Enter valid displayed column numbers.")

    corrected = record

    for selection in selections:
        corrected = _correct_field(
            parser,
            corrected,
            valid_numbers[selection],
        )

    return corrected


def _skip_rule_match(
    record: PurchaseRecord,
):
    return match_product(
        store=record.store,
        product=record.product,
    )


def _display_auto_skip(
    line: dict,
    record: PurchaseRecord,
    match,
) -> None:
    rule_label = (
        "exact term"
        if match.match_type == "term"
        else "sub-string"
    )

    print(
        "\n[AUTO-SKIP] "
        f"OCR Line {line['line_number']} skipped."
    )
    print(
        f'Store: "{record.store}"'
    )
    print(
        f'Product: "{record.product}"'
    )
    print(
        f'Matched {rule_label}: "{match.matched_value}"'
    )


def _prompt_skip_substring(
    current_product: str,
) -> str | None:
    print(
        "\nEnter the Product sub-string that should "
        "cause future lines for this store to be skipped."
    )
    print(
        "The current Product is pre-populated so it can "
        "be shortened before saving."
    )

    value = _input_with_current_value(
        "Enter sub-string to skip forever: ",
        current_product,
    ).strip()

    if not value:
        print(
            "\n[INFO] No sub-string was saved."
        )
        return None

    if value == NA:
        print(
            "\n[ERROR] NA cannot be stored as a skip sub-string."
        )
        return None

    return value


def _review_line(parser, line: dict, record: PurchaseRecord) -> tuple[str, PurchaseRecord]:
    current = record

    while True:
        _display_line(parser, line, current)
        print("\n1. Accept Line")
        print("2. Correct Columns")
        print("3. Accept With NAs / Skip Corrections")
        print("4. Skip Line")
        print("5. Skip Term Forever")
        print("6. Skip Sub-String Forever")
        print("7. Finish Receipt")
        print("8. Accept Remaining Lines")
        print("0. Cancel Receipt Import")

        option = input("\nSelect option: ").strip()

        if option in {"1", "3"}:
            return "accept", current

        if option == "2":
            current = _correct_columns(parser, current)
            continue

        if option == "4":
            return "skip", current

        if option == "5":
            try:
                added, path = add_skip_term(
                    store=current.store,
                    product=current.product,
                )
            except ValueError as error:
                print(
                    f"\n[ERROR] {error}"
                )
                continue

            if added:
                print(
                    "\n[OK] Store-specific skip term saved."
                )
            else:
                print(
                    "\n[INFO] This store-specific skip term "
                    "was already saved."
                )

            print(
                f'Store: "{current.store}"'
            )
            print(
                f'Term: "{current.product}"'
            )
            print(
                f"Config:\n{path}"
            )

            return "skip", current

        if option == "6":
            substring = _prompt_skip_substring(
                current.product
            )

            if substring is None:
                continue

            try:
                added, path = add_skip_substring(
                    store=current.store,
                    substring=substring,
                )
            except ValueError as error:
                print(
                    f"\n[ERROR] {error}"
                )
                continue

            if added:
                print(
                    "\n[OK] Store-specific skip sub-string saved."
                )
            else:
                print(
                    "\n[INFO] This store-specific skip sub-string "
                    "was already saved."
                )

            print(
                f'Store: "{current.store}"'
            )
            print(
                f'Sub-string: "{substring}"'
            )
            print(
                f"Config:\n{path}"
            )

            return "skip", current

        if option == "7":
            return "finish", current

        if option == "8":
            return "accept_remaining", current

        if option == "0":
            return "cancel", current

        print("\n[ERROR] Invalid option.")


def run_receipt_import(
    source_path: str | Path | None = None,
) -> None:
    if source_path is None:
        selected_source = choose_raw_ocr_file()
    else:
        selected_source = Path(source_path).expanduser().resolve()
        print("\n=== Add Receipt to Purchase History ===\n")
        print(
            "[INFO] Using OCR file from completed capability:"
            f"\n{selected_source}"
        )

    if selected_source is None:
        return

    source_path = selected_source

    try:
        lines = load_ocr_lines(source_path)
    except (OSError, ValueError) as error:
        print(f"\n[ERROR] {error}")
        return

    filename_metadata = parse_receipt_filename_metadata(source_path)

    if filename_metadata is not None:
        print(
            "\n[OK] Receipt metadata detected from filename:"
            f"\nDate: {filename_metadata.receipt_date}"
            f"\nStore: {filename_metadata.store_name}"
            f"\nStore Number: {filename_metadata.store_number}"
        )
    else:
        print(
            "\n[INFO] Filename metadata was not recognized."
            "\nReceipt Type, Store Number, and Receipt Date "
            "will be entered manually."
        )

    refined = load_matching_refined_json(
        source_path
    )

    if refined is None:
        print(
            "\n[INFO] No valid matching refined JSON was found. "
            "Data Base Builder will use the existing parser guesses."
        )
        refined_line_map = {}
        refined_context = {}

    else:
        print(
            "\n[OK] Refined JSON loaded for improved initial guesses:"
            f"\n{refined['path']}"
        )
        refined_line_map = refined["line_map"]
        refined_context = refined["receipt_context"]

        suggested_store = refined_context.get(
            "store",
            NA,
        )

        if suggested_store != NA:
            print(
                "\n[INFO] Refined store best guess: "
                f"{suggested_store}"
            )

    if filename_metadata is not None:
        parser = build_parser(filename_metadata.parser_option)
        if parser is None:
            print("\n[ERROR] Could not select parser from filename metadata.")
            return
        print(
            "\n[INFO] Receipt parser selected automatically: "
            f"{parser.receipt_type}"
        )
    else:
        parser = _choose_receipt_parser()
        if parser is None:
            return

    refined_store_number = str(
        refined_context.get(
            "store_number",
            NA,
        )
        or NA
    )

    if filename_metadata is not None:
        store_number = filename_metadata.store_number
        print(
            "\n[INFO] Store Number filled from filename: "
            f"{store_number}"
        )
    else:
        store_number = _prompt_store_number(
            parser.receipt_type,
            default_value=refined_store_number,
        )
        if store_number is None:
            return

    refined_date = str(
        refined_context.get(
            "receipt_date",
            NA,
        )
        or NA
    )

    if filename_metadata is not None:
        receipt_date = filename_metadata.receipt_date
        print(
            "\n[INFO] Receipt Date filled from filename: "
            f"{receipt_date}"
        )
    else:
        receipt_date = _prompt_receipt_date(
            default_value=refined_date,
        )
        if receipt_date is None:
            return

    starting_line = _prompt_starting_line(
        lines
    )

    if starting_line is None:
        return

    if not _confirm_duplicate_import(
        source_path
    ):
        return

    session = ReceiptSession(
        source_path=source_path,
        receipt_type=parser.receipt_type,
        store_number=store_number,
        receipt_date=receipt_date,
        starting_line_number=starting_line,
    )

    eligible_lines = [
        line
        for line in lines
        if line["line_number"]
        >= starting_line
    ]

    def _initial_record(
        line: dict,
    ) -> PurchaseRecord:
        parser_record = parser.parse_line(
            text=line["text"],
            store_number=store_number,
            receipt_date=receipt_date,
        )

        # Store selection, Store Number, and Date have just been explicitly
        # confirmed by the user in this session. They outrank Stage-7 guesses.
        confirmed_store_name = (
            filename_metadata.store_name
            if filename_metadata is not None
            else parser.receipt_type
        )

        parser_record = parser_record.with_value(
            "store",
            confirmed_store_name,
        )

        return merge_refined_guess(
            parser_record,
            refined_line_map.get(
                line["line_number"]
            ),
            protected_fields={
                "store",
                "store_number",
                "date",
            },
        )

    should_commit = False

    for line in eligible_lines:
        record = _initial_record(line)

        skip_match = _skip_rule_match(
            record
        )

        if skip_match.matched:
            _display_auto_skip(
                line,
                record,
                skip_match,
            )
            session.skip(
                line["line_number"]
            )
            continue

        action, reviewed_record = _review_line(
            parser,
            line,
            record,
        )

        if action == "accept":
            session.accept(
                line_number=line["line_number"],
                purchase=reviewed_record,
            )
            continue

        if action == "skip":
            session.skip(
                line["line_number"]
            )
            continue

        if action == "accept_remaining":
            session.accept(
                line_number=line["line_number"],
                purchase=reviewed_record,
                status="bulk_accepted",
            )

            current_index = (
                eligible_lines.index(line)
            )

            for remaining_line in (
                eligible_lines[
                    current_index + 1:
                ]
            ):
                remaining_record = (
                    _initial_record(
                        remaining_line
                    )
                )

                remaining_skip_match = (
                    _skip_rule_match(
                        remaining_record
                    )
                )

                if remaining_skip_match.matched:
                    _display_auto_skip(
                        remaining_line,
                        remaining_record,
                        remaining_skip_match,
                    )
                    session.skip(
                        remaining_line[
                            "line_number"
                        ]
                    )
                    continue

                session.accept(
                    line_number=remaining_line[
                        "line_number"
                    ],
                    purchase=remaining_record,
                    status="bulk_accepted",
                )

            should_commit = True
            break

        if action == "finish":
            should_commit = True
            break

        if action == "cancel":
            print(
                "\n[INFO] Receipt import cancelled. "
                "No workbook changes were made."
            )
            return

    else:
        should_commit = True

    if not should_commit:
        return

    if not session.accepted_purchases:
        print(
            "\n[INFO] No purchase lines were accepted. "
            "Nothing was written."
        )
        return

    try:
        summary = commit_receipt(
            session
        )
    except (OSError, ValueError) as error:
        print(
            f"\n[ERROR] Could not commit receipt: {error}"
        )
        return

    benchmark_path = None

    try:
        benchmark_path = (
            write_corrected_benchmark(
                session
            )
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(
            "\n[WARNING] Purchase History was committed successfully, "
            "but the corrected benchmark could not be written:"
            f"\n{error}"
        )

    print(
        "\n[OK] Receipt committed to Purchase History."
    )
    print(
        f"\nWorkbook:\n{summary['workbook_path']}"
    )

    if benchmark_path is not None:
        print(
            f"\nCorrected Benchmark:\n{benchmark_path}"
        )
    else:
        print(
            "\nCorrected Benchmark:\n"
            "Existing benchmark kept unchanged."
        )

    print(
        f"\nPurchases added: "
        f"{summary['purchases_added']}"
        f"\nExisting product histories updated: "
        f"{summary['existing_histories_updated']}"
        f"\nNew product rows created: "
        f"{summary['new_product_rows']}"
    )


def _run_purchase_analytics() -> None:
    print("\n=== Purchase Analytics ===\n")

    try:
        summary = generate_purchase_analytics()
    except (
        FileNotFoundError,
        OSError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] Could not generate Purchase Analytics: {error}"
        )
        return

    print(
        "[OK] Purchase Analytics refreshed."
        f"\n\nWorkbook:\n{summary['workbook_path']}"
        f"\n\nCharts created: {summary['charts_created']}"
        f"\nPurchase observations: {summary['purchase_observations']}"
    )

    if summary.get("skipped_pairs", 0):
        print(
            "\n[WARNING] Skipped malformed/incomplete Date/Price pairs: "
            f"{summary['skipped_pairs']}"
        )


def run_data_base_builder_menu() -> None:
    while True:
        display_data_base_builder_menu()
        option = input("\nSelect option: ").strip()

        if option == "1":
            run_receipt_import()

        elif option == "2":
            _run_purchase_analytics()

        elif option == "3":
            run_category_manager_menu()

        elif option == "0":
            return

        else:
            print("\n[ERROR] Invalid option.")


def main() -> None:
    run_data_base_builder_menu()


if __name__ == "__main__":
    main()
