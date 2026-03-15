"""
Generates DuckDB SQL from natural language queries.

Strategy:
1. Attempt LLM-generated SQL (Claude)
2. Fall back to template-based SQL for common patterns
3. Enforce read-only (block DROP/DELETE/UPDATE/INSERT)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import LLM_MODEL, DUCKDB_PATH
from query.retrieve.query_classifier import Classification, QueryType

_SCHEMA_SUMMARY = """
DuckDB tables for schizophrenia genomics:

de_results(dataset_id, gene, logFC, mean_SCZ, mean_control, stat, pvalue, padj)
  - Differential expression per dataset. dataset_id in {GSE38484, GSE27383, GSE21138}

meta_de(gene, mean_logFC, fisher_stat, combined_pvalue, direction_consistent, n_datasets, combined_padj)
  - Meta-analysis across all 3 datasets. direction_consistent BOOLEAN.

modules(dataset_id, gene, module, module_color)
  - WGCNA module assignments. 5000 genes per dataset.

hub_genes(dataset_id, gene, module, kME, kME_signed)
  - Top hub genes per module. kME = module membership score (0-1).

module_trait(dataset_id, module, correlation, pvalue, n_samples)
  - Module-SCZ correlation. Positive = higher in SCZ.

risk_de_overlap(dataset_id, gene, logFC, padj, is_significant, in_PGC3, in_family_study, source)
  - Risk gene overlap with DE results.

high_evidence_genes(gene, evidence_count, is_DE, is_hub, is_risk_gene, logFC, padj, module, kME, risk_source, dataset)
  - Genes supported by 2-3 lines of evidence.

gsea_results(dataset_id, gene_set_library, term, ES, NES, nom_pval, fdr_qval, fwer_pval, tag_pct, gene_pct, lead_genes)
  - GSEA results. gene_set_library in {KEGG, GO, Reactome}.

drug_candidates(dataset_id, drug_name, mean_NES, min_FDR, n_libraries, best_term, is_known_psychiatric, is_repurposing_interest, composite_score)
  - Drug repurposing candidates per dataset.

cross_dataset_drugs(drug_name, n_datasets, mean_NES, best_FDR, is_known, is_repurpose, datasets)
  - Drugs replicated in 2+ datasets.

cell_type_de(dataset_id, cell_type, mean_score_SCZ, mean_score_ctrl, logFC, stat, pvalue, padj)
  - Cell type deconvolution DE.

ppi_nodes(dataset_id, gene, degree, degree_centrality, betweenness, eigenvector, is_DE, logFC, is_hub, is_risk)
  - PPI network nodes with centrality scores.

module_preservation(ref_dataset, test_dataset, module, n_genes_ref, n_genes_common, ref_density, test_density, cor_adj, cor_kIM, Z_density, Z_cor_adj, Z_cor_kIM, Zsummary)
  - Module preservation Zsummary scores.

dose_response(gene, spearman_rho, pvalue, padj)
  - GSE21138 medication dose-response.

blood_brain_confounding(comparison, gene, blood_logFC, blood_padj, brain_dose_rho, brain_dose_padj, is_dose_responsive, confounding_risk)
  - Medication confounding cross-reference.
"""

_READ_ONLY_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)

# Template SQL for common query patterns
_TEMPLATES: dict[str, str] = {
    "count_de": "SELECT COUNT(*) as n_de FROM de_results WHERE dataset_id = '{dataset_id}' AND padj < 0.05",
    "top_de": "SELECT gene, logFC, padj FROM de_results WHERE dataset_id = '{dataset_id}' AND padj IS NOT NULL ORDER BY padj ASC LIMIT 20",
    "gene_all": """
        SELECT 'de_results' as source, dataset_id, logFC, padj FROM de_results WHERE gene = '{gene}' AND padj IS NOT NULL
        UNION ALL
        SELECT 'hub_genes', dataset_id, kME, NULL FROM hub_genes WHERE gene = '{gene}'
        UNION ALL
        SELECT 'risk_de_overlap', dataset_id, logFC, padj FROM risk_de_overlap WHERE gene = '{gene}'
    """,
    "high_evidence": "SELECT gene, evidence_count, is_DE, is_hub, is_risk_gene, logFC, padj FROM high_evidence_genes ORDER BY evidence_count DESC, padj ASC NULLS LAST LIMIT 30",
    "top_drugs_cross": "SELECT drug_name, n_datasets, mean_NES, best_FDR, is_known FROM cross_dataset_drugs ORDER BY n_datasets DESC, ABS(mean_NES) DESC LIMIT 20",
    "cell_types": "SELECT dataset_id, cell_type, logFC, padj FROM cell_type_de WHERE padj < 0.05 ORDER BY padj ASC",
}


def _validate_sql(sql: str) -> bool:
    """Block any write operations."""
    return not _READ_ONLY_PATTERN.search(sql)


def _apply_template(classification: Classification, query: str) -> str | None:
    """Try to match a template."""
    q = query.lower()

    if classification.query_type == QueryType.GENE_LOOKUP and classification.gene:
        return _TEMPLATES["gene_all"].format(gene=classification.gene)

    if classification.query_type == QueryType.DATASET_AGG:
        if "how many" in q and "de" in q and classification.dataset_id:
            return _TEMPLATES["count_de"].format(dataset_id=classification.dataset_id)
        if ("top" in q or "most significant" in q) and classification.dataset_id:
            return _TEMPLATES["top_de"].format(dataset_id=classification.dataset_id)

    if "high-evidence" in q or "high evidence" in q:
        return _TEMPLATES["high_evidence"]

    if "drug" in q and ("across" in q or "replicate" in q or "cross" in q):
        return _TEMPLATES["top_drugs_cross"]

    if "cell type" in q or "immune cell" in q:
        return _TEMPLATES["cell_types"]

    return None


def generate_sql(
    query: str,
    classification: Classification,
    use_llm: bool = True,
) -> tuple[str, str]:
    """
    Generate SQL for a query.
    Returns (sql, method) where method is 'llm', 'template', or 'none'.
    """
    # Try template first for efficiency
    template_sql = _apply_template(classification, query)
    if template_sql:
        return template_sql.strip(), "template"

    if not use_llm:
        return "", "none"

    # LLM-generated SQL
    try:
        import anthropic
        client = anthropic.Anthropic()

        dataset_hint = f"\nThe user is asking about dataset {classification.dataset_id}." if classification.dataset_id else ""
        gene_hint = f"\nThe user is asking about gene {classification.gene}." if classification.gene else ""

        prompt = f"""Given this DuckDB schema:
{_SCHEMA_SUMMARY}

Generate a single DuckDB SQL SELECT query to answer this question:
"{query}"{dataset_hint}{gene_hint}

Rules:
- Return ONLY the SQL query, no explanation
- Use only SELECT statements (no DROP/INSERT/UPDATE/DELETE)
- Limit results to 50 rows maximum
- All string comparisons on gene/dataset are case-sensitive (genes are uppercase)
- padj threshold for significance: < 0.05

SQL:"""

        message = client.messages.create(
            model=LLM_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        sql = message.content[0].text.strip()

        # Strip markdown code blocks if present
        sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"```\s*", "", sql)
        sql = sql.strip()

        if _validate_sql(sql):
            return sql, "llm"
        else:
            return "", "none"

    except Exception:
        return "", "none"
