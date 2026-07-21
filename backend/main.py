# backend/main.py
# Convenience entry point — run from rag-engine/ root:
#   python backend/main.py
#
# Or directly with uvicorn (preferred for --reload), run from backend/:
#   cd backend && uvicorn api.main:app --reload
#
# Internal modules (api/, ingestion/, retrieval/, generation/) use bare
# imports (e.g. "from ingestion.store import ...") that only resolve when
# backend/ itself is on sys.path and is the working directory — not the
# repo root. So this entry point chdirs into its own directory and adds
# it to sys.path before handing off to uvicorn, making `python
# backend/main.py` behave identically to `cd backend && uvicorn
# api.main:app --reload`.

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR)],
    )
