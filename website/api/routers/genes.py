"""Gene browser and single-gene evidence endpoints."""
from fastapi import APIRouter, Query, HTTPException
from api.deps import get_db

router = APIRouter(prefix="/api/genes", tags=["genes"])


@router.get("")
def list_genes(
    limit: int = Query(100, le=500),
    sort: str = Query("combined_padj"),
    direction_consistent: bool = Query(None),
):
    con = get_db()
    where = "WHERE m.combined_padj IS NOT NULL"
    if direction_consistent is not None:
        where += f" AND m.direction_consistent = {str(direction_consistent).upper()}"
    order = "m.combined_padj ASC" if sort == "combined_padj" else "ABS(m.mean_logFC) DESC"
    rows = con.execute(f"""
        SELECT m.gene, m.mean_logFC, m.combined_padj, m.direction_consistent, m.n_datasets,
               h.evidence_count, h.is_DE, h.is_hub, h.is_risk_gene
        FROM meta_de m
        LEFT JOIN high_evidence_genes h ON m.gene = h.gene
        {where}
        ORDER BY {order}
        LIMIT {limit}
    """).fetchall()
    cols = ["gene","mean_logFC","combined_padj","direction_consistent","n_datasets",
            "evidence_count","is_DE","is_hub","is_risk_gene"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{gene}")
def get_gene(gene: str):
    gene = gene.upper()
    con = get_db()

    # DE results across all datasets
    de = con.execute(f"""
        SELECT dataset_id, logFC, mean_SCZ, mean_control, stat, pvalue, padj
        FROM de_results WHERE gene = '{gene}'
        ORDER BY dataset_id
    """).fetchall()

    # Meta
    meta = con.execute(f"""
        SELECT mean_logFC, fisher_stat, combined_pvalue, direction_consistent, n_datasets, combined_padj
        FROM meta_de WHERE gene = '{gene}'
    """).fetchone()

    # Hub gene
    hubs = con.execute(f"""
        SELECT dataset_id, module, kME, kME_signed FROM hub_genes WHERE gene = '{gene}'
    """).fetchall()

    # Module membership
    modules = con.execute(f"""
        SELECT dataset_id, module, module_color FROM modules WHERE gene = '{gene}'
    """).fetchall()

    # Risk
    risk = con.execute(f"""
        SELECT dataset_id, logFC, padj, is_significant, in_PGC3, in_family_study, source
        FROM risk_de_overlap WHERE gene = '{gene}'
    """).fetchall()

    # High evidence
    high_ev = con.execute(f"""
        SELECT evidence_count, is_DE, is_hub, is_risk_gene, logFC, padj, module, kME, risk_source, dataset
        FROM high_evidence_genes WHERE gene = '{gene}'
    """).fetchone()

    # PPI neighbors
    ppi_neighbors = con.execute(f"""
        SELECT e.gene_a, e.gene_b, e.score,
               CASE WHEN e.gene_a = '{gene}' THEN e.gene_b ELSE e.gene_a END as neighbor
        FROM ppi_edges e
        WHERE e.gene_a = '{gene}' OR e.gene_b = '{gene}'
        ORDER BY e.score DESC
        LIMIT 20
    """).fetchall()

    # Dose response (brain dataset)
    dose = con.execute(f"""
        SELECT spearman_rho, pvalue, padj FROM dose_response WHERE gene = '{gene}'
    """).fetchone()

    if not de and not meta:
        raise HTTPException(404, f"Gene {gene} not found in database")

    return {
        "gene": gene,
        "de_results": [
            dict(zip(["dataset_id","logFC","mean_SCZ","mean_control","stat","pvalue","padj"], r))
            for r in de
        ],
        "meta": dict(zip(["mean_logFC","fisher_stat","combined_pvalue","direction_consistent","n_datasets","combined_padj"], meta)) if meta else None,
        "hub_genes": [dict(zip(["dataset_id","module","kME","kME_signed"], r)) for r in hubs],
        "module_membership": [dict(zip(["dataset_id","module","module_color"], r)) for r in modules],
        "risk_overlap": [
            dict(zip(["dataset_id","logFC","padj","is_significant","in_PGC3","in_family_study","source"], r))
            for r in risk
        ],
        "high_evidence": dict(zip(
            ["evidence_count","is_DE","is_hub","is_risk_gene","logFC","padj","module","kME","risk_source","dataset"],
            high_ev
        )) if high_ev else None,
        "ppi_neighbors": [
            {"gene_a": r[0], "gene_b": r[1], "score": r[2], "neighbor": r[3]}
            for r in ppi_neighbors
        ],
        "dose_response": dict(zip(["spearman_rho","pvalue","padj"], dose)) if dose else None,
    }
