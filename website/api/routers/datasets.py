"""Per-dataset data endpoints."""
from fastapi import APIRouter, HTTPException, Query
from api.deps import get_db

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

DATASET_META = {
    "GSE38484": {"tissue": "whole_blood", "platform": "Illumina HT-12 V3 (GPL6947)", "n_scz": 106, "n_ctrl": 96},
    "GSE27383": {"tissue": "PBMC", "platform": "Affymetrix HG-U133+2 (GPL570)", "n_scz": 43, "n_ctrl": 29},
    "GSE21138": {"tissue": "prefrontal_cortex", "platform": "Affymetrix HG-U133+2 (GPL570)", "n_scz": 30, "n_ctrl": 29},
}


def _valid_ds(dataset_id: str):
    if dataset_id not in DATASET_META:
        raise HTTPException(404, f"Dataset {dataset_id} not found")


@router.get("")
def list_datasets():
    con = get_db()
    result = []
    for ds, meta in DATASET_META.items():
        n_de = con.execute(f"SELECT COUNT(*) FROM de_results WHERE dataset_id = '{ds}' AND padj < 0.05").fetchone()[0]
        n_mods = con.execute(f"SELECT COUNT(DISTINCT module) FROM modules WHERE dataset_id = '{ds}'").fetchone()[0]
        n_hub = con.execute(f"SELECT COUNT(*) FROM hub_genes WHERE dataset_id = '{ds}'").fetchone()[0]
        n_risk = con.execute(f"SELECT COUNT(*) FROM risk_de_overlap WHERE dataset_id = '{ds}' AND is_significant = TRUE").fetchone()[0]
        n_drugs = con.execute(f"SELECT COUNT(*) FROM drug_candidates WHERE dataset_id = '{ds}' AND min_FDR < 0.25").fetchone()[0]
        result.append({
            "dataset_id": ds,
            **meta,
            "n_de_genes": n_de,
            "n_modules": n_mods,
            "n_hub_genes": n_hub,
            "n_risk_overlaps": n_risk,
            "n_drug_candidates": n_drugs,
        })
    return result


@router.get("/{dataset_id}/de")
def get_de(
    dataset_id: str,
    limit: int = Query(100, le=500),
    padj_max: float = Query(0.05),
    sort: str = Query("padj"),
):
    _valid_ds(dataset_id)
    con = get_db()
    order = "padj ASC" if sort == "padj" else "ABS(logFC) DESC"
    rows = con.execute(f"""
        SELECT gene, logFC, mean_SCZ, mean_control, stat, pvalue, padj
        FROM de_results
        WHERE dataset_id = '{dataset_id}' AND padj <= {padj_max}
        ORDER BY {order}
        LIMIT {limit}
    """).fetchall()
    return [dict(zip(["gene","logFC","mean_SCZ","mean_control","stat","pvalue","padj"], r)) for r in rows]


@router.get("/{dataset_id}/modules")
def get_modules(dataset_id: str):
    _valid_ds(dataset_id)
    con = get_db()
    rows = con.execute(f"""
        SELECT mt.module, mt.correlation, mt.pvalue, mt.n_samples,
               COUNT(m.gene) as n_genes,
               mr.risk_genes_count, mr.fraction_risk
        FROM module_trait mt
        LEFT JOIN modules m ON mt.dataset_id = m.dataset_id AND mt.module = m.module
        LEFT JOIN module_risk_overlap mr ON mt.dataset_id = mr.dataset_id AND mt.module = mr.module
        WHERE mt.dataset_id = '{dataset_id}'
        GROUP BY mt.module, mt.correlation, mt.pvalue, mt.n_samples, mr.risk_genes_count, mr.fraction_risk
        ORDER BY ABS(mt.correlation) DESC
    """).fetchall()
    cols = ["module","correlation","pvalue","n_samples","n_genes","risk_genes_count","fraction_risk"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{dataset_id}/hub_genes")
def get_hub_genes(dataset_id: str, module: str = Query(None)):
    _valid_ds(dataset_id)
    con = get_db()
    where = f"dataset_id = '{dataset_id}'"
    if module:
        where += f" AND module = '{module}'"
    rows = con.execute(f"""
        SELECT gene, module, kME, kME_signed
        FROM hub_genes WHERE {where}
        ORDER BY kME DESC
    """).fetchall()
    return [dict(zip(["gene","module","kME","kME_signed"], r)) for r in rows]


@router.get("/{dataset_id}/risk_overlap")
def get_risk_overlap(dataset_id: str):
    _valid_ds(dataset_id)
    con = get_db()
    rows = con.execute(f"""
        SELECT gene, logFC, padj, is_significant, in_PGC3, in_family_study, source
        FROM risk_de_overlap WHERE dataset_id = '{dataset_id}'
        ORDER BY padj ASC NULLS LAST
    """).fetchall()
    return [dict(zip(["gene","logFC","padj","is_significant","in_PGC3","in_family_study","source"], r)) for r in rows]


@router.get("/{dataset_id}/pathways")
def get_pathways(
    dataset_id: str,
    library: str = Query(None),
    fdr_max: float = Query(0.05),
    limit: int = Query(50, le=200),
):
    _valid_ds(dataset_id)
    con = get_db()
    where = f"dataset_id = '{dataset_id}' AND fdr_qval <= {fdr_max}"
    if library:
        where += f" AND gene_set_library = '{library}'"
    rows = con.execute(f"""
        SELECT gene_set_library, term, ES, NES, nom_pval, fdr_qval, lead_genes
        FROM gsea_results WHERE {where}
        ORDER BY fdr_qval ASC
        LIMIT {limit}
    """).fetchall()
    cols = ["gene_set_library","term","ES","NES","nom_pval","fdr_qval","lead_genes"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{dataset_id}/cell_types")
def get_cell_types(dataset_id: str):
    _valid_ds(dataset_id)
    con = get_db()
    rows = con.execute(f"""
        SELECT cell_type, mean_score_SCZ, mean_score_ctrl, logFC, stat, pvalue, padj
        FROM cell_type_de WHERE dataset_id = '{dataset_id}'
        ORDER BY padj ASC NULLS LAST
    """).fetchall()
    cols = ["cell_type","mean_score_SCZ","mean_score_ctrl","logFC","stat","pvalue","padj"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{dataset_id}/ppi")
def get_ppi(dataset_id: str):
    _valid_ds(dataset_id)
    con = get_db()
    nodes = con.execute(f"""
        SELECT gene, degree, degree_centrality, betweenness, eigenvector, is_DE, logFC, is_hub, is_risk
        FROM ppi_nodes WHERE dataset_id = '{dataset_id}'
        ORDER BY betweenness DESC NULLS LAST
    """).fetchall()
    edges = con.execute(f"""
        SELECT gene_a, gene_b, score FROM ppi_edges WHERE dataset_id = '{dataset_id}'
    """).fetchall()
    node_cols = ["gene","degree","degree_centrality","betweenness","eigenvector","is_DE","logFC","is_hub","is_risk"]
    return {
        "nodes": [dict(zip(node_cols, r)) for r in nodes],
        "edges": [{"gene_a": r[0], "gene_b": r[1], "score": r[2]} for r in edges],
    }


@router.get("/{dataset_id}/drugs")
def get_drugs(
    dataset_id: str,
    limit: int = Query(50, le=200),
    fdr_max: float = Query(0.25),
):
    _valid_ds(dataset_id)
    con = get_db()
    rows = con.execute(f"""
        SELECT drug_name, mean_NES, min_FDR, n_libraries, best_term,
               is_known_psychiatric, is_repurposing_interest, composite_score
        FROM drug_candidates
        WHERE dataset_id = '{dataset_id}' AND min_FDR <= {fdr_max}
        ORDER BY composite_score DESC
        LIMIT {limit}
    """).fetchall()
    cols = ["drug_name","mean_NES","min_FDR","n_libraries","best_term","is_known_psychiatric","is_repurposing_interest","composite_score"]
    return [dict(zip(cols, r)) for r in rows]
