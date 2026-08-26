from utils.codebase_bundler import (
    export_codebase_bundle
)


def run_codebase_export() -> None:

    print(
        "\n=== Export Clean Codebase ===\n"
    )

    output_path = (
        export_codebase_bundle()
    )

    print(
        f"\n[OK] Codebase bundle created:\n"
        f"{output_path}"
    )
