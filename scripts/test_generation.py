# scripts/test_generation.py

import sys

sys.path.append(".")

from backend.generation.generator import generate
from backend.retrieval.router import route_and_retrieve

# ------------------------------------------------------------------
# Step 41: 10 questions — verify citations appear, no hallucinations
# ------------------------------------------------------------------

ANSWERABLE_QUESTIONS = [
    # syllabus (sample.pdf)
    ("What is the final project due date for DATA 606?", "simple"),
    ("What percentage of the grade is based on project success?", "simple"),
    ("What GitHub file naming conventions are required?", "simple"),
    ("What are the three main phases of the DATA 606 course?", "simple"),
    ("What is the policy on using AI tools like ChatGPT?", "simple"),
    # AI education paper (sample2.pdf)
    (
        "What are the four research trends identified in the AI education review?",
        "complex",
    ),
    ("How many papers were reviewed in the study?", "simple"),
    ("What is adaptive learning according to the paper?", "complex"),
    ("What ethical challenges does AI face in education?", "complex"),
    (
        "What is the difference between feedback and reasoning in AI education systems?",
        "complex",
    ),
]

print("=" * 60)
print("STEP 41 — Citation verification (10 questions)")
print("=" * 60)

citation_counts = []
hallucination_flags = []

for question, expected_route in ANSWERABLE_QUESTIONS:
    # run full pipeline: router → retrieval → generation
    retrieval_result = route_and_retrieve(question)
    response = generate(
        query=question,
        chunks=retrieval_result["chunks"],
        route_taken=retrieval_result["query_type"],
    )

    # check 1: did citations appear in the answer?
    has_citations = len(response.citations) > 0
    citation_counts.append(len(response.citations))

    # check 2: are all cited labels valid (within range of chunks provided)?
    import re

    cited_labels = re.findall(r"\[C(\d+)\]", response.answer)
    max_valid = len(retrieval_result["chunks"])
    hallucinated = [l for l in cited_labels if int(l) > max_valid]
    hallucination_flags.append(len(hallucinated) > 0)

    response.print_pretty()
    if hallucinated:
        print(f"  ⚠ HALLUCINATED LABELS: {hallucinated} (max valid: C{max_valid})")
    else:
        print(f"  ✓ No hallucinated citations")
    if not has_citations and "cannot answer" not in response.answer.lower():
        print(f"  ⚠ NO CITATIONS in a non-refusal answer")

print(f"\n--- Summary ---")
print(f"Questions answered    : {len(ANSWERABLE_QUESTIONS)}")
print(f"Avg citations/answer  : {sum(citation_counts)/len(citation_counts):.1f}")
print(
    f"Answers with citations: {sum(1 for c in citation_counts if c > 0)}/{len(citation_counts)}"
)
print(f"Hallucinated labels   : {sum(hallucination_flags)}/{len(hallucination_flags)}")

# ------------------------------------------------------------------
# Step 42: Refusal path — questions the docs cannot answer
# ------------------------------------------------------------------

UNANSWERABLE_QUESTIONS = [
    "What is the current stock price of Apple?",
    "Who won the 2024 US presidential election?",
    "What is the best Italian restaurant in Baltimore?",
    "Explain how transformer neural networks work internally",
    "What is Kushal's GPA in undergraduate studies?",  # not in any doc
]

print(f"\n\n{'=' * 60}")
print("STEP 42 — Refusal path verification")
print("=" * 60)

refusal_phrase = "i cannot answer this question based on the provided documents"
refusal_count = 0

for question in UNANSWERABLE_QUESTIONS:
    # use direct retrieval for these — router would classify most as complex
    # but the chunks returned will be irrelevant, so LLM should still refuse
    from backend.retrieval.retriever import retrieve

    chunks = retrieve(question, k=5)
    response = generate(query=question, chunks=chunks, route_taken="simple")

    did_refuse = refusal_phrase in response.answer.lower()
    refusal_count += int(did_refuse)

    print(f"\nQ: {question}")
    print(f"  Answer   : {response.answer[:200]}")
    print(f"  Refused  : {'✓ YES' if did_refuse else '⚠ NO — check for hallucination'}")
    print(f"  Citations: {len(response.citations)}")

print(f"\n--- Refusal summary ---")
print(f"Correctly refused: {refusal_count}/{len(UNANSWERABLE_QUESTIONS)}")
print(
    f"Note: some partial refusals are acceptable if citations are from tangentially related chunks"
)
# scripts/test_generation.py — add after the summary block:

print("\n--- Known retrieval gaps (for RAGAS test set) ---")
print("Q5 (ChatGPT policy): retrieval pulls from AI paper instead of syllabus")
print("   → HyDE drifts toward general AI ethics, missing the specific syllabus chunk")
print("Q6 (four research trends): reranker deprioritizes the correct chunk")
print("   → Both are good candidates for RAGAS test set to measure improvement")
