# backend/api/dependencies.py

import os
from typing import Optional

from api.models import IngestionStatus
from fastapi import Header, HTTPException

# In-memory ingestion status store
ingestion_status: dict[str, dict] = {}


def set_status(
    doc_id: str, status: IngestionStatus, message: str | None = None
) -> None:
    ingestion_status[doc_id] = {"status": status, "message": message}


def get_status(doc_id: str) -> dict | None:
    return ingestion_status.get(doc_id)


def resolve_openai_key(x_openai_key: Optional[str] = Header(None)) -> str:
    """
    Use the key from the request header if provided,
    otherwise fall back to the server environment variable.
    Raises 401 if neither is available.
    """
    key = x_openai_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=401,
            detail="No OpenAI API key provided. Pass X-OpenAI-Key header or set OPENAI_API_KEY on the server.",
        )
    return key


def resolve_groq_key(x_groq_key: Optional[str] = Header(None)) -> str:
    """
    Use the key from the request header if provided,
    otherwise fall back to the server environment variable.
    """
    key = x_groq_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise HTTPException(
            status_code=401,
            detail="No Groq API key provided. Pass X-Groq-Key header or set GROQ_API_KEY on the server.",
        )
    return key
