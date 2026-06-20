"""
pipeline.py
-----------
End-to-end orchestration:

    PDF -> per-page text -> per-page FIRST/OTHER/LAST classification
        -> document ranges -> split PDFs + manifest.json (+ optional
           stitched tables for tabular doc types)

# Includes an optional Gemini-powered post-processing step that enriches each
# manifest entry with a human-friendly name and a logical folder/category,
# used by the Infrragment dashboard for a meaningful folder structure.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import time

from . import table_extractor
from .boundary_detector import detect_boundaries
from .page_classifier import HeuristicClassifier, PagePrediction, TrainableClassifier
from .pdf_extract import extract_pages
from .pdf_splitter import split_pdf

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gemini folder/name enrichment
# ---------------------------------------------------------------------------

def gemini_enrich_manifest(manifest_entries: list[dict], gemini_api_key: str) -> list[dict]:
    """
    Use Gemini to assign a human-friendly name and a logical folder category to
    each manifest entry.

    The function sends a single batched request describing all detected
    document types and instances, then maps the returned labels back onto
    the entries. If the API call fails for any reason the original entries
    are returned unchanged (graceful degradation).

    Parameters
    ----------
    manifest_entries : list of manifest dicts (as produced by split_pdf).
    gemini_api_key   : Gemini API secret key.

    Returns
    -------
    The same list with two new fields added per entry:
        friendly_name    – short, readable title (e.g. "Federal Tax Return 2023")
        folder_category  – logical grouping (e.g. "Tax Documents")
    """
    if not gemini_api_key or not manifest_entries:
        return manifest_entries

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning("google-genai package not installed; skipping Gemini enrichment.")
        return manifest_entries

    client = genai.Client(api_key=gemini_api_key)

    # Build a compact description of each entry for the prompt
    doc_descriptions = []
    for i, entry in enumerate(manifest_entries):
        snippet = entry.get("text_snippet", "")
        if len(snippet) > 100:
            snippet = snippet[:150] + "..."
            
        doc_descriptions.append(
            f"{i}: doc_type={entry['doc_type']}, "
            f"pages={entry['start_page']}-{entry['end_page']}, "
            f"snippet=\"{snippet}\""
        )

    prompt = (
        "You are an intelligent document classifier. Given a list of detected document "
        "segments from a multi-document PDF package, produce a JSON array where each "
        "element has:\n"
        "  - index: the same integer index as in the input\n"
        "  - friendly_name: a short, human-readable document title (e.g. 'Software License Agreement', "
        "'Data Science Article', 'Bank Statement', 'Technical Specification')\n"
        "  - folder_category: a logical folder/grouping name (e.g. 'Articles', "
        "'Financials', 'Legal', 'Technical Docs', 'Identity Documents')\n\n"
        "CRITICAL INSTRUCTION: Read the 'snippet' of text for each document. "
        "If doc_type is 'Unclassified', YOU MUST infer the name from the snippet. "
        "DO NOT use the example names above unless they actually match the content! "
        "If it is an article, research paper, or blog post, use its title as the friendly_name.\n\n"
        "Documents:\n"
        + "\n".join(doc_descriptions)
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        
        raw = response.text.strip()
        enrichments = json.loads(raw)
        enrichment_map = {item["index"]: item for item in enrichments}

        for i, entry in enumerate(manifest_entries):
            gpt = enrichment_map.get(i, {})
            entry["friendly_name"] = gpt.get("friendly_name", entry["doc_type"].replace("_", " "))
            entry["folder_category"] = gpt.get("folder_category", "Uncategorized")

    except Exception as exc:
        logger.warning("Gemini enrichment failed: %s — falling back to raw doc_type names.", exc)
        for entry in manifest_entries:
            entry.setdefault("friendly_name", entry["doc_type"].replace("_", " "))
            entry.setdefault("folder_category", "Uncategorized")

    return manifest_entries


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    pdf_path: str,
    output_dir: str,
    classifier=None,
    extract_tables: bool = True,
    gemini_api_key: str | None = None,
) -> dict:
    """Run the full split pipeline on a single PDF.

    Parameters
    ----------
    pdf_path: input PDF (a whole document package).
    output_dir: directory to write split PDFs + manifest.json into.
    classifier: an object with .classify(list[str]) -> list[PagePrediction].
        Defaults to HeuristicClassifier() (no training data required).
    extract_tables: if True, also writes a stitched CSV per document
        instance whose doc_type is in table_extractor.TABULAR_DOC_TYPES.
    gemini_api_key: if provided, Gemini is called to enrich the manifest with
        friendly_name and folder_category fields.

    Returns
    -------
    The manifest dict that's also written to {output_dir}/manifest.json.
    """
    t0 = time.time()
    classifier = classifier or HeuristicClassifier()

    pages = extract_pages(pdf_path)
    page_texts = [p.text for p in pages]

    predictions: list[PagePrediction] = classifier.classify(page_texts)
    ranges = detect_boundaries(predictions)

    os.makedirs(output_dir, exist_ok=True)
    manifest_entries = split_pdf(pdf_path, page_texts, ranges, output_dir)

    if extract_tables:
        for entry in manifest_entries:
            if entry["doc_type"] in table_extractor.TABULAR_DOC_TYPES:
                rows = table_extractor.extract_tables_for_range(
                    pdf_path, entry["start_page"], entry["end_page"]
                )
                if rows:
                    csv_name = entry["file"].replace(".pdf", "_table.csv")
                    with open(os.path.join(output_dir, csv_name), "w", newline="") as f:
                        csv.writer(f).writerows(rows)
                    entry["table_file"] = csv_name

    # Gemini enrichment (optional — gracefully skipped if key is absent)
    if gemini_api_key:
        manifest_entries = gemini_enrich_manifest(manifest_entries, gemini_api_key)
    else:
        for entry in manifest_entries:
            entry.setdefault("friendly_name", entry["doc_type"].replace("_", " "))
            entry.setdefault("folder_category", "Uncategorized")

    manifest = {
        "source_pdf": os.path.basename(pdf_path),
        "total_pages": len(pages),
        "documents_found": len(manifest_entries),
        "processing_seconds": round(time.time() - t0, 3),
        "ocr_pages_used": sum(1 for p in pages if p.source == "ocr"),
        "documents": manifest_entries,
    }

    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
