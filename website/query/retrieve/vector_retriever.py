"""
Vector retrieval from ChromaDB with dataset-aware filtering and MMR.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import TOP_K_VECTOR, MMR_LAMBDA
from query.embed.embedder import Embedder
from query.embed.chroma_store import ChromaStore
from query.retrieve.query_classifier import Classification, QueryType


def retrieve_chunks(
    query: str,
    classification: Classification,
    embedder: Embedder,
    store: ChromaStore,
    k: int = TOP_K_VECTOR,
) -> list[dict]:
    """
    Embed query and retrieve relevant chunks from ChromaDB.
    Applies dataset filter when detected.
    """
    query_emb = embedder.embed(query)

    # Dataset-specific filter for single-dataset queries
    dataset_id = classification.dataset_id if classification.query_type != QueryType.CROSS_EVIDENCE else None

    # Category hint based on query type
    category = None
    if classification.query_type == QueryType.BIOLOGICAL:
        # For biological queries, don't filter by category - get diverse results
        pass

    chunks = store.search(
        query_text=query,
        query_embedding=query_emb,
        k=k,
        dataset_id=dataset_id,
        mmr=True,
        mmr_lambda=MMR_LAMBDA,
    )

    return chunks
