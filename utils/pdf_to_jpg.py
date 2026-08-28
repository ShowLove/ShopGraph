from __future__ import annotations

from pathlib import Path

import fitz

from utils.constants import (
    CURRENT_PIC_DIR,
    PDF_FILES_DIR,
)


DEFAULT_DPI = 300
JPEG_QUALITY = 95


def _list_pdf_files() -> list[Path]:
    PDF_FILES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sorted(
        (
            path
            for path in PDF_FILES_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.name.lower(),
    )


def _display_pdf_files(
    pdf_files: list[Path],
) -> None:
    print(
        "\nAvailable PDF files:\n"
    )

    for index, path in enumerate(
        pdf_files,
        start=1,
    ):
        print(
            f"{index}. {path.name}"
        )


def _parse_selection(
    value: str,
    pdf_files: list[Path],
) -> list[Path] | None:
    cleaned = value.strip()

    if cleaned == "0":
        return None

    if cleaned.lower() in {
        "a",
        "all",
    }:
        return list(pdf_files)

    # A single integer N means:
    # convert the first N PDFs in the displayed list.
    if cleaned.isdigit():
        count = int(cleaned)

        if 1 <= count <= len(pdf_files):
            return pdf_files[:count]

        raise ValueError(
            f"Enter a number from 1 to {len(pdf_files)}, "
            "A for all, or 0 to cancel."
        )

    # Optional convenience:
    # comma-separated file numbers allow specific files.
    parts = [
        part.strip()
        for part in cleaned.split(",")
        if part.strip()
    ]

    if not parts or not all(
        part.isdigit()
        for part in parts
    ):
        raise ValueError(
            "Enter A for all, a number N, comma-separated "
            "file numbers, or 0 to cancel."
        )

    indexes = []

    for part in parts:
        index = int(part)

        if not 1 <= index <= len(pdf_files):
            raise ValueError(
                f"PDF number {index} is out of range."
            )

        if index not in indexes:
            indexes.append(index)

    return [
        pdf_files[index - 1]
        for index in indexes
    ]


def _choose_pdf_files(
    pdf_files: list[Path],
) -> list[Path] | None:
    _display_pdf_files(
        pdf_files
    )

    print(
        "\nChoose what to convert:"
    )
    print(
        "- Enter A to convert all PDF files."
    )
    print(
        "- Enter a number N to convert the first N PDFs."
    )
    print(
        "- Or enter specific file numbers separated by commas "
        "(example: 1,3,5)."
    )
    print(
        "- Enter 0 to cancel."
    )

    while True:
        value = input(
            "\nSelection: "
        ).strip()

        try:
            return _parse_selection(
                value,
                pdf_files,
            )
        except ValueError as error:
            print(
                f"\n[ERROR] {error}"
            )


def _output_path(
    pdf_path: Path,
    page_number: int,
    page_count: int,
) -> Path:
    if page_count == 1:
        filename = (
            f"{pdf_path.stem}.jpg"
        )
    else:
        filename = (
            f"{pdf_path.stem}"
            f"_page_{page_number:03d}.jpg"
        )

    return (
        CURRENT_PIC_DIR
        / filename
    )


def _convert_pdf(
    pdf_path: Path,
    dpi: int = DEFAULT_DPI,
) -> list[Path]:
    outputs = []

    try:
        document = fitz.open(
            pdf_path
        )
    except Exception as error:
        raise ValueError(
            f"Could not open PDF '{pdf_path.name}': {error}"
        ) from error

    try:
        page_count = document.page_count

        if page_count == 0:
            raise ValueError(
                f"PDF has no pages: {pdf_path.name}"
            )

        for page_index in range(
            page_count
        ):
            page = document.load_page(
                page_index
            )

            pixmap = page.get_pixmap(
                dpi=dpi,
                alpha=False,
            )

            output_path = _output_path(
                pdf_path=pdf_path,
                page_number=page_index + 1,
                page_count=page_count,
            )

            pixmap.save(
                output_path,
                jpg_quality=JPEG_QUALITY,
            )

            outputs.append(
                output_path.resolve()
            )

    finally:
        document.close()

    return outputs


def convert_selected_pdfs_to_jpg() -> dict:
    pdf_files = _list_pdf_files()

    if not pdf_files:
        print(
            "\n[INFO] No PDF files were found in:"
            f"\n{PDF_FILES_DIR.resolve()}"
        )

        return {
            "pdf_count": 0,
            "jpg_count": 0,
            "outputs": [],
        }

    selected = _choose_pdf_files(
        pdf_files
    )

    if selected is None:
        print(
            "\n[INFO] PDF to JPG conversion cancelled."
        )

        return {
            "pdf_count": 0,
            "jpg_count": 0,
            "outputs": [],
        }

    CURRENT_PIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n[INFO] Converting PDF files to JPG..."
    )
    print(
        f"[INFO] Resolution: {DEFAULT_DPI} DPI"
    )
    print(
        f"[INFO] Output directory:"
        f"\n{CURRENT_PIC_DIR.resolve()}"
    )

    outputs = []
    converted_pdf_count = 0

    for pdf_path in selected:
        print(
            f"\n[INFO] Converting: {pdf_path.name}"
        )

        try:
            pdf_outputs = _convert_pdf(
                pdf_path
            )
        except ValueError as error:
            print(
                f"[ERROR] {error}"
            )
            continue

        converted_pdf_count += 1
        outputs.extend(
            pdf_outputs
        )

        print(
            f"[OK] Created {len(pdf_outputs)} JPG file(s)."
        )

        for output_path in pdf_outputs:
            print(
                f"- {output_path.name}"
            )

    return {
        "pdf_count": converted_pdf_count,
        "jpg_count": len(outputs),
        "outputs": outputs,
    }


def run_pdf_to_jpg_converter() -> None:
    print(
        "\n=== Convert PDF Files to JPG ===\n"
    )

    try:
        result = (
            convert_selected_pdfs_to_jpg()
        )

        if (
            result["pdf_count"] == 0
            and result["jpg_count"] == 0
        ):
            return

        print(
            "\n[OK] PDF to JPG conversion complete."
        )
        print(
            f"\nPDF files converted: "
            f"{result['pdf_count']}"
        )
        print(
            f"JPG files created: "
            f"{result['jpg_count']}"
        )
        print(
            "\nJPG output directory:"
            f"\n{CURRENT_PIC_DIR.resolve()}"
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            f"\n[ERROR] {error}"
        )
