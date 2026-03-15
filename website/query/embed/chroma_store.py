"""
ChromaDB persistent store with MMR (Maximal Marginal Relevance) reranking.
"""
import sys
import hashlib
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import CHROMA_PATH, CHROMA_COLLECTION, TOP_K_VECTOR, MMR_LAMBDA


def _chunk_id(text: str, source: str) -> str:
    """Deterministic chunk ID from content hash."""
    return hashlib.sha256(f"{source}:{text[:100]}".encode()).hexdigest()[:16]


def _mmr(
    query_emb: list[float],
    candidate_embs: list[list[float]],
    candidates: list[dict],
    k: int,
    lambda_param: float,
) -> list[dict]:
    """
    Maximal Marginal Relevance reranking.
    Balances relevance to query with diversity among selected results.
    """
    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    query_sims = [cosine(query_emb, e) for e in candidate_embs]
    selected = []
    selected_embs = []
    remaining = list(range(len(candidates)))

    for _ in range(min(k, len(candidates))):
        best_score = -float("inf")
        best_idx = -1

        for i in remaining:
            relevance = query_sims[i]
            if selected_embs:
                redundancy = max(cosine(candidate_embs[i], s) for s in selected_embs)
            else:
                redundancy = 0.0
            score = lambda_param * relevance - (1 - lambda_param) * redundancy
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0:
            selected.append(candidates[best_idx])
            selected_embs.append(candidate_embs[best_idx])
            remaining.remove(best_idx)

    return selected


class ChromaStore:
    def __init__(self, path: Path = CHROMA_PATH, collection: str = CHROMA_COLLECTION):
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        chunks: list[dict],
        embedder: Any,
        verbose: bool = False,
        batch_size: int = 50,
    ) -> None:
        """Embed and upsert chunks into ChromaDB."""
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            texts = [c["text"] for c in batch]
            metas = [c["metadata"] for c in batch]
            ids = [_chunk_id(c["text"], c["metadata"].get("source", "")) for c in batch]

            if verbose:
                print(f"  Embedding batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}...")

            embeddings = embedder.embed_batch(texts)

            self._col.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metas,
            )

    def search(
        self,
        query_text: str,
        query_embedding: list[float],
        k: int = TOP_K_VECTOR,
        dataset_id: str | None = None,
        category: str | None = None,
        mmr: bool = True,
        mmr_lambda: float = MMR_LAMBDA,
    ) -> list[dict]:
        """
        Search ChromaDB with optional MMR reranking.
        Returns list of dicts with text, metadata, score.
        """
        where: dict = {}
        if dataset_id and category:
            where = {"$and": [
                {"dataset_id": {"$eq": dataset_id}},
                {"category": {"$eq": category}},
            ]}
        elif dataset_id:
            where = {"dataset_id": {"$eq": dataset_id}}
        elif category:
            where = {"category": {"$eq": category}}

        # Fetch more candidates for MMR
        fetch_k = min(k * 3, 50) if mmr else k

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": fetch_k,
            "include": ["documents", "metadatas", "distances", "embeddings"],
        }
        if where:
            query_kwargs["where"] = where

        results = self._col.query(**query_kwargs)

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
        embeddings = results["embeddings"][0]

        candidates = [
            {
                "text": doc,
                "metadata": meta,
                "score": 1 - dist,  # cosine distance -> similarity
            }
            for doc, meta, dist in zip(docs, metas, distances)
        ]

        if not mmr or len(candidates) <= k:
            return candidates[:k]

        # MMR reranking
        reranked = _mmr(query_embedding, embeddings, candidates, k, mmr_lambda)
        return reranked

    def count(self) -> int:
        return self._col.count()

    def delete_collection(self) -> None:
        self._client.delete_collection(CHROMA_COLLECTION)
