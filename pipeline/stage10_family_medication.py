"""
Stage 10: Family-discordant analysis framework + medication dose-response.

Part A - Family Framework (ready for data):
    Implements within-family paired analysis for discordant sibling/twin pairs.
    Currently no public family-structured blood expression data exists on GEO
    for schizophrenia. This framework is ready when such data becomes available
    (e.g., from dbGaP controlled-access datasets).

Part B - Medication Dose-Response (GSE21138):
    Uses post-mortem brain data with detailed antipsychotic medication records
    (chlorpromazine equivalents) to test:
    1. Which blood DE genes correlate with drug dose in brain?
    2. Do our blood signatures reflect disease or medication effects?
    3. Are risk genes dose-dependent (drug-responsive)?

    If a blood DE gene also correlates with drug dose in brain, that gene's
    blood signal may be a medication artifact rather than a disease marker.
"""
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests

import config
from pipeline.utils import get_logger, save_df, configure_plotting, savefig

log = get_logger("stage10")


# ─────────────────────────────────────────────────────────────────────────────
# Part A: Family-discordant analysis framework
# ─────────────────────────────────────────────────────────────────────────────

def paired_family_de(
    expr_df: pd.DataFrame,
    pair_map: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    """
    Within-family paired differential expression.

    For each family with one affected and one unaffected sibling,
    computes the within-pair difference and tests with paired t-test.

    Args:
        expr_df: genes x samples expression matrix
        pair_map: {family_id: (affected_sample_id, unaffected_sample_id)}

    Returns:
        DataFrame with gene, mean_diff, stat, pvalue, padj
    """
    affected = [v[0] for v in pair_map.values() if v[0] in expr_df.columns]
    unaffected = [v[1] for v in pair_map.values() if v[1] in expr_df.columns]

    if len(affected) < 3:
        log.error(f"Too few paired samples: {len(affected)} families")
        return pd.DataFrame()

    log.info(f"Running paired analysis on {len(affected)} family pairs")

    results = []
    for gene in expr_df.index:
        aff_vals = expr_df.loc[gene, affected].values.astype(float)
        unaff_vals = expr_df.loc[gene, unaffected].values.astype(float)

        # Paired differences
        diffs = aff_vals - unaff_vals
        mean_diff = np.mean(diffs)

        # Paired t-test (more powerful than unpaired for related samples)
        stat_val, p_val = stats.ttest_rel(aff_vals, unaff_vals)

        results.append({
            "gene": gene,
            "mean_paired_diff": mean_diff,
            "stat": stat_val,
            "pvalue": p_val,
        })

    de_df = pd.DataFrame(results)
    _, padj, _, _ = multipletests(de_df["pvalue"].values, method="fdr_bh")
    de_df["padj"] = padj
    de_df = de_df.sort_values("padj").reset_index(drop=True)

    n_sig = (de_df["padj"] < 0.05).sum()
    log.info(f"Paired DE significant genes (FDR<0.05): {n_sig}")

    return de_df


def detect_family_structure(pheno_df: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """
    Auto-detect family pair structure from phenotype metadata.

    Looks for family_id, pair_id, twin_id or similar columns.
    Returns {family_id: (affected_sample, unaffected_sample)} or empty dict.
    """
    family_cols = [
        c for c in pheno_df.columns
        if re.search(r"family|pair|twin|sibling|kindred|pedigree", c, re.IGNORECASE)
    ]

    if not family_cols:
        return {}

    log.info(f"Detected family columns: {family_cols}")

    pair_col = family_cols[0]
    pairs = {}

    for family_id, group in pheno_df.groupby(pair_col):
        affected = group[group["group"] == "SCZ"]
        unaffected = group[group["group"] == "control"]

        if len(affected) >= 1 and len(unaffected) >= 1:
            pairs[str(family_id)] = (affected.index[0], unaffected.index[0])

    log.info(f"Found {len(pairs)} discordant family pairs")
    return pairs


# ─────────────────────────────────────────────────────────────────────────────
# Part B: Medication dose-response analysis
# ─────────────────────────────────────────────────────────────────────────────

def extract_drug_doses(pheno_df: pd.DataFrame) -> pd.Series | None:
    """
    Extract chlorpromazine-equivalent doses from phenotype data.

    Looks for dose columns with numeric values (mg).
    Returns Series indexed by sample_id with float dose values.
    """
    dose_cols = [
        c for c in pheno_df.columns
        if re.search(r"dose|chlorpromazine|cpz|medication", c, re.IGNORECASE)
    ]

    if not dose_cols:
        return None

    dose_col = dose_cols[0]
    log.info(f"Using dose column: '{dose_col}'")

    # Extract numeric values
    doses = pheno_df[dose_col].apply(
        lambda x: float(re.search(r"(\d+\.?\d*)", str(x)).group(1))
        if isinstance(x, str) and re.search(r"\d+", str(x))
        else np.nan
    )

    valid = doses.dropna()
    log.info(f"Valid dose values: {len(valid)} samples, range {valid.min():.0f}-{valid.max():.0f} mg CPZ equiv")
    return doses


def medication_dose_response(
    expr_df: pd.DataFrame,
    doses: pd.Series,
) -> pd.DataFrame:
    """
    Correlate gene expression with medication dose.

    For SCZ patients with known drug doses, compute Spearman correlation
    between expression and chlorpromazine-equivalent dose.

    Genes with strong dose-response may be medication artifacts rather
    than disease markers.
    """
    # Align samples
    common = expr_df.columns.intersection(doses.dropna().index)
    if len(common) < 5:
        log.warning(f"Only {len(common)} samples with dose data - too few")
        return pd.DataFrame()

    log.info(f"Computing dose-response for {len(common)} medicated samples")
    dose_vals = doses[common].values.astype(float)

    results = []
    for gene in expr_df.index:
        expr_vals = expr_df.loc[gene, common].values.astype(float)

        # Skip genes with no variance
        if np.std(expr_vals) == 0:
            continue

        rho, pval = stats.spearmanr(expr_vals, dose_vals)

        results.append({
            "gene": gene,
            "spearman_rho": rho,
            "pvalue": pval,
        })

    dose_df = pd.DataFrame(results)
    _, padj, _, _ = multipletests(dose_df["pvalue"].values, method="fdr_bh")
    dose_df["padj"] = padj
    dose_df = dose_df.sort_values("pvalue").reset_index(drop=True)

    n_sig = (dose_df["padj"] < 0.05).sum()
    log.info(f"Dose-responsive genes (FDR<0.05): {n_sig}")

    return dose_df


def cross_reference_blood_brain(
    blood_de: pd.DataFrame,
    brain_dose_response: pd.DataFrame,
    blood_dataset_id: str,
) -> pd.DataFrame:
    """
    Cross-reference blood DE genes with brain dose-responsive genes.

    Genes that are both:
    - Differentially expressed in blood (SCZ vs control)
    - Dose-correlated in brain (dose-responsive)

    ...are potential medication confounders. Their blood signal may
    reflect medication effects rather than disease.

    Genes that are:
    - DE in blood but NOT dose-responsive in brain

    ...are stronger candidates for true disease markers.
    """
    if blood_de.empty or brain_dose_response.empty:
        return pd.DataFrame()

    blood_sig = blood_de[blood_de["padj"] < 0.05][["gene", "logFC", "padj"]].copy()
    blood_sig.columns = ["gene", "blood_logFC", "blood_padj"]

    brain_cols = ["gene", "spearman_rho", "padj"]
    brain_all = brain_dose_response[brain_cols].copy()
    brain_all.columns = ["gene", "brain_dose_rho", "brain_dose_padj"]

    merged = blood_sig.merge(brain_all, on="gene", how="left")

    merged["is_dose_responsive"] = merged["brain_dose_padj"] < 0.05
    merged["confounding_risk"] = "unknown"
    merged.loc[merged["is_dose_responsive"] == True, "confounding_risk"] = "HIGH"
    merged.loc[merged["is_dose_responsive"] == False, "confounding_risk"] = "LOW"
    merged.loc[merged["brain_dose_padj"].isna(), "confounding_risk"] = "unknown"

    n_high = (merged["confounding_risk"] == "HIGH").sum()
    n_low = (merged["confounding_risk"] == "LOW").sum()
    n_unknown = (merged["confounding_risk"] == "unknown").sum()

    log.info(
        f"Blood-brain cross-reference ({blood_dataset_id}):\n"
        f"  {n_high} blood DE genes are dose-responsive in brain (medication confounders)\n"
        f"  {n_low} blood DE genes are NOT dose-responsive (stronger disease markers)\n"
        f"  {n_unknown} blood DE genes not in brain dataset"
    )

    return merged.sort_values("blood_padj")


def plot_dose_response(
    dose_df: pd.DataFrame,
    expr_df: pd.DataFrame,
    doses: pd.Series,
    dataset_id: str,
    top_n: int = 9,
):
    """Plot scatter of top dose-responsive genes."""
    configure_plotting()

    common = expr_df.columns.intersection(doses.dropna().index)
    dose_vals = doses[common].values.astype(float)

    top_genes = dose_df.head(top_n)
    n_plots = min(len(top_genes), top_n)
    ncols = 3
    nrows = (n_plots + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 4 * nrows))
    axes = axes.flatten() if nrows > 1 else [axes] if ncols == 1 else axes.flatten()

    for i, (_, row) in enumerate(top_genes.iterrows()):
        ax = axes[i]
        gene = row["gene"]
        expr_vals = expr_df.loc[gene, common].values.astype(float)

        ax.scatter(dose_vals, expr_vals, alpha=0.6, s=20, color="#1f77b4")
        z = np.polyfit(dose_vals, expr_vals, 1)
        p = np.poly1d(z)
        x_line = np.linspace(dose_vals.min(), dose_vals.max(), 50)
        ax.plot(x_line, p(x_line), "--", color="#d62728", lw=1.5)

        ax.set_title(
            f"{gene}\nrho={row['spearman_rho']:.3f}, p={row['pvalue']:.2e}",
            fontsize=9,
        )
        ax.set_xlabel("CPZ equiv (mg)", fontsize=8)
        ax.set_ylabel("Expression", fontsize=8)

    for j in range(n_plots, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        f"Medication Dose-Response: {dataset_id}",
        fontsize=12, fontweight="bold",
    )
    plt.tight_layout()
    savefig(fig, f"{dataset_id}_dose_response")


def plot_confounding_summary(
    cross_ref: pd.DataFrame,
    blood_dataset_id: str,
    brain_dataset_id: str,
):
    """Volcano-style plot colored by confounding risk."""
    configure_plotting()

    if cross_ref.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    neg_log_p = -np.log10(cross_ref["blood_padj"].clip(lower=1e-300))

    high = cross_ref["confounding_risk"] == "HIGH"
    low = cross_ref["confounding_risk"] == "LOW"
    unknown = cross_ref["confounding_risk"] == "unknown"

    ax.scatter(
        cross_ref.loc[unknown, "blood_logFC"], neg_log_p[unknown],
        c="grey", alpha=0.3, s=8, label=f"Not in brain data ({unknown.sum()})",
    )
    ax.scatter(
        cross_ref.loc[low, "blood_logFC"], neg_log_p[low],
        c="#2ca02c", alpha=0.6, s=12,
        label=f"Disease markers ({low.sum()})",
    )
    ax.scatter(
        cross_ref.loc[high, "blood_logFC"], neg_log_p[high],
        c="#d62728", alpha=0.8, s=18,
        label=f"Medication confounders ({high.sum()})",
    )

    # Label confounders
    confounders = cross_ref[high].nsmallest(10, "blood_padj")
    for _, row in confounders.iterrows():
        ax.annotate(
            row["gene"],
            (row["blood_logFC"], -np.log10(max(row["blood_padj"], 1e-300))),
            fontsize=6, ha="center",
            arrowprops=dict(arrowstyle="-", color="red", lw=0.5),
        )

    ax.set_xlabel("Blood log2FC (SCZ vs Control)")
    ax.set_ylabel("-log10(Blood adjusted p-value)")
    ax.set_title(
        f"Medication Confounding: {blood_dataset_id} (blood) vs {brain_dataset_id} (brain dose)",
        fontsize=10, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    savefig(fig, f"confounding_{blood_dataset_id}_vs_{brain_dataset_id}")


def run(dataset_ids: list[str] | None = None):
    """Run Stage 10: family analysis + medication dose-response."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 10: Family & Medication Analysis\n{'='*60}")

    # ── Part A: Check for family structure in all datasets ──
    log.info("\n--- Part A: Family Structure Detection ---")

    for ds_id in dataset_ids:
        pheno_path = config.DATA_PROCESSED / f"{ds_id}_phenotype.csv"
        if not pheno_path.exists():
            continue

        pheno_df = pd.read_csv(pheno_path, index_col=0)
        pairs = detect_family_structure(pheno_df)

        if pairs:
            log.info(f"{ds_id}: {len(pairs)} family pairs detected - running paired analysis")
            expr_df = pd.read_csv(
                config.DATA_PROCESSED / f"{ds_id}_expression.csv", index_col=0
            )
            de_df = paired_family_de(expr_df, pairs)
            if not de_df.empty:
                save_df(
                    de_df,
                    config.RESULTS_DIR / f"{ds_id}_family_paired_de.csv",
                    f"{ds_id} family paired DE",
                )
        else:
            log.info(f"{ds_id}: No family structure detected")

    log.info(
        "\nNote: Family-structured blood expression data for schizophrenia is not\n"
        "available on GEO. Such data is typically in dbGaP (controlled access).\n"
        "The paired analysis framework above is ready when data becomes available."
    )

    # ── Part B: Medication dose-response (brain datasets with drug data) ──
    log.info("\n--- Part B: Medication Dose-Response ---")

    # Find datasets with medication data
    brain_dose_results = {}
    for ds_id in dataset_ids:
        pheno_path = config.DATA_PROCESSED / f"{ds_id}_phenotype.csv"
        if not pheno_path.exists():
            continue

        pheno_df = pd.read_csv(pheno_path, index_col=0)
        doses = extract_drug_doses(pheno_df)

        if doses is None:
            log.info(f"{ds_id}: No medication dose data")
            continue

        n_valid = doses.dropna().shape[0]
        if n_valid < 5:
            log.info(f"{ds_id}: Only {n_valid} samples with dose data - skipping")
            continue

        log.info(f"\n{ds_id}: Running medication dose-response ({n_valid} dosed samples)")

        expr_df = pd.read_csv(
            config.DATA_PROCESSED / f"{ds_id}_expression.csv", index_col=0
        )

        dose_df = medication_dose_response(expr_df, doses)

        if not dose_df.empty:
            save_df(
                dose_df,
                config.RESULTS_DIR / f"{ds_id}_dose_response.csv",
                f"{ds_id} medication dose-response",
            )

            log.info(f"Top 10 dose-responsive genes in {ds_id}:")
            for _, row in dose_df.head(10).iterrows():
                direction = "+" if row["spearman_rho"] > 0 else "-"
                log.info(
                    f"  {row['gene']}: rho={row['spearman_rho']:.3f} ({direction}dose), "
                    f"padj={row['padj']:.2e}"
                )

            plot_dose_response(dose_df, expr_df, doses, ds_id)
            brain_dose_results[ds_id] = dose_df

    # ── Part C: Cross-reference blood DE with brain dose-response ──
    if brain_dose_results:
        log.info("\n--- Part C: Blood-Brain Confounding Cross-Reference ---")

        blood_datasets = [
            ds_id for ds_id in dataset_ids
            if ds_id not in brain_dose_results
            and (config.RESULTS_DIR / f"{ds_id}_de_results.csv").exists()
        ]

        for blood_id in blood_datasets:
            blood_de = pd.read_csv(
                config.RESULTS_DIR / f"{blood_id}_de_results.csv", index_col=0
            )

            for brain_id, brain_dose in brain_dose_results.items():
                log.info(f"\nCross-referencing {blood_id} (blood) vs {brain_id} (brain)...")

                cross_ref = cross_reference_blood_brain(
                    blood_de, brain_dose, blood_id
                )

                if not cross_ref.empty:
                    save_df(
                        cross_ref,
                        config.RESULTS_DIR / f"confounding_{blood_id}_vs_{brain_id}.csv",
                        f"Confounding {blood_id} vs {brain_id}",
                    )
                    plot_confounding_summary(cross_ref, blood_id, brain_id)

                    # Check risk genes specifically
                    risk_genes = set()
                    for gf in [
                        config.REFERENCE_DIR / "pgc3_risk_genes.csv",
                        config.REFERENCE_DIR / "family_study_genes.csv",
                    ]:
                        if gf.exists():
                            risk_genes |= set(pd.read_csv(gf)["gene"].tolist())

                    risk_confounded = cross_ref[
                        (cross_ref["gene"].isin(risk_genes))
                        & (cross_ref["confounding_risk"] == "HIGH")
                    ]
                    risk_clean = cross_ref[
                        (cross_ref["gene"].isin(risk_genes))
                        & (cross_ref["confounding_risk"] == "LOW")
                    ]

                    if not risk_confounded.empty:
                        log.warning(
                            f"Risk genes that may be medication confounders: "
                            f"{risk_confounded['gene'].tolist()}"
                        )
                    if not risk_clean.empty:
                        log.info(
                            f"Risk genes validated as disease markers (not dose-responsive): "
                            f"{risk_clean['gene'].tolist()[:15]}"
                        )

    log.info("\nStage 10 complete.")
