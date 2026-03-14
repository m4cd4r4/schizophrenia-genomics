"""
Stage 7: Blood cell type deconvolution.

Estimates relative immune cell type proportions per sample using
MCPcounter-style marker gene scoring (geometric mean of z-scored marker
gene expression). No licensed tools required.

Reference: Becht et al. 2016 (MCPcounter), Newman et al. 2015 (CIBERSORT concept).

Cell types scored:
- T cells (CD3+)
- CD8 T cells
- NK cells
- B cells
- Monocytes
- Neutrophils
- Dendritic cells
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import config
from pipeline.utils import get_logger, save_df, configure_plotting, savefig

log = get_logger("stage7")

# MCPcounter marker genes (Becht et al. 2016 + TIMER)
# Selected from published supplementary tables - freely available
CELL_TYPE_MARKERS = {
    "T_cells": [
        "CD3D", "CD3E", "CD3G", "CD2", "CD7", "IL7R", "TRAC",
    ],
    "CD8_T_cells": [
        "CD8A", "CD8B", "GZMK", "GZMH", "GZMA", "PRF1",
    ],
    "NK_cells": [
        "KLRD1", "KLRB1", "NKG7", "GNLY", "NCAM1", "FCGR3A",
    ],
    "B_cells": [
        "CD19", "CD79A", "MS4A1", "IGHM", "IGHG1", "CD22",
    ],
    "Monocytes": [
        "CD14", "LYZ", "S100A8", "S100A9", "FCGR3A", "ITGAM",
    ],
    "Neutrophils": [
        "ELANE", "MPO", "PRTN3", "CEACAM8", "CSF3R", "FPR1",
    ],
    "Dendritic_cells": [
        "FCER1A", "CD1C", "CLEC10A", "ITGAX", "HLA-DQA1",
    ],
    "Platelets": [
        "PPBP", "PF4", "GP9", "ITGA2B", "GP1BB",
    ],
}


def score_cell_types(
    expr_df: pd.DataFrame,
    markers: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    """
    Compute per-sample cell type enrichment scores.

    Method: z-score expression across samples, then take mean of
    available marker genes per cell type. This gives a relative
    abundance score (comparable within a dataset, not across datasets).

    Args:
        expr_df: genes x samples expression matrix (log2 normalized)
        markers: cell type -> list of marker genes

    Returns:
        cell_types x samples score matrix
    """
    if markers is None:
        markers = CELL_TYPE_MARKERS

    # Z-score each gene across samples
    gene_means = expr_df.mean(axis=1)
    gene_stds = expr_df.std(axis=1)
    gene_stds_safe = gene_stds.replace(0, 1)
    expr_z = expr_df.subtract(gene_means, axis=0).divide(gene_stds_safe, axis=0)

    scores = {}
    for cell_type, marker_genes in markers.items():
        available = [g for g in marker_genes if g in expr_z.index]
        if not available:
            log.warning(f"{cell_type}: 0 / {len(marker_genes)} markers found")
            continue
        if len(available) < len(marker_genes):
            log.info(
                f"{cell_type}: {len(available)} / {len(marker_genes)} markers found"
            )
        scores[cell_type] = expr_z.loc[available].mean(axis=0)

    score_df = pd.DataFrame(scores).T  # cell_types x samples
    log.info(
        f"Scored {len(scores)} cell types across {score_df.shape[1]} samples"
    )
    return score_df


def test_cell_type_differences(
    score_df: pd.DataFrame,
    pheno_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Welch t-test: compare cell type scores SCZ vs control.

    Returns DataFrame with logFC and p-value per cell type.
    """
    from scipy import stats
    from statsmodels.stats.multitest import multipletests

    scz_samples = pheno_df[pheno_df["group"] == "SCZ"].index.intersection(
        score_df.columns
    )
    ctrl_samples = pheno_df[pheno_df["group"] == "control"].index.intersection(
        score_df.columns
    )

    rows = []
    for cell_type in score_df.index:
        scz_vals = score_df.loc[cell_type, scz_samples].dropna().values.astype(float)
        ctrl_vals = score_df.loc[cell_type, ctrl_samples].dropna().values.astype(float)

        if len(scz_vals) < 3 or len(ctrl_vals) < 3:
            continue

        logfc = float(np.mean(scz_vals) - np.mean(ctrl_vals))
        stat, pval = stats.ttest_ind(scz_vals, ctrl_vals, equal_var=False)

        rows.append({
            "cell_type": cell_type,
            "mean_score_SCZ": float(np.mean(scz_vals)),
            "mean_score_ctrl": float(np.mean(ctrl_vals)),
            "logFC": logfc,
            "stat": stat,
            "pvalue": pval,
        })

    diff_df = pd.DataFrame(rows)
    if not diff_df.empty:
        _, padj, _, _ = multipletests(diff_df["pvalue"].values, method="fdr_bh")
        diff_df["padj"] = padj
        diff_df = diff_df.sort_values("pvalue").reset_index(drop=True)

    return diff_df


def plot_cell_type_scores(
    score_df: pd.DataFrame,
    pheno_df: pd.DataFrame,
    dataset_id: str,
):
    """Boxplots of cell type scores by disease group."""
    configure_plotting()

    # Align samples
    common = score_df.columns.intersection(pheno_df.index)
    score_sub = score_df[common]
    groups = pheno_df.loc[common, "group"]

    cell_types = score_df.index.tolist()
    n_types = len(cell_types)

    fig, axes = plt.subplots(2, (n_types + 1) // 2, figsize=(14, 8))
    axes = axes.flatten()

    palette = {"SCZ": "#d62728", "control": "#1f77b4"}

    for i, ct in enumerate(cell_types):
        ax = axes[i]
        data = pd.DataFrame({
            "score": score_sub.loc[ct].values,
            "group": groups.values,
        })
        for grp, color in palette.items():
            sub = data[data["group"] == grp]["score"]
            ax.boxplot(
                sub, positions=[list(palette.keys()).index(grp)],
                widths=0.5, patch_artist=True,
                boxprops=dict(facecolor=color, alpha=0.7),
                medianprops=dict(color="black"),
                whiskerprops=dict(color=color),
                capprops=dict(color=color),
                flierprops=dict(marker="o", markersize=3, color=color, alpha=0.5),
            )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["SCZ", "Control"], fontsize=8)
        ax.set_title(ct.replace("_", " "), fontsize=9, fontweight="bold")
        ax.set_ylabel("Score (z)", fontsize=7)

    # Hide unused axes
    for j in range(n_types, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(f"Cell Type Scores: {dataset_id}", fontsize=12, fontweight="bold")
    plt.tight_layout()
    savefig(fig, f"{dataset_id}_cell_type_scores")


def plot_score_heatmap(score_df: pd.DataFrame, pheno_df: pd.DataFrame, dataset_id: str):
    """Heatmap of cell type scores per sample, annotated by group."""
    configure_plotting()

    common = score_df.columns.intersection(pheno_df.index)
    score_sub = score_df[common]
    groups = pheno_df.loc[common, "group"]

    # Sort samples by group
    order = groups.sort_values().index
    score_sorted = score_sub[order]
    groups_sorted = groups[order]

    group_colors = groups_sorted.map({"SCZ": "#d62728", "control": "#1f77b4"})

    g = sns.clustermap(
        score_sorted,
        col_cluster=False,
        row_cluster=True,
        col_colors=group_colors,
        cmap="RdBu_r",
        center=0,
        figsize=(12, 6),
        yticklabels=True,
        xticklabels=False,
    )
    g.ax_heatmap.set_title(f"Cell Type Deconvolution: {dataset_id}", pad=20)
    g.fig.savefig(
        config.FIGURES_DIR / f"{dataset_id}_deconvolution_heatmap.png",
        dpi=config.FIGURE_DPI,
        bbox_inches="tight",
    )
    plt.close(g.fig)
    log.info(f"Saved figure: {config.FIGURES_DIR}/{dataset_id}_deconvolution_heatmap.png")


def run(dataset_ids: list[str] | None = None):
    """Run Stage 7 deconvolution for all datasets."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 7: Cell Type Deconvolution\n{'='*60}")

    for ds_id in dataset_ids:
        expr_path = config.DATA_PROCESSED / f"{ds_id}_expression.csv"
        pheno_path = config.DATA_PROCESSED / f"{ds_id}_phenotype.csv"

        if not expr_path.exists():
            log.warning(f"{ds_id}: no expression data - run stage1 first")
            continue

        log.info(f"\n--- {ds_id} ---")
        expr_df = pd.read_csv(expr_path, index_col=0)
        pheno_df = pd.read_csv(pheno_path, index_col=0)

        # Score cell types
        score_df = score_cell_types(expr_df)

        if score_df.empty:
            log.warning(f"{ds_id}: no cell type scores computed")
            continue

        # Save scores
        save_df(
            score_df,
            config.RESULTS_DIR / f"{ds_id}_cell_type_scores.csv",
            f"{ds_id} cell type scores",
        )

        # Test for SCZ differences
        diff_df = test_cell_type_differences(score_df, pheno_df)
        if not diff_df.empty:
            save_df(
                diff_df,
                config.RESULTS_DIR / f"{ds_id}_cell_type_de.csv",
                f"{ds_id} cell type differential",
            )
            sig = diff_df[diff_df["padj"] < 0.05]
            if not sig.empty:
                log.info(f"Significantly different cell types (FDR<0.05):")
                for _, row in sig.iterrows():
                    direction = "higher" if row["logFC"] > 0 else "lower"
                    log.info(
                        f"  {row['cell_type']}: {direction} in SCZ "
                        f"(FC={row['logFC']:.3f}, padj={row['padj']:.3e})"
                    )
            else:
                log.info("No significantly different cell types at FDR<0.05")
                # Log top result anyway
                log.info(
                    f"  Top: {diff_df.iloc[0]['cell_type']} "
                    f"(pval={diff_df.iloc[0]['pvalue']:.3e})"
                )

        # Plots
        plot_cell_type_scores(score_df, pheno_df, ds_id)
        plot_score_heatmap(score_df, pheno_df, ds_id)
