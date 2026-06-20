"""
PDF utility functions using PyMuPDF for reading, rendering, and splitting PDFs.
"""
import pymupdf
import numpy as np
from pathlib import Path
from typing import Optional


def open_pdf(path: str | Path) -> pymupdf.Document:
    """Open a PDF document."""
    return pymupdf.open(str(path))


def get_page_count(path: str | Path) -> int:
    """Get total page count of a PDF."""
    with pymupdf.open(str(path)) as doc:
        return len(doc)


def get_page_text(doc: pymupdf.Document, page_index: int, sort: bool = True) -> str:
    """Extract text from a specific page in natural reading order."""
    page = doc[page_index]
    return page.get_text("text", sort=sort)


def get_page_text_dict(doc: pymupdf.Document, page_index: int) -> dict:
    """
    Extract structured text data (with font info, positions, bboxes) from a page.
    Returns the full 'dict' output from PyMuPDF.
    """
    page = doc[page_index]
    return page.get_text("dict", sort=True)


def render_page_to_image(
    doc: pymupdf.Document,
    page_index: int,
    dpi: int = 150
) -> np.ndarray:
    """
    Render a PDF page to a numpy array (RGB).
    Suitable for OpenCV processing.
    """
    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)

    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

    # Handle alpha channel if present
    if pix.n == 4:
        img = img[:, :, :3]  # Drop alpha

    return img


def render_page_to_png_bytes(
    doc: pymupdf.Document,
    page_index: int,
    dpi: int = 150
) -> bytes:
    """Render a page to PNG bytes (for sending to LLM or frontend)."""
    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    return pix.tobytes("png")


def split_pdf(
    source_path: str | Path,
    output_path: str | Path,
    start_page: int,
    end_page: int
) -> Path:
    """
    Extract pages [start_page, end_page] (inclusive, 0-indexed) from source PDF
    and save as a new PDF at output_path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(str(source_path)) as source_doc:
        new_doc = pymupdf.open()
        new_doc.insert_pdf(source_doc, from_page=start_page, to_page=end_page)
        new_doc.save(str(output_path))
        new_doc.close()

    return output_path


def is_page_scanned(doc: pymupdf.Document, page_index: int) -> bool:
    """
    Detect if a page is scanned (image-only with no/minimal text layer).
    A page is considered scanned if it has very little extractable text
    but contains images.
    """
    page = doc[page_index]
    text = page.get_text("text").strip()
    images = page.get_images()

    # If very little text but has images, it's likely scanned
    if len(text) < 20 and len(images) > 0:
        return True

    # If no text and no images, it might be a blank page
    if len(text) < 5:
        return True

    return False


def get_page_fonts(doc: pymupdf.Document, page_index: int) -> list[dict]:
    """
    Get font information for all text spans on a page.
    Returns list of dicts with font name, size, and character count.
    """
    text_dict = get_page_text_dict(doc, page_index)
    fonts = {}

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # Skip image blocks
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_key = f"{span.get('font', 'unknown')}_{span.get('size', 0):.1f}"
                if font_key not in fonts:
                    fonts[font_key] = {
                        "font": span.get("font", "unknown"),
                        "size": span.get("size", 0),
                        "char_count": 0,
                        "flags": span.get("flags", 0),
                    }
                fonts[font_key]["char_count"] += len(span.get("text", ""))

    return sorted(fonts.values(), key=lambda x: x["char_count"], reverse=True)


def get_page_dimensions(doc: pymupdf.Document, page_index: int) -> tuple[float, float]:
    """Get page width and height in points."""
    page = doc[page_index]
    rect = page.rect
    return rect.width, rect.height
