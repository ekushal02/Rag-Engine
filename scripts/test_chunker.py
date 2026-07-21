# scripts/test_chunker.py

import sys

sys.path.append(".")

from backend.ingestion.chunker import chunk_text
from backend.ingestion.extractor import extract_text

pages = extract_text("eval_data/nist_sp800-145.pdf")

for chunk_size, overlap in [(256, 32), (512, 64), (1024, 128)]:
    chunks = chunk_text(
        pages, source="test.pdf", chunk_size=chunk_size, chunk_overlap=overlap
    )

    avg_len = sum(c["chunk_size_chars"] for c in chunks) / len(chunks)
    print(
        f"chunk_size={chunk_size}, overlap={overlap} → {len(chunks)} chunks, avg {avg_len:.0f} chars"
    )

print()

# Inspect a few chunks at your chosen size
chunks = chunk_text(pages, source="test.pdf", chunk_size=512, chunk_overlap=64)
for c in chunks[:3]:
    print(f"[Chunk {c['chunk_index']} | Page {c['page_number']}]")
    print(c["text"])
    print()
