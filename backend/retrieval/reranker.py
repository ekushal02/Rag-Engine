# backend/retrieval/reranker.py

from sentence_transformers import CrossEncoder

# Free, runs locally, no API cost.
# Downloads ~85 MB on first run, cached after that.
MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    """Lazy-load the cross-encoder model (expensive; load once)."""
    global _model
    if _model is None:
        print("  [Reranker] Loading cross-encoder model (first time only)...")
        _model = CrossEncoder(MODEL_NAME)
    return _model


def rerank(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Re-rank chunks using a cross-encoder.

    The cross-encoder reads (query, chunk_text) pairs together —
    unlike embeddings which represent query and chunk independently.
    This gives much more accurate relevance scores.

    Takes your top-k vector results and returns the top_n most relevant.
    """
    if not chunks:
        return []

    model = get_reranker()
    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores = model.predict(pairs)

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = round(float(score), 4)

    reranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_n]
