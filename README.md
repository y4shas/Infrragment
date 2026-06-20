# Infrragment

**Organize large PDFs into structured documents and machine-readable tables.**

Infrragment takes a single large, unstructured, multi-document PDF (e.g., a 100–2000 page mortgage loan file) and produces:

1. **Logical pagination** — splits the PDF into individual document instances with precise page boundaries
2. **Table structuring** — extracts tables (including multi-page tables) into clean, structured row/column data
3. **Dashboard UI** — upload, browse, and inspect results

## Architecture

```
Upload PDF
  → Page feature extraction (text, layout, visual)
  → Deterministic boundary detection (find document breaks)
  → Document instance resolution (group + disambiguate same-type docs)
  → Optional: Cheap-LLM verification (Gemini Flash Lite checks boundaries)
  → Split PDF into per-document-instance files
  → Table extraction per document instance (handles multi-page tables)
  → Optional: LLM verification on extracted tables
  → Persist structured JSON + organize output folders
  → Serve via API to frontend dashboard
```

### Design: Deterministic-First, LLM-as-Verifier

- Boundary detection and table extraction are done **deterministically/locally** using classical text analysis, layout heuristics, and PDF parsing libraries
- A **cheap Gemini model** (`gemini-3.1-flash-lite`) is used only as a **verifier** — confirming or flagging the deterministic output — not as the primary extraction engine
- This keeps cost at **~$0.02-0.03 per 2000-page document** vs. $10+ with per-page LLM extraction
- LLM verification is **fully optional** — the system works without a Gemini API key

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- (Optional) Tesseract OCR: `brew install tesseract`
- (Optional) Gemini API key for LLM verification

### Setup & Run

```bash
# Clone the repository
git clone <repo-url>
cd Infrragment

# Option 1: One-command startup
chmod +x run.sh
./run.sh

# Option 2: Manual startup
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** and upload a PDF.

### Environment Variables (optional)

```bash
export ENABLE_LLM_VERIFICATION=true      # Enable Gemini verification
export GEMINI_API_KEY=your_key_here       # Your Gemini API key
```

### Generate a Test PDF

```bash
cd backend
source .venv/bin/activate
python create_test_pdf.py
# Creates: test_documents/sample_loan_file.pdf
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **PDF parsing/rendering** | PyMuPDF (`pymupdf`) |
| **Table extraction** | pdfplumber (primary), camelot-py (optional) |
| **OCR** | pytesseract + Tesseract |
| **CV/layout analysis** | OpenCV, scikit-image (SSIM) |
| **LLM verification** | Gemini 3.1 Flash Lite via `google-genai` |
| **Backend** | FastAPI + SQLite/JSON |
| **Frontend** | React + Vite + Tailwind CSS v4 |
| **PDF viewing** | PDF.js (pdfjs-dist) |

## Pipeline Stages

### 1. Feature Extraction
For each page, computes a feature vector:
- Text-layer features: titles, form identifiers, page numbers, font profiles
- Visual features: layout similarity (SSIM), whitespace density, letterhead detection
- OCR fallback for scanned pages

### 2. Boundary Detection
Weighted heuristic scoring on page transitions:
- Page number reset to 1 (weight: 0.35)
- Different form/document identifier (weight: 0.30)
- "Page X of X" final page indicator (weight: 0.15)
- Layout dissimilarity via SSIM (weight: 0.12)
- Font profile change (weight: 0.08)
- Letterhead/logo detection (weight: 0.08)
- Title text presence (weight: 0.07)
- Whitespace density spike (weight: 0.05)

Threshold: score > 0.50 → mark as document boundary.

### 3. Instance Resolution
- Assigns document type labels from content (generic, not hardcoded)
- Disambiguates same-type documents using distinguishing attributes (dates, periods, account numbers)
- Assigns instance ordinals per type

### 4. Table Extraction
- Primary: pdfplumber (lattice + text modes)
- Multi-page table detection via header similarity matching
- Header deduplication for merged tables
- Structured output: headers + rows as clean arrays

### 5. LLM Verification (Optional)
- Only verifies ambiguous decisions (confidence 0.35–0.75)
- ~60-80 API calls for a 2000-page PDF
- Full token counting and cost logging

## Output Structure

```
/output/<upload_id>/
  manifest.json                  # Full processing manifest
  /bank_statement/
    instance_1/
      pages_0001_0003.pdf
      tables.json
    instance_2/
      pages_0004_0005.pdf
      tables.json
  /form_1040/
    instance_1/
      pages_0006_0007.pdf
      tables.json
  /uncategorized/
    instance_1/
      ...
```

## Cost Model at Scale

| Metric | Value |
|--------|-------|
| LLM calls per 2000 pages | ~60-80 |
| Avg tokens per call | ~800 input, ~50 output |
| Cost per 2000-page PDF | ~$0.02-0.03 |
| Processing speed | ~2-5 pages/second |
| Total LLM cost | <0.1% of per-page LLM approach |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload PDF, start processing |
| `GET` | `/api/status/{id}` | SSE stream of processing stages |
| `GET` | `/api/documents/{id}` | List all document instances |
| `GET` | `/api/documents/{id}/{doc_id}` | Document instance detail |
| `GET` | `/api/documents/{id}/{doc_id}/pdf` | Serve split PDF |
| `GET` | `/api/tables/{id}/{doc_id}` | Tables for a document |
| `GET` | `/api/efficiency/{id}` | Cost/performance stats |
| `GET` | `/api/uploads` | List processed uploads |

## Dependencies

### Python (backend/requirements.txt)
- fastapi, uvicorn, python-multipart, pydantic
- pymupdf, pdfplumber
- pytesseract, Pillow
- opencv-python-headless, numpy, scikit-image
- google-genai
- python-slugify

### Node.js (frontend/package.json)
- react, react-dom
- vite, @vitejs/plugin-react
- tailwindcss, @tailwindcss/vite
- pdfjs-dist

## License

MIT
