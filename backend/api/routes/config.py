# backend/api/routes/config.py
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter()


class KeyCheckResponse(BaseModel):
    openai_ok: bool
    groq_ok: bool


@router.get("/config/check", response_model=KeyCheckResponse, tags=["Config"])
async def check_keys(
    x_openai_key: Optional[str] = Header(None),
    x_groq_key: Optional[str] = Header(None),
):
    """
    Validate that the provided API keys are non-empty.
    Does NOT make a live API call — just checks presence.
    """
    return KeyCheckResponse(
        openai_ok=bool(x_openai_key and x_openai_key.startswith("sk-")),
        groq_ok=bool(x_groq_key and x_groq_key.startswith("gsk_")),
    )
