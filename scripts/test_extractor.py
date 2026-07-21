# scripts/test_extractor.py

import sys

sys.path.append(".")

from backend.ingestion.extractor import extract_text

pages = extract_text("eval_data/nist_sp800-145.pdf")

for p in pages:
    print(f"--- Page {p['page_number']} ---")
    print(p["text"][:300])  # first 300 chars only
    print()

print(f"Total pages extracted: {len(pages)}")
