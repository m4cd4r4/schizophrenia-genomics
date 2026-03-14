"""
Stage 3: WGCNA-style co-expression network analysis.

Builds gene co-expression networks from blood expression data, identifies
modules of co-expressed genes, correlates modules with disease status,
and identifies hub genes within each module.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from scipy import stats
from scipy.cluster.hierarchy import fcluster, dendrogram
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA
from tqdm import tqdm

try:
    import fastcluster
    linkage_fn = fastcluster.linkage
except ImportError:
    from scipy.cluster.hierarchy import linkage as linkage_fn

import config
from pipeline.utils import get_logger, save_df, load_df, configure_plotting, savefig

log = get_logger("stage3")

# Module colors for visualization
MODULE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
    "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
]


def select_variable_genes(expr_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Select the top N most variable genes by median absolute deviation."""
    mad = expr_df.apply(lambda row: np.median(np.abs(row - np.median(row))), axis=1)
    top_genes = mad.nlargest(min(top_n, len(mad))).index
    log.info(f"Selected {len(top_genes)} most variable genes (MAD-based)")
    return expr_df.loc[top_genes]


def select_soft_power(expr_df: pd.DataFrame) -> int:
    """
    Determine the soft-thresholding power for scale-free topology.

    Tests powers 1-20, selects the lowest power where the scale-free
    topology fit R^2 exceeds the threshold (0.85).
    """
    log.info("Selecting soft-thresholding power...")
    # Use a subset of genes for speed if very large
    if expr_df.shape[0] > 5000:
        subset = expr_df.sample(n=5000, random_state=42)
    else:
        subset = expr_df

    cor_matrix = np.corrcoef(subset.values)
    np.fill_diagonal(cor_matrix, 0)

    powers = list(config.WGCNA_POWER_RANGE)
    sft_r2 = []
    mean_k = []

    for power in tqdm(powers, desc="Testing powers"):
        adj = np.abs(cor_matrix) ** power
        connectivity = adj.sum(axis=0)
        mean_k.append(np.mean(connectivity))

        # Scale-free topology fit
        # Bin connectivity values and fit log-log linear model
        k = connectivity[connectivity > 0]
        if len(k) < 10:
            sft_r2.append(0)
            continue

        # Discretize connectivity into bins
        n_bins = min(30, len(np.unique(k.astype(int))))
        if n_bins < 3:
            sft_r2.append(0)
            continue

        hist, bin_edges = np.histogram(k, bins=n_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Remove zero-count bins
        mask = hist > 0
        if mask.sum() < 3:
            sft_r2.append(0)
            continue

        log_k = np.log10(bin_centers[mask])
        log_p = np.log10(hist[mask] / hist[mask].sum())

        slope, intercept, r_value, _, _ = stats.linregress(log_k, log_p)
        # Use signed R^2 (negative slope expected for scale-free)
        signed_r2 = -np.sign(slope) * r_value ** 2
        sft_r2.append(signed_r2)

    # Select power
    selected_power = None
    for i, r2 in enumerate(sft_r2):
        if r2 > config.WGCNA_SFT_R2_THRESHOLD:
            selected_power = powers[i]
            break

    if selected_power is None:
        selected_power = 6  # Default fallback
        log.warning(f"No power reached R^2 > {config.WGCNA_SFT_R2_THRESHOLD}, using default: {selected_power}")
    else:
        log.info(f"Selected soft-threshold power: {selected_power} (R^2 = {sft_r2[selected_power-1]:.3f})")

    # Plot power selection
    configure_plotting()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(powers, sft_r2, "o-", color="#1f77b4")
    ax1.axhline(config.WGCNA_SFT_R2_THRESHOLD, ls="--", color="red", lw=0.8)
    ax1.axvline(selected_power, ls="--", color="green", lw=0.8, alpha=0.7)
    ax1.set_xlabel("Soft Threshold Power")
    ax1.set_ylabel("Scale Free Topology Fit (signed R^2)")
    ax1.set_title("Scale-Free Topology Fit")
    for i, power in enumerate(powers):
        ax1.annotate(str(power), (power, sft_r2[i]), fontsize=7, ha="center", va="bottom")

    ax2.plot(powers, mean_k, "o-", color="#ff7f0e")
    ax2.axvline(selected_power, ls="--", color="green", lw=0.8, alpha=0.7)
    ax2.set_xlabel("Soft Threshold Power")
    ax2.set_ylabel("Mean Connectivity")
    ax2.set_title("Mean Connectivity")

    fig.suptitle("Soft-Threshold Power Selection", fontsize=14)
    savefig(fig, "soft_power_selection")

    return selected_power


def build_tom(expr_df: pd.DataFrame, power: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the Topological Overlap Matrix (TOM).

    TOM measures shared connectivity between gene pairs, providing a
    more robust measure than simple correlation.
    """
    n_genes = expr_df.shape[0]
    log.info(f"Computing correlation matrix for {n_genes} genes...")

    cor_matrix = np.corrcoef(expr_df.values)
    np.fill_diagonal(cor_matrix, 0)

    log.info(f"Building adjacency matrix (power={power})...")
    adj = np.abs(cor_matrix) ** power

    log.info("Computing TOM (this may take a few minutes)...")
    # Vectorized TOM computation
    # TOM[i,j] = (sum_u(a_iu * a_uj) + a_ij) / (min(k_i, k_j) + 1 - a_ij)
    connectivity = adj.sum(axis=0)
    numerator = adj @ adj + adj

    # Pairwise minimum of connectivity
    k_min = np.minimum.outer(connectivity, connectivity)
    denominator = k_min + 1 - adj

    # Avoid division by zero
    denominator = np.maximum(denominator, 1e-10)
    tom = numerator / denominator
    np.fill_diagonal(tom, 1)

    # Clip to [0, 1]
    tom = np.clip(tom, 0, 1)

    log.info("TOM computation complete")
    return tom, adj


def detect_modules(
    tom: np.ndarray,
    genes: pd.Index,
    min_module_size: int,
) -> dict[str, list[str]]:
    """
    Detect co-expression modules via hierarchical clustering on 1-TOM.

    Uses average linkage clustering and distance-based cutting.
    """
    n_genes = len(genes)
    log.info(f"Detecting modules from {n_genes} genes...")

    # Dissimilarity
    diss_tom = 1 - tom
    np.fill_diagonal(diss_tom, 0)
    diss_tom = np.maximum(diss_tom, 0)  # Ensure non-negative

    # Convert to condensed form for linkage
    diss_condensed = squareform(diss_tom, checks=False)

    # Hierarchical clustering
    log.info("Running hierarchical clustering...")
    Z = linkage_fn(diss_condensed, method="average")

    # Try different cut heights to get reasonable module count
    best_labels = None
    best_n_modules = 0

    for cut_height in np.arange(0.99, 0.80, -0.02):
        labels = fcluster(Z, t=cut_height, criterion="distance")

        # Count modules with enough genes
        unique, counts = np.unique(labels, return_counts=True)
        valid_modules = unique[counts >= min_module_size]
        n_valid = len(valid_modules)

        if 5 <= n_valid <= 30:
            best_labels = labels
            best_n_modules = n_valid
            log.info(f"Cut height {cut_height:.2f}: {n_valid} modules (selected)")
            break
        elif n_valid > best_n_modules:
            best_labels = labels
            best_n_modules = n_valid

    if best_labels is None:
        log.warning("Could not find good cut height, using default 0.95")
        best_labels = fcluster(Z, t=0.95, criterion="distance")

    # Build module dict
    modules = {}
    gene_list = list(genes)
    unique_labels = sorted(set(best_labels))

    module_idx = 0
    for label in unique_labels:
        member_indices = np.where(best_labels == label)[0]
        if len(member_indices) >= min_module_size:
            color = MODULE_COLORS[module_idx % len(MODULE_COLORS)]
            module_name = f"M{module_idx + 1}"
            modules[module_name] = {
                "genes": [gene_list[i] for i in member_indices],
                "color": color,
                "size": len(member_indices),
            }
            module_idx += 1
        # Genes in small clusters go to "unassigned"

    # Unassigned genes
    assigned_genes = set()
    for mod in modules.values():
        assigned_genes.update(mod["genes"])
    unassigned = [g for g in gene_list if g not in assigned_genes]
    if unassigned:
        modules["M0_grey"] = {
            "genes": unassigned,
            "color": "#cccccc",
            "size": len(unassigned),
        }

    log.info(f"Detected {len(modules)} modules:")
    for name, info in sorted(modules.items()):
        log.info(f"  {name}: {info['size']} genes")

    # Plot dendrogram with module color bar
    # Use truncated dendrogram to avoid recursion limit with 5000+ genes
    import sys
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, n_genes * 3))

    configure_plotting()
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(14, 7),
                                   gridspec_kw={"height_ratios": [6, 0.3], "hspace": 0.02})

    try:
        dendro = dendrogram(Z, no_labels=True, color_threshold=0,
                            above_threshold_color="grey", ax=ax)
        ax.set_title("Gene Dendrogram with Module Colors")
        ax.set_ylabel("1 - TOM")
        ax.set_xticks([])

        # Module color bar using dendrogram leaf order
        gene_to_color = {}
        for mod_name, mod_info in modules.items():
            for g in mod_info["genes"]:
                gene_to_color[g] = mod_info["color"]

        leaves = dendro["leaves"]
        colors_ordered = [gene_to_color.get(gene_list[i], "#cccccc") for i in leaves]

        for i, c in enumerate(colors_ordered):
            ax2.axvspan(i, i + 1, color=c)
        ax2.set_xlim(0, len(colors_ordered))
        ax2.set_yticks([])
        ax2.set_xticks([])
        ax2.set_xlabel("Genes")

    except RecursionError:
        log.warning("Dendrogram too deep for plotting - creating module summary instead")
        ax.clear()
        ax2.clear()
        mod_names = sorted([m for m in modules if not m.startswith("M0")])
        sizes = [modules[m]["size"] for m in mod_names]
        colors_bar = [modules[m]["color"] for m in mod_names]
        ax.bar(mod_names, sizes, color=colors_bar, alpha=0.8)
        ax.set_ylabel("Number of Genes")
        ax.set_title("Co-expression Module Sizes")
        ax2.axis("off")

    sys.setrecursionlimit(old_limit)
    savefig(fig, "module_dendrogram")

    return modules, Z


def compute_module_eigengenes(
    expr_df: pd.DataFrame,
    modules: dict,
) -> pd.DataFrame:
    """Compute module eigengenes (first PC of each module's expression)."""
    eigengenes = {}
    for mod_name, mod_info in modules.items():
        if mod_name.startswith("M0"):
            continue
        genes_in_module = [g for g in mod_info["genes"] if g in expr_df.index]
        if len(genes_in_module) < 3:
            continue

        mod_expr = expr_df.loc[genes_in_module].values.T  # samples x genes
        # Standardize
        mod_expr = (mod_expr - mod_expr.mean(axis=0)) / (mod_expr.std(axis=0) + 1e-10)

        pca = PCA(n_components=1)
        eigengene = pca.fit_transform(mod_expr).flatten()
        eigengenes[mod_name] = eigengene
        log.info(f"  {mod_name}: PC1 explains {pca.explained_variance_ratio_[0]*100:.1f}% variance")

    me_df = pd.DataFrame(eigengenes, index=expr_df.columns)
    return me_df


def merge_similar_modules(
    modules: dict,
    me_df: pd.DataFrame,
    merge_threshold: float,
) -> tuple[dict, pd.DataFrame]:
    """Merge modules whose eigengenes are highly correlated."""
    mod_names = [m for m in me_df.columns if m in modules]
    if len(mod_names) < 2:
        return modules, me_df

    cor_matrix = me_df[mod_names].corr().abs()

    merged = set()
    merge_map = {}

    for i, m1 in enumerate(mod_names):
        if m1 in merged:
            continue
        for m2 in mod_names[i + 1:]:
            if m2 in merged:
                continue
            if cor_matrix.loc[m1, m2] > (1 - merge_threshold):
                # Merge m2 into m1
                merged.add(m2)
                merge_map[m2] = m1
                log.info(f"Merging {m2} into {m1} (cor={cor_matrix.loc[m1, m2]:.3f})")

    if not merge_map:
        log.info("No modules to merge")
        return modules, me_df

    # Apply merges
    new_modules = {}
    for mod_name, mod_info in modules.items():
        target = merge_map.get(mod_name, mod_name)
        if target not in new_modules:
            new_modules[target] = {
                "genes": list(mod_info["genes"]),
                "color": mod_info["color"],
                "size": mod_info["size"],
            }
        else:
            new_modules[target]["genes"].extend(mod_info["genes"])
            new_modules[target]["size"] = len(new_modules[target]["genes"])

    # Recompute eigengenes for merged modules
    log.info(f"After merging: {len(new_modules)} modules")
    return new_modules, None  # Caller should recompute eigengenes


def module_trait_correlation(
    me_df: pd.DataFrame,
    pheno_df: pd.DataFrame,
    dataset_id: str,
) -> pd.DataFrame:
    """Correlate module eigengenes with disease status."""
    # Binary trait: SCZ=1, control=0
    trait = pheno_df["group"].map({"SCZ": 1, "control": 0})
    trait = trait.dropna()
    common = me_df.index.intersection(trait.index)
    trait = trait[common]

    results = []
    for mod_name in me_df.columns:
        me = me_df.loc[common, mod_name]
        r, p = stats.pearsonr(me.values, trait.values)
        results.append({
            "module": mod_name,
            "correlation": r,
            "pvalue": p,
            "n_samples": len(common),
        })

    mt_df = pd.DataFrame(results).sort_values("pvalue")

    # Heatmap
    configure_plotting()
    fig, ax = plt.subplots(figsize=(4, max(6, len(me_df.columns) * 0.4)))

    cors = mt_df.set_index("module")["correlation"]
    pvals = mt_df.set_index("module")["pvalue"]

    # Create annotation: r (p)
    annot = cors.apply(lambda r: f"{r:.2f}") + "\n" + pvals.apply(
        lambda p: f"(p={p:.1e})" if p < 0.001 else f"(p={p:.3f})"
    )

    heatmap_data = cors.values.reshape(-1, 1)
    sns.heatmap(
        heatmap_data,
        annot=annot.values.reshape(-1, 1),
        fmt="",
        cmap="RdBu_r",
        center=0,
        vmin=-1, vmax=1,
        yticklabels=cors.index,
        xticklabels=["SCZ vs Control"],
        ax=ax,
        cbar_kws={"label": "Correlation"},
    )
    ax.set_title(f"Module-Trait Correlation: {dataset_id}")

    savefig(fig, f"{dataset_id}_module_trait_heatmap")

    return mt_df


def identify_hub_genes(
    expr_df: pd.DataFrame,
    modules: dict,
    me_df: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    """Identify hub genes per module by module membership (kME)."""
    hub_rows = []
    for mod_name, mod_info in modules.items():
        if mod_name.startswith("M0") or mod_name not in me_df.columns:
            continue
        genes_in_module = [g for g in mod_info["genes"] if g in expr_df.index]
        if len(genes_in_module) < 3:
            continue

        eigengene = me_df[mod_name].values
        for gene in genes_in_module:
            gene_expr = expr_df.loc[gene].values
            # Align lengths
            min_len = min(len(gene_expr), len(eigengene))
            kme, _ = stats.pearsonr(gene_expr[:min_len], eigengene[:min_len])
            hub_rows.append({
                "gene": gene,
                "module": mod_name,
                "kME": abs(kme),
                "kME_signed": kme,
            })

    hub_df = pd.DataFrame(hub_rows)

    # Get top N per module
    top_hubs = (
        hub_df.sort_values("kME", ascending=False)
        .groupby("module")
        .head(top_n)
        .reset_index(drop=True)
    )

    log.info(f"Identified {len(top_hubs)} hub genes across {top_hubs['module'].nunique()} modules")
    return top_hubs


def run(dataset_id: str = "GSE38484") -> dict:
    """Run Stage 3: WGCNA-style co-expression network analysis."""
    log.info(f"\n{'='*60}\nStage 3: Co-expression Network - {dataset_id}\n{'='*60}")

    # Load data
    expr_df = load_df(config.DATA_PROCESSED / f"{dataset_id}_expression.csv")
    pheno_df = load_df(config.DATA_PROCESSED / f"{dataset_id}_phenotype.csv")

    # Select most variable genes
    var_expr = select_variable_genes(expr_df, config.WGCNA_TOP_VARIABLE_GENES)

    # Select soft-thresholding power
    power = select_soft_power(var_expr)

    # Build TOM
    tom, adj = build_tom(var_expr, power)

    # Detect modules
    modules, linkage_matrix = detect_modules(
        tom, var_expr.index, config.WGCNA_MIN_MODULE_SIZE
    )

    # Module eigengenes
    me_df = compute_module_eigengenes(var_expr, modules)

    # Merge similar modules
    modules, _ = merge_similar_modules(modules, me_df, config.WGCNA_MERGE_CUT_HEIGHT)
    me_df = compute_module_eigengenes(var_expr, modules)

    # Module-trait correlation
    mt_df = module_trait_correlation(me_df, pheno_df, dataset_id)

    # Hub genes
    hub_df = identify_hub_genes(var_expr, modules, me_df, config.WGCNA_HUB_GENES_PER_MODULE)

    # Save results
    # Gene-to-module mapping
    gene_module_rows = []
    for mod_name, mod_info in modules.items():
        for gene in mod_info["genes"]:
            gene_module_rows.append({
                "gene": gene,
                "module": mod_name,
                "module_color": mod_info["color"],
            })
    gene_module_df = pd.DataFrame(gene_module_rows)

    save_df(gene_module_df, config.RESULTS_DIR / f"{dataset_id}_modules.csv",
            f"{dataset_id} module assignments")
    save_df(me_df, config.RESULTS_DIR / f"{dataset_id}_module_eigengenes.csv",
            f"{dataset_id} module eigengenes")
    save_df(mt_df, config.RESULTS_DIR / f"{dataset_id}_module_trait.csv",
            f"{dataset_id} module-trait correlations")
    save_df(hub_df, config.RESULTS_DIR / f"{dataset_id}_hub_genes.csv",
            f"{dataset_id} hub genes")

    return {
        "modules": modules,
        "eigengenes": me_df,
        "module_trait": mt_df,
        "hub_genes": hub_df,
    }
