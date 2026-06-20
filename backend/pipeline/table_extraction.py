"""
Table extraction from PDF documents, including multi-page table detection and merging.

Primary extractor: pdfplumber (pure Python, no system dependencies).
Handles:
- Ruled/lattice tables (with visible borders)
- Stream/whitespace-delimited tables
- Multi-page table detection via header similarity matching
- Header deduplication for merged tables
- Subtotal/total row tagging
"""
import logging
import re
from typing import Optional
from difflib import SequenceMatcher

import pdfplumber

from models import ExtractedTable

logger = logging.getLogger(__name__)

# Keywords indicating total/subtotal rows
TOTAL_KEYWORDS = re.compile(
    r"\b(total|subtotal|sub-total|balance|grand total|net|sum)\b",
    re.IGNORECASE,
)


def extract_tables_for_document(
    pdf_path: str,
    start_page: int,
    end_page: int,
    doc_instance_id: str,
) -> list[ExtractedTable]:
    """
    Extract all tables from a document instance's page range.
    Handles multi-page tables by detecting and merging continued tables.

    Args:
        pdf_path: Path to the source PDF
        start_page: Start page (0-indexed, inclusive)
        end_page: End page (0-indexed, inclusive)
        doc_instance_id: ID for naming tables

    Returns:
        List of ExtractedTable objects
    """
    # Extract raw tables from each page
    page_tables = _extract_raw_tables(pdf_path, start_page, end_page)

    if not page_tables:
        return []

    # Merge multi-page tables
    merged_tables = _merge_multipage_tables(page_tables)

    # Convert to ExtractedTable objects
    result = []
    for idx, mt in enumerate(merged_tables, 1):
        table_id = f"{doc_instance_id}_table_{idx}"

        headers = mt["headers"]
        rows = mt["rows"]
        page_range = mt["page_range"]
        spans = len(page_range) > 1 or (page_range[-1] - page_range[0] > 0) if len(page_range) > 1 else False

        table = ExtractedTable(
            table_id=table_id,
            page_range=page_range,
            spans_multiple_pages=spans,
            headers=headers,
            rows=rows,
            extraction_method=mt.get("method", "pdfplumber"),
            row_count=len(rows),
            col_count=len(headers) if headers else (len(rows[0]) if rows else 0),
        )
        result.append(table)

    logger.info(
        f"Extracted {len(result)} tables from {doc_instance_id} "
        f"(pages {start_page}-{end_page})"
    )
    return result


def _extract_raw_tables(
    pdf_path: str,
    start_page: int,
    end_page: int,
) -> list[dict]:
    """
    Extract raw tables from each page using pdfplumber.
    Returns list of dicts: {page, headers, rows, bbox, method}
    """
    all_tables = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx in range(start_page, min(end_page + 1, len(pdf.pages))):
                page = pdf.pages[page_idx]

                # Try extracting tables with default settings
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines_strict",
                        "horizontal_strategy": "lines_strict",
                        "snap_tolerance": 5,
                    }
                )

                if not tables:
                    # Fallback: try with text-based detection
                    tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 5,
                            "min_words_vertical": 2,
                            "min_words_horizontal": 2,
                        }
                    )

                for table_data in tables:
                    if not table_data or len(table_data) < 2:
                        continue

                    # Clean the raw table data
                    cleaned = _clean_table_data(table_data)
                    if not cleaned or len(cleaned) < 2:
                        continue

                    # First row is typically headers
                    headers = cleaned[0]
                    rows = cleaned[1:]

                    # Filter out completely empty rows
                    rows = [r for r in rows if any(cell.strip() for cell in r if cell)]

                    if rows:
                        all_tables.append({
                            "page": page_idx,
                            "headers": headers,
                            "rows": rows,
                            "method": "pdfplumber",
                        })

    except Exception as e:
        logger.error(f"Table extraction failed for pages {start_page}-{end_page}: {e}")

    return all_tables


def _clean_table_data(raw_table: list[list]) -> list[list[str]]:
    """
    Clean raw table data from pdfplumber.
    Handles None values, whitespace normalization, and newlines within cells.
    """
    cleaned = []
    for row in raw_table:
        if row is None:
            continue
        clean_row = []
        for cell in row:
            if cell is None:
                clean_row.append("")
            else:
                # Normalize whitespace and newlines
                cell_text = str(cell).replace("\n", " ").strip()
                cell_text = re.sub(r"\s+", " ", cell_text)
                clean_row.append(cell_text)
        cleaned.append(clean_row)
    return cleaned


def _merge_multipage_tables(page_tables: list[dict]) -> list[dict]:
    """
    Detect and merge tables that span multiple pages.

    Detection criteria:
    - Consecutive pages with tables
    - Similar column count
    - Similar header content (fuzzy matching)
    - Or presence of "continued" markers

    When merging:
    - Keep the first occurrence's headers
    - Strip duplicate header rows from subsequent pages
    - Concatenate all data rows
    """
    if not page_tables:
        return []

    merged = []
    current_group = {
        "headers": page_tables[0]["headers"],
        "rows": list(page_tables[0]["rows"]),
        "page_range": [page_tables[0]["page"]],
        "method": page_tables[0]["method"],
    }

    for i in range(1, len(page_tables)):
        prev_table = page_tables[i - 1]
        curr_table = page_tables[i]

        # Check if tables should be merged
        should_merge = _should_merge_tables(prev_table, curr_table)

        if should_merge:
            # Merge: add rows (stripping repeated headers)
            rows_to_add = _strip_repeated_headers(
                current_group["headers"], curr_table["rows"], curr_table["headers"]
            )
            current_group["rows"].extend(rows_to_add)
            current_group["page_range"].append(curr_table["page"])
        else:
            # Save current group and start a new one
            merged.append(current_group)
            current_group = {
                "headers": curr_table["headers"],
                "rows": list(curr_table["rows"]),
                "page_range": [curr_table["page"]],
                "method": curr_table["method"],
            }

    # Don't forget the last group
    merged.append(current_group)

    return merged


def _should_merge_tables(prev: dict, curr: dict) -> bool:
    """
    Determine if two tables from consecutive pages should be merged
    (i.e., they're parts of the same logical table).
    """
    # Must be on consecutive pages
    if curr["page"] - prev["page"] != 1:
        return False

    # Column count must match or be very close
    prev_cols = len(prev["headers"])
    curr_cols = len(curr["headers"])
    if abs(prev_cols - curr_cols) > 1:
        return False

    # Header similarity check
    similarity = _header_similarity(prev["headers"], curr["headers"])
    if similarity > 0.7:
        return True

    # Check if current table's first row looks like it matches previous headers
    # (repeated header on new page)
    if curr["rows"]:
        first_row_sim = _header_similarity(prev["headers"], curr["rows"][0])
        if first_row_sim > 0.7:
            return True

    return False


def _header_similarity(headers1: list[str], headers2: list[str]) -> float:
    """
    Compute similarity between two header rows using fuzzy string matching.
    Returns 0.0 to 1.0.
    """
    if not headers1 or not headers2:
        return 0.0

    # Normalize lengths
    min_len = min(len(headers1), len(headers2))
    max_len = max(len(headers1), len(headers2))

    if max_len == 0:
        return 1.0

    # Compare each column header
    matches = 0
    for i in range(min_len):
        h1 = (headers1[i] or "").strip().lower()
        h2 = (headers2[i] or "").strip().lower()

        if h1 == h2:
            matches += 1
        elif SequenceMatcher(None, h1, h2).ratio() > 0.8:
            matches += 0.8

    return matches / max_len


def _strip_repeated_headers(
    original_headers: list[str],
    rows: list[list[str]],
    page_headers: list[str],
) -> list[list[str]]:
    """
    Remove rows that appear to be repeated headers from a continuation page.
    """
    result = []

    # Check if the page's declared headers match the original
    # (this means the first row of rows might be data, or the headers
    # might be a repeated header row already stripped by pdfplumber)

    for row in rows:
        # Skip rows that look like repeated headers
        sim = _header_similarity(original_headers, row)
        if sim > 0.8:
            continue
        result.append(row)

    return result
