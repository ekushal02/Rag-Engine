# backend/generation/schema.py

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Citation:
    """One resolved citation from the LLM's answer."""

    label: str  # "C1", "C2" — matches what appears in answer text
    source: str  # filename, e.g. "sample.pdf"
    page: int  # page number
    chunk_text: str  # the actual chunk text that was cited
    relevance_score: Optional[float] = None  # cosine similarity score
    rerank_score: Optional[float] = None  # cross-encoder score (complex path only)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RAGResponse:
    """
    Complete structured response from the RAG pipeline.

    This is the contract between generation and everything downstream
    (FastAPI endpoints, frontend, RAGAS evaluator).
    """

    query: str
    answer: str
    citations: list[Citation]
    route_taken: str  # "simple" | "complex" | "unknown"
    latency_ms: int  # total wall-clock time for the full pipeline call
    model: str  # which LLM was used

    def to_dict(self) -> dict:
        return asdict(self)

    def print_pretty(self) -> None:
        """Human-readable output for test scripts."""
        print(f"\n{'='*60}")
        print(f"Query     : {self.query}")
        print(
            f"Route     : {self.route_taken} | Latency: {self.latency_ms}ms | Model: {self.model}"
        )
        print(f"\nAnswer:\n{self.answer}")
        print(f"\nCitations ({len(self.citations)}):")
        for c in self.citations:
            print(f"  [{c.label}] {c.source} p.{c.page}")
            print(f"         Score: {c.relevance_score} | Rerank: {c.rerank_score}")
            print(f'         "{c.chunk_text[:100].strip()}"')
        print(f"{'='*60}")
