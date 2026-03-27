"""
One-time index builder for the genomics RAG system.

Phase 1: Ingest all 64 CSVs into DuckDB
Phase 2: Generate natural-language chunks from data + README
Phase 3: Embed chunks and store in ChromaDB

Usage:
  python -m query.build_index --phase 1          # DuckDB only
  python -m query.build_index --phase 2          # Chunks only (print preview)
  python -m query.build_index --phase 3          # Embed + ChromaDB (requires Ollama)
  python -m query.build_index                    # All phases
  python -m query.build_index --phase 1 --fresh  # Drop and recreate DuckDB
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "website"))

from query.config import RESULTS_DIR, DUCKDB_PATH, CHROMA_PATH


def phase1_ingest(fresh: bool = False) -> None:
    """Load all CSVs into DuckDB."""
    import os
    import duckdb
    from query.ingest.csv_ingest import ingest_all, verify_counts

    schema_path = Path(__file__).parent / "ingest" / "schema.sql"

    if fresh and DUCKDB_PATH.exists():
        os.remove(DUCKDB_PATH)
        print(f"Removed {DUCKDB_PATH}")

    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute(schema_path.read_text())
    print("Schema created.")

    print("\nIngesting CSVs...")
    ingest_all(con, RESULTS_DIR, verbose=True)
    verify_counts(con)
    con.close()


def phase2_generate_chunks() -> list[dict]:
    """Generate all natural-language chunks from data + README."""
    from query.ingest.narrative_generator import generate_data_chunks
    from query.ingest.methodology_chunker import generate_methodology_chunks

    import duckdb
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)

    print("Generating data narrative chunks...")
    data_chunks = generate_data_chunks(con)
    print(f"  {len(data_chunks)} data chunks")

    con.close()

    print("Generating methodology chunks from README...")
    method_chunks = generate_methodology_chunks()
    print(f"  {len(method_chunks)} methodology chunks")

    all_chunks = data_chunks + method_chunks
    print(f"Total chunks: {len(all_chunks)}")
    return all_chunks


def phase3_embed(chunks: list[dict]) -> None:
    """Embed chunks and store in ChromaDB."""
    from query.embed.chroma_store import ChromaStore
    from query.embed.embedder import Embedder

    embedder = Embedder()
    store = ChromaStore(CHROMA_PATH)

    print(f"\nEmbedding {len(chunks)} chunks with nomic-embed-text...")
    store.upsert_chunks(chunks, embedder, verbose=True)
    print(f"ChromaDB collection size: {store.count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build genomics RAG index")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run only this phase")
    parser.add_argument("--fresh", action="store_true", help="Drop and recreate DuckDB")
    args = parser.parse_args()

    run_all = args.phase is None

    if run_all or args.phase == 1:
        print("=" * 60)
        print("PHASE 1: DuckDB ingest")
        print("=" * 60)
        phase1_ingest(fresh=args.fresh or run_all)

    chunks = []
    if run_all or args.phase == 2:
        print("\n" + "=" * 60)
        print("PHASE 2: Chunk generation")
        print("=" * 60)
        chunks = phase2_generate_chunks()

    if run_all or args.phase == 3:
        print("\n" + "=" * 60)
        print("PHASE 3: Embedding + ChromaDB")
        print("=" * 60)
        if not chunks:
            chunks = phase2_generate_chunks()
        phase3_embed(chunks)

    print("\nBuild complete.")


if __name__ == "__main__":
    main()
