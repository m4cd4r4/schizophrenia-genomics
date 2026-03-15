"""
Singleton dependencies for FastAPI: DuckDB connection, ChromaDB store, Embedder.
"""
import sys
from pathlib import Path
from functools import lru_cache

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "website"))
from query.config import DUCKDB_PATH, CHROMA_PATH
from query.embed.embedder import Embedder
from query.embed.chroma_store import ChromaStore


@lru_cache(maxsize=1)
def get_db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)


@lru_cache(maxsize=1)
def get_store() -> ChromaStore:
    return ChromaStore(CHROMA_PATH)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()
