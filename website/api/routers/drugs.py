"""Drug repurposing candidate endpoints."""
from fastapi import APIRouter, Query
from api.deps import get_db

router = APIRouter(prefix="/api/drugs", tags=["drugs"])


@router.get("/cross_dataset")
def get_cross_dataset_drugs(
    min_datasets: int = Query(2),
    limit: int = Query(100, le=500),
):
    con = get_db()
    rows = con.execute(f"""
        SELECT drug_name, n_datasets, mean_NES, best_FDR, is_known, is_repurpose, datasets
        FROM cross_dataset_drugs
        WHERE n_datasets >= {min_datasets}
        ORDER BY n_datasets DESC, ABS(mean_NES) DESC
        LIMIT {limit}
    """).fetchall()
    cols = ["drug_name","n_datasets","mean_NES","best_FDR","is_known","is_repurpose","datasets"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/validated")
def get_validated_antipsychotics():
    """Known psychiatric drugs recovered by our approach."""
    con = get_db()
    rows = con.execute("""
        SELECT drug_name, n_datasets, mean_NES, best_FDR, datasets
        FROM cross_dataset_drugs
        WHERE is_known = TRUE
        ORDER BY n_datasets DESC, ABS(mean_NES) DESC
    """).fetchall()
    cols = ["drug_name","n_datasets","mean_NES","best_FDR","datasets"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/candidates")
def get_repurposing_candidates():
    """Novel repurposing candidates (not currently psychiatric drugs)."""
    con = get_db()
    rows = con.execute("""
        SELECT drug_name, n_datasets, mean_NES, best_FDR, datasets
        FROM cross_dataset_drugs
        WHERE is_repurpose = TRUE AND is_known = FALSE AND n_datasets >= 2
        ORDER BY n_datasets DESC, ABS(mean_NES) DESC
        LIMIT 50
    """).fetchall()
    cols = ["drug_name","n_datasets","mean_NES","best_FDR","datasets"]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/confounding")
def get_confounding():
    """Medication confounding analysis."""
    con = get_db()
    report = con.execute("""
        SELECT dataset, confounding_risk, note FROM confounding_report
    """).fetchall()
    flagged = con.execute("""
        SELECT comparison, gene, blood_logFC, blood_padj, brain_dose_rho, brain_dose_padj, confounding_risk
        FROM blood_brain_confounding
        WHERE confounding_risk != 'low'
        ORDER BY ABS(brain_dose_rho) DESC
        LIMIT 20
    """).fetchall()
    return {
        "report": [dict(zip(["dataset","confounding_risk","note"], r)) for r in report],
        "flagged_genes": [
            dict(zip(["comparison","gene","blood_logFC","blood_padj","brain_dose_rho","brain_dose_padj","confounding_risk"], r))
            for r in flagged
        ],
    }
