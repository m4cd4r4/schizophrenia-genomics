"""
Maps each CSV filename (in results/) to its target DuckDB table.

Each entry is a dict with:
  - table: target table name
  - dataset_id: inject this value as dataset_id column (None for global tables)
  - rename: optional column rename dict {old: new}
  - extra_cols: additional columns to inject beyond dataset_id
  - skip: if True, this file is not ingested (raw/wide-format files)
"""

DATASETS = ["GSE38484", "GSE27383", "GSE21138"]

# Build the full mapping
CSV_TABLE_MAP: list[dict] = []

for ds in DATASETS:
    # --- Per-dataset tables ---
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_de_results.csv",
        "table": "de_results",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_modules.csv",
        "table": "modules",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_module_eigengenes.csv",
        "table": "module_eigengenes",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_module_trait.csv",
        "table": "module_trait",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_hub_genes.csv",
        "table": "hub_genes",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_risk_de_overlap.csv",
        "table": "risk_de_overlap",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_module_risk_overlap.csv",
        "table": "module_risk_overlap",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_gsea_kegg.csv",
        "table": "gsea_results",
        "dataset_id": ds,
        "extra_cols": {"gene_set_library": "KEGG"},
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_gsea_go.csv",
        "table": "gsea_results",
        "dataset_id": ds,
        "extra_cols": {"gene_set_library": "GO"},
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_gsea_reactome.csv",
        "table": "gsea_results",
        "dataset_id": ds,
        "extra_cols": {"gene_set_library": "Reactome"},
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_module_enrichment.csv",
        "table": "module_enrichment",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_cell_type_de.csv",
        "table": "cell_type_de",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_ppi_node_stats.csv",
        "table": "ppi_nodes",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_ppi_edges.csv",
        "table": "ppi_edges",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_drug_perturbations.csv",
        "table": "drug_perturbations",
        "dataset_id": ds,
    })
    CSV_TABLE_MAP.append({
        "filename": f"{ds}_drug_candidates.csv",
        "table": "drug_candidates",
        "dataset_id": ds,
    })

    # Skipped: {ds}_cell_type_scores.csv  (wide per-sample matrix, not analytical)
    # Skipped: {ds}_hub_risk_genes.csv    (subset of hub_genes, not a separate table)

# --- Global / cross-dataset tables ---
CSV_TABLE_MAP.extend([
    {
        "filename": "meta_de_results.csv",
        "table": "meta_de",
        "dataset_id": None,
    },
    {
        "filename": "high_evidence_genes.csv",
        "table": "high_evidence_genes",
        "dataset_id": None,
    },
    {
        "filename": "enrichment_tests.csv",
        "table": "enrichment_tests",
        "dataset_id": None,
    },
    {
        "filename": "scz_pathway_enrichment.csv",
        "table": "scz_pathway_enrichment",
        "dataset_id": None,
    },
    {
        "filename": "cross_dataset_drug_candidates.csv",
        "table": "cross_dataset_drugs",
        "dataset_id": None,
    },
    {
        "filename": "module_preservation_GSE38484_in_GSE27383.csv",
        "table": "module_preservation",
        "dataset_id": None,
        "extra_cols": {"ref_dataset": "GSE38484", "test_dataset": "GSE27383"},
    },
    {
        "filename": "module_preservation_GSE38484_in_GSE21138.csv",
        "table": "module_preservation",
        "dataset_id": None,
        "extra_cols": {"ref_dataset": "GSE38484", "test_dataset": "GSE21138"},
    },
    {
        "filename": "GSE21138_dose_response.csv",
        "table": "dose_response",
        "dataset_id": None,
    },
    {
        "filename": "confounding_GSE38484_vs_GSE21138.csv",
        "table": "blood_brain_confounding",
        "dataset_id": None,
        "extra_cols": {"comparison": "GSE38484_vs_GSE21138"},
    },
    {
        "filename": "confounding_GSE27383_vs_GSE21138.csv",
        "table": "blood_brain_confounding",
        "dataset_id": None,
        "extra_cols": {"comparison": "GSE27383_vs_GSE21138"},
    },
    {
        "filename": "confounding_report.csv",
        "table": "confounding_report",
        "dataset_id": None,
    },
    # Legacy / superseded - skip
    # "GSE54913_de_results.csv"  (lncRNA array, not used in analysis)
])

# Quick lookup by filename
CSV_TABLE_MAP_BY_FILENAME: dict[str, dict] = {
    entry["filename"]: entry for entry in CSV_TABLE_MAP
}
