"""
table_extractor.py
--------------------
Extracts structured tables from a page range of a PDF.

Strategy (two-pass):
  1. pdfplumber  — fast, text-layer aware; works great on born-digital PDFs.
  2. camelot-py  — lattice mode (ghostscript-backed); used as a fallback ONLY
     when pdfplumber finds no tables in a given range. camelot excels at
     image-rendered tables with visible grid lines.

This means we never pay the camelot overhead when pdfplumber already succeeds,
which keeps the common case cheap.
"""
from __future__ import annotations

import logging

import pdfplumber

logger = logging.getLogger(__name__)

TABULAR_DOC_TYPES = {"Bank_Statement", "Pay_Stub"}


# ---------------------------------------------------------------------------
# pdfplumber pass
# ---------------------------------------------------------------------------

def _extract_via_pdfplumber(pdf_path: str, start_page: int, end_page: int) -> list[list[str]]:
    """Return a stitched table using pdfplumber. Returns [] if nothing found."""
    rows: list[list[str]] = []
    header: list[str] | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_no in range(start_page, end_page + 1):
            page = pdf.pages[page_no - 1]
            for table in page.extract_tables():
                if not table:
                    continue
                this_header, body = table[0], table[1:]
                if header is None:
                    header = this_header
                    rows.append(header)
                if this_header == header:
                    rows.extend(body)
                else:
                    # Header didn't repeat verbatim; treat entire table as data.
                    rows.extend(table)
    return rows


# ---------------------------------------------------------------------------
# camelot fallback pass
# ---------------------------------------------------------------------------

def _extract_via_camelot(pdf_path: str, start_page: int, end_page: int) -> list[list[str]]:
    """
    Fallback: use camelot-py (lattice mode) when pdfplumber finds nothing.
    Returns [] if camelot is not installed or finds no tables.
    """
    try:
        import camelot  # type: ignore
    except ImportError:
        logger.debug("camelot-py not installed; skipping camelot fallback.")
        return []

    page_range = f"{start_page}-{end_page}"
    rows: list[list[str]] = []
    header: list[str] | None = None

    try:
        # Try lattice first (grid lines), then stream (whitespace-based)
        for flavor in ("lattice", "stream"):
            tables = camelot.read_pdf(pdf_path, pages=page_range, flavor=flavor)
            if tables and tables.n > 0:
                for t in tables:
                    df = t.df
                    table_rows = df.values.tolist()
                    if not table_rows:
                        continue
                    this_header = [str(c) for c in table_rows[0]]
                    body = [[str(c) for c in r] for r in table_rows[1:]]
                    if header is None:
                        header = this_header
                        rows.append(header)
                    if this_header == header:
                        rows.extend(body)
                    else:
                        rows.extend([[str(c) for c in r] for r in table_rows])
                if rows:
                    break  # found something, no need to try stream mode
    except Exception as exc:
        logger.warning("camelot extraction failed for pages %s: %s", page_range, exc)

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_tables_for_range(pdf_path: str, start_page: int, end_page: int) -> list[list[str]]:
    """
    Return a single stitched table (list of rows) for the given 1-indexed page range.

    Tries pdfplumber first; falls back to camelot only if pdfplumber finds nothing.
    """
    rows = _extract_via_pdfplumber(pdf_path, start_page, end_page)
    if not rows:
        logger.debug(
            "pdfplumber found no tables in pages %d-%d; trying camelot fallback.",
            start_page,
            end_page,
        )
        rows = _extract_via_camelot(pdf_path, start_page, end_page)
    return rows
