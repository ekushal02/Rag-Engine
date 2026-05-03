import os

from groq import Groq
from ingestion.store import get_collection

from .retriever import embed_query

HYDE_SYSTEM_PROMPT = (
    "You are a helpful assistant. Given a question, write a single paragraph "
    "that directly answers the question as if you were writing a relevant document excerpt. "
    "Be specific and factual. Do not say 'I' or reference yourself. "
    "Write only the answer paragraph, nothing else."
)


def generate_hypothetical_answer(query: str, groq_key: str) -> str:
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": HYDE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {query}"},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def hyde_retrieve(
    query: str,
    k: int = 15,
    collection_name: str = "documents",
    openai_key: str | None = None,
    groq_key: str | None = None,
) -> tuple[list[dict], str]:
    _groq_key = groq_key or os.getenv("GROQ_API_KEY")
    _openai_key = openai_key or os.getenv("OPENAI_API_KEY")

    hypothetical_answer = generate_hypothetical_answer(query, _groq_key)
    print(f"  [HyDE] Hypothetical: {hypothetical_answer[:100]}...")

    hypo_embedding = embed_query(hypothetical_answer, _openai_key)
    collection = get_collection(collection_name)
    results = collection.query(
        query_embeddings=[hypo_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "source": meta["source"],
                "page_number": meta["page_number"],
                "chunk_index": meta["chunk_index"],
                "distance": round(dist, 4),
                "relevance_score": round(1 - dist, 4),
                "retrieved_via": "hyde",
            }
        )
    return chunks, hypothetical_answer
