"""
Stage 2: Differential expression analysis.

Compares gene expression between SCZ and control groups using appropriate
statistical tests for microarray data (already log2-normalized).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.multitest import multipletests
from adjustText import adjust_text

import config
from pipeline.utils import get_logger, save_df, load_df, configure_plotting, savefig

log = get_logger("stage2")


def differential_expression(
    expr_df: pd.DataFrame,
    pheno_df: pd.DataFrame,
    method: str = "ttest",
) -> pd.DataFrame:
    """
    Run differential expression: SCZ vs control.

    Args:
        expr_df: genes x samples expression matrix (log2 normalized)
        pheno_df: sample metadata with 'group' column
        method: 'ttest' (Welch's) or 'mannwhitney'

    Returns:
        DataFrame with gene, logFC, stat, pvalue, padj columns
    """
    scz_samples = pheno_df[pheno_df["group"] == "SCZ"].index
    ctrl_samples = pheno_df[pheno_df["group"] == "control"].index

    # Keep only samples present in expression matrix
    scz_samples = scz_samples.intersection(expr_df.columns)
    ctrl_samples = ctrl_samples.intersection(expr_df.columns)

    log.info(f"Comparing {len(scz_samples)} SCZ vs {len(ctrl_samples)} control samples")

    if len(scz_samples) < 3 or len(ctrl_samples) < 3:
        raise ValueError(f"Too few samples: {len(scz_samples)} SCZ, {len(ctrl_samples)} control")

    scz_expr = expr_df[scz_samples]
    ctrl_expr = expr_df[ctrl_samples]

    results = []
    for gene in expr_df.index:
        scz_vals = scz_expr.loc[gene].dropna().values.astype(float)
        ctrl_vals = ctrl_expr.loc[gene].dropna().values.astype(float)

        if len(scz_vals) < 3 or len(ctrl_vals) < 3:
            continue

        log_fc = np.mean(scz_vals) - np.mean(ctrl_vals)

        if method == "ttest":
            stat_val, p_val = stats.ttest_ind(scz_vals, ctrl_vals, equal_var=False)
        elif method == "mannwhitney":
            stat_val, p_val = stats.mannwhitneyu(
                scz_vals, ctrl_vals, alternative="two-sided"
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        results.append({
            "gene": gene,
            "logFC": log_fc,
            "mean_SCZ": np.mean(scz_vals),
            "mean_control": np.mean(ctrl_vals),
            "stat": stat_val,
            "pvalue": p_val,
        })

    de_df = pd.DataFrame(results)

    # FDR correction
    _, padj, _, _ = multipletests(de_df["pvalue"].values, method="fdr_bh")
    de_df["padj"] = padj

    # Sort by adjusted p-value
    de_df = de_df.sort_values("padj").reset_index(drop=True)

    n_sig = (de_df["padj"] < config.DE_PVALUE_THRESHOLD).sum()
    n_sig_fc = (
        (de_df["padj"] < config.DE_PVALUE_THRESHOLD)
        & (de_df["logFC"].abs() > config.DE_LOGFC_THRESHOLD)
    ).sum()
    log.info(f"Significant genes (FDR<{config.DE_PVALUE_THRESHOLD}): {n_sig}")
    log.info(f"Significant with |logFC|>{config.DE_LOGFC_THRESHOLD}: {n_sig_fc}")

    return de_df


def volcano_plot(de_df: pd.DataFrame, dataset_id: str):
    """Generate volcano plot of differential expression results."""
    configure_plotting()
    fig, ax = plt.subplots(figsize=(10, 8))

    # Classify genes
    sig_up = (de_df["padj"] < config.DE_PVALUE_THRESHOLD) & (de_df["logFC"] > config.DE_LOGFC_THRESHOLD)
    sig_down = (de_df["padj"] < config.DE_PVALUE_THRESHOLD) & (de_df["logFC"] < -config.DE_LOGFC_THRESHOLD)
    not_sig = ~(sig_up | sig_down)

    neg_log_p = -np.log10(de_df["padj"].clip(lower=1e-300))

    ax.scatter(de_df.loc[not_sig, "logFC"], neg_log_p[not_sig],
               c="grey", alpha=0.4, s=8, label="NS")
    ax.scatter(de_df.loc[sig_up, "logFC"], neg_log_p[sig_up],
               c="#d62728", alpha=0.7, s=12, label=f"Up ({sig_up.sum()})")
    ax.scatter(de_df.loc[sig_down, "logFC"], neg_log_p[sig_down],
               c="#1f77b4", alpha=0.7, s=12, label=f"Down ({sig_down.sum()})")

    # Threshold lines
    ax.axhline(-np.log10(config.DE_PVALUE_THRESHOLD), ls="--", c="grey", lw=0.8)
    ax.axvline(config.DE_LOGFC_THRESHOLD, ls="--", c="grey", lw=0.8)
    ax.axvline(-config.DE_LOGFC_THRESHOLD, ls="--", c="grey", lw=0.8)

    # Label top genes
    top_genes = de_df.nsmallest(config.DE_TOP_GENES_LABEL, "padj")
    texts = []
    for _, row in top_genes.iterrows():
        t = ax.text(row["logFC"], -np.log10(max(row["padj"], 1e-300)),
                    row["gene"], fontsize=7, ha="center")
        texts.append(t)
    if texts:
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="grey", lw=0.5))

    ax.set_xlabel("log2 Fold Change (SCZ vs Control)")
    ax.set_ylabel("-log10(adjusted p-value)")
    ax.set_title(f"Differential Expression: {dataset_id}")
    ax.legend(loc="upper right", framealpha=0.8)

    savefig(fig, f"{dataset_id}_volcano")


def meta_analysis(de_results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine DE results across datasets using Fisher's method."""
    if len(de_results) < 2:
        log.info("Only one dataset - skipping meta-analysis")
        return None

    # Get all genes tested in at least 2 datasets
    gene_sets = [set(df["gene"]) for df in de_results.values()]
    common_genes = set.intersection(*gene_sets)
    log.info(f"Genes tested in all datasets: {len(common_genes)}")

    if not common_genes:
        log.warning("No common genes across datasets")
        return None

    meta_rows = []
    for gene in common_genes:
        pvals = []
        logfcs = []
        for ds_id, de_df in de_results.items():
            row = de_df[de_df["gene"] == gene]
            if row.empty:
                continue
            pvals.append(row.iloc[0]["pvalue"])
            logfcs.append(row.iloc[0]["logFC"])

        if len(pvals) < 2:
            continue

        # Fisher's method: -2 * sum(log(p)) ~ chi2(2k)
        fisher_stat = -2 * np.sum(np.log(np.array(pvals).clip(min=1e-300)))
        combined_p = stats.chi2.sf(fisher_stat, df=2 * len(pvals))
        mean_logfc = np.mean(logfcs)
        direction_consistent = all(x > 0 for x in logfcs) or all(x < 0 for x in logfcs)

        meta_rows.append({
            "gene": gene,
            "mean_logFC": mean_logfc,
            "fisher_stat": fisher_stat,
            "combined_pvalue": combined_p,
            "direction_consistent": direction_consistent,
            "n_datasets": len(pvals),
        })

    meta_df = pd.DataFrame(meta_rows)
    _, padj, _, _ = multipletests(meta_df["combined_pvalue"].values, method="fdr_bh")
    meta_df["combined_padj"] = padj
    meta_df = meta_df.sort_values("combined_padj").reset_index(drop=True)

    n_sig = (meta_df["combined_padj"] < config.DE_PVALUE_THRESHOLD).sum()
    n_consistent = (
        (meta_df["combined_padj"] < config.DE_PVALUE_THRESHOLD)
        & meta_df["direction_consistent"]
    ).sum()
    log.info(f"Meta-analysis significant genes: {n_sig} ({n_consistent} direction-consistent)")

    return meta_df


def run(dataset_ids: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Run Stage 2 for specified datasets."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    de_results = {}
    for ds_id in dataset_ids:
        ds_config = config.DATASETS[ds_id]
        log.info(f"\n{'='*60}\nStage 2: {ds_id}\n{'='*60}")

        # Load processed data from Stage 1
        expr_df = load_df(config.DATA_PROCESSED / f"{ds_id}_expression.csv")
        pheno_df = load_df(config.DATA_PROCESSED / f"{ds_id}_phenotype.csv")

        # Run differential expression
        method = ds_config.get("stat_test", "ttest")
        de_df = differential_expression(expr_df, pheno_df, method=method)

        # Save results
        save_df(de_df, config.RESULTS_DIR / f"{ds_id}_de_results.csv",
                f"{ds_id} DE results")

        # Volcano plot
        volcano_plot(de_df, ds_id)

        de_results[ds_id] = de_df

    # Meta-analysis across datasets
    meta_df = meta_analysis(de_results)
    if meta_df is not None:
        save_df(meta_df, config.RESULTS_DIR / "meta_de_results.csv",
                "Meta-analysis DE results")

    return de_results
