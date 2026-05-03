# backend/ingestion/extractor.py

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> list[dict]:
    """
    Opens a PDF and returns a list of page dicts.
    Each dict: { page_number: int, text: str }
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        if text and len(text) > 50:  # skip blank/near-blank pages
            pages.append(
                {
                    "page_number": page_num + 1,  # 1-indexed
                    "text": text,
                }
            )

    doc.close()
    return pages
