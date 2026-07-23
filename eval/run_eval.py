# eval/run_eval.py
"""
Runs the full RAG pipeline + RAGAS evaluation for ONE configuration
(chunk_size, overlap, k) against eval_data/test_set.json.

RESUMABILITY
------------
Every question's pipeline output (answer, contexts, route, latency) is
saved to eval/checkpoints/pipeline_<label>.json the moment it succeeds.
If the process dies -- network failure, Groq/OpenAI rate limit, ctrl-C,
laptop sleeps -- re-running the exact same command skips every question
already answered and only does the remaining ones.

RAGAS scoring (the GPT-4.1-mini judge calls) is itself checkpointed to
eval/checkpoints/scores_<label>.json once it completes, so re-running
after a fully-scored crash (e.g. the CSV write failed) does not re-pay
for scoring.

Usage:
    python eval/run_eval.py --label my_run --chunk-size 1024 --overlap 32 --k 8
    python eval/run_eval.py --label my_run ...        # re-run -> resumes
    python eval/run_eval.py --label my_run --force ... # ignore checkpoints, start clean
"""
import argparse
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

from checkpoint_utils import (  # noqa: E402
    CHECKPOINT_DIR,
    load_json,
    question_key,
    retry_with_backoff,
    save_json,
)

# These imports must come after load_dotenv() -- retrieval.router builds a
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


# ---------------------------------------------------------------------------
# Pipeline execution (checkpointed per-question)
# ---------------------------------------------------------------------------


@retry_with_backoff(max_retries=5, base_delay=3.0)
def run_pipeline(question: str, k: int = 5) -> dict:
    """
    Run the full RAG pipeline for one question.
    Returns the answer string and list of retrieved context strings.
    Wrapped in retry_with_backoff since this hits Groq + OpenAI embeddings.
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


def _pipeline_checkpoint_path(label: str) -> Path:
    return CHECKPOINT_DIR / f"pipeline_{label}.json"


def _scores_checkpoint_path(label: str) -> Path:
    return CHECKPOINT_DIR / f"scores_{label}.json"


def build_ragas_dataset(
    test_set: list[dict], k: int, label: str, force: bool = False
) -> tuple[Dataset, list[dict]]:
    """
    Run the pipeline on every question in the test set, resuming from
    a checkpoint if one exists. Returns:
        ragas_dataset: HuggingFace Dataset ready for ragas.evaluate()
        run_log:       list of dicts with per-question metadata for the CSV
    """
    ckpt_path = _pipeline_checkpoint_path(label)
    checkpoint = {} if force else load_json(ckpt_path, default={})
    if force and ckpt_path.exists():
        print(f"  [checkpoint] --force set: ignoring existing {ckpt_path.name}")

    total = len(test_set)
    done_count = sum(
        1
        for i in range(total)
        if question_key(i, test_set[i]["question"]) in checkpoint
    )
    if done_count:
        print(
            f"  [checkpoint] resuming: {done_count}/{total} questions already answered for '{label}'"
        )

    for i, item in enumerate(test_set, 0):
        q = item["question"]
        gt = item["ground_truth"]
        key = question_key(i, q)

        if key in checkpoint:
            print(f"[{i + 1:02d}/{total}] cached: {q[:60]}...")
            continue

        print(f"[{i + 1:02d}/{total}] Running: {q[:70]}...")

        try:
            result = run_pipeline(q, k=k)
            entry = {
                "question": q,
                "ground_truth": gt,
                "answer": result["answer"],
                "contexts": result["contexts"],
                "route": result["route"],
                "latency_ms": result["latency"],
                "source": item.get("source", "unknown"),
                "error": False,
            }
            print(
                f"       route={result['route']} | latency={result['latency']}ms "
                f"| contexts={len(result['contexts'])}"
            )
        except Exception as e:
            # Retries inside run_pipeline are already exhausted at this point.
            # Record it as an error case (worst-case RAGAS score) but DO NOT
            # crash the whole run -- keep going so later questions still get
            # a chance, and this one can be retried on the next invocation
            # since it is intentionally NOT written to the checkpoint.
            print(f"       ERROR (giving up on this question for now): {e}")
            print(
                "       This question was NOT checkpointed -- it will be retried next run."
            )
            time.sleep(1)
            continue

        checkpoint[key] = entry
        save_json(ckpt_path, checkpoint)  # save immediately -- crash-safe

        # small pause between runs to avoid rate limits
        time.sleep(0.5)

    remaining = total - sum(
        1
        for i in range(total)
        if question_key(i, test_set[i]["question"]) in checkpoint
    )
    if remaining:
        raise RuntimeError(
            f"{remaining}/{total} questions still unanswered after retries were exhausted. "
            f"Re-run this script (same --label) to resume -- completed questions are saved "
            f"in {ckpt_path}."
        )

    # Reassemble in original test-set order
    questions, answers, contexts, ground_truth, run_log = [], [], [], [], []
    for i, item in enumerate(test_set, 0):
        entry = checkpoint[question_key(i, item["question"])]
        questions.append(entry["question"])
        answers.append(entry["answer"])
        contexts.append(entry["contexts"])
        ground_truth.append(entry["ground_truth"])
        run_log.append(
            {
                "question": entry["question"],
                "ground_truth": entry["ground_truth"],
                "answer": entry["answer"],
                "route": entry["route"],
                "latency_ms": entry["latency_ms"],
                "context_count": len(entry["contexts"]),
                "source": entry["source"],
            }
        )

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truth,
        }
    )
    return dataset, run_log


# ---------------------------------------------------------------------------
# RAGAS scoring (checkpointed as a whole, since it's cheap relative to the
# pipeline calls and ragas.evaluate() already has its own internal retries)
# ---------------------------------------------------------------------------


@retry_with_backoff(max_retries=3, base_delay=5.0)
def _ragas_evaluate(dataset: Dataset) -> dict:
    from ragas.run_config import RunConfig

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


def score_dataset(dataset: Dataset, label: str, force: bool = False) -> dict:
    """Run RAGAS evaluation, resuming from checkpoint if already scored."""
    ckpt_path = _scores_checkpoint_path(label)
    if not force:
        cached = load_json(ckpt_path)
        if cached is not None:
            print(
                f"  [checkpoint] RAGAS scores already computed for '{label}', reusing cached scores."
            )
            return cached

    print("\nRunning RAGAS evaluation (this calls GPT internally)...")
    scores = _ragas_evaluate(dataset)
    save_json(ckpt_path, scores)  # save immediately once scoring succeeds
    return scores


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


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
    """Save detailed per-question results and summary scores to CSV.
    Idempotent per label -- if this label's summary row was already
    written by a previous (interrupted-then-resumed) invocation, it is
    not duplicated."""
    written_marker = CHECKPOINT_DIR / f"saved_{label}.json"
    if load_json(written_marker) is not None:
        print(
            f"  [checkpoint] Results for '{label}' were already saved to CSV in a prior run; skipping re-write."
        )
        return

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
    save_json(written_marker, {"label": label, "timestamp": timestamp})


def run_evaluation(config: dict, label: str, force: bool = False) -> dict:
    """
    Full evaluation run for one configuration.
    Loads test set, runs pipeline (resumable), scores with RAGAS
    (resumable), saves results (idempotent).
    """
    print(f"\n{'#' * 60}")
    print(f"# Evaluation run: {label}")
    print(f"# Config: {config}")
    print(f"{'#' * 60}")

    with open(TEST_SET_PATH) as f:
        test_set = json.load(f)

    print(f"\nLoaded {len(test_set)} questions from {TEST_SET_PATH}")

    dataset, run_log = build_ragas_dataset(
        test_set, k=config["k"], label=label, force=force
    )
    scores = score_dataset(dataset, label=label, force=force)
    print_score_table(scores, config)
    save_results(scores, run_log, config, label)

    return scores


def _parse_args():
    p = argparse.ArgumentParser(
        description="Run one RAGAS evaluation configuration (resumable)."
    )
    p.add_argument(
        "--label",
        default="final_winner_1024_32_k8",
        help="Unique run label (used for checkpoint + CSV filenames).",
    )
    p.add_argument("--chunk-size", type=int, default=1024)
    p.add_argument("--overlap", type=int, default=32)
    p.add_argument("--k", type=int, default=8)
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing checkpoints for this label and start clean.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    final_config = {
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "k": args.k,
    }
    run_evaluation(final_config, label=args.label, force=args.force)
