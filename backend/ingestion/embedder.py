# backend/ingestion/embedder.py

import time

from openai import OpenAI, RateLimitError
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

client = OpenAI()

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per request; 100 is safe


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        input=texts,
        model=EMBEDDING_MODEL,
    )
    return [item.embedding for item in response.data]


def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """
    Takes list of chunk dicts, returns list of embedding vectors.
    Order is preserved — embeddings[i] corresponds to chunks[i].
    """
    texts = [c["text"] for c in chunks]
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings = _embed_batch(batch)
        all_embeddings.extend(embeddings)
        print(f"  Embedded batch {i // BATCH_SIZE + 1} ({len(batch)} chunks)")

        if i + BATCH_SIZE < len(texts):
            time.sleep(0.5)  # gentle rate-limit buffer

    return all_embeddings
