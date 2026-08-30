
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UTILS_DIR = Path(__file__).resolve().parent
LEGACY_CONFIG_PATH = UTILS_DIR / "config.txt"
CONFIG_DIR = UTILS_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "settings.txt"
DEFAULT_IMPORT_LOCATION = Path("~/Downloads").expanduser()
CONFIG_KEY = "code_update_import_location"

PROTECTED_RELATIVE_PATHS = {
    Path("utils") / "config.txt",
}


def _is_protected_relative_path(relative: Path) -> bool:
    if relative in PROTECTED_RELATIVE_PATHS:
        return True
    parts = relative.parts
    return len(parts) >= 2 and parts[0] == "utils" and parts[1] == "config"

PROJECT_ROOT_MARKERS = {
    "main.py",
    "utils",
    "capabilities",
    "README",
    "data",
    "extractors",
    "receipt",
}


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser().resolve()


def _read_key_value_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            values[key] = value
    return values


def _read_config() -> dict[str, str]:
    # Legacy config is read first so existing installations migrate without
    # losing their saved Code Update Importer location. New settings override
    # legacy values when both files exist.
    values = _read_key_value_file(LEGACY_CONFIG_PATH)
    values.update(_read_key_value_file(CONFIG_PATH))

    if values and not CONFIG_PATH.exists():
        try:
            _write_config(values)
        except OSError:
            # Reading legacy settings must still work even if migration cannot
            # be written at this moment.
            pass

    return values


def _write_config(values: dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ShopGraph utility configuration",
        "# Paths may use ~ and environment variables.",
        "",
    ]
    for key in sorted(values):
        lines.append(f"{key}={values[key]}")
    lines.append("")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".shopgraph_config_",
        suffix=".txt",
        dir=CONFIG_PATH.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text("\n".join(lines), encoding="utf-8")
        os.replace(temporary_path, CONFIG_PATH)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _migrate_legacy_config() -> None:
    if CONFIG_PATH.exists() or not LEGACY_CONFIG_PATH.exists():
        return

    values = _read_key_value_file(LEGACY_CONFIG_PATH)
    if not values:
        return

    try:
        _write_config(values)
    except OSError:
        # Legacy settings remain readable through _read_config(), so migration
        # failure must not prevent ShopGraph from starting.
        return


_migrate_legacy_config()


def _save_import_location(path: Path) -> None:
    values = _read_config()
    try:
        relative = path.relative_to(Path.home())
        display_value = f"~/{relative}"
    except ValueError:
        display_value = str(path)
    values[CONFIG_KEY] = display_value
    _write_config(values)


def _prompt_for_existing_directory(prompt: str, current: Path | None = None) -> Path:
    while True:
        suffix = f" [{current}]" if current is not None else ""
        entered = input(f"{prompt}{suffix}: ").strip()
        if not entered and current is not None:
            candidate = current
        elif entered:
            candidate = _expand_path(entered)
        else:
            print("\n[ERROR] Please enter a folder path.")
            continue

        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
        print(f"\n[ERROR] Folder does not exist or is not accessible:\n{candidate}")


def get_import_location() -> Path:
    values = _read_config()
    configured = _text(values.get(CONFIG_KEY))

    if configured:
        configured_path = _expand_path(configured)
        if configured_path.exists() and configured_path.is_dir():
            return configured_path
        print(
            "\n[WARNING] The configured code-update import folder is unavailable:"
            f"\n{configured_path}"
        )
        replacement = _prompt_for_existing_directory(
            "Enter a new code-update import folder"
        )
        _save_import_location(replacement)
        return replacement

    if DEFAULT_IMPORT_LOCATION.exists() and DEFAULT_IMPORT_LOCATION.is_dir():
        resolved = DEFAULT_IMPORT_LOCATION.resolve()
        _save_import_location(resolved)
        return resolved

    print(
        "\n[INFO] This is the first Code Update Importer run."
        "\nThe default import folder is unavailable:"
        f"\n{DEFAULT_IMPORT_LOCATION}"
    )
    replacement = _prompt_for_existing_directory(
        "Enter the folder containing ShopGraph update ZIPs"
    )
    _save_import_location(replacement)
    return replacement


def change_import_location() -> Path:
    try:
        current = get_import_location()
    except (OSError, PermissionError):
        current = None

    print("\n=== Change Code Update Import Location ===\n")
    print("This is the folder where ShopGraph looks for update ZIP files.")
    selected = _prompt_for_existing_directory("New import folder", current=current)
    _save_import_location(selected)
    print(
        "\n[OK] Code update import location saved:"
        f"\n{selected}"
        f"\n\nConfiguration:\n{CONFIG_PATH}"
    )
    return selected


def _available_zip_files(folder: Path) -> list[Path]:
    try:
        files = [
            path for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() == ".zip"
        ]
    except OSError as error:
        raise OSError(f"Could not read import folder:\n{folder}\n\n{error}") from error

    files.sort(key=lambda path: (path.stat().st_mtime, path.name.casefold()), reverse=True)
    return files


def _select_zip_file(folder: Path) -> Path | None:
    while True:
        zip_files = _available_zip_files(folder)
        print("\n=== Available ShopGraph Update ZIPs ===\n")
        print(f"Import folder:\n{folder}\n")

        if not zip_files:
            print("[INFO] No ZIP files were found in this folder.")
            print("\n1. Choose another folder for this import")
            print("0. Cancel")
            option = input("\nSelect option: ").strip()
            if option == "1":
                folder = _prompt_for_existing_directory("Folder containing the update ZIP")
                continue
            if option == "0":
                return None
            print("\n[ERROR] Invalid option.")
            continue

        for index, path in enumerate(zip_files, start=1):
            print(f"{index}. {path.name}")
        print("\nF. Choose another folder for this import")
        print("0. Cancel")

        option = input("\nSelect update ZIP: ").strip()
        if option.casefold() == "f":
            folder = _prompt_for_existing_directory("Folder containing the update ZIP")
            continue
        if option == "0":
            return None
        try:
            index = int(option)
        except ValueError:
            print("\n[ERROR] Invalid option.")
            continue
        if 1 <= index <= len(zip_files):
            return zip_files[index - 1]
        print("\n[ERROR] Invalid option.")


def _safe_member_parts(name: str) -> tuple[str, ...] | None:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute():
        return None
    parts = tuple(part for part in path.parts if part not in ("", "."))
    if not parts:
        return tuple()
    if any(part == ".." for part in parts):
        return None
    if ":" in parts[0]:
        return None
    return parts


def _payload_root_prefix(file_parts: list[tuple[str, ...]]) -> tuple[str, ...]:
    if not file_parts:
        return tuple()
    first_components = {parts[0] for parts in file_parts if parts}
    if len(first_components) != 1:
        return tuple()
    only = next(iter(first_components))
    if only in PROJECT_ROOT_MARKERS:
        return tuple()
    second_components = {parts[1] for parts in file_parts if len(parts) >= 2}
    if second_components & PROJECT_ROOT_MARKERS:
        return (only,)
    return tuple()


def _build_payload_plan(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, Path]]:
    infos = [info for info in archive.infolist() if not info.is_dir()]
    safe_parts: dict[int, tuple[str, ...]] = {}
    unsafe_names: list[str] = []

    for index, info in enumerate(infos):
        parts = _safe_member_parts(info.filename)
        if parts is None:
            unsafe_names.append(info.filename)
            continue
        if parts and parts[0] == "__MACOSX":
            continue
        safe_parts[index] = parts

    if unsafe_names:
        raise ValueError(
            "Update ZIP contains unsafe paths and will not be imported:\n"
            + "\n".join(f"- {name}" for name in unsafe_names)
        )

    usable_parts = [parts for parts in safe_parts.values() if parts]
    prefix = _payload_root_prefix(usable_parts)
    plan: list[tuple[zipfile.ZipInfo, Path]] = []
    destinations_seen: set[Path] = set()

    for index, info in enumerate(infos):
        parts = safe_parts.get(index)
        if not parts:
            continue
        if prefix and parts[:len(prefix)] == prefix:
            parts = parts[len(prefix):]
        if not parts:
            continue
        relative = Path(*parts)
        if _is_protected_relative_path(relative):
            continue
        if relative.name in {".DS_Store", "Thumbs.db"}:
            continue
        if relative in destinations_seen:
            raise ValueError(f"Update ZIP contains duplicate destination paths:\n{relative}")
        destinations_seen.add(relative)
        plan.append((info, relative))

    if not plan:
        raise ValueError("No importable files were found in the selected ZIP.")

    top_level_names = {relative.parts[0] for _, relative in plan}
    if not (top_level_names & PROJECT_ROOT_MARKERS):
        raise ValueError(
            "The selected ZIP does not look like a ShopGraph update overlay. "
            "Expected project-relative content such as utils/, README/, capabilities/, data/, or main.py."
        )
    return plan


def _extract_to_staging(archive: zipfile.ZipFile, plan, staging_root: Path) -> None:
    for info, relative in plan:
        destination = staging_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info, "r") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def _display_plan(plan) -> None:
    print("\nFiles to add / replace:\n")
    for _, relative in plan:
        action = "REPLACE" if (PROJECT_ROOT / relative).exists() else "ADD"
        print(f"[{action}] {relative}")
    print(f"\nTotal files: {len(plan)}")


def _confirm_import(zip_path: Path) -> bool:
    print(
        "\nThis update will overlay files onto:"
        f"\n{PROJECT_ROOT}"
        f"\n\nSelected ZIP:\n{zip_path}"
    )
    print(
        "\nFiles not present in the ZIP will NOT be deleted."
        "\nLocal utils/config.txt and the utils/config/ runtime settings directory are protected and will NOT be replaced."
    )
    while True:
        answer = input("\nApply this update? [y/N]: ").strip().casefold()
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("\n[ERROR] Enter y or n.")


def _transactional_overlay(staging_root: Path, plan) -> dict:
    changed_paths = [relative for _, relative in plan]
    existed_before: set[Path] = set()

    with tempfile.TemporaryDirectory(prefix="shopgraph_update_rollback_") as rollback_name:
        rollback_root = Path(rollback_name)
        created_directories: set[Path] = set()

        for relative in changed_paths:
            destination = PROJECT_ROOT / relative
            if destination.exists():
                if destination.is_dir():
                    raise ValueError(f"Update would replace a directory with a file:\n{relative}")
                backup = rollback_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                existed_before.add(relative)

        applied: list[Path] = []
        try:
            for relative in changed_paths:
                source = staging_root / relative
                destination = PROJECT_ROOT / relative
                parent = destination.parent
                cursor = parent
                missing = []
                while cursor != PROJECT_ROOT and not cursor.exists():
                    missing.append(cursor)
                    cursor = cursor.parent
                parent.mkdir(parents=True, exist_ok=True)
                created_directories.update(missing)

                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{destination.name}.shopgraph_update_",
                    dir=parent,
                )
                os.close(descriptor)
                temporary_path = Path(temporary_name)
                try:
                    shutil.copy2(source, temporary_path)
                    os.replace(temporary_path, destination)
                finally:
                    if temporary_path.exists():
                        temporary_path.unlink()
                applied.append(relative)

        except Exception:
            for relative in reversed(applied):
                destination = PROJECT_ROOT / relative
                if relative in existed_before:
                    backup = rollback_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, destination)
                elif destination.exists() and destination.is_file():
                    destination.unlink()
            for directory in sorted(created_directories, key=lambda p: len(p.parts), reverse=True):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            raise

    return {
        "file_count": len(changed_paths),
        "replaced_count": sum(1 for relative in changed_paths if relative in existed_before),
        "added_count": sum(1 for relative in changed_paths if relative not in existed_before),
    }


def import_update_zip(zip_path: Path) -> dict:
    zip_path = Path(zip_path).expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        raise FileNotFoundError(f"Update ZIP was not found:\n{zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise ValueError(f"Selected file is not a ZIP archive:\n{zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ValueError(f"ZIP integrity check failed at:\n{bad_member}")
            plan = _build_payload_plan(archive)
            _display_plan(plan)
            if not _confirm_import(zip_path):
                return {"success": False, "cancelled": True, "zip_path": zip_path}

            with tempfile.TemporaryDirectory(prefix="shopgraph_update_staging_") as staging_name:
                staging_root = Path(staging_name)
                _extract_to_staging(archive, plan, staging_root)
                result = _transactional_overlay(staging_root, plan)
    except zipfile.BadZipFile as error:
        raise ValueError(f"Selected file is not a valid ZIP archive:\n{zip_path}") from error

    return {"success": True, "cancelled": False, "zip_path": zip_path, **result}


def run_import_code_update() -> None:
    print("\n=== Import ShopGraph Code Update ZIP ===\n")
    print(f"Detected ShopGraph project root:\n{PROJECT_ROOT}")
    try:
        import_folder = get_import_location()
        zip_path = _select_zip_file(import_folder)
        if zip_path is None:
            print("\n[INFO] Code update import cancelled.")
            return
        result = import_update_zip(zip_path)
    except (FileNotFoundError, PermissionError, ValueError, OSError) as error:
        print(f"\n[ERROR] {error}")
        return

    if result.get("cancelled"):
        print("\n[INFO] Code update import cancelled.")
        return

    print("\n[OK] ShopGraph code update imported successfully.")
    print(f"Files added: {result['added_count']}")
    print(f"Files replaced: {result['replaced_count']}")
    print(f"Total files applied: {result['file_count']}")
    print(f"Update ZIP:\n{result['zip_path']}")
    print(
        "\nRestart ShopGraph before using newly imported code. "
        "This is especially important when the update replaced a Python module already loaded in this process."
    )


def display_code_update_importer_menu() -> None:
    print("\n=== ShopGraph Code Update Importer ===\n")
    print("1. Import Update ZIP")
    print("2. Change Default Import Location")
    print("0. Return to Utilities")


def run_code_update_importer_menu() -> None:
    while True:
        display_code_update_importer_menu()
        option = input("\nSelect option: ").strip()
        if option == "1":
            run_import_code_update()
        elif option == "2":
            try:
                change_import_location()
            except (PermissionError, OSError) as error:
                print(f"\n[ERROR] {error}")
        elif option == "0":
            return
        else:
            print("\n[ERROR] Invalid option.")


if __name__ == "__main__":
    run_code_update_importer_menu()
