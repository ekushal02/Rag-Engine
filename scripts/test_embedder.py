# scripts/test_embedder.py

import sys

sys.path.append(".")

from backend.ingestion.embedder import embed_chunks

fake_chunks = [
    {"text": "The contract is effective as of January 1 2024."},
    {"text": "All parties must comply with the terms outlined in section 3."},
    {"text": "Payment is due within 30 days of invoice."},
]

embeddings = embed_chunks(fake_chunks)

print(f"Number of embeddings: {len(embeddings)}")
print(
    f"Embedding dimensions: {len(embeddings[0])}"
)  # should be 1536 for text-embedding-3-small
