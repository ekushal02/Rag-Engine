# eval/parameter_sweep.py

import sys
import time
from pathlib import Path

# Add backend to path so imports work from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from ingestion.pipeline import ingest_document

# Now import eval module by adding its parent (repo root) to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.run_eval import run_evaluation

DOCUMENTS_TO_INGEST = [
    "eval_data/sample.pdf",
    "eval_data/sample2.pdf",
    "eval_data/nist_sp800-145.pdf",
]

# 3 chunk sizes × 2 overlaps × 3 k values = 18 configurations
CHUNK_SIZES = [512, 1024]
OVERLAPS = [32, 64]
K_VALUES = [3, 5, 8]

# note: overlap must be less than chunk_size — validated below


def reingest_all(chunk_size: int, overlap: int):
    """Re-ingest all documents with new chunking parameters."""
    print(f"\n  Re-ingesting with chunk_size={chunk_size}, overlap={overlap}...")
    for pdf_path in DOCUMENTS_TO_INGEST:
        result = ingest_document(
            pdf_path,
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )
        print(f"    {result['source']}: {result['chunks']} chunks")


def run_sweep():
    all_scores = []

    for chunk_size in CHUNK_SIZES:
        for overlap in OVERLAPS:
            if overlap >= chunk_size:
                print(f"  Skipping overlap={overlap} >= chunk_size={chunk_size}")
                continue

            # re-ingest with this chunk/overlap combo
            reingest_all(chunk_size, overlap)

            for k in K_VALUES:
                config = {
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "k": k,
                }
                label = f"cs{chunk_size}_ov{overlap}_k{k}"

                scores = run_evaluation(config, label=label)
                print("  Cooling down 30s between configurations...")
                time.sleep(30)

                avg = (
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

                all_scores.append(
                    {
                        "label": label,
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "k": k,
                        "faithfulness": round(scores.get("faithfulness", 0), 4),
                        "answer_relevancy": round(scores.get("answer_relevancy", 0), 4),
                        "context_precision": round(
                            scores.get("context_precision", 0), 4
                        ),
                        "context_recall": round(scores.get("context_recall", 0), 4),
                        "avg_score": round(avg, 4),
                    }
                )

                # small pause between runs
                time.sleep(2)

    # print final comparison table
    print("\n\n" + "=" * 80)
    print("PARAMETER SWEEP — FULL RESULTS")
    print("=" * 80)
    print(
        f"{'Label':<30} {'Faith':>7} {'AnsRel':>7} "
        f"{'CtxPrec':>8} {'CtxRec':>8} {'AVG':>7}"
    )
    print("-" * 80)

    all_scores.sort(key=lambda x: x["avg_score"], reverse=True)
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

    # restore best config
    print("\nRestoring best configuration...")
    reingest_all(winner["chunk_size"], winner["overlap"])
    print("Done. ChromaDB now contains chunks from the winning configuration.")

    return winner


if __name__ == "__main__":
    winner = run_sweep()
