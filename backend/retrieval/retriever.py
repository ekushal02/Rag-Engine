from ingestion.store import get_collection
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"


def embed_query(query: str, openai_key: str) -> list[float]:
    client = OpenAI(api_key=openai_key)
    response = client.embeddings.create(input=[query], model=EMBEDDING_MODEL)
    return response.data[0].embedding


def retrieve(
    query: str,
    k: int = 5,
    collection_name: str = "documents",
    source_filter: str | None = None,
    openai_key: str | None = None,
) -> list[dict]:
    import os

    key = openai_key or os.getenv("OPENAI_API_KEY")
    query_embedding = embed_query(query, key)
    collection = get_collection(collection_name)
    where = {"source": source_filter} if source_filter else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
        where=where,
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "source": meta["source"],
                "page_number": meta["page_number"],
                "chunk_index": meta["chunk_index"],
                "distance": round(dist, 4),
                "relevance_score": round(1 - dist, 4),
                "retrieved_via": "direct",
            }
        )
    return chunks
