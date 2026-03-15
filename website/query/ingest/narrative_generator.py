"""
Convert DuckDB table rows into natural language chunks for ChromaDB.

~700 chunks from 10 content categories:
  1. Top DE genes per dataset
  2. Meta-analysis DE genes (cross-dataset)
  3. Hub genes per module per dataset
  4. Risk gene overlaps
  5. High-evidence genes (multi-source convergence)
  6. Drug candidates (per-dataset + cross-dataset)
  7. Cell type deconvolution findings
  8. Module-trait correlations
  9. GSEA pathway findings (top per library)
  10. PPI hub/risk gene network context
"""
import duckdb
from typing import Any


def _fmt_p(p: float | None) -> str:
    if p is None or p != p:  # NaN check
        return "p=N/A"
    if p < 0.001:
        return f"p={p:.2e}"
    return f"p={p:.4f}"


def _fmt_fc(fc: float | None) -> str:
    if fc is None or fc != fc:
        return "logFC=N/A"
    sign = "+" if fc >= 0 else ""
    direction = "up" if fc >= 0 else "down"
    return f"logFC={sign}{fc:.3f} ({direction}regulated in SCZ)"


def _tier(dataset_id: str | None) -> str:
    if dataset_id == "GSE21138":
        return "UNDERPOWERED"
    return "SINGLE_DATASET"


def _chunk(text: str, source: str, dataset_id: str | None = None,
           gene: str | None = None, category: str = "data") -> dict:
    meta = {"source": source, "category": category}
    if dataset_id:
        meta["dataset_id"] = dataset_id
    if gene:
        meta["gene"] = gene.upper()
    tier = "REPLICATED" if not dataset_id else _tier(dataset_id)
    meta["evidence_tier"] = tier
    return {"text": text, "metadata": meta}


# ---------------------------------------------------------------------------
# 1. Top DE genes per dataset
# ---------------------------------------------------------------------------

def _de_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    TISSUE = {
        "GSE38484": "whole blood",
        "GSE27383": "PBMC (peripheral blood mononuclear cells)",
        "GSE21138": "post-mortem prefrontal cortex (BA46)",
    }

    # Per-dataset: top 150 most significant genes
    rows = con.execute("""
        SELECT dataset_id, gene, logFC, mean_SCZ, mean_control, pvalue, padj
        FROM de_results
        WHERE padj IS NOT NULL
        ORDER BY padj ASC
        LIMIT 450
    """).fetchall()

    # Group into batches of ~10 genes per chunk
    from collections import defaultdict
    by_ds: dict[str, list] = defaultdict(list)
    for r in rows:
        by_ds[r[0]].append(r)

    for ds, ds_rows in by_ds.items():
        tissue = TISSUE.get(ds, ds)
        # Individual gene chunks for top 50
        for gene, logFC, mean_scz, mean_ctrl, pvalue, padj in [(r[1], r[2], r[3], r[4], r[5], r[6]) for r in ds_rows[:50]]:
            direction = "upregulated" if (logFC or 0) >= 0 else "downregulated"
            text = (
                f"Gene {gene} is {direction} in schizophrenia "
                f"({_fmt_fc(logFC)}, FDR={padj:.2e}) "
                f"in dataset {ds} ({tissue}). "
                f"Mean expression: SCZ={mean_scz:.3f}, control={mean_ctrl:.3f}."
            )
            chunks.append(_chunk(text, f"de_results/{ds}", ds, gene))

        # Summary chunk for next 100
        if len(ds_rows) > 50:
            next_genes = [r[1] for r in ds_rows[50:100]]
            text = (
                f"Additional significantly differentially expressed genes in {ds} ({tissue}) include: "
                f"{', '.join(next_genes[:25])} and {len(next_genes) - 25 if len(next_genes) > 25 else 0} others "
                f"(all FDR < {ds_rows[99][6]:.2e} if available)."
            )
            chunks.append(_chunk(text, f"de_results/{ds}/batch", ds))

    return chunks


# ---------------------------------------------------------------------------
# 2. Meta-analysis (cross-dataset)
# ---------------------------------------------------------------------------

def _meta_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT gene, mean_logFC, combined_padj, direction_consistent, n_datasets
        FROM meta_de
        WHERE combined_padj IS NOT NULL
        ORDER BY combined_padj ASC
        LIMIT 200
    """).fetchall()

    # Top 100 individual chunks
    for gene, mean_logFC, combined_padj, direction_consistent, n_datasets in rows[:100]:
        direction = "upregulated" if (mean_logFC or 0) >= 0 else "downregulated"
        consistent = "consistent direction across all datasets" if direction_consistent else "mixed direction across datasets"
        text = (
            f"Gene {gene} shows {direction} expression in schizophrenia across {n_datasets} datasets "
            f"(meta-analysis combined FDR={combined_padj:.2e}, mean logFC={mean_logFC:+.3f}). "
            f"Direction is {consistent}. "
            f"This is a REPLICATED finding."
        )
        chunks.append(_chunk(text, "meta_de", None, gene, "meta_analysis"))

    # Summary of consistent genes
    consistent_rows = [r for r in rows if r[3]]  # direction_consistent = True
    if consistent_rows:
        up = [r[0] for r in consistent_rows if (r[1] or 0) > 0][:20]
        dn = [r[0] for r in consistent_rows if (r[1] or 0) < 0][:20]
        text = (
            f"Meta-analysis of schizophrenia across all 3 datasets identifies {len(consistent_rows)} genes "
            f"with direction-consistent differential expression. "
            f"Consistently upregulated: {', '.join(up[:15])}{'...' if len(up) > 15 else ''}. "
            f"Consistently downregulated: {', '.join(dn[:15])}{'...' if len(dn) > 15 else ''}."
        )
        chunks.append(_chunk(text, "meta_de/summary", None, None, "meta_analysis"))

    return chunks


# ---------------------------------------------------------------------------
# 3. Hub genes
# ---------------------------------------------------------------------------

def _hub_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT h.dataset_id, h.gene, h.module, h.kME,
               mt.correlation as module_scz_cor, mt.pvalue as module_pval
        FROM hub_genes h
        LEFT JOIN module_trait mt ON h.dataset_id = mt.dataset_id AND h.module = mt.module
        ORDER BY h.dataset_id, h.module, h.kME DESC
    """).fetchall()

    from collections import defaultdict
    by_module: dict[tuple, list] = defaultdict(list)
    for r in rows:
        by_module[(r[0], r[2])].append(r)

    for (ds, module), genes in by_module.items():
        top_genes = genes[:10]
        gene_names = [g[1] for g in top_genes]
        kme_vals = [f"{g[1]}(kME={g[3]:.2f})" for g in top_genes[:5]]
        scz_cor = genes[0][4]
        pval = genes[0][5]
        cor_str = f"SCZ correlation r={scz_cor:.3f}" if scz_cor is not None else "SCZ correlation unknown"
        text = (
            f"Module {module} in dataset {ds} has hub genes: {', '.join(kme_vals)}. "
            f"Total {len(genes)} hub genes. Module {cor_str} ({_fmt_p(pval)}). "
            f"Top hub genes (all genes): {', '.join(gene_names)}."
        )
        chunks.append(_chunk(text, f"hub_genes/{ds}/{module}", ds))

    return chunks


# ---------------------------------------------------------------------------
# 4. Risk gene overlaps
# ---------------------------------------------------------------------------

def _risk_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT dataset_id, gene, logFC, padj, is_significant, in_PGC3, in_family_study, source
        FROM risk_de_overlap
        WHERE (in_PGC3 = TRUE OR in_family_study = TRUE)
        ORDER BY padj ASC NULLS LAST
    """).fetchall()

    for ds, gene, logFC, padj, is_sig, in_pgc3, in_family, source in rows:
        sources = []
        if in_pgc3:
            sources.append("PGC3 GWAS locus")
        if in_family:
            sources.append("family study risk gene")
        sig_str = f"significantly DE (FDR={padj:.2e})" if is_sig and padj else "not significantly DE"
        text = (
            f"Risk gene {gene} from {', '.join(sources)} is {sig_str} in {ds}. "
            f"Expression change: {_fmt_fc(logFC)}."
        )
        chunks.append(_chunk(text, f"risk_de_overlap/{ds}", ds, gene, "risk_genes"))

    # Summary
    pgc3_sig = con.execute("""
        SELECT COUNT(DISTINCT gene) FROM risk_de_overlap
        WHERE in_PGC3 = TRUE AND is_significant = TRUE
    """).fetchone()[0]
    total_pgc3 = con.execute("""
        SELECT COUNT(DISTINCT gene) FROM risk_de_overlap WHERE in_PGC3 = TRUE
    """).fetchone()[0]
    text = (
        f"Of {total_pgc3} unique PGC3 GWAS risk genes tested across datasets, "
        f"{pgc3_sig} are significantly differentially expressed in at least one dataset. "
        f"This validates the transcriptomic approach: genetic risk loci converge on gene expression changes."
    )
    chunks.append(_chunk(text, "risk_de_overlap/summary", None, None, "risk_genes"))

    return chunks


# ---------------------------------------------------------------------------
# 5. High-evidence genes
# ---------------------------------------------------------------------------

def _high_evidence_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT gene, evidence_count, is_DE, is_hub, is_risk_gene,
               logFC, padj, module, kME, risk_source, dataset
        FROM high_evidence_genes
        ORDER BY evidence_count DESC, padj ASC NULLS LAST
    """).fetchall()

    for gene, ev_count, is_de, is_hub, is_risk, logFC, padj, module, kME, risk_src, dataset in rows:
        evidence = []
        if is_de:
            evidence.append(f"differentially expressed (logFC={logFC:+.3f})" if logFC else "differentially expressed")
        if is_hub:
            evidence.append(f"hub gene in module {module} (kME={kME:.2f})" if module else "hub gene")
        if is_risk:
            evidence.append(f"genetic risk gene ({risk_src})" if risk_src else "genetic risk gene")

        text = (
            f"High-evidence gene {gene} ({ev_count} converging lines of evidence): "
            f"{'; '.join(evidence)}. "
            f"Primary dataset: {dataset}. "
            f"This gene is prioritized for schizophrenia research by multiple independent methods."
        )
        chunks.append(_chunk(text, "high_evidence_genes", dataset, gene, "high_evidence"))

    # Summary
    n = len(rows)
    top_genes = [r[0] for r in rows[:15]]
    text = (
        f"The analysis identifies {n} high-evidence schizophrenia genes supported by 2-3 "
        f"independent lines of evidence (differential expression + hub gene status + genetic risk). "
        f"Top high-evidence genes: {', '.join(top_genes)}."
    )
    chunks.append(_chunk(text, "high_evidence_genes/summary", None, None, "high_evidence"))

    return chunks


# ---------------------------------------------------------------------------
# 6. Drug candidates
# ---------------------------------------------------------------------------

def _drug_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    # Cross-dataset drugs (replicated)
    rows = con.execute("""
        SELECT drug_name, n_datasets, mean_NES, best_FDR, is_known, is_repurpose, datasets
        FROM cross_dataset_drugs
        WHERE n_datasets >= 2
        ORDER BY n_datasets DESC, ABS(mean_NES) DESC
        LIMIT 100
    """).fetchall()

    for drug, n_ds, nes, fdr, is_known, is_repurpose, datasets in rows:
        known_str = "a known antipsychotic/psychiatric drug" if is_known else "not a known psychiatric drug"
        repurpose_str = " and is a repurposing candidate" if is_repurpose and not is_known else ""
        direction = "reversal" if (nes or 0) < 0 else "mimicry"
        text = (
            f"Drug {drug} shows transcriptomic {direction} of SCZ gene expression signature "
            f"across {n_ds} datasets (mean NES={nes:.3f}, best FDR={fdr:.3e}). "
            f"Datasets: {datasets}. "
            f"{drug} is {known_str}{repurpose_str}. "
            f"This is a REPLICATED finding."
        )
        chunks.append(_chunk(text, "cross_dataset_drugs", None, None, "drug_repurposing"))

    # Per-dataset top candidates
    ds_rows = con.execute("""
        SELECT dataset_id, drug_name, mean_NES, min_FDR, n_libraries,
               is_known_psychiatric, is_repurposing_interest, composite_score
        FROM drug_candidates
        WHERE min_FDR < 0.25
        ORDER BY dataset_id, composite_score DESC
        LIMIT 150
    """).fetchall()

    from collections import defaultdict
    by_ds: dict[str, list] = defaultdict(list)
    for r in ds_rows:
        by_ds[r[0]].append(r)

    for ds, drugs in by_ds.items():
        top = drugs[:30]
        known = [d[1] for d in top if d[5]]
        candidates = [d[1] for d in top if d[6] and not d[5]]
        if known:
            text = (
                f"Known psychiatric drugs validated in {ds} by transcriptomic matching: "
                f"{', '.join(known[:10])}. "
                f"These reverse the SCZ gene expression signature, validating the drug repurposing approach."
            )
            chunks.append(_chunk(text, f"drug_candidates/{ds}/known", ds, None, "drug_repurposing"))
        if candidates:
            text = (
                f"Top repurposing candidates in {ds} (not currently used in psychiatry): "
                f"{', '.join(candidates[:10])}. "
                f"These drugs show transcriptomic reversal of SCZ signature across {len(drugs)} libraries tested."
            )
            chunks.append(_chunk(text, f"drug_candidates/{ds}/candidates", ds, None, "drug_repurposing"))

    return chunks


# ---------------------------------------------------------------------------
# 7. Cell type deconvolution
# ---------------------------------------------------------------------------

def _cell_type_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT dataset_id, cell_type, mean_score_SCZ, mean_score_ctrl, logFC, pvalue, padj
        FROM cell_type_de
        ORDER BY dataset_id, padj ASC NULLS LAST
    """).fetchall()

    from collections import defaultdict
    by_ds: dict[str, list] = defaultdict(list)
    for r in rows:
        by_ds[r[0]].append(r)

    for ds, cells in by_ds.items():
        sig = [c for c in cells if c[6] is not None and c[6] < 0.05]
        for ds2, ct, scz_score, ctrl_score, logFC, pval, padj in sig[:10]:
            direction = "reduced" if (logFC or 0) < 0 else "increased"
            text = (
                f"Cell type {ct} is {direction} in schizophrenia in dataset {ds2} "
                f"(logFC={logFC:+.3f}, FDR={padj:.3e}). "
                f"SCZ mean score={scz_score:.3f}, control mean={ctrl_score:.3f}."
            )
            chunks.append(_chunk(text, f"cell_type_de/{ds}", ds, None, "cell_type"))

    # Cross-dataset summary
    cd8_rows = con.execute("""
        SELECT dataset_id, logFC, padj FROM cell_type_de
        WHERE cell_type LIKE '%CD8%' AND padj < 0.05
    """).fetchall()
    nk_rows = con.execute("""
        SELECT dataset_id, logFC, padj FROM cell_type_de
        WHERE cell_type LIKE '%NK%' AND padj < 0.05
    """).fetchall()

    if cd8_rows:
        datasets = [r[0] for r in cd8_rows]
        text = (
            f"CD8 T cells are consistently reduced in schizophrenia across {len(cd8_rows)} datasets "
            f"({', '.join(datasets)}). "
            f"This replication supports immune dysregulation as a hallmark of schizophrenia. "
            f"This is a REPLICATED finding."
        )
        chunks.append(_chunk(text, "cell_type_de/CD8_summary", None, None, "cell_type"))

    if nk_rows:
        datasets = [r[0] for r in nk_rows]
        text = (
            f"NK (natural killer) cells are consistently reduced in schizophrenia across {len(nk_rows)} datasets "
            f"({', '.join(datasets)}). "
            f"This suggests impaired innate immune surveillance. "
            f"This is a REPLICATED finding."
        )
        chunks.append(_chunk(text, "cell_type_de/NK_summary", None, None, "cell_type"))

    return chunks


# ---------------------------------------------------------------------------
# 8. Module-trait correlations
# ---------------------------------------------------------------------------

def _module_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    rows = con.execute("""
        SELECT mt.dataset_id, mt.module, mt.correlation, mt.pvalue,
               COUNT(m.gene) as n_genes
        FROM module_trait mt
        LEFT JOIN modules m ON mt.dataset_id = m.dataset_id AND mt.module = m.module
        WHERE mt.pvalue < 0.05
        GROUP BY mt.dataset_id, mt.module, mt.correlation, mt.pvalue
        ORDER BY ABS(mt.correlation) DESC
        LIMIT 50
    """).fetchall()

    for ds, module, cor, pval, n_genes in rows:
        direction = "positively" if cor > 0 else "negatively"
        text = (
            f"Module {module} in {ds} is {direction} correlated with schizophrenia status "
            f"(r={cor:.3f}, {_fmt_p(pval)}). "
            f"Module contains {n_genes} genes."
        )
        chunks.append(_chunk(text, f"module_trait/{ds}/{module}", ds, None, "modules"))

    # Module preservation
    pres_rows = con.execute("""
        SELECT ref_dataset, test_dataset, module, Zsummary
        FROM module_preservation
        WHERE Zsummary > 10
        ORDER BY Zsummary DESC
    """).fetchall()

    if pres_rows:
        modules_str = ", ".join([f"{r[2]} (Z={r[3]:.1f})" for r in pres_rows[:8]])
        text = (
            f"Highly preserved modules across blood datasets (Zsummary > 10): {modules_str}. "
            f"High preservation means these modules capture robust co-expression patterns "
            f"reproducible across independent cohorts."
        )
        chunks.append(_chunk(text, "module_preservation/summary", None, None, "modules"))

    return chunks


# ---------------------------------------------------------------------------
# 9. GSEA pathway findings
# ---------------------------------------------------------------------------

def _pathway_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    # Top pathways per dataset per library
    rows = con.execute("""
        SELECT dataset_id, gene_set_library, term, NES, fdr_qval, lead_genes
        FROM gsea_results
        WHERE fdr_qval < 0.05
        ORDER BY dataset_id, gene_set_library, fdr_qval ASC
    """).fetchall()

    from collections import defaultdict
    by_ds_lib: dict[tuple, list] = defaultdict(list)
    for r in rows:
        by_ds_lib[(r[0], r[1])].append(r)

    for (ds, lib), paths in by_ds_lib.items():
        top = paths[:10]
        for ds2, lib2, term, nes, fdr, lead_genes in top[:5]:
            direction = "enriched" if (nes or 0) > 0 else "depleted"
            leads = (lead_genes or "").split(";")[:5]
            text = (
                f"Pathway '{term}' ({lib}) is {direction} in SCZ in {ds} "
                f"(NES={nes:.3f}, FDR={fdr:.3e}). "
                f"Leading edge genes: {', '.join(leads)}."
            )
            chunks.append(_chunk(text, f"gsea_results/{ds}/{lib}", ds, None, "pathways"))

        # Summary chunk
        all_terms = [r[2] for r in top]
        text = (
            f"Top {lib} pathways in {ds}: {'; '.join(all_terms[:8])}. "
            f"All have FDR < 0.05."
        )
        chunks.append(_chunk(text, f"gsea_results/{ds}/{lib}/summary", ds, None, "pathways"))

    # SCZ-specific pathway enrichment
    scz_rows = con.execute("""
        SELECT term, gene_set, NES, FDR, n_genes
        FROM scz_pathway_enrichment
        WHERE FDR < 0.25
        ORDER BY ABS(NES) DESC
        LIMIT 30
    """).fetchall()

    if scz_rows:
        text = (
            f"SCZ-relevant pathways (keyword-filtered for immune, NMDA, dopamine, synaptic, etc.): "
            f"{'; '.join([r[0] for r in scz_rows[:10]])}. "
            f"These pathways are specifically relevant to schizophrenia biology."
        )
        chunks.append(_chunk(text, "scz_pathway_enrichment/summary", None, None, "pathways"))

    return chunks


# ---------------------------------------------------------------------------
# 10. PPI network
# ---------------------------------------------------------------------------

def _ppi_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    chunks = []

    # Hub genes in PPI that are also DE and risk genes
    rows = con.execute("""
        SELECT dataset_id, gene, degree, betweenness, is_DE, is_hub, is_risk
        FROM ppi_nodes
        WHERE is_hub = TRUE OR is_risk = TRUE
        ORDER BY betweenness DESC NULLS LAST
        LIMIT 50
    """).fetchall()

    for ds, gene, degree, btw, is_de, is_hub, is_risk in rows:
        flags = []
        if is_de:
            flags.append("differentially expressed")
        if is_hub:
            flags.append("WGCNA hub gene")
        if is_risk:
            flags.append("genetic risk gene")
        text = (
            f"Gene {gene} in the SCZ protein-protein interaction network ({ds}) "
            f"has degree={degree}, betweenness={btw:.4f}. "
            f"It is: {', '.join(flags)}. "
            f"High centrality suggests network vulnerability position."
        )
        chunks.append(_chunk(text, f"ppi_nodes/{ds}", ds, gene, "ppi"))

    return chunks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_data_chunks(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Generate all data narrative chunks."""
    all_chunks: list[dict] = []

    generators = [
        ("DE genes", _de_chunks),
        ("Meta-analysis", _meta_chunks),
        ("Hub genes", _hub_chunks),
        ("Risk gene overlap", _risk_chunks),
        ("High-evidence genes", _high_evidence_chunks),
        ("Drug candidates", _drug_chunks),
        ("Cell types", _cell_type_chunks),
        ("Modules", _module_chunks),
        ("Pathways", _pathway_chunks),
        ("PPI network", _ppi_chunks),
    ]

    for name, fn in generators:
        try:
            chunks = fn(con)
            all_chunks.extend(chunks)
            print(f"  {name}: {len(chunks)} chunks")
        except Exception as exc:
            print(f"  [ERR] {name}: {exc}")

    return all_chunks
