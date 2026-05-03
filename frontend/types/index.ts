// frontend/types/index.ts
// Shared TypeScript types that mirror the FastAPI Pydantic models.
// These are the contract between the backend API and the frontend.

// ── Enums ──────────────────────────────────────────────────────────────────

export type IngestionStatus = "pending" | "done" | "error"

export type RouteType = "simple" | "complex" | "unknown"

// ── Upload ─────────────────────────────────────────────────────────────────

export interface UploadResponse {
  doc_id: string        // filename used as document identifier
  chunk_count: number   // number of chunks stored in ChromaDB
  pages: number         // number of pages extracted from the PDF
  status: IngestionStatus
}

export interface StatusResponse {
  doc_id: string
  status: IngestionStatus
  message?: string      // error message if status === "error"
}

// ── Documents ──────────────────────────────────────────────────────────────

export interface DocumentInfo {
  doc_id: string
  chunk_count: number
  status: IngestionStatus
}

export interface DocumentListResponse {
  documents: DocumentInfo[]
  total: number
}

export interface DeleteResponse {
  doc_id: string
  chunks_deleted: number
  status: "deleted" | "not_found"
}

// ── Query ──────────────────────────────────────────────────────────────────

export interface Citation {
  label: string           // "C1", "C2" etc — matches inline citations in the answer
  source: string          // original filename, e.g. "sample.pdf"
  page: number            // 1-indexed page number
  chunk_text: string      // the actual text chunk that was cited
  relevance_score: number | null  // cosine similarity score (0–1)
  rerank_score: number | null     // cross-encoder score (complex path only; negative = low confidence)
}

export interface QueryResponse {
  query: string
  answer: string
  citations: Citation[]
  route_taken: RouteType   // tells you whether HyDE+rerank was used
  latency_ms: number
  model: string
}