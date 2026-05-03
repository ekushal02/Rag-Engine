# scripts/test_retrieval.py

import sys

sys.path.append(".")

from backend.retrieval.hyde import hyde_retrieve
from backend.retrieval.retriever import retrieve

# ------------------------------------------------------------------
# Step 29: 10 hand-written questions — inspect chunks manually
# Write questions that are genuinely answerable from your documents
# ------------------------------------------------------------------
TEST_QUESTIONS = [
    # questions about sample.pdf (DATA 606 syllabus)
    "What is the final project due date for DATA 606?",
    "What percentage of the grade is based on the project success?",
    "What GitHub file naming conventions are required?",
    "What are the three main phases of the course?",
    "What is the policy on using AI tools like ChatGPT?",
    # questions about sample2.pdf (AI in education paper)
    "What are the four research trends identified in AI education?",
    "How many papers were reviewed in the study?",
    "What is the definition of adaptive learning in this paper?",
    "What challenges does AI face in education?",
    "What is the difference between feedback and reasoning in AI education?",
]

print("=" * 60)
print("STEP 29 — Manual inspection of retrieval results")
print("=" * 60)

for i, question in enumerate(TEST_QUESTIONS, 1):
    print(f"\n[Q{i}] {question}")
    print("-" * 50)
    chunks = retrieve(question, k=5)
    for j, chunk in enumerate(chunks, 1):
        print(
            f"  [{j}] {chunk['source']} p.{chunk['page_number']} "
            f"| score={chunk['relevance_score']} | dist={chunk['distance']}"
        )
        print(f"      {chunk['text'][:150].strip()}")
    print()

# ------------------------------------------------------------------
# Step 30: k experiment — which k gives best coverage without noise?
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 30 — k experiment")
print("=" * 60)

experiment_query = "What are the grading criteria and requirements?"

for k in [3, 5, 8, 10]:
    chunks = retrieve(experiment_query, k=k)
    avg_score = sum(c["relevance_score"] for c in chunks) / len(chunks)
    min_score = min(c["relevance_score"] for c in chunks)
    print(f"\nk={k}: avg_score={avg_score:.3f}, min_score={min_score:.3f}")
    for c in chunks:
        print(
            f"  {c['source']} p.{c['page_number']} score={c['relevance_score']} "
            f"| {c['text'][:80].strip()}"
        )

print("\n→ Pick the k where min_score starts dropping below 0.25")
print("→ Default recommendation: k=5 for simple, k=12-15 for complex before re-ranking")


print("\n" + "=" * 60)
print("STEP 33 — Direct vs HyDE comparison")
print("=" * 60)

COMPLEX_QUESTIONS = [
    "How does adaptive learning differ from feedback-based AI systems in education?",
    "What methodological approaches were used to analyze the research papers?",
    "Summarize the challenges facing AI integration in educational institutions",
]

for question in COMPLEX_QUESTIONS:
    print(f"\nQ: {question}")

    direct = retrieve(question, k=5)
    hyde_chunks, hypo = hyde_retrieve(question, k=5)

    direct_avg = sum(c["relevance_score"] for c in direct) / len(direct)
    hyde_avg = sum(c["relevance_score"] for c in hyde_chunks) / len(hyde_chunks)

    print(f"  Direct avg score : {direct_avg:.3f}")
    print(f"  HyDE   avg score : {hyde_avg:.3f}")
    print(f"  Winner: {'HyDE' if hyde_avg > direct_avg else 'Direct'}")
    print(f"  Hypothetical: {hypo[:120]}")
