"""
FastAPI application — main entry point for the Loan File Structuring System backend.

Serves:
- PDF upload + background processing
- SSE status streaming during processing
- Document listing and detail APIs
- Split PDF file serving
- Table data APIs
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from config import CORS_ORIGINS, UPLOAD_DIR, OUTPUT_DIR
from models import (
    UploadResponse,
    DocumentListResponse,
    ProcessingStatus,
    ProcessingStage,
    ProcessingManifest,
    EfficiencyStats,
)
from pipeline.orchestrator import run_pipeline
from pipeline.pdf_utils import get_page_count

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Infrragment — Loan File Structuring System",
    description="Splits multi-document PDFs into structured documents with extracted tables",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output directory for serving split PDFs
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# --- In-memory state for active processing jobs ---
# Maps upload_id -> latest ProcessingStatus
processing_status: dict[str, ProcessingStatus] = {}
# Maps upload_id -> asyncio.Queue for SSE events
status_queues: dict[str, list[asyncio.Queue]] = {}


def _status_callback(status: ProcessingStatus):
    """Callback invoked by the pipeline to report progress."""
    processing_status[status.upload_id] = status

    # Push to all SSE listeners
    if status.upload_id in status_queues:
        for queue in status_queues[status.upload_id]:
            try:
                queue.put_nowait(status)
            except asyncio.QueueFull:
                pass  # Drop if consumer is slow


async def _process_pdf(upload_id: str, pdf_path: str, filename: str):
    """Background task to process an uploaded PDF."""
    try:
        await run_pipeline(pdf_path, upload_id, filename, status_callback=_status_callback)
    except Exception as e:
        logger.exception(f"Processing failed for {upload_id}: {e}")
        _status_callback(ProcessingStatus(
            upload_id=upload_id,
            stage=ProcessingStage.FAILED,
            message=f"Processing failed: {str(e)}",
            error=str(e),
        ))


# ===== API ENDPOINTS =====

@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and start processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    upload_id = str(uuid.uuid4())[:8]
    upload_dir = UPLOAD_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = upload_dir / file.filename
    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)

    # Get page count
    try:
        total_pages = get_page_count(str(pdf_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {e}")

    # Initialize processing status
    processing_status[upload_id] = ProcessingStatus(
        upload_id=upload_id,
        stage=ProcessingStage.UPLOADING,
        message="Upload received, starting processing...",
        total_pages=total_pages,
    )

    # Start processing in background
    asyncio.create_task(_process_pdf(upload_id, str(pdf_path), file.filename))

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        total_pages=total_pages,
    )


@app.get("/api/status/{upload_id}")
async def stream_status(upload_id: str):
    """SSE endpoint for real-time processing status updates."""
    queue = asyncio.Queue(maxsize=100)

    if upload_id not in status_queues:
        status_queues[upload_id] = []
    status_queues[upload_id].append(queue)

    async def event_generator():
        try:
            # Send current status immediately
            if upload_id in processing_status:
                data = processing_status[upload_id].model_dump_json()
                yield f"data: {data}\n\n"

            while True:
                try:
                    status = await asyncio.wait_for(queue.get(), timeout=30.0)
                    data = status.model_dump_json()
                    yield f"data: {data}\n\n"

                    # Stop streaming when processing is complete or failed
                    if status.stage in (ProcessingStage.COMPLETED, ProcessingStage.FAILED):
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
        finally:
            if upload_id in status_queues:
                try:
                    status_queues[upload_id].remove(queue)
                except ValueError:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/documents/{upload_id}")
async def get_documents(upload_id: str):
    """Get all document instances for a processed upload."""
    manifest = _load_manifest(upload_id)

    return DocumentListResponse(
        upload_id=manifest.upload_id,
        source_filename=manifest.source_filename,
        total_pages=manifest.total_pages,
        document_count=len(manifest.documents),
        documents=manifest.documents,
        processing_time_seconds=manifest.processing_time_seconds,
        llm_calls_made=manifest.llm_calls_made,
        estimated_llm_cost_usd=manifest.estimated_llm_cost_usd,
    )


@app.get("/api/documents/{upload_id}/{doc_instance_id}")
async def get_document_detail(upload_id: str, doc_instance_id: str):
    """Get details for a specific document instance."""
    manifest = _load_manifest(upload_id)

    for doc in manifest.documents:
        if doc.doc_instance_id == doc_instance_id:
            return doc

    raise HTTPException(status_code=404, detail=f"Document {doc_instance_id} not found")


@app.get("/api/documents/{upload_id}/{doc_instance_id}/pdf")
async def get_document_pdf(upload_id: str, doc_instance_id: str):
    """Serve the split PDF for a document instance."""
    manifest = _load_manifest(upload_id)

    for doc in manifest.documents:
        if doc.doc_instance_id == doc_instance_id:
            if not doc.pdf_filename:
                raise HTTPException(status_code=404, detail="PDF file not available")

            pdf_path = (
                OUTPUT_DIR / upload_id / doc.key
                / f"instance_{doc.instance_ordinal}" / doc.pdf_filename
            )

            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="PDF file not found on disk")

            return FileResponse(
                str(pdf_path),
                media_type="application/pdf",
                filename=f"{doc.doc_instance_id}.pdf",
            )

    raise HTTPException(status_code=404, detail=f"Document {doc_instance_id} not found")


@app.get("/api/tables/{upload_id}/{doc_instance_id}")
async def get_document_tables(upload_id: str, doc_instance_id: str):
    """Get all extracted tables for a document instance."""
    manifest = _load_manifest(upload_id)

    for doc in manifest.documents:
        if doc.doc_instance_id == doc_instance_id:
            return {"tables": doc.tables}

    raise HTTPException(status_code=404, detail=f"Document {doc_instance_id} not found")


@app.get("/api/efficiency/{upload_id}")
async def get_efficiency_stats(upload_id: str):
    """Get efficiency/cost statistics for a processed upload."""
    manifest = _load_manifest(upload_id)

    total_tables = sum(len(doc.tables) for doc in manifest.documents)
    pages_per_sec = (
        manifest.total_pages / manifest.processing_time_seconds
        if manifest.processing_time_seconds > 0 else 0
    )

    # Extrapolate to 2000 pages
    scale_factor = 2000 / max(manifest.total_pages, 1)
    estimated_2000_cost = manifest.estimated_llm_cost_usd * scale_factor

    return EfficiencyStats(
        total_pages=manifest.total_pages,
        document_count=len(manifest.documents),
        table_count=total_tables,
        processing_time_seconds=manifest.processing_time_seconds,
        llm_calls_made=manifest.llm_calls_made,
        llm_total_input_tokens=manifest.llm_total_input_tokens,
        llm_total_output_tokens=manifest.llm_total_output_tokens,
        estimated_llm_cost_usd=manifest.estimated_llm_cost_usd,
        estimated_cost_at_2000_pages=round(estimated_2000_cost, 4),
        pages_per_second=round(pages_per_sec, 2),
    )


@app.get("/api/status-poll/{upload_id}")
async def poll_status(upload_id: str):
    """Polling endpoint for processing status (fallback for SSE)."""
    if upload_id in processing_status:
        return processing_status[upload_id]
    raise HTTPException(status_code=404, detail="Upload not found")


@app.get("/api/uploads")
async def list_uploads():
    """List all processed uploads."""
    uploads = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir():
                manifest_path = d / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            data = json.load(f)
                        uploads.append({
                            "upload_id": data.get("upload_id", d.name),
                            "source_filename": data.get("source_filename", "unknown"),
                            "total_pages": data.get("total_pages", 0),
                            "document_count": len(data.get("documents", [])),
                            "processing_time_seconds": data.get("processing_time_seconds", 0),
                        })
                    except Exception:
                        pass
    return {"uploads": uploads}


# --- Helpers ---

def _load_manifest(upload_id: str) -> ProcessingManifest:
    """Load the processing manifest for an upload."""
    manifest_path = OUTPUT_DIR / upload_id / "manifest.json"
    if not manifest_path.exists():
        # Check if still processing
        if upload_id in processing_status:
            stage = processing_status[upload_id].stage
            if stage not in (ProcessingStage.COMPLETED, ProcessingStage.FAILED):
                raise HTTPException(
                    status_code=202,
                    detail=f"Still processing (stage: {stage.value})"
                )
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")

    with open(manifest_path) as f:
        data = json.load(f)

    return ProcessingManifest(**data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
