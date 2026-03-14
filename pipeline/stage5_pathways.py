"""
Stage 5: Pathway enrichment analysis and visualization.

Runs GSEA/Enrichr against KEGG, GO, and Reactome gene sets. Builds pathway
networks and creates a summary dashboard of all pipeline results.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import networkx as nx
from itertools import combinations

import config
from pipeline.utils import get_logger, save_df, load_df, configure_plotting, savefig

log = get_logger("stage5")

# Try importing gseapy - it's the most fragile dependency
try:
    import gseapy as gp
    HAS_GSEAPY = True
except ImportError:
    HAS_GSEAPY = False
    log.warning("gseapy not installed. Pathway analysis will be limited.")


def run_gsea_prerank(de_df: pd.DataFrame, dataset_id: str) -> dict[str, pd.DataFrame]:
    """Run GSEA prerank analysis using DE statistics."""
    if not HAS_GSEAPY:
        log.error("gseapy required for GSEA. Install with: pip install gseapy")
        return {}

    # Build ranked gene list (by t-statistic or signed -log10p)
    rank_df = de_df[["gene", "stat"]].dropna()
    rank_df = rank_df.drop_duplicates(subset="gene")
    rank_df = rank_df.set_index("gene")
    rank_series = rank_df["stat"].sort_values(ascending=False)

    log.info(f"Running GSEA prerank with {len(rank_series)} genes...")

    results = {}
    for gene_set_name in config.GSEA_GENE_SETS:
        log.info(f"  Gene set: {gene_set_name}")
        try:
            pre_res = gp.prerank(
                rnk=rank_series,
                gene_sets=gene_set_name,
                outdir=None,  # Don't write temp files
                min_size=10,
                max_size=500,
                permutation_num=1000,
                seed=42,
                verbose=False,
            )
            res_df = pre_res.res2d
            if res_df is not None and not res_df.empty:
                res_df = res_df.sort_values("FDR q-val")
                results[gene_set_name] = res_df
                n_sig = (res_df["FDR q-val"].astype(float) < 0.25).sum()
                log.info(f"    {len(res_df)} pathways tested, {n_sig} significant (FDR<0.25)")

                save_df(
                    res_df,
                    config.RESULTS_DIR / f"{dataset_id}_gsea_{gene_set_name.split('_')[0].lower()}.csv",
                    f"{dataset_id} GSEA {gene_set_name}",
                )
        except Exception as e:
            log.warning(f"    GSEA failed for {gene_set_name}: {e}")

    return results


def run_enrichr_modules(
    module_df: pd.DataFrame,
    dataset_id: str,
) -> pd.DataFrame:
    """Run Enrichr over-representation for each module's genes."""
    if not HAS_GSEAPY:
        return pd.DataFrame()

    all_results = []
    for module in module_df["module"].unique():
        if module.startswith("M0"):
            continue
        genes = module_df[module_df["module"] == module]["gene"].tolist()
        if len(genes) < 5:
            continue

        try:
            enr = gp.enrichr(
                gene_list=genes,
                gene_sets=config.GSEA_GENE_SETS,
                outdir=None,
                verbose=False,
            )
            res_df = enr.results
            if res_df is not None and not res_df.empty:
                res_df["module"] = module
                all_results.append(res_df)
        except Exception as e:
            log.warning(f"Enrichr failed for {module}: {e}")

    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        save_df(combined, config.RESULTS_DIR / f"{dataset_id}_module_enrichment.csv",
                f"{dataset_id} module enrichment")
        return combined

    return pd.DataFrame()


def filter_scz_pathways(gsea_results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Filter GSEA results to schizophrenia-relevant pathways."""
    scz_rows = []
    for gene_set_name, res_df in gsea_results.items():
        for _, row in res_df.iterrows():
            term = str(row.get("Term", row.get("Name", "")))
            is_scz = any(
                kw.lower() in term.lower()
                for kw in config.SCZ_PATHWAY_KEYWORDS
            )
            if is_scz:
                scz_rows.append({
                    "term": term,
                    "gene_set": gene_set_name,
                    "NES": float(row.get("NES", row.get("nes", 0))),
                    "FDR": float(row.get("FDR q-val", row.get("fdr", 1))),
                    "pvalue": float(row.get("NOM p-val", row.get("pval", 1))),
                    "n_genes": int(row.get("Tag %", row.get("matched_size", "0")).split("/")[0])
                    if isinstance(row.get("Tag %", ""), str) and "/" in str(row.get("Tag %", ""))
                    else int(row.get("matched_size", 0)) if "matched_size" in row.index else 0,
                })

    scz_df = pd.DataFrame(scz_rows).sort_values("FDR") if scz_rows else pd.DataFrame()
    if not scz_df.empty:
        log.info(f"SCZ-relevant pathways found: {len(scz_df)}")
    return scz_df


def pathway_network(gsea_results: dict[str, pd.DataFrame], dataset_id: str):
    """Build and visualize a pathway network based on shared genes."""
    configure_plotting()

    # Collect significant pathways with their gene sets
    pathways = {}
    for gene_set_name, res_df in gsea_results.items():
        sig = res_df[res_df["FDR q-val"].astype(float) < 0.25]
        for _, row in sig.head(30).iterrows():
            term = str(row.get("Term", row.get("Name", "")))
            lead_genes_str = str(row.get("Lead_genes", row.get("lead_genes", "")))
            genes = set(lead_genes_str.split(";")) if lead_genes_str else set()
            if genes and term:
                pathways[term] = {
                    "genes": genes,
                    "NES": float(row.get("NES", 0)),
                    "FDR": float(row.get("FDR q-val", 1)),
                }

    if len(pathways) < 2:
        log.warning("Too few significant pathways for network visualization")
        return

    # Build network
    G = nx.Graph()
    for term, info in pathways.items():
        # Shorten long names
        short_name = term[:40] + "..." if len(term) > 40 else term
        G.add_node(short_name, NES=info["NES"], FDR=info["FDR"],
                   genes=info["genes"], full_name=term)

    # Add edges based on Jaccard similarity
    nodes = list(G.nodes())
    for n1, n2 in combinations(nodes, 2):
        g1 = G.nodes[n1]["genes"]
        g2 = G.nodes[n2]["genes"]
        if g1 and g2:
            jaccard = len(g1 & g2) / len(g1 | g2)
            if jaccard > 0.1:
                G.add_edge(n1, n2, weight=jaccard)

    # Remove isolated nodes
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)

    if len(G.nodes()) < 2:
        log.warning("Too few connected pathways for network")
        return

    fig, ax = plt.subplots(figsize=(14, 10))

    pos = nx.spring_layout(G, k=2.5, seed=42)

    # Node properties
    node_sizes = [max(100, 500 * (-np.log10(G.nodes[n]["FDR"] + 1e-10))) for n in G.nodes()]
    node_colors = [G.nodes[n]["NES"] for n in G.nodes()]

    # Edge properties
    edge_widths = [G.edges[e]["weight"] * 5 for e in G.edges()]

    nx.draw_networkx_edges(G, pos, alpha=0.3, width=edge_widths, ax=ax)
    nodes_drawn = nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes, node_color=node_colors,
        cmap="RdBu_r", vmin=-3, vmax=3, alpha=0.8, ax=ax,
    )
    nx.draw_networkx_labels(G, pos, font_size=6, ax=ax)

    plt.colorbar(nodes_drawn, ax=ax, label="NES", shrink=0.6)
    ax.set_title(f"Pathway Network: {dataset_id}\n(node size = significance, color = NES)")
    ax.axis("off")

    savefig(fig, f"{dataset_id}_pathway_network")


def module_pathway_heatmap(enrichment_df: pd.DataFrame, dataset_id: str):
    """Heatmap of module vs pathway enrichment."""
    if enrichment_df.empty:
        return

    configure_plotting()

    # Get top pathways by significance across all modules
    top_terms = (
        enrichment_df
        .sort_values("Adjusted P-value")
        .drop_duplicates("Term")
        .head(25)["Term"]
        .tolist()
    )

    if not top_terms:
        return

    # Build matrix
    modules = sorted(enrichment_df["module"].unique())
    matrix = pd.DataFrame(index=top_terms, columns=modules, dtype=float)
    matrix[:] = 0

    for _, row in enrichment_df.iterrows():
        if row["Term"] in top_terms and row["module"] in modules:
            val = -np.log10(max(float(row["Adjusted P-value"]), 1e-20))
            matrix.loc[row["Term"], row["module"]] = val

    # Shorten long term names
    matrix.index = [t[:50] + "..." if len(t) > 50 else t for t in matrix.index]

    fig, ax = plt.subplots(figsize=(max(8, len(modules) * 0.8), max(8, len(top_terms) * 0.35)))
    sns.heatmap(
        matrix.astype(float),
        cmap="YlOrRd",
        ax=ax,
        xticklabels=True,
        yticklabels=True,
        cbar_kws={"label": "-log10(adj p-value)"},
    )
    ax.set_title(f"Module-Pathway Enrichment: {dataset_id}")
    ax.set_xlabel("Co-expression Module")
    ax.set_ylabel("Pathway")

    savefig(fig, f"{dataset_id}_module_pathway_heatmap")


def summary_dashboard(dataset_id: str):
    """Create a multi-panel summary dashboard of all results."""
    configure_plotting()

    fig = plt.figure(figsize=(20, 16))
    gs = gridspec.GridSpec(3, 2, hspace=0.35, wspace=0.3)

    # Panel A: DE summary (top genes bar chart)
    ax_a = fig.add_subplot(gs[0, 0])
    try:
        de_df = load_df(config.RESULTS_DIR / f"{dataset_id}_de_results.csv")
        top_up = de_df[de_df["logFC"] > 0].nsmallest(10, "padj")
        top_down = de_df[de_df["logFC"] < 0].nsmallest(10, "padj")
        top_genes = pd.concat([top_up, top_down]).sort_values("logFC")

        colors = ["#d62728" if fc > 0 else "#1f77b4" for fc in top_genes["logFC"]]
        ax_a.barh(top_genes["gene"], top_genes["logFC"], color=colors, alpha=0.8)
        ax_a.set_xlabel("log2 Fold Change")
        ax_a.set_title("A. Top Differentially Expressed Genes")
        ax_a.axvline(0, color="grey", lw=0.5)
    except Exception as e:
        ax_a.text(0.5, 0.5, f"DE data not available\n{e}", ha="center", va="center",
                  transform=ax_a.transAxes)
        ax_a.set_title("A. Differential Expression")

    # Panel B: Module-trait correlation
    ax_b = fig.add_subplot(gs[0, 1])
    try:
        mt_df = load_df(config.RESULTS_DIR / f"{dataset_id}_module_trait.csv")
        mt_df = mt_df.sort_values("correlation")
        colors_mt = ["#d62728" if c > 0 else "#1f77b4" for c in mt_df["correlation"]]
        ax_b.barh(mt_df["module"], mt_df["correlation"], color=colors_mt, alpha=0.8)
        ax_b.set_xlabel("Correlation with SCZ status")
        ax_b.set_title("B. Module-Disease Correlation")
        ax_b.axvline(0, color="grey", lw=0.5)

        # Mark significant modules
        for i, (_, row) in enumerate(mt_df.iterrows()):
            if row["pvalue"] < 0.05:
                ax_b.text(row["correlation"], i, " *", va="center", fontsize=14,
                         fontweight="bold", color="red")
    except Exception:
        ax_b.text(0.5, 0.5, "Module-trait data not available", ha="center", va="center",
                  transform=ax_b.transAxes)
        ax_b.set_title("B. Module-Disease Correlation")

    # Panel C: Risk gene overlap summary
    ax_c = fig.add_subplot(gs[1, 0])
    try:
        conv_df = load_df(config.RESULTS_DIR / "high_evidence_genes.csv")
        conv_ds = conv_df[conv_df["dataset"] == dataset_id] if "dataset" in conv_df.columns else conv_df
        evidence_counts = conv_ds["evidence_count"].value_counts().sort_index()

        ax_c.bar(evidence_counts.index.astype(str), evidence_counts.values,
                 color=["#ff7f0e", "#2ca02c", "#d62728"][:len(evidence_counts)], alpha=0.8)
        ax_c.set_xlabel("Lines of Evidence")
        ax_c.set_ylabel("Number of Genes")
        ax_c.set_title("C. Convergent Evidence Distribution")

        # Annotate with gene names for triple evidence
        triple = conv_ds[conv_ds["evidence_count"] == 3]["gene"].tolist()
        if triple:
            gene_text = ", ".join(triple[:8])
            if len(triple) > 8:
                gene_text += f" +{len(triple)-8} more"
            ax_c.text(0.5, 0.95, f"Triple: {gene_text}",
                     transform=ax_c.transAxes, fontsize=7, ha="center", va="top",
                     bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    except Exception:
        ax_c.text(0.5, 0.5, "Convergent evidence not available", ha="center", va="center",
                  transform=ax_c.transAxes)
        ax_c.set_title("C. Convergent Evidence")

    # Panel D: Enrichment test results
    ax_d = fig.add_subplot(gs[1, 1])
    try:
        enrich_df = load_df(config.RESULTS_DIR / "enrichment_tests.csv")
        enrich_ds = enrich_df[enrich_df["dataset"] == dataset_id] if "dataset" in enrich_df.columns else enrich_df
        sig_enrich = enrich_ds[enrich_ds["pvalue"] < 0.05].head(15)

        if not sig_enrich.empty:
            y_labels = sig_enrich["category"] + " vs " + sig_enrich["test"].str.split("_vs_").str[-1]
            ax_d.barh(y_labels, -np.log10(sig_enrich["pvalue"]), color="#2ca02c", alpha=0.8)
            ax_d.set_xlabel("-log10(p-value)")
            ax_d.axvline(-np.log10(0.05), ls="--", color="red", lw=0.8, label="p=0.05")
            ax_d.legend()
        else:
            ax_d.text(0.5, 0.5, "No significant enrichments", ha="center", va="center",
                      transform=ax_d.transAxes)
        ax_d.set_title("D. Risk Gene Enrichment Tests")
    except Exception:
        ax_d.text(0.5, 0.5, "Enrichment data not available", ha="center", va="center",
                  transform=ax_d.transAxes)
        ax_d.set_title("D. Risk Gene Enrichment")

    # Panel E: Top SCZ-relevant pathways
    ax_e = fig.add_subplot(gs[2, 0])
    try:
        scz_path = config.RESULTS_DIR / "scz_pathway_enrichment.csv"
        if scz_path.exists():
            scz_df = load_df(scz_path)
            top_scz = scz_df.nsmallest(15, "FDR")
            colors_nes = ["#d62728" if n > 0 else "#1f77b4" for n in top_scz["NES"]]
            short_terms = [t[:45] + "..." if len(t) > 45 else t for t in top_scz["term"]]
            ax_e.barh(short_terms, top_scz["NES"], color=colors_nes, alpha=0.8)
            ax_e.set_xlabel("Normalized Enrichment Score")
            ax_e.axvline(0, color="grey", lw=0.5)
        else:
            ax_e.text(0.5, 0.5, "SCZ pathway data not available", ha="center", va="center",
                      transform=ax_e.transAxes)
        ax_e.set_title("E. SCZ-Relevant Pathways")
    except Exception:
        ax_e.text(0.5, 0.5, "Pathway data not available", ha="center", va="center",
                  transform=ax_e.transAxes)
        ax_e.set_title("E. SCZ-Relevant Pathways")

    # Panel F: Hub genes from disease-associated modules
    ax_f = fig.add_subplot(gs[2, 1])
    try:
        hub_df = load_df(config.RESULTS_DIR / f"{dataset_id}_hub_genes.csv")
        mt_df = load_df(config.RESULTS_DIR / f"{dataset_id}_module_trait.csv")

        # Get modules significantly correlated with disease
        sig_modules = mt_df[mt_df["pvalue"] < 0.1]["module"].tolist()
        sig_hubs = hub_df[hub_df["module"].isin(sig_modules)].nlargest(20, "kME")

        if not sig_hubs.empty:
            colors_hub = [MODULE_COLORS_MAP.get(m, "#999999") for m in sig_hubs["module"]]
            ax_f.barh(sig_hubs["gene"], sig_hubs["kME"], color=colors_hub, alpha=0.8)
            ax_f.set_xlabel("Module Membership (kME)")
        else:
            ax_f.text(0.5, 0.5, "No significant module hubs", ha="center", va="center",
                      transform=ax_f.transAxes)
        ax_f.set_title("F. Hub Genes in Disease Modules")
    except Exception:
        ax_f.text(0.5, 0.5, "Hub gene data not available", ha="center", va="center",
                  transform=ax_f.transAxes)
        ax_f.set_title("F. Hub Genes in Disease Modules")

    fig.suptitle(
        f"Schizophrenia Blood Expression Analysis: {dataset_id}",
        fontsize=16, fontweight="bold", y=0.98,
    )

    savefig(fig, "summary_dashboard")


# Simple color map for modules in dashboard
MODULE_COLORS_MAP = {f"M{i+1}": c for i, c in enumerate([
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
])}


def run(dataset_ids: list[str] | None = None):
    """Run Stage 5: Pathway analysis and visualization."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 5: Pathway Analysis\n{'='*60}")

    for ds_id in dataset_ids:
        log.info(f"\n--- {ds_id} ---")

        # Load DE results
        de_path = config.RESULTS_DIR / f"{ds_id}_de_results.csv"
        if not de_path.exists():
            log.warning(f"No DE results for {ds_id}, skipping GSEA")
            continue
        de_df = load_df(de_path)

        # GSEA prerank
        gsea_results = run_gsea_prerank(de_df, ds_id)

        # Filter SCZ-relevant pathways
        if gsea_results:
            scz_df = filter_scz_pathways(gsea_results)
            if not scz_df.empty:
                save_df(scz_df, config.RESULTS_DIR / "scz_pathway_enrichment.csv",
                        "SCZ-relevant pathway enrichment")

            # Pathway network
            pathway_network(gsea_results, ds_id)

        # Module enrichment
        mod_path = config.RESULTS_DIR / f"{ds_id}_modules.csv"
        if mod_path.exists():
            mod_df = load_df(mod_path)
            enrichment_df = run_enrichr_modules(mod_df, ds_id)
            if not enrichment_df.empty:
                module_pathway_heatmap(enrichment_df, ds_id)

        # Summary dashboard
        summary_dashboard(ds_id)

    log.info("\nStage 5 complete. Check figures/ for visualizations.")
