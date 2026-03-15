"""RAG query endpoint with streaming support."""
import sys
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from api.deps import get_db, get_store, get_embedder
from api.models import QueryRequest
from query.retrieve.hybrid_retriever import retrieve
from query.synthesise.prompt_builder import build_prompt
from query.synthesise.claude_client import synthesize, synthesize_stream

router = APIRouter(prefix="/api/query", tags=["query"])


def _get_evidence_tiers(retrieval: dict) -> list[str]:
    tiers = set()
    for chunk in retrieval.get("chunks", []):
        tier = chunk.get("metadata", {}).get("evidence_tier")
        if tier:
            tiers.add(tier)
    return sorted(tiers)


@router.post("")
def run_query(request: QueryRequest):
    con = get_db()
    embedder = get_embedder()
    store = get_store()

    retrieval = retrieve(request.query, con, embedder, store, request.dataset_id)
    system_prompt, user_message = build_prompt(request.query, retrieval)

    if request.stream:
        def stream_response():
            # First yield the metadata
            meta = {
                "type": "meta",
                "classification": retrieval["classification"],
                "sql": retrieval["sql"],
                "sql_method": retrieval["sql_method"],
                "sql_results": retrieval["sql_results"],
                "chunks": [
                    {"text": c["text"][:500], "metadata": c["metadata"], "score": c.get("score", 0)}
                    for c in retrieval["chunks"]
                ],
                "evidence_tiers": _get_evidence_tiers(retrieval),
            }
            yield f"data: {json.dumps(meta)}\n\n"

            # Then stream the answer
            for token in synthesize_stream(system_prompt, user_message):
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    # Non-streaming
    answer = synthesize(system_prompt, user_message)

    return {
        "query": request.query,
        "classification": retrieval["classification"],
        "sql": retrieval["sql"],
        "sql_method": retrieval["sql_method"],
        "sql_results": retrieval["sql_results"],
        "chunks": [
            {"text": c["text"], "metadata": c["metadata"], "score": c.get("score", 0)}
            for c in retrieval["chunks"]
        ],
        "answer": answer,
        "evidence_tiers": _get_evidence_tiers(retrieval),
    }
