# backend/ingestion/store.py

import os
from pathlib import Path

import chromadb

# Anchored to this file's own location so the store resolves to the same
# physical path regardless of the process's working directory (API server
# runs from backend/, eval/test scripts run from the repo root).
CHROMA_PATH = os.getenv(
    "CHROMA_PATH", str(Path(__file__).resolve().parent / "chroma_db")
)


def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection(collection_name: str = "documents"):
    client = get_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    collection_name: str = "documents",
) -> int:
    """
    Upserts chunks + embeddings into ChromaDB.
    Returns number of chunks stored.
    """
    collection = get_collection(collection_name)

    ids = [f"{c['source']}__chunk_{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "source": c["source"],
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
            "chunk_size_chars": c["chunk_size_chars"],
            "total_chunks": c["total_chunks"],
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def delete_document(source: str, collection_name: str = "documents") -> int:
    """
    Deletes all chunks belonging to a given source document.
    Returns number of chunks deleted.
    """
    collection = get_collection(collection_name)
    results = collection.get(where={"source": source})
    ids_to_delete = results["ids"]

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)

    return len(ids_to_delete)


def list_documents(collection_name: str = "documents") -> list[str]:
    """Returns unique source document names in the collection."""
    collection = get_collection(collection_name)
    results = collection.get(include=["metadatas"])
    sources = {m["source"] for m in results["metadatas"]}
    return sorted(sources)
