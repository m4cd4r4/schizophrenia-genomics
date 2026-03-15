-- DuckDB schema for schizophrenia genomics pipeline results
-- 22 table types covering all 64 CSV output files

-- Per-dataset differential expression results
CREATE TABLE IF NOT EXISTS de_results (
    dataset_id  TEXT NOT NULL,
    gene        TEXT NOT NULL,
    logFC       DOUBLE,
    mean_SCZ    DOUBLE,
    mean_control DOUBLE,
    stat        DOUBLE,
    pvalue      DOUBLE,
    padj        DOUBLE
);

-- Meta-analysis across all datasets (Fisher's method)
CREATE TABLE IF NOT EXISTS meta_de (
    gene                TEXT NOT NULL,
    mean_logFC          DOUBLE,
    fisher_stat         DOUBLE,
    combined_pvalue     DOUBLE,
    direction_consistent BOOLEAN,
    n_datasets          INTEGER,
    combined_padj       DOUBLE
);

-- WGCNA module assignments (top 5000 variable genes per dataset)
CREATE TABLE IF NOT EXISTS modules (
    dataset_id   TEXT NOT NULL,
    gene         TEXT NOT NULL,
    module       TEXT,
    module_color TEXT
);

-- Module eigengene values per sample
CREATE TABLE IF NOT EXISTS module_eigengenes (
    dataset_id      TEXT NOT NULL,
    sample_id       TEXT,
    module          TEXT,
    eigengene_value DOUBLE
);

-- Module-trait (SCZ status) correlation
CREATE TABLE IF NOT EXISTS module_trait (
    dataset_id  TEXT NOT NULL,
    module      TEXT,
    correlation DOUBLE,
    pvalue      DOUBLE,
    n_samples   INTEGER
);

-- Top hub genes per module (ranked by kME)
CREATE TABLE IF NOT EXISTS hub_genes (
    dataset_id TEXT NOT NULL,
    gene       TEXT,
    module     TEXT,
    kME        DOUBLE,
    kME_signed DOUBLE
);

-- Risk gene overlap with DE results
CREATE TABLE IF NOT EXISTS risk_de_overlap (
    dataset_id      TEXT NOT NULL,
    gene            TEXT,
    logFC           DOUBLE,
    padj            DOUBLE,
    is_significant  BOOLEAN,
    in_PGC3         BOOLEAN,
    in_family_study BOOLEAN,
    source          TEXT
);

-- Module-level risk gene enrichment
CREATE TABLE IF NOT EXISTS module_risk_overlap (
    dataset_id       TEXT NOT NULL,
    module           TEXT,
    module_size      INTEGER,
    risk_genes_count INTEGER,
    risk_genes       TEXT,
    pgc3_count       INTEGER,
    family_count     INTEGER,
    fraction_risk    DOUBLE
);

-- High-evidence genes (DE + hub + risk gene convergence)
CREATE TABLE IF NOT EXISTS high_evidence_genes (
    gene           TEXT,
    is_DE          BOOLEAN,
    is_hub         BOOLEAN,
    is_risk_gene   BOOLEAN,
    evidence_count INTEGER,
    logFC          DOUBLE,
    padj           DOUBLE,
    module         TEXT,
    kME            DOUBLE,
    risk_source    TEXT,
    dataset        TEXT
);

-- Fisher's exact test for module enrichment in risk genes
CREATE TABLE IF NOT EXISTS enrichment_tests (
    test             TEXT,
    category         TEXT,
    risk_and_sig     INTEGER,
    risk_not_sig     INTEGER,
    not_risk_sig     INTEGER,
    not_risk_not_sig INTEGER,
    odds_ratio       DOUBLE,
    pvalue           DOUBLE,
    dataset          TEXT
);

-- GSEA preranked results (KEGG, GO, Reactome per dataset)
CREATE TABLE IF NOT EXISTS gsea_results (
    dataset_id      TEXT NOT NULL,
    gene_set_library TEXT,
    term            TEXT,
    ES              DOUBLE,
    NES             DOUBLE,
    nom_pval        DOUBLE,
    fdr_qval        DOUBLE,
    fwer_pval       DOUBLE,
    tag_pct         TEXT,
    gene_pct        TEXT,
    lead_genes      TEXT
);

-- SCZ-relevant pathway enrichment (keyword-filtered from GSEA)
CREATE TABLE IF NOT EXISTS scz_pathway_enrichment (
    term       TEXT,
    gene_set   TEXT,
    NES        DOUBLE,
    FDR        DOUBLE,
    pvalue     DOUBLE,
    n_genes    INTEGER
);

-- Enrichr module-level over-representation
CREATE TABLE IF NOT EXISTS module_enrichment (
    dataset_id       TEXT NOT NULL,
    gene_set         TEXT,
    term             TEXT,
    overlap          TEXT,
    pvalue           DOUBLE,
    adjusted_pvalue  DOUBLE,
    odds_ratio       DOUBLE,
    combined_score   DOUBLE,
    genes            TEXT,
    module           TEXT
);

-- Cell type deconvolution scores (MCPcounter-style)
CREATE TABLE IF NOT EXISTS cell_type_de (
    dataset_id       TEXT NOT NULL,
    cell_type        TEXT,
    mean_score_SCZ   DOUBLE,
    mean_score_ctrl  DOUBLE,
    logFC            DOUBLE,
    stat             DOUBLE,
    pvalue           DOUBLE,
    padj             DOUBLE
);

-- PPI network nodes (STRING DB, score >= 700)
CREATE TABLE IF NOT EXISTS ppi_nodes (
    dataset_id        TEXT NOT NULL,
    gene              TEXT,
    degree            INTEGER,
    degree_centrality DOUBLE,
    betweenness       DOUBLE,
    eigenvector       DOUBLE,
    is_DE             BOOLEAN,
    logFC             DOUBLE,
    is_hub            BOOLEAN,
    is_risk           BOOLEAN
);

-- PPI network edges
CREATE TABLE IF NOT EXISTS ppi_edges (
    dataset_id TEXT NOT NULL,
    gene_a     TEXT,
    gene_b     TEXT,
    score      DOUBLE
);

-- Module preservation (Zsummary cross-dataset)
CREATE TABLE IF NOT EXISTS module_preservation (
    ref_dataset     TEXT,
    test_dataset    TEXT,
    module          TEXT,
    n_genes_ref     INTEGER,
    n_genes_common  INTEGER,
    ref_density     DOUBLE,
    test_density    DOUBLE,
    cor_adj         DOUBLE,
    cor_kIM         DOUBLE,
    Z_density       DOUBLE,
    Z_cor_adj       DOUBLE,
    Z_cor_kIM       DOUBLE,
    Zsummary        DOUBLE
);

-- Drug perturbation GSEA results (raw, all libraries)
CREATE TABLE IF NOT EXISTS drug_perturbations (
    dataset_id  TEXT NOT NULL,
    term        TEXT,
    ES          DOUBLE,
    NES         DOUBLE,
    nom_pval    DOUBLE,
    fdr_qval    DOUBLE,
    tag_pct     TEXT,
    gene_pct    TEXT,
    lead_genes  TEXT,
    library     TEXT,
    drug_name   TEXT
);

-- Scored drug repurposing candidates per dataset
CREATE TABLE IF NOT EXISTS drug_candidates (
    dataset_id             TEXT NOT NULL,
    drug_name              TEXT,
    mean_NES               DOUBLE,
    min_FDR                DOUBLE,
    n_libraries            INTEGER,
    best_term              TEXT,
    is_known_psychiatric   BOOLEAN,
    is_repurposing_interest BOOLEAN,
    composite_score        DOUBLE
);

-- Cross-dataset drug candidates (replicated in 2+ datasets)
CREATE TABLE IF NOT EXISTS cross_dataset_drugs (
    drug_name   TEXT,
    n_datasets  INTEGER,
    mean_NES    DOUBLE,
    best_FDR    DOUBLE,
    is_known    BOOLEAN,
    is_repurpose BOOLEAN,
    datasets    TEXT
);

-- Medication dose-response (GSE21138 brain, Spearman rho vs CPZ-equiv dose)
CREATE TABLE IF NOT EXISTS dose_response (
    gene         TEXT,
    spearman_rho DOUBLE,
    pvalue       DOUBLE,
    padj         DOUBLE
);

-- Blood-brain confounding cross-reference
CREATE TABLE IF NOT EXISTS blood_brain_confounding (
    comparison          TEXT,
    gene                TEXT,
    blood_logFC         DOUBLE,
    blood_padj          DOUBLE,
    brain_dose_rho      DOUBLE,
    brain_dose_padj     DOUBLE,
    is_dose_responsive  BOOLEAN,
    confounding_risk    TEXT
);

-- Medication confounding risk report per dataset
CREATE TABLE IF NOT EXISTS confounding_report (
    dataset          TEXT,
    confounding_risk TEXT,
    note             TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_de_dataset ON de_results(dataset_id);
CREATE INDEX IF NOT EXISTS idx_de_gene ON de_results(gene);
CREATE INDEX IF NOT EXISTS idx_de_padj ON de_results(padj);
CREATE INDEX IF NOT EXISTS idx_meta_gene ON meta_de(gene);
CREATE INDEX IF NOT EXISTS idx_meta_padj ON meta_de(combined_padj);
CREATE INDEX IF NOT EXISTS idx_modules_dataset ON modules(dataset_id);
CREATE INDEX IF NOT EXISTS idx_hub_dataset ON hub_genes(dataset_id);
CREATE INDEX IF NOT EXISTS idx_hub_gene ON hub_genes(gene);
CREATE INDEX IF NOT EXISTS idx_gsea_dataset ON gsea_results(dataset_id);
CREATE INDEX IF NOT EXISTS idx_gsea_fdr ON gsea_results(fdr_qval);
CREATE INDEX IF NOT EXISTS idx_drug_dataset ON drug_candidates(dataset_id);
CREATE INDEX IF NOT EXISTS idx_drug_nes ON drug_candidates(mean_NES);
CREATE INDEX IF NOT EXISTS idx_cross_drug_n ON cross_dataset_drugs(n_datasets);
CREATE INDEX IF NOT EXISTS idx_cross_drug_nes ON cross_dataset_drugs(mean_NES);
CREATE INDEX IF NOT EXISTS idx_high_ev ON high_evidence_genes(evidence_count);
CREATE INDEX IF NOT EXISTS idx_ppi_dataset ON ppi_nodes(dataset_id);
CREATE INDEX IF NOT EXISTS idx_confounding ON blood_brain_confounding(confounding_risk);
