# backend/main.py
# Convenience entry point — run from rag-engine/ root:
#   python backend/main.py
#
# Or directly with uvicorn (preferred for --reload):
#   uvicorn backend.api.main:app --reload

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
