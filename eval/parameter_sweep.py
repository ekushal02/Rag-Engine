# eval/parameter_sweep.py
"""
Sweeps chunk_size x overlap x k, re-ingesting the 3 finalized source
documents for each (chunk_size, overlap) pair and running the full
RAGAS evaluation for every k value, then reports the winning config.

RESUMABILITY
------------
Three separate things are checkpointed to eval/checkpoints/sweep_state.json,
so killing this script (network drop, API rate limit, laptop sleep,
ctrl-C) and re-running `python eval/parameter_sweep.py` picks up exactly
where it left off -- no re-ingestion and no re-evaluation of anything
already finished:

  1. Which documents have been re-ingested for the CURRENT
     (chunk_size, overlap) pair (ingestion happens per-document, so a
     crash partway through re-ingesting 3 documents doesn't force you
     to redo the ones that already succeeded).
  2. Which (chunk_size, overlap, k) configs have a completed RAGAS score
     (skipped entirely on resume).
  3. Within a config that hasn't completed, run_eval.py's own
     per-question checkpoint (eval/checkpoints/pipeline_<label>.json)
     means even a crash mid-config resumes at the exact question.

Use --force to wipe all sweep checkpoints and start completely clean.

Usage:
    python eval/parameter_sweep.py
    python eval/parameter_sweep.py --sleep 15     # shorter cooldown between configs
    python eval/parameter_sweep.py --force        # ignore all checkpoints, start over
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Add backend to path so imports work from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from ingestion.pipeline import ingest_document  # noqa: E402

# Now import eval modules by adding eval/ (this file's own directory) and
# the repo root to path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checkpoint_utils import (  # noqa: E402
    CHECKPOINT_DIR,
    load_json,
    retry_with_backoff,
    save_json,
)
from run_eval import run_evaluation  # noqa: E402

# The 3 finalized source documents used for the whole evaluation corpus.
DOCUMENTS_TO_INGEST = [
    "eval_data/Subclass_500_Student_visa.pdf",
    "eval_data/Generative_Artificial_Intelligence__GenAI__in_the_research_process.pdf",
    "eval_data/AWS_Certified_Cloud_Practitioner.pdf",
]

# 2 chunk sizes x 2 overlaps x 3 k values = up to 12 configurations
# (some overlap/chunk_size combos are skipped when overlap >= chunk_size)
CHUNK_SIZES = [512, 1024]
OVERLAPS = [32, 64]
K_VALUES = [3, 5, 8]

SWEEP_STATE_PATH = CHECKPOINT_DIR / "sweep_state.json"
SWEEP_COMPLETE_PATH = CHECKPOINT_DIR / "sweep_complete.json"

DEFAULT_STATE = {
    "last_ingested": None,  # {"chunk_size":.., "overlap":.., "documents_done": [...]}
    "completed_configs": {},  # label -> {chunk_size, overlap, k, scores, avg_score}
}


@retry_with_backoff(max_retries=5, base_delay=5.0)
def _ingest_one(pdf_path: str, chunk_size: int, overlap: int) -> dict:
    return ingest_document(pdf_path, chunk_size=chunk_size, chunk_overlap=overlap)


def reingest_all(chunk_size: int, overlap: int, state: dict) -> None:
    """Re-ingest all documents with new chunking parameters. Resumable
    per-document: if a previous attempt at this exact (chunk_size,
    overlap) pair got partway through, only the remaining documents are
    (re-)ingested."""
    last = state.get("last_ingested")
    same_config = (
        last is not None
        and last.get("chunk_size") == chunk_size
        and last.get("overlap") == overlap
    )
    documents_done = set(last["documents_done"]) if same_config else set()

    if same_config and len(documents_done) == len(DOCUMENTS_TO_INGEST):
        print(
            f"\n  [checkpoint] chunk_size={chunk_size}, overlap={overlap} already fully ingested. Skipping."
        )
        return

    print(f"\n  Re-ingesting with chunk_size={chunk_size}, overlap={overlap}...")
    if documents_done:
        print(
            f"  [checkpoint] resuming ingestion: {len(documents_done)}/{len(DOCUMENTS_TO_INGEST)} documents already done"
        )

    state["last_ingested"] = {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "documents_done": sorted(documents_done),
    }
    save_json(SWEEP_STATE_PATH, state)

    for pdf_path in DOCUMENTS_TO_INGEST:
        if pdf_path in documents_done:
            print(f"    {pdf_path}: cached (already ingested for this config)")
            continue
        result = _ingest_one(pdf_path, chunk_size, overlap)
        print(f"    {result['source']}: {result['chunks']} chunks")
        documents_done.add(pdf_path)
        state["last_ingested"]["documents_done"] = sorted(documents_done)
        save_json(SWEEP_STATE_PATH, state)  # save after every document


def _avg_score(scores: dict) -> float:
    return (
        sum(
            [
                scores.get("faithfulness", 0),
                scores.get("answer_relevancy", 0),
                scores.get("context_precision", 0),
                scores.get("context_recall", 0),
            ]
        )
        / 4
    )


def _print_final_table(all_scores: list[dict]) -> dict:
    print("\n\n" + "=" * 80)
    print("PARAMETER SWEEP -- FULL RESULTS")
    print("=" * 80)
    print(
        f"{'Label':<30} {'Faith':>7} {'AnsRel':>7} "
        f"{'CtxPrec':>8} {'CtxRec':>8} {'AVG':>7}"
    )
    print("-" * 80)

    all_scores = sorted(all_scores, key=lambda x: x["avg_score"], reverse=True)
    for row in all_scores:
        print(
            f"{row['label']:<30} "
            f"{row['faithfulness']:>7.4f} "
            f"{row['answer_relevancy']:>7.4f} "
            f"{row['context_precision']:>8.4f} "
            f"{row['context_recall']:>8.4f} "
            f"{row['avg_score']:>7.4f}"
        )

    winner = all_scores[0]
    print("\n" + "=" * 80)
    print(f"WINNER: {winner['label']}")
    print(
        f"  chunk_size={winner['chunk_size']} | overlap={winner['overlap']} | k={winner['k']}"
    )
    print(f"  avg_score={winner['avg_score']:.4f}")
    print("=" * 80)
    return winner


def run_sweep(sleep_seconds: int = 30, force: bool = False):
    if force:
        for p in [SWEEP_STATE_PATH, SWEEP_COMPLETE_PATH]:
            if p.exists():
                p.unlink()
        print("[checkpoint] --force set: cleared sweep-level checkpoints.")
        print(
            "[checkpoint] Note: per-question pipeline/score checkpoints for each label are NOT"
        )
        print(
            "             cleared automatically -- delete eval/checkpoints/pipeline_*.json /"
        )
        print(
            "             scores_*.json yourself if you also want those redone from scratch."
        )

    state = load_json(SWEEP_STATE_PATH, default=None) or {
        k: v for k, v in DEFAULT_STATE.items()
    }
    if state.get("completed_configs"):
        print(
            f"[checkpoint] resuming sweep: {len(state['completed_configs'])} configuration(s) already completed."
        )

    for chunk_size in CHUNK_SIZES:
        for overlap in OVERLAPS:
            if overlap >= chunk_size:
                print(f"  Skipping overlap={overlap} >= chunk_size={chunk_size}")
                continue

            labels_for_combo = [f"cs{chunk_size}_ov{overlap}_k{k}" for k in K_VALUES]
            combo_fully_done = all(
                label in state["completed_configs"] for label in labels_for_combo
            )

            if combo_fully_done:
                print(
                    f"\n  [checkpoint] all k-values for chunk_size={chunk_size}, overlap={overlap} already scored. Skipping ingestion + eval."
                )
            else:
                reingest_all(chunk_size, overlap, state)

            for k in K_VALUES:
                config = {"chunk_size": chunk_size, "overlap": overlap, "k": k}
                label = f"cs{chunk_size}_ov{overlap}_k{k}"

                if label in state["completed_configs"]:
                    print(f"\n  [checkpoint] '{label}' already scored. Skipping.")
                    continue

                scores = run_evaluation(config, label=label)

                avg = _avg_score(scores)
                state["completed_configs"][label] = {
                    "label": label,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "k": k,
                    "faithfulness": round(scores.get("faithfulness", 0), 4),
                    "answer_relevancy": round(scores.get("answer_relevancy", 0), 4),
                    "context_precision": round(scores.get("context_precision", 0), 4),
                    "context_recall": round(scores.get("context_recall", 0), 4),
                    "avg_score": round(avg, 4),
                }
                save_json(
                    SWEEP_STATE_PATH, state
                )  # save the instant this config finishes

                print(f"  Cooling down {sleep_seconds}s between configurations...")
                time.sleep(sleep_seconds)

    all_scores = list(state["completed_configs"].values())
    winner = _print_final_table(all_scores)

    # restore best config (skip if it's already what's currently ingested)
    last = state.get("last_ingested")
    already_on_winner = (
        last is not None
        and last.get("chunk_size") == winner["chunk_size"]
        and last.get("overlap") == winner["overlap"]
        and len(last.get("documents_done", [])) == len(DOCUMENTS_TO_INGEST)
    )
    if already_on_winner:
        print(
            "\nWinning configuration is already the currently-ingested one. Nothing to restore."
        )
    else:
        print("\nRestoring best configuration...")
        reingest_all(winner["chunk_size"], winner["overlap"], state)
        print("Done. ChromaDB now contains chunks from the winning configuration.")

    completion = {
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "winner": winner,
        "num_configs_evaluated": len(all_scores),
        "results_csv": "eval/results/summary_scores.csv",
    }
    save_json(SWEEP_COMPLETE_PATH, completion)

    print("\n" + "#" * 80)
    print("# SWEEP COMPLETE")
    print("#" * 80)
    print(
        f"All {len(all_scores)} configuration(s) evaluated and ChromaDB is on the winning config."
    )
    print(f"Winner: {winner['label']}  (avg_score={winner['avg_score']:.4f})")
    print("Full comparison table: eval/results/summary_scores.csv")
    print(f"Completion marker written to: {SWEEP_COMPLETE_PATH}")
    print("#" * 80)

    return winner


def _parse_args():
    p = argparse.ArgumentParser(
        description="Sweep chunk_size/overlap/k configurations (resumable)."
    )
    p.add_argument(
        "--sleep",
        type=int,
        default=30,
        help="Cooldown in seconds between configurations.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Clear sweep-level checkpoints and start over.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_sweep(sleep_seconds=args.sleep, force=args.force)
