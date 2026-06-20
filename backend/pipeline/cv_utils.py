"""
OpenCV-based layout analysis utilities.
Computes structural similarity between pages and detects visual features.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def compute_layout_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute structural similarity between two page images using SSIM.
    Returns a value between 0.0 (completely different) and 1.0 (identical).
    
    Uses a lightweight approach: resize to small thumbnails, convert to grayscale,
    then compute SSIM. This is fast enough for per-page comparison.
    """
    try:
        from skimage.metrics import structural_similarity as ssim

        # Resize both to a standard small size for comparison
        target_size = (200, 280)  # Roughly A4 aspect ratio

        gray1 = _to_gray_thumbnail(img1, target_size)
        gray2 = _to_gray_thumbnail(img2, target_size)

        score = ssim(gray1, gray2)
        return float(max(0.0, min(1.0, score)))
    except Exception as e:
        logger.warning(f"SSIM computation failed: {e}")
        return 0.5  # Default to uncertain


def _to_gray_thumbnail(img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Convert image to grayscale and resize to thumbnail."""
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA)


def detect_horizontal_lines(img: np.ndarray, min_length_ratio: float = 0.3) -> int:
    """
    Detect prominent horizontal lines in an image (indicators of table grids,
    section separators, or form boundaries).
    Returns the count of detected lines.
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
        height, width = gray.shape

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines using HoughLinesP
        min_length = int(width * min_length_ratio)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=min_length, maxLineGap=10
        )

        if lines is None:
            return 0

        # Count roughly horizontal lines (within 5 degrees of horizontal)
        horizontal_count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 5 or angle > 175:
                horizontal_count += 1

        return horizontal_count
    except Exception as e:
        logger.warning(f"Horizontal line detection failed: {e}")
        return 0


def detect_header_region_has_logo(img: np.ndarray, header_fraction: float = 0.15) -> bool:
    """
    Detect if the top portion of the page has a logo-like element.
    Uses contour analysis to find dense, non-text graphical elements
    in the header region.
    """
    try:
        height, width = img.shape[:2]
        header_height = int(height * header_fraction)
        header = img[:header_height, :]

        gray = cv2.cvtColor(header, cv2.COLOR_RGB2GRAY) if len(header.shape) == 3 else header

        # Threshold to find dark elements
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for contours that are:
        # - Reasonably sized (not tiny dots, not full-page)
        # - Roughly square or logo-shaped aspect ratio
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            page_area = width * header_height

            # Logo: 1-15% of header area, aspect ratio not too extreme
            if 0.01 * page_area < area < 0.15 * page_area:
                aspect = w / max(h, 1)
                if 0.3 < aspect < 5.0:
                    return True

        return False
    except Exception as e:
        logger.warning(f"Logo detection failed: {e}")
        return False


def compute_whitespace_density(img: np.ndarray) -> float:
    """
    Compute the ratio of white/near-white pixels to total pixels.
    High whitespace density may indicate a cover page, separator, or mostly-empty page.
    Returns value between 0.0 (all dark) and 1.0 (all white).
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

        # Resize for speed
        small = cv2.resize(gray, (200, 280), interpolation=cv2.INTER_AREA)

        # Count near-white pixels (value > 240)
        white_pixels = np.sum(small > 240)
        total_pixels = small.size

        return float(white_pixels / total_pixels)
    except Exception as e:
        logger.warning(f"Whitespace density computation failed: {e}")
        return 0.5
