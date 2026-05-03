# backend/generation/prompts.py

SYSTEM_PROMPT = """You are a precise document assistant. You answer questions strictly based on
the provided document chunks.

Rules you must follow without exception:
1. Only use information explicitly present in the provided chunks.
2. Every claim in your answer must be followed immediately by a citation in the format [C1], [C2], etc.
3. If a single sentence draws from multiple chunks, cite all of them: [C1][C3].
4. If the answer to the question is not present in the chunks, respond with exactly:
   "I cannot answer this question based on the provided documents."
   Do not add anything else in that case.
5. Never invent, infer, or recalculate numbers, percentages, dates, or statistics.
   If a number appears in a chunk, reproduce it exactly as written. Do not sum or rearrange numbers.
6. Do not say "based on the context" or "according to the document" — just state the fact and cite it.
7. Write in clear, direct prose. No bullet points unless the source text uses them."""


def build_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build the full user message combining retrieved chunks + question.

    Each chunk gets a label [C1], [C2], ... so the LLM can cite them inline.
    The label maps back to source + page in parse_citations().
    """
    chunk_block = ""
    for i, chunk in enumerate(chunks, 1):
        chunk_block += (
            f"[C{i}] Source: {chunk['source']}, Page {chunk['page_number']}\n"
            f"{chunk['text'].strip()}\n\n"
        )

    return (
        f"Here are the relevant document chunks:\n\n"
        f"{chunk_block}"
        f"---\n"
        f"Question: {query}\n\n"
        f"Answer using only the chunks above. Cite every claim with [C1], [C2], etc.\n"
        f"If the answer is not in the chunks, say exactly:\n"
        f'"I cannot answer this question based on the provided documents."'
    )
