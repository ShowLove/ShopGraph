import os
from pathlib import Path
from datetime import datetime

from utils.constants import PROJECT_ROOT, CODEBASE_OUTPUT_FILE


ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt"
}

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "node_modules",

    # ShopGraph data directories
    "raw_receipts",
    "cropped",
    "perspective_corrected",
    "preprocessed",
    "raw_ocr",
    "extracted",
    "normalized",

    # Generated / runtime directories
    "logs",
    "exports"
}

IGNORE_FILES = {
    "shopgraph_codebase.txt",
    ".DS_Store"
}

IGNORE_SUFFIXES = {
    ".pyc",
    ".json",
    ".log",
    ".sqlite",
    ".sqlite3",
    ".db",

    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".webp",
    ".tif",
    ".tiff",
    ".pdf"
}


def _should_ignore(path: Path) -> bool:
    if any(
        part in IGNORE_DIRS
        for part in path.parts
    ):
        return True

    if path.name in IGNORE_FILES:
        return True

    if path.suffix.lower() in IGNORE_SUFFIXES:
        return True

    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return True

    return False


def _build_tree(root: Path) -> str:
    lines = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)

        dirnames[:] = [
            directory
            for directory in dirnames
            if directory not in IGNORE_DIRS
        ]

        level = len(
            dirpath.relative_to(root).parts
        )

        indent = "    " * level

        lines.append(
            f"{indent}{dirpath.name}/"
        )

        for filename in sorted(filenames):
            file_path = (
                dirpath
                / filename
            )

            if not _should_ignore(file_path):
                lines.append(
                    f"{indent}    {filename}"
                )

    return "\n".join(lines)


def _collect_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)

        dirnames[:] = [
            directory
            for directory in dirnames
            if directory not in IGNORE_DIRS
        ]

        for filename in sorted(filenames):
            file_path = (
                dirpath
                / filename
            )

            if not _should_ignore(file_path):
                yield file_path


def export_codebase_bundle(
    root_path: str | None = None
) -> str:
    root = (
        PROJECT_ROOT
        if root_path is None
        else Path(root_path).resolve()
    )

    output_path = (
        CODEBASE_OUTPUT_FILE
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"\n[INFO] Exporting CLEAN ShopGraph codebase from: {root}"
    )

    tree = _build_tree(root)
    files = list(
        _collect_files(root)
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as out:
        out.write(
            "=== SHOPGRAPH CLEAN CODEBASE FOR LLM ===\n\n"
        )

        out.write(tree)
        out.write("\n\n")
        out.write("=" * 80 + "\n\n")
        out.write(
            f"Generated: {datetime.now()}\n"
        )
        out.write(
            f"Root: {root}\n"
        )
        out.write(
            "Mode: LLM-clean export\n"
        )
        out.write(
            "Excluded: receipt images, OCR JSON, datasets, databases, logs, caches\n\n"
        )
        out.write("=" * 80 + "\n\n")

        for file_path in files:
            try:
                relative = (
                    file_path.relative_to(root)
                )

                out.write("\n\n")
                out.write("=" * 80 + "\n")
                out.write(
                    f"FILE: {relative}\n"
                )
                out.write("=" * 80 + "\n\n")

                content = (
                    file_path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )

                out.write(content)

            except Exception as error:
                out.write(
                    f"\n[ERROR READING FILE: {file_path}] "
                    f"{error}\n"
                )

    print(
        f"[OK] Clean ShopGraph codebase exported to: "
        f"{output_path}"
    )

    return str(
        output_path
    )
