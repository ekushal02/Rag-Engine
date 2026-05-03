# backend/ingestion/pipeline.py

import os

from .chunker import chunk_text
from .embedder import embed_chunks
from .extractor import extract_text
from .logger import log_ingestion
from .store import delete_document, store_chunks


def ingest_document(
    pdf_path: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 32,
    collection_name: str = "documents",
    replace_existing: bool = True,
) -> dict:
    """
    Full ingestion pipeline: PDF → chunks → embeddings → ChromaDB.
    Returns a summary dict with keys: source, pages, chunks, status.
    """
    source = os.path.basename(pdf_path)

    try:
        if replace_existing:
            deleted = delete_document(source, collection_name)
            if deleted > 0:
                print(f"  Removed {deleted} existing chunks for '{source}'")

        print(f"[1/4] Extracting text from {source}...")
        pages = extract_text(pdf_path)
        print(f"  → {len(pages)} pages extracted")

        print(f"[2/4] Chunking (size={chunk_size}, overlap={chunk_overlap})...")
        chunks = chunk_text(
            pages,
            source=source,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        print(f"  → {len(chunks)} chunks created")

        print("[3/4] Embedding chunks...")
        embeddings = embed_chunks(chunks)
        print(f"  → {len(embeddings)} embeddings generated")

        print("[4/4] Storing in ChromaDB...")
        stored = store_chunks(chunks, embeddings, collection_name)
        print(f"  → {stored} chunks stored")

        log_ingestion(source=source, chunk_count=stored, status="success")

        return {
            "source": source,
            "pages": len(pages),
            "chunks": stored,
            "status": "success",
        }

    except Exception as e:
        log_ingestion(source=source, chunk_count=0, status="error", error=str(e))
        raise
