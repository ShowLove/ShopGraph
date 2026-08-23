from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"

EXPORT_DIR = DATA_DIR / "exports"

CODEBASE_OUTPUT_FILE = (
    EXPORT_DIR
    / "codebase"
    / "shopgraph_codebase.txt"
)
