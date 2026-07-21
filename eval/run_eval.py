# eval/run_eval.py

import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

# Add backend to path so imports work from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# These imports must come after load_dotenv() — retrieval.router builds a
# module-level Groq client from GROQ_API_KEY at import time.
from datasets import Dataset  # noqa: E402
from generation.generator import generate  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)
from retrieval.router import route_and_retrieve  # noqa: E402

TEST_SET_PATH = "eval_data/test_set.json"
RESULTS_DIR = "eval/results"
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_pipeline(question: str, k: int = 5) -> dict:
    """
    Run the full RAG pipeline for one question.
    Returns the answer string and list of retrieved context strings.
    """
    retrieval_result = route_and_retrieve(
        question, simple_k=k, complex_k=max(k * 3, 15)
    )
    response = generate(
        query=question,
        chunks=retrieval_result["chunks"],
        route_taken=retrieval_result["query_type"],
    )
    contexts = [chunk["text"] for chunk in retrieval_result["chunks"]]
    return {
        "answer": response.answer,
        "contexts": contexts,
        "route": retrieval_result["query_type"],
        "latency": response.latency_ms,
    }


def build_ragas_dataset(test_set: list[dict], k: int = 5) -> tuple[Dataset, list[dict]]:
    """
    Run the pipeline on every question in the test set and collect outputs.

    Returns:
        ragas_dataset: HuggingFace Dataset ready for ragas.evaluate()
        run_log:       list of dicts with per-question metadata for the CSV
    """
    questions = []
    answers = []
    contexts = []
    ground_truth = []
    run_log = []

    total = len(test_set)
    for i, item in enumerate(test_set, 1):
        q = item["question"]
        gt = item["ground_truth"]

        print(f"[{i:02d}/{total}] Running: {q[:70]}...")

        try:
            result = run_pipeline(q, k=k)
            questions.append(q)
            answers.append(result["answer"])
            contexts.append(result["contexts"])
            ground_truth.append(gt)

            run_log.append(
                {
                    "question": q,
                    "ground_truth": gt,
                    "answer": result["answer"],
                    "route": result["route"],
                    "latency_ms": result["latency"],
                    "context_count": len(result["contexts"]),
                    "source": item.get("source", "unknown"),
                }
            )
            print(
                f"       route={result['route']} | latency={result['latency']}ms "
                f"| contexts={len(result['contexts'])}"
            )

        except Exception as e:
            print(f"       ERROR: {e}")
            # still include with empty answer so RAGAS scores this as worst case
            questions.append(q)
            answers.append("")
            contexts.append([])
            ground_truth.append(gt)
            run_log.append(
                {
                    "question": q,
                    "ground_truth": gt,
                    "answer": "",
                    "route": "error",
                    "latency_ms": 0,
                    "context_count": 0,
                    "source": item.get("source", "unknown"),
                }
            )

        # small sleep to avoid rate limits across 25 questions
        time.sleep(0.5)

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truth,
        }
    )
    return dataset, run_log


def score_dataset(dataset: Dataset) -> dict:
    """
    Run RAGAS evaluation on the dataset.
    Returns dict of metric_name -> score.
    """
    from ragas.run_config import RunConfig

    print("\nRunning RAGAS evaluation (this calls GPT internally)...")
    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            AnswerRelevancy(),
            ContextPrecision(),
            ContextRecall(),
        ],
        llm=ChatOpenAI(model="gpt-4.1-mini"),
        embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
        run_config=RunConfig(
            max_retries=5,
            max_wait=120,
            timeout=180,  # 3 minutes per metric call
            max_workers=2,  # fewer parallel calls = fewer rate limit hits
        ),
    )

    aggregated = defaultdict(list)
    for row in result.scores:
        for key, value in row.items():
            aggregated[key].append(float(value))

    return {metric: sum(values) / len(values) for metric, values in aggregated.items()}


def print_score_table(scores: dict, config: dict):
    """Print a clean table of scores and config to terminal."""
    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)
    print(
        f"Config: chunk_size={config['chunk_size']} | "
        f"overlap={config['overlap']} | k={config['k']}"
    )
    print("-" * 60)
    metrics = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]
    for metric in metrics:
        score = scores.get(metric, "N/A")
        if isinstance(score, float):
            bar = "█" * int(score * 20)
            print(f"  {metric:<25} {score:.4f}  {bar}")
        else:
            print(f"  {metric:<25} {score}")
    print("=" * 60)


def save_results(scores: dict, run_log: list[dict], config: dict, label: str):
    """Save detailed per-question results and summary scores to CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # per-question log
    log_path = os.path.join(RESULTS_DIR, f"run_{label}_{timestamp}.csv")
    if run_log:
        with open(log_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=run_log[0].keys())
            writer.writeheader()
            writer.writerows(run_log)
        print(f"\nPer-question log saved to: {log_path}")

    # summary scores
    summary_path = os.path.join(RESULTS_DIR, "summary_scores.csv")
    file_exists = os.path.exists(summary_path)
    with open(summary_path, "a", newline="") as f:
        fieldnames = [
            "timestamp",
            "label",
            "chunk_size",
            "overlap",
            "k",
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": timestamp,
                "label": label,
                "chunk_size": config["chunk_size"],
                "overlap": config["overlap"],
                "k": config["k"],
                "faithfulness": round(scores.get("faithfulness", 0), 4),
                "answer_relevancy": round(scores.get("answer_relevancy", 0), 4),
                "context_precision": round(scores.get("context_precision", 0), 4),
                "context_recall": round(scores.get("context_recall", 0), 4),
            }
        )
    print(f"Summary scores appended to: {summary_path}")


def run_evaluation(config: dict, label: str):
    """
    Full evaluation run for one configuration.
    Loads test set, runs pipeline, scores with RAGAS, saves results.
    """
    print(f"\n{'#' * 60}")
    print(f"# Evaluation run: {label}")
    print(f"# Config: {config}")
    print(f"{'#' * 60}")

    with open(TEST_SET_PATH) as f:
        test_set = json.load(f)

    print(f"\nLoaded {len(test_set)} questions from {TEST_SET_PATH}")

    dataset, run_log = build_ragas_dataset(test_set, k=config["k"])
    scores = score_dataset(dataset)
    print_score_table(scores, config)
    save_results(scores, run_log, config, label)

    return scores


if __name__ == "__main__":
    # Step 58: baseline evaluation at current defaults
    final_config = {
        "chunk_size": 512,
        "overlap": 32,
        "k": 3,
    }
    run_evaluation(final_config, label="final_winner_512_32_k3")
