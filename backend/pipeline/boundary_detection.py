"""
Document boundary detection using weighted heuristic scoring.

Takes the per-page feature vectors from feature_extraction and produces
boundary decisions — identifying which page transitions represent the start
of a new document within the larger PDF.

Design: deterministic-first approach. No ML models, no LLM calls.
The verifier module (verifier.py) can optionally validate these decisions.
"""
import logging
from typing import Optional

from models import PageFeatures, BoundaryDecision
from config import BOUNDARY_THRESHOLD

logger = logging.getLogger(__name__)


def detect_boundaries(
    page_features: list[PageFeatures],
    threshold: float = BOUNDARY_THRESHOLD,
) -> list[BoundaryDecision]:
    """
    Detect document boundaries by scoring each page transition.

    Args:
        page_features: List of PageFeatures (one per page, in order)
        threshold: Score above this value marks a boundary

    Returns:
        List of BoundaryDecision objects. The first page is always a boundary.
    """
    if not page_features:
        return []

    decisions = []

    # First page is always a boundary
    decisions.append(BoundaryDecision(
        page_index=0,
        score=1.0,
        is_boundary=True,
        reasons=["First page of document"],
    ))

    for i in range(1, len(page_features)):
        prev = page_features[i - 1]
        curr = page_features[i]

        score, reasons = _compute_boundary_score(prev, curr)

        is_boundary = score >= threshold

        decisions.append(BoundaryDecision(
            page_index=i,
            score=score,
            is_boundary=is_boundary,
            reasons=reasons,
        ))

        if is_boundary:
            logger.info(
                f"Boundary detected at page {i} (score={score:.2f}): {', '.join(reasons)}"
            )

    return decisions


def _compute_boundary_score(
    prev: PageFeatures,
    curr: PageFeatures,
) -> tuple[float, list[str]]:
    """
    Compute a boundary score for the transition from prev page to curr page.

    Returns (score, list_of_reasons). Score is 0.0 to 1.0.

    Weight allocation:
    - Page number reset to 1:           0.35 (strong signal)
    - Different form/document identifier: 0.30 (strong signal)
    - Layout dissimilarity:             0.12 (medium signal)
    - Font profile change:              0.08 (medium signal)
    - Letterhead/logo present:          0.08 (medium signal)
    - Title text present:               0.07 (weak-medium signal)
    - Whitespace density spike:         0.05 (weak signal)
    - "Page X of Y" final page:         0.15 (bonus: prev was last page of its doc)
    """
    score = 0.0
    reasons = []

    # --- Strong signals ---

    # Page number reset to 1 (strongest single signal)
    if curr.has_page_number and curr.page_number_value == 1:
        # Make sure the previous page wasn't also page 1 (single-page docs)
        if not (prev.has_page_number and prev.page_number_value == 1):
            score += 0.35
            reasons.append("Page number reset to 1")

    # Previous page was "Page X of X" (last page indicator)
    if (prev.has_page_number and prev.page_number_value is not None
            and prev.page_number_total is not None
            and prev.page_number_value == prev.page_number_total):
        score += 0.15
        reasons.append(f"Previous page was final page ({prev.page_number_value} of {prev.page_number_total})")

    # Different form/document identifier
    if curr.has_form_identifier:
        if not prev.has_form_identifier or prev.form_identifier != curr.form_identifier:
            score += 0.30
            reasons.append(f"New form identifier: {curr.form_identifier}")
        elif prev.form_identifier == curr.form_identifier:
            # Same form type — might still be a new instance, but this signal alone
            # isn't enough. Instance resolution will handle this.
            pass

    # --- Medium signals ---

    # Layout dissimilarity (low SSIM = different layout)
    if curr.layout_similarity_to_prev < 0.45:
        contribution = 0.12 * (1.0 - curr.layout_similarity_to_prev)
        score += contribution
        reasons.append(f"Layout change (similarity={curr.layout_similarity_to_prev:.2f})")

    # Font profile change
    if curr.font_change_score > 0.3:
        contribution = min(0.08, 0.08 * curr.font_change_score)
        score += contribution
        reasons.append(f"Font change (score={curr.font_change_score:.2f})")

    # Letterhead/logo present on current page
    if curr.has_letterhead:
        score += 0.08
        reasons.append("Letterhead/logo detected")

    # Title text present on current page
    if curr.has_title_text:
        # Only count if previous page didn't have a title (avoid consecutive title pages)
        if not prev.has_title_text or prev.title_text != curr.title_text:
            score += 0.07
            reasons.append(f"Title text: {curr.title_text[:50]}")

    # --- Weak signals ---

    # Whitespace density spike (cover page or separator)
    ws_diff = curr.whitespace_density - prev.whitespace_density
    if ws_diff > 0.2 and curr.whitespace_density > 0.85:
        score += 0.05
        reasons.append("High whitespace density (possible separator/cover page)")

    # Text density drop (significant reduction may indicate new doc type)
    if prev.text_density > 0 and curr.text_density > 0:
        density_ratio = curr.text_density / prev.text_density
        if density_ratio < 0.3 or density_ratio > 3.0:
            score += 0.03
            reasons.append("Significant text density change")

    # Date header change
    if curr.has_date_header and prev.has_date_header:
        if curr.date_header_text != prev.date_header_text:
            score += 0.04
            reasons.append(f"Date header changed: {curr.date_header_text[:40]}")

    return min(score, 1.0), reasons


def get_document_segments(
    decisions: list[BoundaryDecision],
    total_pages: int,
) -> list[tuple[int, int, float]]:
    """
    Convert boundary decisions into document segments (page ranges).

    Returns list of (start_page, end_page, boundary_confidence) tuples.
    Pages are 0-indexed and end_page is inclusive.
    """
    boundary_pages = [d.page_index for d in decisions if d.is_boundary]

    if not boundary_pages:
        # No boundaries found — treat entire PDF as one document
        return [(0, total_pages - 1, 0.5)]

    segments = []
    for i, start in enumerate(boundary_pages):
        if i + 1 < len(boundary_pages):
            end = boundary_pages[i + 1] - 1
        else:
            end = total_pages - 1

        # Get the boundary confidence for this segment
        confidence = next(
            (d.score for d in decisions if d.page_index == start), 0.5
        )
        segments.append((start, end, confidence))

    return segments
