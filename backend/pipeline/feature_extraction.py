"""
Page-level feature extraction for boundary detection.

For each page in the PDF, computes a feature vector containing:
- Text-layer features (titles, form identifiers, page numbers, fonts)
- Visual/layout features (whitespace density, layout similarity, logo detection)
- OCR fallback for scanned pages

These features are consumed by the boundary detection module to determine
where one document ends and another begins.
"""
import re
import logging
from typing import Optional

import numpy as np

from models import PageFeatures
from pipeline.pdf_utils import (
    get_page_text,
    get_page_text_dict,
    get_page_fonts,
    render_page_to_image,
    is_page_scanned,
    get_page_dimensions,
)
from pipeline.cv_utils import (
    compute_layout_similarity,
    detect_header_region_has_logo,
    compute_whitespace_density,
)
from pipeline.ocr import ocr_page
from config import RENDER_DPI

logger = logging.getLogger(__name__)

# --- Regex patterns for text feature extraction ---

# Page number patterns: "Page 1 of 5", "Page 1", "- 1 -", "1 of 5", "pg. 3"
PAGE_NUM_PATTERNS = [
    re.compile(r"[Pp]age\s+(\d+)\s+of\s+(\d+)"),
    re.compile(r"[Pp]age\s+(\d+)"),
    re.compile(r"[Pp]g\.?\s*(\d+)\s+of\s+(\d+)"),
    re.compile(r"[Pp]g\.?\s*(\d+)"),
    re.compile(r"[-–—]\s*(\d+)\s*[-–—]"),
    re.compile(r"(\d+)\s+of\s+(\d+)"),
]

# Form/document identifiers
FORM_ID_PATTERNS = [
    re.compile(r"\b(Form\s+\w[\w-]*)", re.IGNORECASE),
    re.compile(r"\b(Schedule\s+[A-Z][\w-]*)", re.IGNORECASE),
    re.compile(r"\b(Statement\s+(?:of|Period|Date))", re.IGNORECASE),
    re.compile(r"\b(Invoice\s*(?:#|No|Number)?)", re.IGNORECASE),
    re.compile(r"\b(Certificate\s+of\b)", re.IGNORECASE),
    re.compile(r"\b(Application\s+for\b)", re.IGNORECASE),
    re.compile(r"\b(Declaration\s+of\b)", re.IGNORECASE),
    re.compile(r"\b(Notice\s+of\b)", re.IGNORECASE),
    re.compile(r"\b(Agreement|Contract|Deed|Affidavit|Disclosure)\b", re.IGNORECASE),
]

# Date patterns in headers
DATE_HEADER_PATTERNS = [
    re.compile(
        r"(?:Statement|Report|Period|Date|Effective|Issued)[:\s]*"
        r"(\w+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+\d{1,2},?\s+\d{4}",
        re.IGNORECASE,
    ),
    re.compile(r"(?:Tax\s+Year|Fiscal\s+Year|Year)[:\s]*(\d{4})", re.IGNORECASE),
]


def extract_page_features(
    doc,
    page_index: int,
    prev_page_image: Optional[np.ndarray] = None,
    prev_page_fonts: Optional[list[dict]] = None,
) -> tuple[PageFeatures, np.ndarray, list[dict]]:
    """
    Extract comprehensive features from a single PDF page.

    Args:
        doc: PyMuPDF document object
        page_index: 0-indexed page number
        prev_page_image: Rendered image of previous page (for layout similarity)
        prev_page_fonts: Font list from previous page (for font change detection)

    Returns:
        Tuple of (PageFeatures, current_page_image, current_page_fonts)
    """
    features = PageFeatures(page_index=page_index)

    # Check if page is scanned (image-only)
    scanned = is_page_scanned(doc, page_index)
    features.is_scanned = scanned

    # --- Text extraction ---
    if scanned:
        raw_text = ocr_page(doc, page_index)
    else:
        raw_text = get_page_text(doc, page_index)

    features.raw_text = raw_text
    features.word_count = len(raw_text.split())

    # --- Page dimensions and text density ---
    width, height = get_page_dimensions(doc, page_index)
    page_area = width * height
    features.text_density = len(raw_text) / max(page_area, 1.0) * 1000  # chars per 1000 sq pts

    # --- Title detection (large/bold text in top 20% of page) ---
    _extract_title_features(doc, page_index, features, scanned)

    # --- Form identifier detection ---
    _extract_form_identifier(raw_text, features)

    # --- Page number detection ---
    _extract_page_number(raw_text, features)

    # --- Date header detection ---
    _extract_date_header(raw_text, features)

    # --- Font analysis ---
    current_fonts = []
    if not scanned:
        current_fonts = get_page_fonts(doc, page_index)
        if current_fonts:
            features.dominant_font = current_fonts[0]["font"]
            features.dominant_font_size = current_fonts[0]["size"]

        # Font change score vs previous page
        if prev_page_fonts:
            features.font_change_score = _compute_font_change(prev_page_fonts, current_fonts)

    # --- Visual features (render page to image) ---
    current_image = render_page_to_image(doc, page_index, dpi=RENDER_DPI)

    # Layout similarity to previous page
    if prev_page_image is not None:
        features.layout_similarity_to_prev = compute_layout_similarity(
            prev_page_image, current_image
        )
    else:
        features.layout_similarity_to_prev = 0.0  # First page has no previous

    # Whitespace density
    features.whitespace_density = compute_whitespace_density(current_image)

    # Letterhead/logo detection
    features.has_letterhead = detect_header_region_has_logo(current_image)

    return features, current_image, current_fonts


def extract_all_page_features(
    doc,
    progress_callback=None,
) -> list[PageFeatures]:
    """
    Extract features for all pages in the document.

    Args:
        doc: PyMuPDF document object
        progress_callback: Optional callback(page_index, total_pages) for progress

    Returns:
        List of PageFeatures, one per page
    """
    total_pages = len(doc)
    all_features = []
    prev_image = None
    prev_fonts = None

    for i in range(total_pages):
        if progress_callback:
            progress_callback(i, total_pages)

        features, current_image, current_fonts = extract_page_features(
            doc, i, prev_image, prev_fonts
        )
        all_features.append(features)
        prev_image = current_image
        prev_fonts = current_fonts

        logger.debug(
            f"Page {i}: title={features.has_title_text}, form={features.form_identifier}, "
            f"page_num={features.page_number_value}, similarity={features.layout_similarity_to_prev:.2f}, "
            f"scanned={features.is_scanned}"
        )

    return all_features


# --- Private helper functions ---

def _extract_title_features(doc, page_index: int, features: PageFeatures, is_scanned: bool):
    """Detect title text in the top portion of the page."""
    if is_scanned:
        # For scanned pages, check if first line looks like a title (all caps, short)
        lines = features.raw_text.split("\n")
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) > 3 and (line.isupper() or line.istitle()):
                features.has_title_text = True
                features.title_text = line
                break
        return

    text_dict = get_page_text_dict(doc, page_index)
    _, page_height = get_page_dimensions(doc, page_index)
    top_region = page_height * 0.25  # Top 25% of page

    largest_font_size = 0
    title_candidate = ""

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = span.get("bbox", (0, 0, 0, 0))
                # Only consider text in top region
                if bbox[1] > top_region:
                    continue

                font_size = span.get("size", 0)
                text = span.get("text", "").strip()
                flags = span.get("flags", 0)
                is_bold = bool(flags & 2 ** 4)  # Bold flag

                if font_size > largest_font_size and len(text) > 2:
                    # Prefer bold, larger text
                    effective_size = font_size * (1.3 if is_bold else 1.0)
                    if effective_size > largest_font_size:
                        largest_font_size = effective_size
                        title_candidate = text

    # Consider it a title if font is significantly larger than body text
    if title_candidate and largest_font_size > 12:
        features.has_title_text = True
        features.title_text = title_candidate


def _extract_form_identifier(text: str, features: PageFeatures):
    """Detect form/document type identifiers in text."""
    # Only search the first ~500 characters (header area)
    header_text = text[:500]
    for pattern in FORM_ID_PATTERNS:
        match = pattern.search(header_text)
        if match:
            features.has_form_identifier = True
            features.form_identifier = match.group(0).strip()
            return


def _extract_page_number(text: str, features: PageFeatures):
    """Detect page numbering patterns."""
    # Search the last 200 characters (footer) and first 200 characters (header)
    search_areas = [text[-200:], text[:200]]

    for area in search_areas:
        for pattern in PAGE_NUM_PATTERNS:
            match = pattern.search(area)
            if match:
                features.has_page_number = True
                try:
                    features.page_number_value = int(match.group(1))
                    if match.lastindex and match.lastindex >= 2:
                        features.page_number_total = int(match.group(2))
                except (ValueError, IndexError):
                    pass
                return


def _extract_date_header(text: str, features: PageFeatures):
    """Detect date/period information in header area."""
    header_text = text[:600]
    for pattern in DATE_HEADER_PATTERNS:
        match = pattern.search(header_text)
        if match:
            features.has_date_header = True
            features.date_header_text = match.group(0).strip()
            return


def _compute_font_change(prev_fonts: list[dict], curr_fonts: list[dict]) -> float:
    """
    Compute a score indicating how much the font profile changed between pages.
    0.0 = identical fonts, 1.0 = completely different.
    """
    if not prev_fonts or not curr_fonts:
        return 0.5

    prev_dominant = prev_fonts[0]
    curr_dominant = curr_fonts[0]

    score = 0.0

    # Different font family
    if prev_dominant["font"] != curr_dominant["font"]:
        score += 0.5

    # Different font size (more than 2pt difference)
    size_diff = abs(prev_dominant["size"] - curr_dominant["size"])
    if size_diff > 2:
        score += min(0.5, size_diff / 10.0)

    return min(1.0, score)
