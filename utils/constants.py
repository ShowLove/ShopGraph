from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"

CURRENT_PIC_DIR = DATA_DIR / "current_pic"
CROPPED_DIR = DATA_DIR / "cropped"
PERSPECTIVE_DIR = DATA_DIR / "perspective_corrected"
PREPROCESSED_DIR = DATA_DIR / "preprocessed"
RAW_OCR_DIR = DATA_DIR / "raw_ocr"

EXPORT_DIR = DATA_DIR / "exports"

CODEBASE_OUTPUT_FILE = (
    EXPORT_DIR
    / "codebase"
    / "shopgraph_codebase.txt"
)
