import os
import re
import time

from groq import Groq

from .prompts import SYSTEM_PROMPT, build_prompt
from .schema import Citation, RAGResponse

GENERATION_MODEL = "llama-3.3-70b-versatile"


def parse_citations(answer: str, chunks: list[dict]) -> list[Citation]:
    pattern = re.compile(r"\[C(\d+)\]")
    seen: set[str] = set()
    unique_indices: list[int] = []
    for m in pattern.findall(answer):
        if m not in seen:
            seen.add(m)
            unique_indices.append(int(m))
    citations = []
    for idx in unique_indices:
        chunk_pos = idx - 1
        if 0 <= chunk_pos < len(chunks):
            chunk = chunks[chunk_pos]
            citations.append(
                Citation(
                    label=f"C{idx}",
                    source=chunk["source"],
                    page=chunk["page_number"],
                    chunk_text=chunk["text"],
                    relevance_score=chunk.get("relevance_score"),
                    rerank_score=chunk.get("rerank_score"),
                )
            )
    return citations


def generate(
    query: str,
    chunks: list[dict],
    route_taken: str = "unknown",
    groq_key: str | None = None,
) -> RAGResponse:
    client = Groq(api_key=groq_key or os.getenv("GROQ_API_KEY"))
    start = time.time()
    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(query, chunks)},
        ],
        temperature=0.1,
        max_tokens=1000,
    )
    answer = response.choices[0].message.content.strip()
    return RAGResponse(
        query=query,
        answer=answer,
        citations=parse_citations(answer, chunks),
        route_taken=route_taken,
        latency_ms=round((time.time() - start) * 1000),
        model=GENERATION_MODEL,
    )


def generate_stream(
    query: str,
    chunks: list[dict],
    route_taken: str = "unknown",
    groq_key: str | None = None,
):
    client = Groq(api_key=groq_key or os.getenv("GROQ_API_KEY"))
    start = time.time()
    stream = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(query, chunks)},
        ],
        temperature=0.1,
        max_tokens=1000,
        stream=True,
    )
    full_answer = ""
    for chunk_event in stream:
        if not chunk_event.choices:
            continue
        delta = chunk_event.choices[0].delta
        if delta is None or delta.content is None:
            continue
        full_answer += delta.content
        yield delta.content

    yield RAGResponse(
        query=query,
        answer=full_answer,
        citations=parse_citations(full_answer, chunks),
        route_taken=route_taken,
        latency_ms=round((time.time() - start) * 1000),
        model=GENERATION_MODEL,
    )
