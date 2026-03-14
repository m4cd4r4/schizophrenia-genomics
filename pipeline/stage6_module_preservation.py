"""
Stage 6: Module preservation analysis (Zsummary).

Tests whether co-expression modules found in the reference dataset (GSE38484)
are reproduced in validation datasets. Uses permutation-based Z-statistics
following Langfelder & Horvath 2011.

Zsummary > 10: highly preserved
Zsummary 2-10: moderately preserved
Zsummary < 2: not preserved
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from scipy.stats import pearsonr

import config
from pipeline.utils import get_logger, save_df, configure_plotting, savefig

log = get_logger("stage6")

N_PERMUTATIONS = 100


def _module_density(cor_mat: np.ndarray, module_idx: np.ndarray) -> float:
    """Mean absolute off-diagonal correlation within a module."""
    sub = cor_mat[np.ix_(module_idx, module_idx)]
    n = len(module_idx)
    if n < 2:
        return 0.0
    mask = ~np.eye(n, dtype=bool)
    return float(np.mean(np.abs(sub[mask])))


def _module_connectivity(cor_mat: np.ndarray, module_idx: np.ndarray) -> np.ndarray:
    """Intramodular connectivity: row sum of adjacency within module."""
    sub = np.abs(cor_mat[np.ix_(module_idx, module_idx)])
    np.fill_diagonal(sub, 0)
    return sub.sum(axis=1)


def compute_preservation_stats(
    ref_expr: pd.DataFrame,
    test_expr: pd.DataFrame,
    ref_modules: pd.DataFrame,
    n_permutations: int = N_PERMUTATIONS,
) -> pd.DataFrame:
    """
    Compute module preservation Zsummary for each module.

    Args:
        ref_expr: genes x samples expression in reference dataset
        test_expr: genes x samples expression in test dataset
        ref_modules: DataFrame with 'gene' and 'module' columns
        n_permutations: number of permutations for null distribution

    Returns:
        DataFrame with preservation statistics per module
    """
    # Find common genes between datasets
    common_genes = ref_expr.index.intersection(test_expr.index)
    log.info(f"Common genes between datasets: {len(common_genes)}")

    ref_sub = ref_expr.loc[common_genes]
    test_sub = test_expr.loc[common_genes]

    # Correlation matrices (genes x genes)
    log.info("Computing reference correlation matrix...")
    ref_cor = np.corrcoef(ref_sub.values)

    log.info("Computing test correlation matrix...")
    test_cor = np.corrcoef(test_sub.values)

    gene_list = list(common_genes)
    gene_idx = {g: i for i, g in enumerate(gene_list)}

    results = []

    modules = ref_modules[ref_modules["module"] != "M0_grey"]["module"].unique()
    log.info(f"Testing preservation for {len(modules)} modules (excluding grey)")

    for mod in sorted(modules):
        mod_genes = ref_modules[ref_modules["module"] == mod]["gene"].tolist()
        mod_genes_common = [g for g in mod_genes if g in gene_idx]
        n_mod = len(mod_genes_common)

        if n_mod < 10:
            log.info(f"  {mod}: only {n_mod} genes in common - skipping")
            continue

        idx = np.array([gene_idx[g] for g in mod_genes_common])

        # Observed statistics in test dataset
        obs_density = _module_density(test_cor, idx)
        obs_ref_density = _module_density(ref_cor, idx)

        # Correlation of adjacency values (Z.cor.adj)
        ref_adj_flat = np.abs(ref_cor[np.ix_(idx, idx)]).flatten()
        test_adj_flat = np.abs(test_cor[np.ix_(idx, idx)]).flatten()
        if np.std(ref_adj_flat) > 0 and np.std(test_adj_flat) > 0:
            cor_adj, _ = pearsonr(ref_adj_flat, test_adj_flat)
        else:
            cor_adj = 0.0

        # Correlation of connectivity (Z.cor.kIM)
        ref_kIM = _module_connectivity(ref_cor, idx)
        test_kIM = _module_connectivity(test_cor, idx)
        if np.std(ref_kIM) > 0 and np.std(test_kIM) > 0:
            cor_kIM, _ = pearsonr(ref_kIM, test_kIM)
        else:
            cor_kIM = 0.0

        # Null distribution via permutation
        all_idx = np.arange(len(gene_list))
        null_densities = []
        null_cor_adjs = []
        null_cor_kIMs = []

        rng = np.random.default_rng(42)
        for _ in range(n_permutations):
            perm_idx = rng.choice(all_idx, size=n_mod, replace=False)

            null_densities.append(_module_density(test_cor, perm_idx))

            r_adj = np.abs(ref_cor[np.ix_(idx, idx)]).flatten()
            t_adj = np.abs(test_cor[np.ix_(perm_idx, perm_idx)]).flatten()
            if np.std(r_adj) > 0 and np.std(t_adj) > 0:
                c, _ = pearsonr(r_adj, t_adj)
                null_cor_adjs.append(c)
            else:
                null_cor_adjs.append(0.0)

            r_k = _module_connectivity(ref_cor, idx)
            t_k = _module_connectivity(test_cor, perm_idx)
            if np.std(r_k) > 0 and np.std(t_k) > 0:
                c, _ = pearsonr(r_k, t_k)
                null_cor_kIMs.append(c)
            else:
                null_cor_kIMs.append(0.0)

        # Z-scores
        def zscore(obs, null_list):
            mu = np.mean(null_list)
            sd = np.std(null_list)
            return (obs - mu) / sd if sd > 0 else 0.0

        z_density = zscore(obs_density, null_densities)
        z_cor_adj = zscore(cor_adj, null_cor_adjs)
        z_cor_kIM = zscore(cor_kIM, null_cor_kIMs)

        zsummary = np.mean([z_density, z_cor_adj, z_cor_kIM])

        results.append({
            "module": mod,
            "n_genes_ref": len(mod_genes),
            "n_genes_common": n_mod,
            "ref_density": obs_ref_density,
            "test_density": obs_density,
            "cor_adj": cor_adj,
            "cor_kIM": cor_kIM,
            "Z.density": z_density,
            "Z.cor.adj": z_cor_adj,
            "Z.cor.kIM": z_cor_kIM,
            "Zsummary": zsummary,
        })

        preservation_label = (
            "High" if zsummary > 10 else
            "Moderate" if zsummary > 2 else
            "Not preserved"
        )
        log.info(f"  {mod}: n={n_mod} Zsummary={zsummary:.2f} ({preservation_label})")

    return pd.DataFrame(results)


def plot_preservation(pres_df: pd.DataFrame, ref_id: str, test_id: str):
    """Bar chart of Zsummary per module with preservation thresholds."""
    configure_plotting()
    pres_sorted = pres_df.sort_values("Zsummary", ascending=False)

    colors = []
    for z in pres_sorted["Zsummary"]:
        if z > 10:
            colors.append("#2ca02c")
        elif z > 2:
            colors.append("#ff7f0e")
        else:
            colors.append("#d62728")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(pres_sorted["module"], pres_sorted["Zsummary"], color=colors)
    ax.axhline(10, ls="--", c="#2ca02c", lw=1.2, label="High (Z>10)")
    ax.axhline(2, ls="--", c="#ff7f0e", lw=1.2, label="Moderate (Z>2)")
    ax.set_xlabel("Module")
    ax.set_ylabel("Zsummary")
    ax.set_title(f"Module Preservation: {ref_id} -> {test_id}")
    ax.legend(framealpha=0.8)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    savefig(fig, f"module_preservation_{ref_id}_in_{test_id}")


def run(ref_id: str = "GSE38484", test_ids: list[str] | None = None):
    """Run module preservation for reference modules against test datasets."""
    if test_ids is None:
        test_ids = [ds for ds in config.DATASETS if ds != ref_id]

    log.info(f"\n{'='*60}\nStage 6: Module Preservation\nReference: {ref_id}\n{'='*60}")

    # Load reference expression + modules
    ref_expr = pd.read_csv(
        config.DATA_PROCESSED / f"{ref_id}_expression.csv", index_col=0
    )
    ref_modules_path = config.RESULTS_DIR / f"{ref_id}_modules.csv"
    if not ref_modules_path.exists():
        log.warning(f"No module file for {ref_id} - run stage3 first")
        return

    ref_modules = pd.read_csv(ref_modules_path)

    all_results = {}
    for test_id in test_ids:
        test_expr_path = config.DATA_PROCESSED / f"{test_id}_expression.csv"
        if not test_expr_path.exists():
            log.warning(f"No expression data for {test_id} - skipping")
            continue

        log.info(f"\nTesting preservation in {test_id}...")
        test_expr = pd.read_csv(test_expr_path, index_col=0)

        pres_df = compute_preservation_stats(ref_expr, test_expr, ref_modules)
        if pres_df.empty:
            log.warning(f"No preservation results for {test_id}")
            continue

        save_df(
            pres_df,
            config.RESULTS_DIR / f"module_preservation_{ref_id}_in_{test_id}.csv",
            f"Module preservation {ref_id} -> {test_id}",
        )
        plot_preservation(pres_df, ref_id, test_id)
        all_results[test_id] = pres_df

        n_high = (pres_df["Zsummary"] > 10).sum()
        n_mod = ((pres_df["Zsummary"] > 2) & (pres_df["Zsummary"] <= 10)).sum()
        n_not = (pres_df["Zsummary"] <= 2).sum()
        log.info(
            f"{test_id} summary: {n_high} highly preserved, "
            f"{n_mod} moderately, {n_not} not preserved"
        )

    return all_results
