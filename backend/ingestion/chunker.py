# backend/ingestion/chunker.py

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    pages: list[dict],
    source: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 32,
) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    chunk_index = 0

    for page in pages:
        splits = splitter.split_text(page["text"])

        for split in splits:
            cleaned = split.strip()
            if len(cleaned) < 30:
                continue
            # skip near-duplicate of previous chunk
            if all_chunks and cleaned[:100] == all_chunks[-1]["text"][:100]:
                continue

            all_chunks.append(
                {
                    "chunk_index": chunk_index,
                    "source": source,
                    "page_number": page["page_number"],
                    "text": cleaned,
                    "chunk_size_chars": len(cleaned),
                    "total_chunks": 0,  # placeholder, filled below
                }
            )
            chunk_index += 1

    # fill total_chunks now that we know the final count
    total = len(all_chunks)
    for chunk in all_chunks:
        chunk["total_chunks"] = total

    return all_chunks
