# backend/api/models.py

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ── Shared enums ──────────────────────────────────────────────────


class IngestionStatus(str, Enum):
    pending = "pending"
    done = "done"
    error = "error"


class RouteType(str, Enum):
    simple = "simple"
    complex = "complex"
    unknown = "unknown"


# ── Upload endpoint ───────────────────────────────────────────────


class UploadResponse(BaseModel):
    doc_id: str = Field(..., description="Filename used as document identifier")
    chunk_count: int = Field(..., description="Number of chunks stored in ChromaDB")
    pages: int = Field(..., description="Number of pages extracted from the PDF")
    status: IngestionStatus

    model_config = {
        "json_schema_extra": {
            "example": {
                "doc_id": "contract.pdf",
                "chunk_count": 47,
                "pages": 12,
                "status": "done",
            }
        }
    }


# ── Status endpoint ───────────────────────────────────────────────


class StatusResponse(BaseModel):
    doc_id: str
    status: IngestionStatus
    message: Optional[str] = None  # error message if status == error


# ── Query endpoint ────────────────────────────────────────────────


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="The user's question")
    doc_id: Optional[str] = Field(None, description="Restrict search to this document")
    k: Optional[int] = Field(5, ge=1, le=20, description="Number of chunks to retrieve")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What is the final project due date?",
                "doc_id": "sample.pdf",
                "k": 5,
            }
        }
    }


class CitationOut(BaseModel):
    label: str
    source: str
    page: int
    chunk_text: str
    relevance_score: Optional[float] = None
    rerank_score: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationOut]
    route_taken: RouteType
    latency_ms: int
    model: str


# ── Documents endpoint ────────────────────────────────────────────


class DocumentInfo(BaseModel):
    doc_id: str
    chunk_count: int
    status: IngestionStatus


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


# ── Delete endpoint ───────────────────────────────────────────────


class DeleteResponse(BaseModel):
    doc_id: str
    chunks_deleted: int
    status: str  # "deleted" | "not_found"
