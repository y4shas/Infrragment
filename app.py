"""
app.py
------
Infrragment — Flask REST API.

Endpoints
---------
GET  /api/health
POST /api/upload                           → run pipeline, return manifest
GET  /api/output/<sid>/manifest.json       → fetch manifest JSON
GET  /api/output/<sid>/preview/<filename>  → stream a split PDF (inline)
GET  /api/output/<sid>/thumbnail/<filename>→ PNG thumbnail of page-1
GET  /api/output/<sid>/table/<filename>    → table rows as JSON (from CSV)
GET  /                                     → serve dashboard/index.html
"""
from __future__ import annotations

import csv
import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

from src.page_classifier import HeuristicClassifier
from src.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("infrragment")

app = Flask(__name__, static_folder="dashboard", static_url_path="")
CORS(app)

OUTPUT_ROOT = Path("output")
OUTPUT_ROOT.mkdir(exist_ok=True)

GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_dir(sid: str) -> Path:
    return OUTPUT_ROOT / sid


def _manifest_path(sid: str) -> Path:
    return _session_dir(sid) / "manifest.json"


def _require_session(sid: str) -> Path:
    d = _session_dir(sid)
    if not d.exists():
        abort(404, description=f"Session {sid!r} not found.")
    return d


def _generate_thumbnail(pdf_path: Path, thumb_path: Path) -> bool:
    """Render page 1 of *pdf_path* to a PNG at *thumb_path*. Returns True on success."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(str(pdf_path), dpi=120, first_page=1, last_page=1)
        if images:
            images[0].save(str(thumb_path), "PNG")
            return True
    except Exception as exc:
        logger.warning("Thumbnail generation failed for %s: %s", pdf_path.name, exc)
    return False


# ---------------------------------------------------------------------------
# Routes — static dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("dashboard", "index.html")


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "infrragment"})


@app.post("/api/upload")
def upload():
    """Accept a single PDF, run the pipeline, return the manifest."""
    if "file" not in request.files:
        abort(400, description="No file field in request.")
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        abort(400, description="Only PDF files are accepted.")

    sid = uuid.uuid4().hex
    session_dir = _session_dir(sid)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded PDF
    upload_path = session_dir / "source.pdf"
    f.save(str(upload_path))

    # Override original filename in the manifest for a clean display name
    original_name = f.filename

    try:
        classifier = HeuristicClassifier()
        manifest = run_pipeline(
            pdf_path=str(upload_path),
            output_dir=str(session_dir),
            classifier=classifier,
            extract_tables=True,
            gemini_api_key=GEMINI_API_KEY,
        )
        # Patch the source filename to show the real uploaded name
        manifest["source_pdf"] = original_name
        manifest["session_id"] = sid

        # Re-write manifest with patched source name
        with open(session_dir / "manifest.json", "w") as mf:
            json.dump(manifest, mf, indent=2)

        # Pre-generate thumbnails for all split docs (best-effort, non-blocking)
        for entry in manifest.get("documents", []):
            pdf_file = session_dir / entry["file"]
            thumb_file = session_dir / (entry["file"].replace(".pdf", "_thumb.png"))
            if pdf_file.exists() and not thumb_file.exists():
                _generate_thumbnail(pdf_file, thumb_file)

        return jsonify(manifest)

    except Exception as exc:
        logger.exception("Pipeline failed for session %s", sid)
        abort(500, description=f"Processing error: {exc}")


@app.get("/api/output/<sid>/manifest.json")
def get_manifest(sid: str):
    _require_session(sid)
    mp = _manifest_path(sid)
    if not mp.exists():
        abort(404, description="Manifest not found.")
    with open(mp) as mf:
        return jsonify(json.load(mf))


@app.get("/api/output/<sid>/preview/<path:filename>")
def preview_pdf(sid: str, filename: str):
    """Stream a split PDF for inline browser preview."""
    d = _require_session(sid)
    fp = d / filename
    if not fp.exists() or fp.suffix.lower() != ".pdf":
        abort(404, description="PDF not found.")
    return send_file(
        str(fp.resolve()),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )


@app.get("/api/output/<sid>/thumbnail/<path:filename>")
def thumbnail(sid: str, filename: str):
    """Return a PNG thumbnail for a split PDF. Generates on-demand if missing."""
    d = _require_session(sid)
    thumb_name = filename.replace(".pdf", "_thumb.png")
    thumb_path = d / thumb_name

    if not thumb_path.exists():
        pdf_path = d / filename
        if not pdf_path.exists():
            abort(404, description="Source PDF not found.")
        _generate_thumbnail(pdf_path, thumb_path)

    if not thumb_path.exists():
        abort(404, description="Thumbnail could not be generated.")

    return send_file(str(thumb_path.resolve()), mimetype="image/png")


@app.get("/api/output/<sid>/table/<path:filename>")
def get_table(sid: str, filename: str):
    """Return table CSV rows as a JSON array of arrays."""
    d = _require_session(sid)
    # Accept either the .csv filename or the source .pdf filename
    csv_name = filename if filename.endswith(".csv") else filename.replace(".pdf", "_table.csv")
    csv_path = d / csv_name
    if not csv_path.exists():
        return jsonify({"rows": [], "found": False})

    with open(csv_path, newline="") as cf:
        reader = csv.reader(cf)
        rows = list(reader)

    return jsonify({"rows": rows, "found": bool(rows)})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(e):
    return jsonify({"error": str(e.description)}), e.code


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5050, host="0.0.0.0")
