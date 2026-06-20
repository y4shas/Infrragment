"""
Document instance resolution.

After boundary detection identifies page segments, this module:
1. Assigns document type labels by analyzing content (generic, not hardcoded)
2. Disambiguates same-type consecutive documents using distinguishing attributes
3. Assigns instance ordinals and generates doc_instance_ids
4. Infers section categories generically
"""
import re
import logging
from collections import defaultdict
from typing import Optional

from slugify import slugify

from models import PageFeatures, DocumentInstance

logger = logging.getLogger(__name__)

# Generic section inference based on detected content keywords
# These are heuristic mappings, not a hardcoded taxonomy
SECTION_KEYWORDS = {
    "income": [
        "w-2", "w2", "wage", "salary", "1099", "pay stub", "paystub",
        "earnings", "compensation", "income",
    ],
    "tax": [
        "1040", "tax return", "tax year", "schedule", "irs", "internal revenue",
        "tax form", "1065", "1120",
    ],
    "assets": [
        "bank statement", "account statement", "checking", "savings",
        "investment", "brokerage", "401k", "ira", "asset",
    ],
    "identity": [
        "driver", "license", "passport", "identification", "id card", "ssn",
        "social security",
    ],
    "property": [
        "appraisal", "deed", "title", "property", "mortgage", "lien",
        "home", "real estate", "hoa",
    ],
    "legal": [
        "agreement", "contract", "disclosure", "notice", "affidavit",
        "declaration", "certificate", "power of attorney",
    ],
    "financial": [
        "invoice", "receipt", "billing", "payment", "credit report",
        "financial statement", "balance sheet", "profit", "loss",
    ],
}


def resolve_document_instances(
    segments: list[tuple[int, int, float]],
    page_features: list[PageFeatures],
) -> list[DocumentInstance]:
    """
    Resolve detected segments into fully labeled document instances.

    Args:
        segments: List of (start_page, end_page, boundary_confidence) from boundary detection
        page_features: All page features for the PDF

    Returns:
        List of DocumentInstance objects with assigned types, sections, and ordinals
    """
    raw_instances = []

    for order_idx, (start, end, confidence) in enumerate(segments):
        # Gather text from segment pages for classification
        segment_text = _get_segment_text(page_features, start, end)

        # Determine document type label
        doc_key = _infer_document_key(segment_text, page_features, start, end)

        # Determine section
        section = _infer_section(segment_text, doc_key)

        # Extract distinguishing attribute
        distinguishing = _extract_distinguishing_attribute(segment_text, page_features, start, end)

        raw_instances.append({
            "key": doc_key,
            "section": section,
            "order_index": order_idx,
            "start_page": start,
            "end_page": end,
            "page_count": end - start + 1,
            "boundary_confidence": confidence,
            "distinguishing_attribute": distinguishing,
            "segment_text_preview": segment_text[:200],
        })

    # Assign instance ordinals per document type
    instances = _assign_ordinals(raw_instances)

    return instances


def _get_segment_text(
    page_features: list[PageFeatures],
    start: int,
    end: int,
    max_chars: int = 2000,
) -> str:
    """Get combined text from segment pages (limited to max_chars)."""
    texts = []
    total = 0
    for i in range(start, min(end + 1, len(page_features))):
        text = page_features[i].raw_text
        texts.append(text)
        total += len(text)
        if total > max_chars:
            break
    return "\n".join(texts)[:max_chars]


def _infer_document_key(
    segment_text: str,
    page_features: list[PageFeatures],
    start: int,
    end: int,
) -> str:
    """
    Infer a document type key from the segment content.
    Uses form identifiers, title text, and content analysis.
    Generic — does not depend on a fixed taxonomy.
    """
    text_lower = segment_text.lower()

    # Priority 1: Form identifier from the first page
    first_page = page_features[start]
    if first_page.has_form_identifier and first_page.form_identifier:
        return slugify(first_page.form_identifier, separator="_")

    # Priority 2: Title text from the first page
    if first_page.has_title_text and first_page.title_text:
        title = first_page.title_text.strip()
        if len(title) > 3 and len(title) < 80:
            return slugify(title, separator="_")

    # Priority 3: Look for common document type patterns in text
    type_patterns = [
        (r"bank\s+statement", "bank_statement"),
        (r"account\s+statement", "account_statement"),
        (r"pay\s*(?:stub|check|slip)", "pay_stub"),
        (r"tax\s+return", "tax_return"),
        (r"credit\s+report", "credit_report"),
        (r"financial\s+statement", "financial_statement"),
        (r"balance\s+sheet", "balance_sheet"),
        (r"profit\s+(?:and|&)\s+loss", "profit_and_loss"),
        (r"invoice", "invoice"),
        (r"receipt", "receipt"),
        (r"letter", "letter"),
        (r"report", "report"),
    ]

    for pattern, key in type_patterns:
        if re.search(pattern, text_lower):
            return key

    # Priority 4: Use the most prominent heading/title text from any page in segment
    for i in range(start, min(end + 1, start + 3)):
        pf = page_features[i]
        if pf.has_title_text and pf.title_text:
            candidate = slugify(pf.title_text[:60], separator="_")
            if candidate and len(candidate) > 2:
                return candidate

    return "uncategorized"


def _infer_section(segment_text: str, doc_key: str) -> str:
    """
    Infer a section category for the document.
    Generic keyword-based matching, not a fixed taxonomy.
    """
    combined = f"{doc_key} {segment_text}".lower()

    best_section = "uncategorized"
    best_score = 0

    for section, keywords in SECTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_section = section

    # Only assign a section if we have reasonable confidence (2+ keyword matches)
    if best_score < 2:
        return "uncategorized"

    return best_section


def _extract_distinguishing_attribute(
    segment_text: str,
    page_features: list[PageFeatures],
    start: int,
    end: int,
) -> str:
    """
    Extract the key distinguishing attribute for this document instance.
    Used to tell apart multiple instances of the same document type
    (e.g., different statement periods, tax years, account numbers).
    """
    attributes = []

    # Check for date/period in header
    for i in range(start, min(end + 1, start + 2)):
        pf = page_features[i]
        if pf.has_date_header and pf.date_header_text:
            attributes.append(pf.date_header_text)

    # Look for specific period patterns in text
    period_patterns = [
        re.compile(
            r"(?:Statement\s+Period|Period)[:\s]*(.+?)(?:\n|$)", re.IGNORECASE
        ),
        re.compile(r"(?:Tax\s+Year|Year)[:\s]*(\d{4})", re.IGNORECASE),
        re.compile(
            r"(?:For\s+the\s+(?:month|period|year)\s+(?:of|ending))[:\s]*(.+?)(?:\n|$)",
            re.IGNORECASE,
        ),
        re.compile(r"Account\s*(?:#|No\.?|Number)[:\s]*(\S+)", re.IGNORECASE),
    ]

    for pattern in period_patterns:
        match = pattern.search(segment_text[:1000])
        if match:
            attr = match.group(0).strip()
            if attr and attr not in attributes:
                attributes.append(attr)

    return "; ".join(attributes[:3]) if attributes else ""


def _assign_ordinals(raw_instances: list[dict]) -> list[DocumentInstance]:
    """
    Assign instance ordinals per document type key.
    E.g., if there are 3 bank_statement instances, they get ordinals 1, 2, 3.
    Also generates unique doc_instance_ids and doctype_label_ids.
    """
    # Track ordinals per key
    key_counters: dict[str, int] = defaultdict(int)

    # Assign stable label IDs per unique key
    key_to_label_id: dict[str, int] = {}
    next_label_id = 1

    instances = []
    for raw in raw_instances:
        key = raw["key"]

        # Assign label ID
        if key not in key_to_label_id:
            key_to_label_id[key] = next_label_id
            next_label_id += 1

        # Increment ordinal
        key_counters[key] += 1
        ordinal = key_counters[key]

        # Generate instance ID
        doc_instance_id = f"{key}#{ordinal}"

        instance = DocumentInstance(
            doc_instance_id=doc_instance_id,
            key=key,
            doctype_label_id=key_to_label_id[key],
            section=raw["section"],
            order_index=raw["order_index"],
            start_page=raw["start_page"],
            end_page=raw["end_page"],
            page_count=raw["page_count"],
            instance_ordinal=ordinal,
            is_boundary_start=True,
            boundary_confidence=raw["boundary_confidence"],
            distinguishing_attribute=raw["distinguishing_attribute"],
        )
        instances.append(instance)

    return instances
