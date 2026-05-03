# scripts/test_streaming.py

import sys
import time

sys.path.append(".")

from backend.generation.generator import generate_stream
from backend.generation.schema import RAGResponse
from backend.retrieval.router import route_and_retrieve

STREAMING_QUESTIONS = [
    "What are the three main phases of the DATA 606 course?",
    "What are the ethical challenges of AI in education?",
    "What is the final project due date and what deliverables are required?",
]

print("=" * 60)
print("STEP 43 & 44 — Streaming output test")
print("=" * 60)

for question in STREAMING_QUESTIONS:
    print(f"\n{'='*60}")
    print(f"Q: {question}")
    print("-" * 60)
    print("Streaming answer (tokens arriving live):\n")

    retrieval_result = route_and_retrieve(question)
    final_response = None
    token_count = 0
    stream_start = time.time()

    for event in generate_stream(
        query=question,
        chunks=retrieval_result["chunks"],
        route_taken=retrieval_result["query_type"],
    ):
        if isinstance(event, str):
            # this is a token — print immediately without newline
            print(event, end="", flush=True)
            token_count += 1
        elif isinstance(event, RAGResponse):
            # this is the final structured result
            final_response = event

    stream_duration = round((time.time() - stream_start) * 1000)

    print(f"\n\n--- Stream complete ---")
    print(f"Tokens streamed : {token_count}")
    print(f"Stream duration : {stream_duration}ms")
    print(f"Citations found : {len(final_response.citations)}")
    for c in final_response.citations:
        print(f'  [{c.label}] {c.source} p.{c.page} — "{c.chunk_text[:80].strip()}"')
    print(f"Route taken     : {final_response.route_taken}")
    print(f"Latency (total) : {final_response.latency_ms}ms")
