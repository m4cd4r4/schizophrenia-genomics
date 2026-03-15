"""
Hybrid retriever: orchestrates SQL + vector retrieval based on query type.

Type A (GENE_LOOKUP):    SQL gene data + vector narrative chunks
Type B (DATASET_AGG):    SQL only
Type C (BIOLOGICAL):     Vector only
Type D (CROSS_EVIDENCE): SQL cross-dataset + vector synthesis chunks
"""
import sys
from pathlib import Path
from typing import Any

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import TOP_K_SQL_ROWS, TOP_K_VECTOR
from query.embed.embedder import Embedder
from query.embed.chroma_store import ChromaStore
from query.retrieve.query_classifier import Classification, QueryType, classify
from query.retrieve.sql_generator import generate_sql
from query.retrieve.vector_retriever import retrieve_chunks


def _run_sql(sql: str, con: duckdb.DuckDBPyConnection) -> list[dict] | None:
    """Execute SQL and return rows as list of dicts."""
    if not sql:
        return None
    try:
        result = con.execute(sql)
        cols = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(cols, row)) for row in rows[:TOP_K_SQL_ROWS]]
    except Exception as exc:
        return {"error": str(exc)}


def retrieve(
    query: str,
    con: duckdb.DuckDBPyConnection,
    embedder: Embedder,
    store: ChromaStore,
    dataset_id_override: str | None = None,
) -> dict[str, Any]:
    """
    Main retrieval entry point.
    Returns dict with: classification, sql, sql_results, chunks
    """
    classification = classify(query)

    # Override dataset if user specified one in the UI
    if dataset_id_override:
        classification.dataset_id = dataset_id_override

    sql = ""
    sql_method = "none"
    sql_results = None
    chunks: list[dict] = []

    qtype = classification.query_type

    if qtype in (QueryType.GENE_LOOKUP, QueryType.DATASET_AGG, QueryType.CROSS_EVIDENCE):
        sql, sql_method = generate_sql(query, classification)
        if sql:
            sql_results = _run_sql(sql, con)

    if qtype in (QueryType.GENE_LOOKUP, QueryType.BIOLOGICAL, QueryType.CROSS_EVIDENCE):
        chunks = retrieve_chunks(query, classification, embedder, store, k=TOP_K_VECTOR)

    return {
        "classification": {
            "type": classification.query_type.value,
            "dataset_id": classification.dataset_id,
            "gene": classification.gene,
            "confidence": classification.confidence,
        },
        "sql": sql,
        "sql_method": sql_method,
        "sql_results": sql_results,
        "chunks": chunks,
    }
