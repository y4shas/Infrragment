"""
PDF splitting module.

Splits the source PDF into per-document-instance files, organized into
the expected folder structure:

    /output/<upload_id>/
        manifest.json
        /<doc_key>/
            instance_<ordinal>/
                pages_<start>_<end>.pdf
                tables.json
"""
import json
import logging
from pathlib import Path

from models import DocumentInstance, ProcessingManifest
from pipeline.pdf_utils import split_pdf
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def split_and_organize(
    source_pdf_path: str | Path,
    upload_id: str,
    instances: list[DocumentInstance],
    manifest: ProcessingManifest,
) -> Path:
    """
    Split the source PDF and create the organized folder structure.

    Args:
        source_pdf_path: Path to the uploaded PDF
        upload_id: Unique upload identifier
        instances: List of resolved document instances
        manifest: Full processing manifest

    Returns:
        Path to the output directory for this upload
    """
    output_dir = OUTPUT_DIR / upload_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for instance in instances:
        # Create folder: /output/<upload_id>/<doc_key>/instance_<ordinal>/
        instance_dir = output_dir / instance.key / f"instance_{instance.instance_ordinal}"
        instance_dir.mkdir(parents=True, exist_ok=True)

        # Split PDF
        pdf_filename = f"pages_{instance.start_page:04d}_{instance.end_page:04d}.pdf"
        output_pdf_path = instance_dir / pdf_filename

        try:
            split_pdf(source_pdf_path, output_pdf_path, instance.start_page, instance.end_page)
            instance.pdf_filename = pdf_filename
            logger.info(
                f"Split {instance.doc_instance_id}: pages {instance.start_page}-{instance.end_page} "
                f"→ {output_pdf_path}"
            )
        except Exception as e:
            logger.error(f"Failed to split PDF for {instance.doc_instance_id}: {e}")

        # Write tables.json for this instance
        tables_path = instance_dir / "tables.json"
        tables_data = [t.model_dump() for t in instance.tables]
        with open(tables_path, "w") as f:
            json.dump(tables_data, f, indent=2)

    # Write manifest.json
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    logger.info(f"Output organized at {output_dir}")
    return output_dir
