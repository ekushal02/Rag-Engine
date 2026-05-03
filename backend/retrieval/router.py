# backend/retrieval/router.py

import os

from groq import Groq

from .hyde import hyde_retrieve
from .reranker import rerank
from .retriever import retrieve

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

ROUTER_SYSTEM_PROMPT = """You are a query classifier for a document QA system.

Classify the user's question as either "simple" or "complex".

Definitions:

Simple:
- Direct lookup of a single fact explicitly stated in one place
- No reasoning, sorting, or interpretation required
Examples:
- "What is the due date?"
- "Who is the instructor?"
- "What is the document number?"

Complex:
- Requires reasoning, synthesis, or interpretation across multiple pieces of information
- Includes: comparisons, summaries, multi-step reasoning, interpreting tables or lists,
  sorting or ordering (earliest, latest, first, last), resolving ambiguity
Examples:
- "Compare feedback and adaptive learning approaches"
- "Summarize the methodology"
- "What are the tradeoffs?"
- "When did they first arrive?"  ← requires sorting dates

IMPORTANT RULES:
- If the question involves time ordering, tables, or multiple entries → COMPLEX
- If the answer is not directly a single span of text → COMPLEX
- If unsure → prefer COMPLEX (better retrieval quality)

Respond with ONLY one word: simple or complex
"""


def classify_query(query: str, groq_key: str) -> str:
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=5,
    )
    result = response.choices[0].message.content.strip().lower()
    return result if result in ("simple", "complex") else "simple"


def route_and_retrieve(
    query: str,
    simple_k: int = 8,
    complex_k: int = 24,
    rerank_top_n: int = 5,
    collection_name: str = "documents",
    openai_key: str | None = None,
    groq_key: str | None = None,
) -> dict:
    _groq_key = groq_key or os.getenv("GROQ_API_KEY")
    _openai_key = openai_key or os.getenv("OPENAI_API_KEY")

    query_type = classify_query(query, _groq_key)
    print(f"  [Router] Query classified as: {query_type.upper()}")

    if query_type == "simple":
        chunks = retrieve(
            query, k=simple_k, collection_name=collection_name, openai_key=_openai_key
        )
        return {
            "query": query,
            "query_type": "simple",
            "chunks": chunks,
            "hypothetical_answer": None,
            "reranked": False,
        }

    chunks, hypothetical_answer = hyde_retrieve(
        query,
        k=complex_k,
        collection_name=collection_name,
        openai_key=_openai_key,
        groq_key=_groq_key,
    )
    reranked_chunks = rerank(query, chunks, top_n=rerank_top_n)
    return {
        "query": query,
        "query_type": "complex",
        "chunks": reranked_chunks,
        "hypothetical_answer": hypothetical_answer,
        "reranked": True,
    }
