from __future__ import annotations

import shutil
from pathlib import Path

from capabilities.OCRAcquisitionPipeline.receipt_picker import (
    SUPPORTED_IMAGE_SUFFIXES,
)
from utils.code_update_importer import (
    change_import_location,
    get_import_location,
)
from utils.constants import CURRENT_PIC_DIR


def _looks_like_supported_image_signature(path: Path) -> bool:
    """
    Confirm that a file with a ShopGraph-supported image suffix also has a
    recognizable image-file signature.

    The supported suffix list is imported directly from ShopGraph's receipt
    picker so this utility stays synchronized with the formats the OCR pipeline
    accepts.
    """
    try:
        with path.open("rb") as file:
            header = file.read(32)
    except OSError:
        return False

    suffix = path.suffix.casefold()

    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xFF\xD8\xFF")

    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")

    if suffix == ".webp":
        return (
            len(header) >= 12
            and header[:4] == b"RIFF"
            and header[8:12] == b"WEBP"
        )

    if suffix in {".tif", ".tiff"}:
        return header.startswith(
            (
                b"II*\x00",
                b"MM\x00*",
                b"II+\x00",
                b"MM\x00+",
            )
        )

    if suffix == ".heic":
        # HEIC/HEIF files are ISO Base Media File Format containers. The
        # compatible brand normally appears in the initial ftyp box.
        if len(header) < 12 or header[4:8] != b"ftyp":
            return False

        compatible_header = header[8:]
        heif_brands = (
            b"heic",
            b"heix",
            b"hevc",
            b"hevx",
            b"heim",
            b"heis",
            b"hevm",
            b"hevs",
            b"mif1",
            b"msf1",
        )
        return any(
            brand in compatible_header
            for brand in heif_brands
        )

    return False


def is_picture(path: Path) -> bool:
    if not path.is_file():
        return False

    if path.suffix.casefold() not in SUPPORTED_IMAGE_SUFFIXES:
        return False

    return _looks_like_supported_image_signature(path)


def _available_pictures(folder: Path) -> list[Path]:
    """
    Return only real pictures that ShopGraph's receipt picker is prepared to
    ingest. Other files in the import directory are silently ignored.
    """
    try:
        pictures = [
            path
            for path in folder.iterdir()
            if is_picture(path)
        ]
    except OSError as error:
        raise OSError(
            f"Could not read import folder:\n{folder}\n\n{error}"
        ) from error

    pictures.sort(
        key=lambda path: (
            path.stat().st_mtime,
            path.name.casefold(),
        ),
        reverse=True,
    )
    return pictures


def _select_picture(folder: Path) -> Path | None:
    pictures = _available_pictures(folder)

    print("\n=== Available Pictures ===\n")
    print(f"Import folder:\n{folder}\n")

    if not pictures:
        print(
            "[INFO] No supported pictures were found in this folder."
        )
        return None

    for index, path in enumerate(pictures, start=1):
        print(f"{index}. {path.name}")

    print("0. Cancel")

    while True:
        value = input("\nSelect picture: ").strip()

        if value == "0":
            return None

        try:
            index = int(value)
        except ValueError:
            print("\n[ERROR] Invalid option.")
            continue

        if 1 <= index <= len(pictures):
            return pictures[index - 1]

        print("\n[ERROR] Invalid option.")


def _confirm_replace(destination: Path) -> bool:
    if not destination.exists():
        return True

    print(
        "\n[WARNING] A file with this name already exists in "
        "data/current_pic/:"
        f"\n{destination.name}"
    )

    answer = input("\nReplace it? [y/N]: ").strip().casefold()
    return answer in {"y", "yes"}


def import_picture_to_current_folder() -> Path | None:
    print("\n=== Import Picture to Current Folder ===\n")

    import_folder = get_import_location()
    selected = _select_picture(import_folder)

    if selected is None:
        return None

    # The selection list already filters to valid images, but validate once more
    # immediately before the copy in case the file changed while the menu was
    # open.
    if not is_picture(selected):
        print(
            "\n[ERROR] The selected picture is no longer a valid "
            "ShopGraph-supported image."
        )
        return None

    CURRENT_PIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        CURRENT_PIC_DIR
        / selected.name
    )

    if not _confirm_replace(destination):
        print("\n[INFO] Picture import cancelled.")
        return None

    try:
        shutil.copy2(
            selected,
            destination,
        )
    except OSError as error:
        raise OSError(
            "Could not copy the selected picture."
            f"\n\nSource:\n{selected}"
            f"\n\nDestination:\n{destination}"
            f"\n\n{error}"
        ) from error

    print(
        "\n[OK] Picture imported:"
        f"\n{selected.name}"
        f"\n\nDestination:\n{destination.resolve()}"
    )

    return destination.resolve()


def display_picture_importer_menu() -> None:
    print("\n=== ShopGraph Picture Importer ===\n")
    print("1. Import Picture")
    print("2. Change Default Import Location")
    print("0. Return to Utilities")


def run_picture_importer_menu() -> None:
    while True:
        display_picture_importer_menu()

        option = input("\nSelect option: ").strip()

        if option == "1":
            try:
                import_picture_to_current_folder()
            except (
                OSError,
                PermissionError,
            ) as error:
                print(f"\n[ERROR] {error}")

        elif option == "2":
            try:
                change_import_location()
            except (
                OSError,
                PermissionError,
            ) as error:
                print(f"\n[ERROR] {error}")

        elif option == "0":
            return

        else:
            print("\n[ERROR] Invalid option.")
