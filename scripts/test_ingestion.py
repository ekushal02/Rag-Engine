# scripts/test_ingestion.py

import sys

sys.path.append(".")

from backend.ingestion.logger import read_log
from backend.ingestion.pipeline import ingest_document
from backend.ingestion.store import get_collection, list_documents

PDF_FILES = [
    "eval_data/sample.pdf",
    "eval_data/sample2.pdf",
    "eval_data/Transcripts.pdf",
]

# --- Ingest all test documents ---
for pdf_path in PDF_FILES:
    print(f"\n{'='*50}")
    print(f"Ingesting: {pdf_path}")
    print("=" * 50)
    result = ingest_document(pdf_path)
    print(f"Done: {result}")

# --- Verify what's in ChromaDB ---
print("\n--- Documents in collection ---")
for doc in list_documents():
    print(f"  {doc}")

# --- Run a test query against the collection ---
print("\n--- Test retrieval ---")
from openai import OpenAI

client = OpenAI()

test_query = "What is the main purpose of this document?"
response = client.embeddings.create(input=[test_query], model="text-embedding-3-small")
query_embedding = response.data[0].embedding

collection = get_collection()
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3,
    include=["documents", "metadatas", "distances"],
)

for i, (doc, meta, dist) in enumerate(
    zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )
):
    print(
        f"\n[Result {i+1}] source={meta['source']} page={meta['page_number']} distance={dist:.4f}"
    )
    print(doc[:200])

# --- Print ingestion log ---
print("\n--- Ingestion log ---")
for entry in read_log():
    print(
        f"  {entry['timestamp']} | {entry['source']} | {entry['status']} | {entry['chunk_count']} chunks"
    )
