"""
Load all 64 CSV result files into DuckDB.

Handles column renaming, extra column injection (dataset_id, library tags),
and schema-to-CSV alignment for all 22 tables.
"""
import sys
from pathlib import Path
import pandas as pd
import duckdb

# Allow running standalone or imported
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "website"))

from query.config import RESULTS_DIR, DUCKDB_PATH
from query.ingest.csv_table_map import CSV_TABLE_MAP

# ---------------------------------------------------------------------------
# Column rename maps: CSV header → DuckDB column name
# ---------------------------------------------------------------------------

GSEA_RENAME = {
    "Term": "term",
    "ES": "ES",
    "NES": "NES",
    "NOM p-val": "nom_pval",
    "FDR q-val": "fdr_qval",
    "FWER p-val": "fwer_pval",
    "Tag %": "tag_pct",
    "Gene %": "gene_pct",
    "Lead_genes": "lead_genes",
}
GSEA_DROP = {"Name"}  # gseapy method label, not needed

DRUG_PERT_RENAME = {
    "Term": "term",
    "ES": "ES",
    "NES": "NES",
    "NOM p-val": "nom_pval",
    "FDR q-val": "fdr_qval",
    "FWER p-val": "fwer_pval",
    "Tag %": "tag_pct",
    "Gene %": "gene_pct",
    "Lead_genes": "lead_genes",
    "library": "library",
    "drug_name": "drug_name",
}
DRUG_PERT_DROP = {"Name"}

MODULE_ENRICH_RENAME = {
    "Gene_set": "gene_set",
    "Term": "term",
    "Overlap": "overlap",
    "P-value": "pvalue",
    "Adjusted P-value": "adjusted_pvalue",
    "Odds Ratio": "odds_ratio",
    "Combined Score": "combined_score",
    "Genes": "genes",
    "module": "module",
}
MODULE_ENRICH_DROP = {"Old P-value", "Old Adjusted P-value"}

MODULE_PRES_RENAME = {
    "module": "module",
    "n_genes_ref": "n_genes_ref",
    "n_genes_common": "n_genes_common",
    "ref_density": "ref_density",
    "test_density": "test_density",
    "cor_adj": "cor_adj",
    "cor_kIM": "cor_kIM",
    "Z.density": "Z_density",
    "Z.cor.adj": "Z_cor_adj",
    "Z.cor.kIM": "Z_cor_kIM",
    "Zsummary": "Zsummary",
}

# Tables and their special transform rules
TABLE_TRANSFORMS = {
    "gsea_results": {"rename": GSEA_RENAME, "drop": GSEA_DROP},
    "drug_perturbations": {"rename": DRUG_PERT_RENAME, "drop": DRUG_PERT_DROP},
    "module_enrichment": {"rename": MODULE_ENRICH_RENAME, "drop": MODULE_ENRICH_DROP},
    "module_preservation": {"rename": MODULE_PRES_RENAME, "drop": set()},
}


def _load_csv(filepath: Path) -> pd.DataFrame:
    """Read CSV, drop the unnamed index column if present."""
    df = pd.read_csv(filepath)
    # Drop unnamed index columns (first col often named "" or "Unnamed: 0")
    unnamed = [c for c in df.columns if c == "" or c.startswith("Unnamed:")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


def _transform(df: pd.DataFrame, table: str, entry: dict) -> pd.DataFrame:
    """Apply renames, drops, and injections for a given table."""
    transform = TABLE_TRANSFORMS.get(table, {})

    # Drop unwanted columns
    drop_cols = transform.get("drop", set())
    existing_drop = [c for c in drop_cols if c in df.columns]
    if existing_drop:
        df = df.drop(columns=existing_drop)

    # Rename columns
    rename_map = transform.get("rename", {})
    df = df.rename(columns=rename_map)

    # Inject extra_cols (e.g. gene_set_library, ref_dataset, comparison)
    for col, val in entry.get("extra_cols", {}).items():
        df[col] = val

    # Inject dataset_id if specified
    if entry.get("dataset_id") is not None:
        df["dataset_id"] = entry["dataset_id"]

    return df


def _align_to_schema(df: pd.DataFrame, table: str, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Keep only columns that exist in the target table schema, in schema order."""
    schema_cols = [
        row[0] for row in con.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table}' ORDER BY ordinal_position"
        ).fetchall()
    ]
    # No id column in schema (removed for DuckDB compatibility)

    # Keep only schema columns that are present in the DataFrame
    keep = [c for c in schema_cols if c in df.columns]
    missing = [c for c in schema_cols if c not in df.columns]
    if missing:
        # Fill missing with None
        for c in missing:
            df[c] = None

    return df[schema_cols]


def ingest_all(con: duckdb.DuckDBPyConnection, results_dir: Path, verbose: bool = True) -> dict:
    """
    Ingest all mapped CSVs into DuckDB.
    Returns dict of {table: row_count} for verification.
    """
    counts: dict[str, int] = {}
    errors: list[str] = []

    for entry in CSV_TABLE_MAP:
        filepath = results_dir / entry["filename"]
        table = entry["table"]

        if not filepath.exists():
            if verbose:
                print(f"  [SKIP] {entry['filename']} — not found")
            continue

        try:
            df = _load_csv(filepath)
            df = _transform(df, table, entry)
            df = _align_to_schema(df, table, con)

            # Register as a DuckDB relation and insert (explicit column list, skip id)
            col_list = ", ".join(df.columns)
            con.register("_ingest_tmp", df)
            con.execute(f"INSERT INTO {table} ({col_list}) SELECT * FROM _ingest_tmp")
            con.unregister("_ingest_tmp")

            rows = len(df)
            counts[entry["filename"]] = rows
            if verbose:
                ds_tag = f" [{entry['dataset_id']}]" if entry.get("dataset_id") else ""
                print(f"  [OK] {entry['filename']}{ds_tag} -> {table} ({rows:,} rows)")

        except Exception as exc:
            errors.append(f"{entry['filename']}: {exc}")
            if verbose:
                print(f"  [ERR] {entry['filename']}: {exc}")

    if errors:
        print(f"\n{len(errors)} error(s) during ingest:")
        for e in errors:
            print(f"  {e}")

    return counts


def verify_counts(con: duckdb.DuckDBPyConnection) -> None:
    """Print row counts per table."""
    tables = [
        "de_results", "meta_de", "modules", "module_eigengenes", "module_trait",
        "hub_genes", "risk_de_overlap", "module_risk_overlap", "high_evidence_genes",
        "enrichment_tests", "gsea_results", "scz_pathway_enrichment", "module_enrichment",
        "cell_type_de", "ppi_nodes", "ppi_edges", "module_preservation",
        "drug_perturbations", "drug_candidates", "cross_dataset_drugs",
        "dose_response", "blood_brain_confounding", "confounding_report",
    ]
    print("\nTable row counts:")
    total = 0
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        total += n
        print(f"  {t:<30} {n:>8,}")
    print(f"  {'TOTAL':<30} {total:>8,}")


if __name__ == "__main__":
    import os

    schema_path = Path(__file__).parent / "schema.sql"

    print(f"DuckDB: {DUCKDB_PATH}")
    print(f"Results: {RESULTS_DIR}")

    # Remove existing DB if requested
    if "--fresh" in sys.argv and DUCKDB_PATH.exists():
        os.remove(DUCKDB_PATH)
        print("Removed existing database.")

    con = duckdb.connect(str(DUCKDB_PATH))

    # Create schema
    con.execute(schema_path.read_text())
    print("Schema created.")

    # Ingest
    print("\nIngesting CSVs...")
    ingest_all(con, RESULTS_DIR, verbose=True)

    # Verify
    verify_counts(con)

    con.close()
    print("\nDone.")
