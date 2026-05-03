# backend/ingestion/logger.py

import json
import os
from datetime import datetime, timezone

LOG_PATH = "./ingestion_log.json"


def log_ingestion(
    source: str,
    chunk_count: int,
    status: str = "success",
    error: str | None = None,
) -> None:
    """Appends an ingestion record to the log file."""
    record: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "chunk_count": chunk_count,
        "status": status,
    }
    if error:
        record["error"] = error

    existing: list[dict] = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            existing = json.load(f)

    existing.append(record)

    with open(LOG_PATH, "w") as f:
        json.dump(existing, f, indent=2)


def read_log() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r") as f:
        return json.load(f)
