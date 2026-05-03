# scripts/test_router.py

import sys

sys.path.append(".")

from backend.retrieval.router import route_and_retrieve

SIMPLE_QUERIES = [
    "What is the due date for the final project?",
    "Who is the course instructor?",
    "What percentage of the grade is punctuality?",
]

COMPLEX_QUERIES = [
    "Compare the feedback and adaptive learning approaches described in the AI education paper",
    "What methodological steps were used to select and screen papers for the review?",
    "Summarize the challenges and future research directions for AI in education",
]

print("=" * 60)
print("SIMPLE QUERY ROUTING")
print("=" * 60)

for query in SIMPLE_QUERIES:
    print(f"\nQ: {query}")
    result = route_and_retrieve(query)
    print(f"  Path: {result['query_type']} | {len(result['chunks'])} chunks returned")
    for c in result["chunks"][:2]:
        print(f"  → {c['source']} p.{c['page_number']} score={c['relevance_score']}")
        print(f"     {c['text'][:100].strip()}")

print("\n" + "=" * 60)
print("COMPLEX QUERY ROUTING")
print("=" * 60)

for query in COMPLEX_QUERIES:
    print(f"\nQ: {query}")
    result = route_and_retrieve(query)
    print(f"  Path: {result['query_type']} | reranked={result['reranked']}")
    print(
        f"  Hypothetical: {result['hypothetical_answer'][:100] if result['hypothetical_answer'] else 'N/A'}"
    )
    for c in result["chunks"][:2]:
        print(
            f"  → {c['source']} p.{c['page_number']} "
            f"rerank={c.get('rerank_score', 'N/A')} score={c['relevance_score']}"
        )
        print(f"     {c['text'][:100].strip()}")
