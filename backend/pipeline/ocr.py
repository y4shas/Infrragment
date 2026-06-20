"""
OCR fallback for scanned/image-only PDF pages.
Uses pytesseract when available, falls back to PyMuPDF's built-in OCR.
"""
import logging
from typing import Optional

import numpy as np

from config import TESSERACT_AVAILABLE

logger = logging.getLogger(__name__)


def ocr_image(image: np.ndarray) -> str:
    """
    Run OCR on a numpy array image (RGB).
    Uses pytesseract if available, otherwise returns empty string.
    """
    if not TESSERACT_AVAILABLE:
        logger.warning("Tesseract not available — skipping OCR for scanned page")
        return ""

    try:
        import pytesseract
        from PIL import Image

        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(image)

        # Run OCR with English language
        text = pytesseract.image_to_string(pil_image, lang="eng")
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def ocr_page(doc, page_index: int, dpi: int = 300) -> str:
    """
    Run OCR on a specific PDF page.
    Renders the page at specified DPI, then runs OCR.
    """
    from pipeline.pdf_utils import render_page_to_image

    image = render_page_to_image(doc, page_index, dpi=dpi)
    return ocr_image(image)


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Preprocess an image for better OCR accuracy.
    Applies grayscale conversion, thresholding, and noise removal.
    """
    import cv2

    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    # Apply adaptive thresholding for better contrast
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, h=10)

    return denoised
