"""GSEA pathway and module enrichment endpoints."""
from fastapi import APIRouter, Query
from api.deps import get_db

router = APIRouter(prefix="/api/pathways", tags=["pathways"])


@router.get("/gsea")
def get_gsea(
    dataset_id: str = Query(None),
    library: str = Query(None),
    fdr_max: float = Query(0.05),
    limit: int = Query(100, le=500),
):
    con = get_db()
    conditions = [f"fdr_qval <= {fdr_max}"]
    if dataset_id:
        conditions.append(f"dataset_id = '{dataset_id}'")
    if library:
        conditions.append(f"gene_set_library = '{library}'")
    where = " AND ".join(conditions)
    rows = con.execute(f"""
        SELECT dataset_id, gene_set_library, term, ES, NES, nom_pval, fdr_qval, lead_genes
        FROM gsea_results WHERE {where}
        ORDER BY fdr_qval ASC
        LIMIT {limit}
    """).fetchall()
    cols = ["dataset_id","gene_set_library","term","ES","NES","nom_pval","fdr_qval","lead_genes"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/scz_specific")
def get_scz_pathways(fdr_max: float = Query(0.25)):
    con = get_db()
    rows = con.execute(f"""
        SELECT term, gene_set, NES, FDR, pvalue, n_genes
        FROM scz_pathway_enrichment
        WHERE FDR <= {fdr_max}
        ORDER BY ABS(NES) DESC
    """).fetchall()
    cols = ["term","gene_set","NES","FDR","pvalue","n_genes"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/modules")
def get_module_enrichment(
    dataset_id: str = Query(None),
    module: str = Query(None),
    limit: int = Query(50, le=200),
):
    con = get_db()
    conditions = ["adjusted_pvalue < 0.05"]
    if dataset_id:
        conditions.append(f"dataset_id = '{dataset_id}'")
    if module:
        conditions.append(f"module = '{module}'")
    where = " AND ".join(conditions)
    rows = con.execute(f"""
        SELECT dataset_id, gene_set, term, overlap, pvalue, adjusted_pvalue, odds_ratio, combined_score, module
        FROM module_enrichment WHERE {where}
        ORDER BY combined_score DESC
        LIMIT {limit}
    """).fetchall()
    cols = ["dataset_id","gene_set","term","overlap","pvalue","adjusted_pvalue","odds_ratio","combined_score","module"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/preservation")
def get_preservation():
    con = get_db()
    rows = con.execute("""
        SELECT ref_dataset, test_dataset, module, n_genes_ref, n_genes_common,
               Zsummary, Z_density, Z_cor_adj
        FROM module_preservation
        ORDER BY Zsummary DESC
    """).fetchall()
    cols = ["ref_dataset","test_dataset","module","n_genes_ref","n_genes_common","Zsummary","Z_density","Z_cor_adj"]
    return [dict(zip(cols, r)) for r in rows]
