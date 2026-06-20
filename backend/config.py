"""
Configuration for the Loan File Structuring System.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Pipeline Configuration ---

# Boundary detection
BOUNDARY_THRESHOLD = 0.50  # Score above this = new document start
BOUNDARY_VERIFY_LOW = 0.35  # Only verify boundaries with confidence in this range
BOUNDARY_VERIFY_HIGH = 0.75

# OCR
TESSERACT_AVAILABLE = True  # Set False if tesseract is not installed
try:
    import pytesseract
    pytesseract.get_tesseract_version()
except Exception:
    TESSERACT_AVAILABLE = False

# Page rendering DPI for OpenCV analysis
RENDER_DPI = 150

# --- Table Extraction ---
TABLE_HEADER_SIMILARITY_THRESHOLD = 0.8  # For multi-page table merging

# --- LLM Verification ---
ENABLE_LLM_VERIFICATION = os.environ.get("ENABLE_LLM_VERIFICATION", "false").lower() == "true"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Cheapest available tier

# --- Cost Tracking ---
# Gemini 3.1 Flash Lite pricing (per 1M tokens)
INPUT_TOKEN_COST_PER_M = 0.25   # $0.25 per 1M input tokens
OUTPUT_TOKEN_COST_PER_M = 1.50  # $1.50 per 1M output tokens

# --- Server ---
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]
