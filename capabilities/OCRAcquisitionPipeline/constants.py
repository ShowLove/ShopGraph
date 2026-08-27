from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

CURRENT_PIC_DIR = DATA_DIR / "current_pic"
CROPPED_DIR = DATA_DIR / "cropped"
PERSPECTIVE_DIR = DATA_DIR / "perspective_corrected"
ENLARGED_DIR = DATA_DIR / "enlarged"
OCR_VARIANTS_DIR = DATA_DIR / "ocr_variants"
OCR_CANDIDATES_DIR = DATA_DIR / "ocr_candidates"
RAW_OCR_DIR = DATA_DIR / "raw_ocr"
REFINED_JSON_DIR = DATA_DIR / "refined_json"

EXPORT_DIR = DATA_DIR / "exports"

CODEBASE_OUTPUT_FILE = (
    EXPORT_DIR
    / "codebase"
    / "shopgraph_codebase.txt"
)
