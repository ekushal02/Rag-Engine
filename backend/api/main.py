# backend/api/main.py

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

# Validate required environment variables at startup
for var in ("OPENAI_API_KEY", "GROQ_API_KEY"):
    if not os.getenv(var):
        raise RuntimeError(f"{var} not set. Check your .env file.")

from api.routes.documents import router as documents_router
from api.routes.query import router as query_router
from api.routes.upload import router as upload_router

app = FastAPI(
    title="RAG Document Intelligence Engine",
    description=(
        "End-to-end RAG pipeline with query routing, HyDE retrieval, "
        "cross-encoder reranking, and streaming generation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(query_router)
app.include_router(documents_router)


@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok"}


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "RAG engine is running"}
