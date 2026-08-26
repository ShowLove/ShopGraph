from __future__ import annotations

from pathlib import Path

from capabilities.OCRAcquisitionPipeline.constants import CURRENT_PIC_DIR


SUPPORTED_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".webp",
    ".tif",
    ".tiff",
}


def _get_available_receipts() -> list[Path]:
    CURRENT_PIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sorted(
        path
        for path in CURRENT_PIC_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )


def choose_receipt_image() -> Path | None:
    receipts = _get_available_receipts()

    if not receipts:
        print(
            "\n[ERROR] No receipt images were found in:"
            f"\n{CURRENT_PIC_DIR}"
        )
        return None

    print("\nAvailable receipt images:\n")

    for index, receipt in enumerate(
        receipts,
        start=1,
    ):
        print(
            f"{index}. {receipt.name}"
        )

    print("0. Cancel")

    while True:
        choice = input(
            "\nSelect receipt: "
        ).strip()

        if choice == "0":
            return None

        try:
            selected_index = int(choice)
        except ValueError:
            print(
                "[ERROR] Enter a number from the list."
            )
            continue

        if not 1 <= selected_index <= len(receipts):
            print(
                "[ERROR] Invalid selection."
            )
            continue

        return receipts[
            selected_index - 1
        ].resolve()
