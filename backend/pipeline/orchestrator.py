"""
Pipeline orchestrator — coordinates all processing stages.

Runs the full pipeline:
    Upload → Feature extraction → Boundary detection → Instance resolution
    → LLM verification → PDF splitting → Table extraction → Table verification
    → Persist manifest + organize output

Emits status updates via a callback for real-time SSE streaming to the frontend.
"""
import time
import logging
from pathlib import Path
from typing import Optional, Callable

import pymupdf

from models import (
    ProcessingStage,
    ProcessingStatus,
    ProcessingManifest,
    DocumentInstance,
)
from pipeline.feature_extraction import extract_all_page_features
from pipeline.boundary_detection import detect_boundaries, get_document_segments
from pipeline.instance_resolution import resolve_document_instances
from pipeline.table_extraction import extract_tables_for_document
from pipeline.pdf_splitter import split_and_organize
from pipeline.verifier import Verifier
from config import BOUNDARY_VERIFY_LOW, BOUNDARY_VERIFY_HIGH

logger = logging.getLogger(__name__)

# Type alias for the status callback
StatusCallback = Callable[[ProcessingStatus], None]


async def run_pipeline(
    pdf_path: str | Path,
    upload_id: str,
    filename: str,
    status_callback: Optional[StatusCallback] = None,
) -> ProcessingManifest:
    """
    Run the full document processing pipeline.

    Args:
        pdf_path: Path to the uploaded PDF file
        upload_id: Unique identifier for this upload
        filename: Original filename
        status_callback: Optional callback to report progress

    Returns:
        ProcessingManifest with all results
    """
    start_time = time.time()
    pdf_path = Path(pdf_path)

    def emit(stage: ProcessingStage, progress: float = 0.0, message: str = "",
             current_page: int = 0, total_pages: int = 0):
        if status_callback:
            status_callback(ProcessingStatus(
                upload_id=upload_id,
                stage=stage,
                progress=progress,
                message=message,
                current_page=current_page,
                total_pages=total_pages,
            ))

    try:
        # --- Open PDF ---
        doc = pymupdf.open(str(pdf_path))
        total_pages = len(doc)
        logger.info(f"Processing {filename}: {total_pages} pages")

        # --- Stage 1: Feature Extraction ---
        emit(ProcessingStage.EXTRACTING_FEATURES, 0.0,
             f"Analyzing {total_pages} pages...", total_pages=total_pages)

        def feature_progress(page_idx, total):
            emit(
                ProcessingStage.EXTRACTING_FEATURES,
                page_idx / total,
                f"Extracting features from page {page_idx + 1}/{total}",
                current_page=page_idx + 1,
                total_pages=total,
            )

        page_features = extract_all_page_features(doc, progress_callback=feature_progress)
        emit(ProcessingStage.EXTRACTING_FEATURES, 1.0, "Feature extraction complete")

        # --- Stage 2: Boundary Detection ---
        emit(ProcessingStage.DETECTING_BOUNDARIES, 0.0, "Detecting document boundaries...")

        decisions = detect_boundaries(page_features)
        segments = get_document_segments(decisions, total_pages)

        boundary_count = sum(1 for d in decisions if d.is_boundary)
        emit(ProcessingStage.DETECTING_BOUNDARIES, 1.0,
             f"Found {boundary_count} document boundaries ({len(segments)} documents)")

        # --- Stage 3: Instance Resolution ---
        emit(ProcessingStage.RESOLVING_INSTANCES, 0.0, "Resolving document instances...")

        instances = resolve_document_instances(segments, page_features)

        emit(ProcessingStage.RESOLVING_INSTANCES, 1.0,
             f"Resolved {len(instances)} document instances")

        # --- Stage 4: LLM Boundary Verification ---
        verifier = Verifier()
        emit(ProcessingStage.VERIFYING_BOUNDARIES, 0.0,
             "Verifying boundaries..." if verifier.is_available else "Skipping LLM verification (not configured)")

        if verifier.is_available:
            _verify_boundaries(verifier, decisions, page_features, instances, emit)
        emit(ProcessingStage.VERIFYING_BOUNDARIES, 1.0, "Boundary verification complete")

        # --- Stage 5: PDF Splitting ---
        emit(ProcessingStage.SPLITTING_PDF, 0.0, "Splitting PDF into documents...")

        # We need to split before table extraction so we have per-instance PDFs
        # But first create the manifest shell
        manifest = ProcessingManifest(
            upload_id=upload_id,
            source_filename=filename,
            total_pages=total_pages,
            documents=instances,
        )

        emit(ProcessingStage.SPLITTING_PDF, 1.0, "PDF split complete")

        # --- Stage 6: Table Extraction ---
        emit(ProcessingStage.EXTRACTING_TABLES, 0.0, "Extracting tables...")

        total_tables = 0
        for idx, instance in enumerate(instances):
            emit(
                ProcessingStage.EXTRACTING_TABLES,
                idx / len(instances),
                f"Extracting tables from {instance.doc_instance_id}...",
            )

            tables = extract_tables_for_document(
                str(pdf_path),
                instance.start_page,
                instance.end_page,
                instance.doc_instance_id,
            )
            instance.tables = tables
            total_tables += len(tables)

        emit(ProcessingStage.EXTRACTING_TABLES, 1.0,
             f"Extracted {total_tables} tables from {len(instances)} documents")

        # --- Stage 7: LLM Table Verification ---
        emit(ProcessingStage.VERIFYING_TABLES, 0.0,
             "Verifying tables..." if verifier.is_available else "Skipping table verification")

        if verifier.is_available:
            _verify_tables(verifier, instances, emit)
        emit(ProcessingStage.VERIFYING_TABLES, 1.0, "Table verification complete")

        # --- Stage 8: Persist ---
        emit(ProcessingStage.PERSISTING, 0.0, "Organizing output...")

        # Update manifest with verifier stats
        verifier_stats = verifier.get_stats_dict()
        manifest.llm_calls_made = verifier_stats["total_calls"]
        manifest.llm_total_input_tokens = verifier_stats["total_input_tokens"]
        manifest.llm_total_output_tokens = verifier_stats["total_output_tokens"]
        manifest.estimated_llm_cost_usd = verifier_stats["estimated_cost_usd"]

        # Split and organize files
        split_and_organize(pdf_path, upload_id, instances, manifest)

        # Record timing
        elapsed = time.time() - start_time
        manifest.processing_time_seconds = round(elapsed, 2)

        # Re-save manifest with updated timing
        import json
        from config import OUTPUT_DIR
        manifest_path = OUTPUT_DIR / upload_id / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest.model_dump(), f, indent=2)

        emit(ProcessingStage.PERSISTING, 1.0, "Output organized")

        # --- Done ---
        emit(ProcessingStage.COMPLETED, 1.0,
             f"Completed: {len(instances)} documents, {total_tables} tables in {elapsed:.1f}s")

        doc.close()
        logger.info(
            f"Pipeline complete for {filename}: {len(instances)} docs, "
            f"{total_tables} tables, {elapsed:.1f}s, "
            f"{verifier_stats['total_calls']} LLM calls (${verifier_stats['estimated_cost_usd']:.4f})"
        )

        return manifest

    except Exception as e:
        logger.exception(f"Pipeline failed for {filename}: {e}")
        emit(ProcessingStage.FAILED, 0.0, f"Processing failed: {str(e)}")
        raise


def _verify_boundaries(verifier, decisions, page_features, instances, emit):
    """Run LLM verification on ambiguous boundary decisions."""
    ambiguous = [
        d for d in decisions
        if d.is_boundary and BOUNDARY_VERIFY_LOW < d.score < BOUNDARY_VERIFY_HIGH
    ]

    logger.info(f"Verifying {len(ambiguous)} ambiguous boundaries")

    for idx, decision in enumerate(ambiguous):
        emit(
            ProcessingStage.VERIFYING_BOUNDARIES,
            idx / max(len(ambiguous), 1),
            f"Verifying boundary at page {decision.page_index}...",
        )

        prev_text = page_features[decision.page_index - 1].raw_text if decision.page_index > 0 else ""
        curr_text = page_features[decision.page_index].raw_text

        result = verifier.verify_boundary(
            prev_text, curr_text,
            decision.is_boundary, decision.score,
        )

        decision.verifier_agreed = result["agreed"]
        decision.verifier_reason = result["reason"]

        # If verifier disagrees, flag the corresponding instance
        if result["agreed"] is False:
            for inst in instances:
                if inst.start_page == decision.page_index:
                    inst.verifier_flagged = True


def _verify_tables(verifier, instances, emit):
    """Run LLM verification on extracted tables."""
    total_tables = sum(len(inst.tables) for inst in instances)
    verified = 0

    for instance in instances:
        for table in instance.tables:
            emit(
                ProcessingStage.VERIFYING_TABLES,
                verified / max(total_tables, 1),
                f"Verifying {table.table_id}...",
            )

            result = verifier.verify_table(
                table.headers,
                table.rows[:3],
                table.rows[-3:] if len(table.rows) > 3 else table.rows,
                table.row_count,
            )

            if result["agreed"] is False:
                table.verifier_flagged = True
                table.verifier_notes = result["reason"]

            verified += 1
