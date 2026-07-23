# eval/checkpoint_utils.py
"""
Shared checkpointing + retry helpers for the evaluation scripts.

Why this exists: parameter_sweep.py can take hours (18 configs x
re-ingestion x 26 questions x RAGAS scoring, all hitting Groq/OpenAI
APIs). Internet blips, API rate limits, or a laptop going to sleep
will eventually kill a run partway through. Re-running the whole sweep
from scratch every time wastes money (re-calls LLMs for work already
paid for) and time.

The fix: every unit of expensive work (one question through the RAG
pipeline, one RAGAS scoring pass, one re-ingestion of a chunking
config) is checkpointed to disk immediately after it succeeds. Simply
re-running the same command resumes from the last completed unit --
nothing more, nothing less.

All writes are atomic (write to a temp file, then os.replace) so a
crash mid-write can never leave a corrupted checkpoint behind.
"""
import functools
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Optional

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)  # atomic replace on POSIX filesystems


def load_json(path: Path, default: Any = None) -> Any:
    """Load a checkpoint file. Never raises -- a missing or corrupted
    checkpoint is treated as 'nothing done yet' rather than crashing
    the run."""
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"  [checkpoint] WARNING: could not read {path} ({e}); starting fresh for this file."
        )
        return default


def save_json(path: Path, data: Any) -> None:
    _atomic_write_json(path, data)


def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator: retries a flaky network/API call with exponential
    backoff + jitter. Use this on anything that talks to Groq, OpenAI,
    or RAGAS's internal LLM calls.

    After max_retries is exhausted, the original exception is
    re-raised. Whatever checkpoint state was already saved by the
    caller (e.g. earlier questions in the loop) is left untouched --
    just re-run the script to pick up from there.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        break
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay += random.uniform(0, delay * 0.25)
                    print(
                        f"  [retry] {func.__name__} failed (attempt {attempt}/{max_retries}): "
                        f"{type(e).__name__}: {e}"
                    )
                    print(f"  [retry] backing off {delay:.1f}s before retrying...")
                    time.sleep(delay)
            print(
                f"  [retry] {func.__name__} exhausted {max_retries} retries and gave up.\n"
                f"  [retry] Nothing already checkpointed was lost -- just re-run the same "
                f"command to resume from here."
            )
            raise last_exc

        return wrapper

    return decorator


def question_key(index: int, question: str) -> str:
    """Stable per-question checkpoint key. Folding a short hash of the
    question text into the key means that if you ever edit test_set.json
    (reword a question, swap it out), the stale cached answer at that
    index is automatically invalidated instead of silently reused."""
    import hashlib

    h = hashlib.md5(question.encode("utf-8")).hexdigest()[:8]
    return f"{index:03d}_{h}"
