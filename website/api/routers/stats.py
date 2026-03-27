"""Overview statistics for the home page."""
from fastapi import APIRouter
from api.deps import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats():
    con = get_db()

    n_genes_tested = con.execute("SELECT COUNT(DISTINCT gene) FROM de_results").fetchone()[0]
    n_meta_sig = con.execute("SELECT COUNT(*) FROM meta_de WHERE combined_padj < 0.05").fetchone()[0]
    n_high_ev = con.execute("SELECT COUNT(*) FROM high_evidence_genes").fetchone()[0]
    n_drug_candidates = con.execute("SELECT COUNT(DISTINCT drug_name) FROM cross_dataset_drugs WHERE n_datasets >= 2").fetchone()[0]
    n_preserved = con.execute("SELECT COUNT(*) FROM module_preservation WHERE Zsummary > 10").fetchone()[0]
    n_antipsychotics = con.execute(
        "SELECT COUNT(DISTINCT drug_name) FROM cross_dataset_drugs WHERE is_known = TRUE AND n_datasets >= 2"
    ).fetchone()[0]

    # DE genes by dataset
    de_by_ds = con.execute("""
        SELECT dataset_id,
               COUNT(*) FILTER (WHERE padj < 0.05) as n_sig,
               COUNT(*) FILTER (WHERE padj < 0.05 AND logFC > 0) as n_up,
               COUNT(*) FILTER (WHERE padj < 0.05 AND logFC < 0) as n_down
        FROM de_results
        GROUP BY dataset_id
        ORDER BY dataset_id
    """).fetchall()

    # Top cross-dataset drugs
    top_drugs = con.execute("""
        SELECT drug_name, n_datasets, mean_NES, best_FDR, is_known, is_repurpose
        FROM cross_dataset_drugs
        ORDER BY n_datasets DESC, ABS(mean_NES) DESC
        LIMIT 15
    """).fetchall()

    return {
        "n_datasets": con.execute("SELECT COUNT(DISTINCT dataset_id) FROM de_results").fetchone()[0],
        "n_genes_tested": n_genes_tested,
        "n_meta_sig_genes": n_meta_sig,
        "n_high_evidence_genes": n_high_ev,
        "n_drug_candidates": n_drug_candidates,
        "n_preserved_modules": n_preserved,
        "n_validated_antipsychotics": n_antipsychotics,
        "n_pipeline_stages": 10,
        "de_by_dataset": [
            {"dataset_id": r[0], "n_sig": r[1], "n_up": r[2], "n_down": r[3]}
            for r in de_by_ds
        ],
        "top_cross_drugs": [
            {
                "drug_name": r[0], "n_datasets": r[1], "mean_NES": r[2],
                "best_FDR": r[3], "is_known": r[4], "is_repurpose": r[5],
            }
            for r in top_drugs
        ],
    }
