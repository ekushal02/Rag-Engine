# backend/api/routes/documents.py

from fastapi import APIRouter
from ingestion.store import delete_document, get_collection, list_documents

from ..dependencies import ingestion_status, set_status
from ..models import (DeleteResponse, DocumentInfo, DocumentListResponse,
                      IngestionStatus)

router = APIRouter()


def _get_chunk_count(doc_id: str) -> int:
    """Query ChromaDB for the number of chunks belonging to this document."""
    try:
        collection = get_collection()
        results = collection.get(where={"source": doc_id})
        return len(results["ids"])
    except Exception:
        return 0


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all ingested documents",
    description=(
        "Returns all documents currently stored in ChromaDB "
        "with their chunk counts and ingestion status."
    ),
)
async def list_all_documents():
    doc_names = list_documents()

    documents = []
    for doc_id in doc_names:
        status_record = ingestion_status.get(doc_id)
        status = (
            IngestionStatus(status_record["status"])
            if status_record
            else IngestionStatus.done  # present in ChromaDB = ingestion succeeded
        )
        documents.append(
            DocumentInfo(
                doc_id=doc_id,
                chunk_count=_get_chunk_count(doc_id),
                status=status,
            )
        )

    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete(
    "/documents/{doc_id}",
    response_model=DeleteResponse,
    summary="Delete a document and all its chunks",
    description=(
        "Removes all ChromaDB chunks for the given document. "
        "The doc_id is the filename (e.g. 'contract.pdf')."
    ),
)
async def delete_document_endpoint(doc_id: str):
    chunks_deleted = delete_document(doc_id)

    if doc_id in ingestion_status:
        del ingestion_status[doc_id]

    return DeleteResponse(
        doc_id=doc_id,
        chunks_deleted=chunks_deleted,
        status="deleted" if chunks_deleted > 0 else "not_found",
    )
