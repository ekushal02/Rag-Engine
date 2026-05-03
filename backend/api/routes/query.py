# backend/api/routes/query.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from generation.generator import generate, generate_stream
from generation.schema import RAGResponse
from retrieval.retriever import retrieve
from retrieval.router import route_and_retrieve

from ..dependencies import resolve_groq_key, resolve_openai_key
from ..models import CitationOut, QueryRequest, QueryResponse, RouteType

router = APIRouter()


def _build_query_response(response: RAGResponse) -> QueryResponse:
    return QueryResponse(
        query=response.query,
        answer=response.answer,
        citations=[
            CitationOut(
                label=c.label,
                source=c.source,
                page=c.page,
                chunk_text=c.chunk_text,
                relevance_score=c.relevance_score,
                rerank_score=c.rerank_score,
            )
            for c in response.citations
        ],
        route_taken=(
            RouteType(response.route_taken)
            if response.route_taken in RouteType._value2member_map_
            else RouteType.unknown
        ),
        latency_ms=response.latency_ms,
        model=response.model,
    )


@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_documents(
    request: QueryRequest,
    openai_key: str = Depends(resolve_openai_key),
    groq_key: str = Depends(resolve_groq_key),
):
    try:
        retrieval_result = route_and_retrieve(
            query=request.question,
            simple_k=request.k,
            complex_k=max(request.k * 3, 15),
            openai_key=openai_key,
            groq_key=groq_key,
        )
        if request.doc_id:
            source_filtered = [
                c for c in retrieval_result["chunks"] if c["source"] == request.doc_id
            ]
            if not source_filtered:
                source_filtered = retrieve(
                    query=request.question,
                    k=request.k,
                    source_filter=request.doc_id,
                    openai_key=openai_key,
                )
            retrieval_result["chunks"] = source_filtered

        response = generate(
            query=request.question,
            chunks=retrieval_result["chunks"],
            route_taken=retrieval_result["query_type"],
            groq_key=groq_key,
        )
        return _build_query_response(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/stream", tags=["Query"])
async def query_stream(
    question: str = Query(..., min_length=3),
    doc_id: str = Query(None),
    k: int = Query(5, ge=1, le=20),
    openai_key: str = Depends(resolve_openai_key),
    groq_key: str = Depends(resolve_groq_key),
):
    async def event_generator():
        try:
            retrieval_result = route_and_retrieve(
                query=question,
                simple_k=k,
                complex_k=max(k * 3, 15),
                openai_key=openai_key,
                groq_key=groq_key,
            )
            if doc_id:
                source_filtered = [
                    c for c in retrieval_result["chunks"] if c["source"] == doc_id
                ]
                if not source_filtered:
                    source_filtered = retrieve(
                        query=question,
                        k=k,
                        source_filter=doc_id,
                        openai_key=openai_key,
                    )
                retrieval_result["chunks"] = source_filtered

            for event in generate_stream(
                query=question,
                chunks=retrieval_result["chunks"],
                route_taken=retrieval_result["query_type"],
                groq_key=groq_key,
            ):
                if isinstance(event, str):
                    yield f"data: {event.replace(chr(10), chr(92)+'n')}\n\n"
                elif isinstance(event, RAGResponse):
                    final = _build_query_response(event)
                    yield f"event: done\ndata: {final.model_dump_json()}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
