"""
Pydantic models for the Loan File Structuring System.
Covers API request/response schemas and internal pipeline data structures.
"""
from __future__ import annotations

import enum
from typing import Optional
from pydantic import BaseModel, Field


# --- Processing Status ---

class ProcessingStage(str, enum.Enum):
    UPLOADING = "uploading"
    EXTRACTING_FEATURES = "extracting_features"
    DETECTING_BOUNDARIES = "detecting_boundaries"
    RESOLVING_INSTANCES = "resolving_instances"
    VERIFYING_BOUNDARIES = "verifying_boundaries"
    SPLITTING_PDF = "splitting_pdf"
    EXTRACTING_TABLES = "extracting_tables"
    VERIFYING_TABLES = "verifying_tables"
    PERSISTING = "persisting"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(BaseModel):
    upload_id: str
    stage: ProcessingStage
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    total_pages: int = 0
    current_page: int = 0
    error: Optional[str] = None


# --- Page Features ---

class PageFeatures(BaseModel):
    """Feature vector computed for each page, used for boundary detection."""
    page_index: int
    has_title_text: bool = False
    title_text: str = ""
    has_form_identifier: bool = False
    form_identifier: str = ""
    has_page_number: bool = False
    page_number_value: Optional[int] = None
    page_number_total: Optional[int] = None
    has_letterhead: bool = False
    font_change_score: float = 0.0
    whitespace_density: float = 0.0
    text_density: float = 0.0
    layout_similarity_to_prev: float = 1.0  # 1.0 = identical layout
    has_date_header: bool = False
    date_header_text: str = ""
    is_scanned: bool = False
    raw_text: str = ""
    dominant_font: str = ""
    dominant_font_size: float = 0.0
    word_count: int = 0


# --- Boundary Detection ---

class BoundaryDecision(BaseModel):
    """Decision about whether a page transition is a document boundary."""
    page_index: int  # The page that starts a new document
    score: float
    is_boundary: bool
    reasons: list[str] = []
    verifier_agreed: Optional[bool] = None
    verifier_reason: Optional[str] = None


# --- Table Data ---

class ExtractedTable(BaseModel):
    """A single extracted table from a document instance."""
    table_id: str
    page_range: list[int]
    spans_multiple_pages: bool = False
    headers: list[str] = []
    rows: list[list[str]] = []
    extraction_method: str = "pdfplumber"
    verifier_flagged: bool = False
    verifier_notes: Optional[str] = None
    row_count: int = 0
    col_count: int = 0


# --- Document Instance ---

class DocumentInstance(BaseModel):
    """A single detected document within the uploaded PDF."""
    doc_instance_id: str
    key: str
    doctype_label_id: int = 0
    section: str = "uncategorized"
    order_index: int = 0
    start_page: int
    end_page: int
    page_count: int
    instance_ordinal: int = 1
    is_boundary_start: bool = True
    boundary_confidence: float = 0.0
    verifier_flagged: bool = False
    distinguishing_attribute: str = ""
    tables: list[ExtractedTable] = []
    pdf_filename: Optional[str] = None


# --- Manifest ---

class ProcessingManifest(BaseModel):
    """Full output manifest for a processed PDF."""
    upload_id: str
    source_filename: str
    total_pages: int
    documents: list[DocumentInstance] = []
    processing_time_seconds: float = 0.0
    llm_calls_made: int = 0
    llm_total_input_tokens: int = 0
    llm_total_output_tokens: int = 0
    estimated_llm_cost_usd: float = 0.0


# --- API Response Models ---

class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    total_pages: int
    message: str = "Processing started"


class DocumentListResponse(BaseModel):
    upload_id: str
    source_filename: str
    total_pages: int
    document_count: int
    documents: list[DocumentInstance]
    processing_time_seconds: float = 0.0
    llm_calls_made: int = 0
    estimated_llm_cost_usd: float = 0.0


class EfficiencyStats(BaseModel):
    """Stats for the efficiency panel."""
    total_pages: int
    document_count: int
    table_count: int
    processing_time_seconds: float
    llm_calls_made: int
    llm_total_input_tokens: int
    llm_total_output_tokens: int
    estimated_llm_cost_usd: float
    estimated_cost_at_2000_pages: float = 0.0
    pages_per_second: float = 0.0
