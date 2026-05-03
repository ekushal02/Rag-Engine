# backend/api/routes/upload.py

import asyncio
import os
import shutil
from functools import partial

from fastapi import APIRouter, File, HTTPException, UploadFile
from ingestion.pipeline import ingest_document

from ..dependencies import get_status, set_status
from ..models import IngestionStatus, StatusResponse, UploadResponse

router = APIRouter()

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF document for ingestion",
    description=(
        "Accepts a PDF file, runs the full ingestion pipeline "
        "(extract → chunk → embed → store), and returns the document ID and chunk count."
    ),
)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = file.filename
    set_status(doc_id, IngestionStatus.pending)

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        set_status(doc_id, IngestionStatus.error, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # Run blocking ingestion in a thread pool so the event loop stays free.
        # asyncio.get_running_loop() is the correct API in Python 3.10+.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, partial(ingest_document, save_path))
        set_status(doc_id, IngestionStatus.done)
        return UploadResponse(
            doc_id=result["source"],
            chunk_count=result["chunks"],
            pages=result["pages"],
            status=IngestionStatus.done,
        )
    except Exception as e:
        set_status(doc_id, IngestionStatus.error, str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.get(
    "/status/{doc_id}",
    response_model=StatusResponse,
    summary="Get ingestion status for a document",
)
async def get_ingestion_status(doc_id: str):
    record = get_status(doc_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No record found for doc_id '{doc_id}'. Upload the document first.",
        )
    return StatusResponse(
        doc_id=doc_id,
        status=record["status"],
        message=record.get("message"),
    )
