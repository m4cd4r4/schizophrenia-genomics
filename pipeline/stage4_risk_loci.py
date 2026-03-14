"""
Stage 4: Map results to schizophrenia risk loci.

Cross-references differentially expressed genes and co-expression hub genes
with known schizophrenia risk genes from PGC3 GWAS and family linkage studies.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib_venn import venn3
from scipy import stats

import config
from pipeline.utils import get_logger, save_df, load_df, configure_plotting, savefig

log = get_logger("stage4")


def load_risk_genes() -> tuple[set, set, set]:
    """Load curated risk gene lists from reference files."""
    pgc3_path = config.REFERENCE_DIR / "pgc3_risk_genes.csv"
    family_path = config.REFERENCE_DIR / "family_study_genes.csv"

    pgc3_df = pd.read_csv(pgc3_path)
    family_df = pd.read_csv(family_path)

    pgc3_genes = set(pgc3_df["gene"].str.strip())
    family_genes = set(family_df["gene"].str.strip())
    combined = pgc3_genes | family_genes

    log.info(f"Risk gene sets: PGC3={len(pgc3_genes)}, family={len(family_genes)}, "
             f"combined={len(combined)}, overlap={len(pgc3_genes & family_genes)}")

    return pgc3_genes, family_genes, combined


def cross_reference_de(
    de_df: pd.DataFrame,
    pgc3_genes: set,
    family_genes: set,
) -> pd.DataFrame:
    """Find DE genes that overlap with risk gene sets."""
    sig_genes = set(
        de_df[de_df["padj"] < config.DE_PVALUE_THRESHOLD]["gene"]
    )
    sig_with_fc = set(
        de_df[
            (de_df["padj"] < config.DE_PVALUE_THRESHOLD)
            & (de_df["logFC"].abs() > config.DE_LOGFC_THRESHOLD)
        ]["gene"]
    )

    all_de_genes = set(de_df["gene"])

    # Cross-reference
    rows = []
    for gene in de_df["gene"]:
        row = de_df[de_df["gene"] == gene].iloc[0]
        is_sig = row["padj"] < config.DE_PVALUE_THRESHOLD
        in_pgc3 = gene in pgc3_genes
        in_family = gene in family_genes

        if in_pgc3 or in_family:
            rows.append({
                "gene": gene,
                "logFC": row["logFC"],
                "padj": row["padj"],
                "is_significant": is_sig,
                "in_PGC3": in_pgc3,
                "in_family_study": in_family,
                "source": _gene_source(gene, pgc3_genes, family_genes),
            })

    cross_df = pd.DataFrame(rows).sort_values("padj")

    n_risk_in_de = len(cross_df)
    n_risk_sig = cross_df["is_significant"].sum()
    log.info(f"Risk genes found in expression data: {n_risk_in_de}")
    log.info(f"Risk genes significantly DE: {n_risk_sig}")

    return cross_df


def _gene_source(gene: str, pgc3: set, family: set) -> str:
    if gene in pgc3 and gene in family:
        return "PGC3 + family"
    elif gene in pgc3:
        return "PGC3"
    else:
        return "family"


def cross_reference_modules(
    hub_df: pd.DataFrame,
    module_df: pd.DataFrame,
    pgc3_genes: set,
    family_genes: set,
) -> pd.DataFrame:
    """Check overlap between co-expression modules/hubs and risk genes."""
    combined = pgc3_genes | family_genes

    # Module-level overlap
    module_overlap = []
    for module in module_df["module"].unique():
        mod_genes = set(module_df[module_df["module"] == module]["gene"])
        overlap = mod_genes & combined
        pgc3_overlap = mod_genes & pgc3_genes
        family_overlap = mod_genes & family_genes

        module_overlap.append({
            "module": module,
            "module_size": len(mod_genes),
            "risk_genes_count": len(overlap),
            "risk_genes": ", ".join(sorted(overlap)) if overlap else "",
            "pgc3_count": len(pgc3_overlap),
            "family_count": len(family_overlap),
            "fraction_risk": len(overlap) / max(len(mod_genes), 1),
        })

    mod_overlap_df = pd.DataFrame(module_overlap).sort_values("risk_genes_count", ascending=False)

    # Hub genes that are also risk genes
    hub_risk = hub_df[hub_df["gene"].isin(combined)].copy()
    hub_risk["source"] = hub_risk["gene"].apply(lambda g: _gene_source(g, pgc3_genes, family_genes))
    log.info(f"Hub genes that are risk genes: {len(hub_risk)}")

    return mod_overlap_df, hub_risk


def enrichment_test(
    de_df: pd.DataFrame,
    module_df: pd.DataFrame,
    risk_genes: set,
    label: str,
) -> pd.DataFrame:
    """Fisher's exact test for enrichment of risk genes."""
    all_genes = set(de_df["gene"])
    sig_genes = set(de_df[de_df["padj"] < config.DE_PVALUE_THRESHOLD]["gene"])
    risk_in_data = risk_genes & all_genes

    results = []

    # Overall DE enrichment
    a = len(sig_genes & risk_in_data)
    b = len(sig_genes - risk_in_data)
    c = len(risk_in_data - sig_genes)
    d = len(all_genes - sig_genes - risk_in_data)

    odds_ratio, p_value = stats.fisher_exact([[a, b], [c, d]])
    results.append({
        "test": f"DE_vs_{label}",
        "category": "all_DE",
        "risk_and_sig": a,
        "risk_not_sig": c,
        "not_risk_sig": b,
        "not_risk_not_sig": d,
        "odds_ratio": odds_ratio,
        "pvalue": p_value,
    })

    # Per-module enrichment
    for module in module_df["module"].unique():
        mod_genes = set(module_df[module_df["module"] == module]["gene"])
        mod_risk = mod_genes & risk_in_data

        a = len(mod_risk)
        b = len(mod_genes - risk_in_data)
        c = len(risk_in_data - mod_genes)
        d = len(all_genes - mod_genes - risk_in_data)

        if a + b == 0 or a + c == 0:
            continue

        odds_ratio, p_value = stats.fisher_exact([[a, b], [c, d]])
        results.append({
            "test": f"module_vs_{label}",
            "category": module,
            "risk_and_sig": a,
            "risk_not_sig": c,
            "not_risk_sig": b,
            "not_risk_not_sig": d,
            "odds_ratio": odds_ratio,
            "pvalue": p_value,
        })

    return pd.DataFrame(results).sort_values("pvalue")


def build_convergent_evidence(
    de_df: pd.DataFrame,
    hub_df: pd.DataFrame,
    pgc3_genes: set,
    family_genes: set,
) -> pd.DataFrame:
    """Find genes with convergent evidence: DE + hub + risk locus."""
    combined_risk = pgc3_genes | family_genes
    sig_genes = set(de_df[de_df["padj"] < config.DE_PVALUE_THRESHOLD]["gene"])
    hub_genes = set(hub_df["gene"])

    all_genes = set(de_df["gene"]) | hub_genes
    rows = []
    for gene in all_genes:
        is_de = gene in sig_genes
        is_hub = gene in hub_genes
        is_risk = gene in combined_risk

        evidence_count = sum([is_de, is_hub, is_risk])
        if evidence_count >= 2:
            de_row = de_df[de_df["gene"] == gene]
            hub_row = hub_df[hub_df["gene"] == gene]

            rows.append({
                "gene": gene,
                "is_DE": is_de,
                "is_hub": is_hub,
                "is_risk_gene": is_risk,
                "evidence_count": evidence_count,
                "logFC": de_row.iloc[0]["logFC"] if not de_row.empty else np.nan,
                "padj": de_row.iloc[0]["padj"] if not de_row.empty else np.nan,
                "module": hub_row.iloc[0]["module"] if not hub_row.empty else "",
                "kME": hub_row.iloc[0]["kME"] if not hub_row.empty else np.nan,
                "risk_source": _gene_source(gene, pgc3_genes, family_genes) if is_risk else "",
            })

    conv_df = pd.DataFrame(rows).sort_values("evidence_count", ascending=False)
    log.info(f"Genes with 3 lines of evidence (DE + hub + risk): "
             f"{(conv_df['evidence_count'] == 3).sum()}")
    log.info(f"Genes with 2 lines of evidence: "
             f"{(conv_df['evidence_count'] == 2).sum()}")

    return conv_df


def plot_venn(
    de_df: pd.DataFrame,
    hub_df: pd.DataFrame,
    risk_genes: set,
    dataset_id: str,
):
    """Venn diagram of DE genes, hub genes, and risk genes."""
    configure_plotting()
    sig_genes = set(de_df[de_df["padj"] < config.DE_PVALUE_THRESHOLD]["gene"])
    hub_genes_set = set(hub_df["gene"])
    risk_in_data = risk_genes & set(de_df["gene"])

    fig, ax = plt.subplots(figsize=(8, 8))
    v = venn3(
        [sig_genes, hub_genes_set, risk_in_data],
        set_labels=("DE Genes", "Hub Genes", "Risk Genes"),
        ax=ax,
    )

    # Color the patches
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    for i, patch_id in enumerate(["100", "010", "001"]):
        patch = v.get_patch_by_id(patch_id)
        if patch:
            patch.set_alpha(0.4)
            patch.set_color(colors[i])

    # Highlight the triple overlap
    triple = v.get_patch_by_id("111")
    if triple:
        triple.set_alpha(0.8)
        triple.set_color("#d62728")

    ax.set_title(f"Convergent Evidence: {dataset_id}")

    # Add gene names for triple overlap
    triple_genes = sig_genes & hub_genes_set & risk_in_data
    if triple_genes:
        gene_text = "\n".join(sorted(triple_genes)[:15])
        if len(triple_genes) > 15:
            gene_text += f"\n... +{len(triple_genes)-15} more"
        ax.text(0.02, 0.02, f"Triple overlap:\n{gene_text}",
                transform=ax.transAxes, fontsize=7, verticalalignment="bottom",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    savefig(fig, f"{dataset_id}_risk_gene_overlap_venn")


def run(dataset_ids: list[str] | None = None):
    """Run Stage 4: Risk loci mapping."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 4: Risk Loci Mapping\n{'='*60}")

    pgc3_genes, family_genes, combined = load_risk_genes()

    all_enrichment = []
    all_convergent = []

    for ds_id in dataset_ids:
        log.info(f"\n--- {ds_id} ---")

        # Load stage 2 + 3 results
        de_path = config.RESULTS_DIR / f"{ds_id}_de_results.csv"
        hub_path = config.RESULTS_DIR / f"{ds_id}_hub_genes.csv"
        mod_path = config.RESULTS_DIR / f"{ds_id}_modules.csv"

        if not de_path.exists():
            log.warning(f"No DE results for {ds_id}, skipping")
            continue

        de_df = load_df(de_path)

        # Cross-reference DE genes
        cross_df = cross_reference_de(de_df, pgc3_genes, family_genes)
        save_df(cross_df, config.RESULTS_DIR / f"{ds_id}_risk_de_overlap.csv",
                f"{ds_id} risk gene DE overlap")

        # Module overlap (if available)
        if hub_path.exists() and mod_path.exists():
            hub_df = load_df(hub_path)
            mod_df = load_df(mod_path)

            mod_overlap_df, hub_risk_df = cross_reference_modules(
                hub_df, mod_df, pgc3_genes, family_genes
            )
            save_df(mod_overlap_df, config.RESULTS_DIR / f"{ds_id}_module_risk_overlap.csv",
                    f"{ds_id} module-risk overlap")

            if not hub_risk_df.empty:
                save_df(hub_risk_df, config.RESULTS_DIR / f"{ds_id}_hub_risk_genes.csv",
                        f"{ds_id} hub genes that are risk genes")

            # Enrichment tests
            for label, gene_set in [("PGC3", pgc3_genes), ("family", family_genes), ("combined", combined)]:
                enrich_df = enrichment_test(de_df, mod_df, gene_set, label)
                enrich_df["dataset"] = ds_id
                all_enrichment.append(enrich_df)

            # Convergent evidence
            conv_df = build_convergent_evidence(de_df, hub_df, pgc3_genes, family_genes)
            conv_df["dataset"] = ds_id
            all_convergent.append(conv_df)

            # Venn diagram
            plot_venn(de_df, hub_df, combined, ds_id)

    # Save combined results
    if all_enrichment:
        combined_enrich = pd.concat(all_enrichment, ignore_index=True)
        save_df(combined_enrich, config.RESULTS_DIR / "enrichment_tests.csv",
                "Enrichment test results")

    if all_convergent:
        combined_conv = pd.concat(all_convergent, ignore_index=True)
        save_df(combined_conv, config.RESULTS_DIR / "high_evidence_genes.csv",
                "High-evidence convergent genes")

        # Print top genes
        top = combined_conv[combined_conv["evidence_count"] == 3].head(20)
        if not top.empty:
            log.info("\nTop convergent evidence genes (DE + hub + risk):")
            for _, row in top.iterrows():
                log.info(f"  {row['gene']}: logFC={row['logFC']:.3f}, "
                        f"padj={row['padj']:.1e}, module={row['module']}, "
                        f"source={row['risk_source']}")
