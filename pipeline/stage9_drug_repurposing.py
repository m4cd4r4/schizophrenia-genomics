"""
Stage 9: Drug repurposing via Connectivity Map (CMap) / LINCS L1000 approach.

Cross-references our disease gene expression signature against thousands of
drug perturbation signatures from LINCS L1000 and GEO. Drugs whose signatures
anti-correlate with the SCZ signature (reverse the disease state) are
repurposing candidates.

Method:
    1. Build a ranked gene list from DE results (sorted by t-statistic)
    2. Run GSEA prerank against drug perturbation libraries
    3. Negative enrichment = drug reverses disease signature = candidate
    4. Cross-reference with known psychiatric drugs and SCZ-relevant pathways
    5. Score and rank candidates

Drug perturbation libraries used:
    - LINCS_L1000_Chem_Pert_Consensus_Sigs (consensus chemical perturbation)
    - Drug_Perturbations_from_GEO_down/up (GEO-derived drug effects)
    - Old_CMAP_down/up (original Connectivity Map)
    - DrugMatrix (drug toxicogenomics)
"""
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import gseapy
from gseapy import prerank

import config
from pipeline.utils import get_logger, save_df, configure_plotting, savefig

log = get_logger("stage9")

# Drug perturbation libraries to query
DRUG_LIBRARIES = [
    "LINCS_L1000_Chem_Pert_Consensus_Sigs",
    "Drug_Perturbations_from_GEO_down",
    "Drug_Perturbations_from_GEO_up",
    "Old_CMAP_down",
    "Old_CMAP_up",
    "DrugMatrix",
]

# Known psychiatric/CNS drugs to highlight in results
KNOWN_PSYCHIATRIC_DRUGS = re.compile(
    r"haloperidol|clozapine|olanzapine|risperidone|quetiapine|aripiprazole"
    r"|ziprasidone|chlorpromazine|fluphenazine|perphenazine|thioridazine"
    r"|lithium|valproic|valproate|carbamazepine|lamotrigine"
    r"|fluoxetine|sertraline|paroxetine|citalopram|escitalopram|venlafaxine"
    r"|ketamine|phencyclidine|memantine|dizocilpine|MK.801"
    r"|diazepam|lorazepam|alprazolam|midazolam"
    r"|amphetamine|methylphenidate|modafinil"
    r"|clonidine|guanfacine|propranolol"
    r"|dexamethasone|hydrocortisone|prednisone",
    re.IGNORECASE,
)

# Drug classes of particular interest for SCZ repurposing
REPURPOSING_INTEREST = re.compile(
    r"anti.inflammat|NSAID|ibuprofen|celecoxib|aspirin|minocycline"
    r"|statin|simvastatin|lovastatin|atorvastatin"
    r"|metformin|pioglitazone|rosiglitazone"
    r"|omega.3|EPA|DHA|fish.oil"
    r"|N.acetylcysteine|NAC"
    r"|vitamin.D|cholecalciferol"
    r"|estrogen|estradiol|raloxifene"
    r"|erythropoietin|EPO"
    r"|cannabidiol|CBD"
    r"|mifepristone|RU.486"
    r"|oxytocin|vasopressin"
    r"|galantamine|donepezil|rivastigmine"
    r"|memantine|amantadine"
    r"|pregnenolone|DHEA|allopregnanolone",
    re.IGNORECASE,
)


def build_drug_signature(de_df: pd.DataFrame) -> pd.Series:
    """
    Build a ranked gene signature from DE results for GSEA prerank.

    Uses t-statistic (or -log10(p) * sign(logFC)) as the ranking metric.
    Positive = upregulated in SCZ, negative = downregulated.
    """
    if "stat" in de_df.columns:
        ranking = de_df.set_index("gene")["stat"]
    else:
        # Fallback: signed -log10(pvalue)
        ranking = -np.log10(de_df["pvalue"].clip(lower=1e-300)) * np.sign(de_df["logFC"])
        ranking.index = de_df["gene"]

    ranking = ranking.dropna()
    ranking = ranking[~ranking.index.duplicated()]
    ranking = ranking.sort_values(ascending=False)

    log.info(f"Drug signature: {len(ranking)} genes ranked")
    return ranking


def query_drug_perturbations(
    ranking: pd.Series,
    libraries: list[str] | None = None,
) -> pd.DataFrame:
    """
    Run GSEA prerank against drug perturbation libraries.

    Returns combined results with drug name, NES, FDR, and library source.
    """
    if libraries is None:
        libraries = DRUG_LIBRARIES

    all_results = []

    for lib in libraries:
        log.info(f"  Querying {lib}...")
        try:
            res = prerank(
                rnk=ranking,
                gene_sets=lib,
                min_size=5,
                max_size=500,
                permutation_num=100,
                outdir=None,
                no_plot=True,
                verbose=False,
                seed=42,
            )

            if res.res2d is not None and not res.res2d.empty:
                df = res.res2d.copy()
                df["library"] = lib
                df["drug_name"] = df["Term"].apply(_extract_drug_name)
                all_results.append(df)
                n_sig = (df["FDR q-val"] < 0.25).sum()
                log.info(f"    {len(df)} terms tested, {n_sig} significant (FDR<0.25)")
            else:
                log.warning(f"    {lib}: no results returned")
        except Exception as e:
            log.warning(f"    {lib}: query failed - {e}")

    if not all_results:
        return pd.DataFrame()

    combined = pd.concat(all_results, ignore_index=True)
    return combined


def _extract_drug_name(term: str) -> str:
    """Extract clean drug name from enrichment term string."""
    # Handle patterns like "drug_name human GSE12345" or "drug-name-500nM-24h"
    name = term.split(" ")[0]  # first word is usually the drug
    name = re.sub(r"[-_](?:human|mouse|rat|MCF7|HL60|PC3).*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[-_](?:\d+[nuμ]M|hrs?|days?|24h|48h|72h).*", "", name, flags=re.IGNORECASE)
    name = name.strip("-_ ")
    return name if name else term[:40]


def score_repurposing_candidates(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Score drugs as repurposing candidates.

    A good candidate has:
    - Negative NES (reverses disease signature)
    - Low FDR
    - Consistent across libraries
    - Not a known antipsychotic (those confirm mechanism, not repurpose)
    """
    if results_df.empty:
        return pd.DataFrame()

    # Focus on drugs with negative NES (reversing disease)
    reversing = results_df[results_df["NES"] < 0].copy()

    if reversing.empty:
        log.warning("No drugs with negative NES found")
        return pd.DataFrame()

    # Aggregate per drug across libraries
    drug_scores = []
    for drug in reversing["drug_name"].unique():
        drug_rows = reversing[reversing["drug_name"] == drug]
        n_libs = drug_rows["library"].nunique()
        mean_nes = drug_rows["NES"].mean()
        min_fdr = drug_rows["FDR q-val"].min()
        best_term = drug_rows.loc[drug_rows["FDR q-val"].idxmin(), "Term"]

        is_known_psych = bool(KNOWN_PSYCHIATRIC_DRUGS.search(drug))
        is_repurposing = bool(REPURPOSING_INTEREST.search(drug))

        # Composite score: lower = better candidate
        # Penalize high FDR, reward multiple library hits, reward strong reversal
        score = (
            min_fdr * 0.4
            + (1 - n_libs / len(DRUG_LIBRARIES)) * 0.3
            + (1 + mean_nes) * 0.3  # NES is negative, so more negative = lower score
        )

        drug_scores.append({
            "drug_name": drug,
            "mean_NES": mean_nes,
            "min_FDR": min_fdr,
            "n_libraries": n_libs,
            "best_term": best_term,
            "is_known_psychiatric": is_known_psych,
            "is_repurposing_interest": is_repurposing,
            "composite_score": score,
        })

    scored = pd.DataFrame(drug_scores).sort_values("composite_score")
    return scored


def plot_drug_candidates(
    scored_df: pd.DataFrame,
    dataset_id: str,
    top_n: int = 30,
):
    """Horizontal bar chart of top drug repurposing candidates."""
    configure_plotting()

    if scored_df.empty:
        return

    top = scored_df.head(top_n).copy()
    top = top.sort_values("mean_NES", ascending=True)

    colors = []
    for _, row in top.iterrows():
        if row["is_known_psychiatric"]:
            colors.append("#ff7f0e")  # orange = known psychiatric
        elif row["is_repurposing_interest"]:
            colors.append("#2ca02c")  # green = repurposing interest
        else:
            colors.append("#1f77b4")  # blue = novel

    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.3)))

    y_pos = range(len(top))
    bars = ax.barh(y_pos, top["mean_NES"].values, color=colors, alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top["drug_name"].values, fontsize=8)
    ax.set_xlabel("Mean NES (negative = reverses disease signature)")
    ax.set_title(f"Drug Repurposing Candidates: {dataset_id}", fontweight="bold")
    ax.axvline(0, color="black", lw=0.5)

    # Add FDR annotation
    for i, (_, row) in enumerate(top.iterrows()):
        fdr_str = f"FDR={row['min_FDR']:.2e}" if row["min_FDR"] < 0.05 else ""
        if fdr_str:
            ax.text(
                row["mean_NES"] - 0.05, i, fdr_str,
                va="center", ha="right", fontsize=6, color="white", fontweight="bold",
            )

    # Legend
    handles = [
        mpatches.Patch(color="#1f77b4", label="Novel candidate"),
        mpatches.Patch(color="#2ca02c", label="Known repurposing interest"),
        mpatches.Patch(color="#ff7f0e", label="Known psychiatric drug"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    savefig(fig, f"{dataset_id}_drug_repurposing")


def plot_drug_mechanism_network(
    scored_df: pd.DataFrame,
    results_df: pd.DataFrame,
    dataset_id: str,
):
    """
    Scatter: NES vs -log10(FDR) for all drug perturbations.
    Highlights known psychiatric drugs and repurposing candidates.
    """
    configure_plotting()

    if results_df.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    sig = results_df.copy()
    sig["FDR q-val"] = pd.to_numeric(sig["FDR q-val"], errors="coerce").fillna(1.0)
    sig["NES"] = pd.to_numeric(sig["NES"], errors="coerce").fillna(0.0)
    sig["neg_log_fdr"] = -np.log10(sig["FDR q-val"].clip(lower=1e-10).values.astype(float))
    sig["drug_name"] = sig["Term"].apply(_extract_drug_name)

    # Categorize
    is_psych = sig["drug_name"].apply(lambda d: bool(KNOWN_PSYCHIATRIC_DRUGS.search(d)))
    is_repurpose = sig["drug_name"].apply(lambda d: bool(REPURPOSING_INTEREST.search(d)))
    other = ~(is_psych | is_repurpose)

    ax.scatter(sig.loc[other, "NES"], sig.loc[other, "neg_log_fdr"],
               c="grey", alpha=0.15, s=6, label="Other drugs")
    ax.scatter(sig.loc[is_psych, "NES"], sig.loc[is_psych, "neg_log_fdr"],
               c="#ff7f0e", alpha=0.7, s=25, label="Known psychiatric", zorder=3)
    ax.scatter(sig.loc[is_repurpose, "NES"], sig.loc[is_repurpose, "neg_log_fdr"],
               c="#2ca02c", alpha=0.7, s=25, label="Repurposing interest", zorder=3)

    # Label top candidates
    top_candidates = scored_df.head(10)["drug_name"].tolist() if not scored_df.empty else []
    for _, row in sig.iterrows():
        if row["drug_name"] in top_candidates and row["NES"] < -1:
            ax.annotate(
                row["drug_name"], (row["NES"], row["neg_log_fdr"]),
                fontsize=6, ha="center",
                arrowprops=dict(arrowstyle="-", color="grey", lw=0.5),
            )

    ax.axvline(0, color="black", lw=0.5, ls="--")
    ax.axhline(-np.log10(0.25), color="grey", lw=0.5, ls="--", label="FDR=0.25")
    ax.set_xlabel("Normalized Enrichment Score (NES)")
    ax.set_ylabel("-log10(FDR)")
    ax.set_title(f"Drug Perturbation Landscape: {dataset_id}", fontweight="bold")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    savefig(fig, f"{dataset_id}_drug_landscape")


def run(dataset_ids: list[str] | None = None):
    """Run Stage 9 drug repurposing analysis."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 9: Drug Repurposing (CMap/LINCS)\n{'='*60}")

    for ds_id in dataset_ids:
        de_path = config.RESULTS_DIR / f"{ds_id}_de_results.csv"
        if not de_path.exists():
            log.warning(f"{ds_id}: no DE results - run stage2 first")
            continue

        log.info(f"\n--- {ds_id} ---")
        de_df = pd.read_csv(de_path, index_col=0)

        # Build ranked signature
        ranking = build_drug_signature(de_df)

        # Query drug perturbation libraries
        log.info(f"Querying {len(DRUG_LIBRARIES)} drug perturbation libraries...")
        results_df = query_drug_perturbations(ranking)

        if results_df.empty:
            log.warning(f"{ds_id}: no drug perturbation results")
            continue

        save_df(
            results_df,
            config.RESULTS_DIR / f"{ds_id}_drug_perturbations.csv",
            f"{ds_id} drug perturbation results",
        )

        # Score and rank candidates
        scored = score_repurposing_candidates(results_df)

        if not scored.empty:
            save_df(
                scored,
                config.RESULTS_DIR / f"{ds_id}_drug_candidates.csv",
                f"{ds_id} drug repurposing candidates",
            )

            # Report top findings
            log.info(f"\nTop 15 repurposing candidates (reverse SCZ signature):")
            for i, (_, row) in enumerate(scored.head(15).iterrows()):
                flags = []
                if row["is_known_psychiatric"]:
                    flags.append("KNOWN")
                if row["is_repurposing_interest"]:
                    flags.append("INTEREST")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                log.info(
                    f"  {i+1}. {row['drug_name']}: NES={row['mean_NES']:.2f}, "
                    f"FDR={row['min_FDR']:.2e}, libs={row['n_libraries']}{flag_str}"
                )

            # Known psychiatric drugs in results (mechanism validation)
            psych_hits = scored[scored["is_known_psychiatric"]]
            if not psych_hits.empty:
                log.info(f"\nKnown psychiatric drugs detected ({len(psych_hits)}):")
                for _, row in psych_hits.head(5).iterrows():
                    direction = "reverses" if row["mean_NES"] < 0 else "mimics"
                    log.info(
                        f"  {row['drug_name']}: {direction} SCZ signature "
                        f"(NES={row['mean_NES']:.2f})"
                    )

            # Plots
            plot_drug_candidates(scored, ds_id)
            plot_drug_mechanism_network(scored, results_df, ds_id)

    # Cross-dataset meta-repurposing: drugs that reverse SCZ in multiple datasets
    all_candidates = []
    for ds_id in dataset_ids:
        cand_path = config.RESULTS_DIR / f"{ds_id}_drug_candidates.csv"
        if cand_path.exists():
            df = pd.read_csv(cand_path)
            df["dataset"] = ds_id
            all_candidates.append(df)

    if len(all_candidates) >= 2:
        combined = pd.concat(all_candidates)
        cross_ds = (
            combined.groupby("drug_name")
            .agg(
                n_datasets=("dataset", "nunique"),
                mean_NES=("mean_NES", "mean"),
                best_FDR=("min_FDR", "min"),
                is_known=("is_known_psychiatric", "any"),
                is_repurpose=("is_repurposing_interest", "any"),
            )
            .query("n_datasets >= 2")
            .sort_values("mean_NES")
        )

        if not cross_ds.empty:
            save_df(
                cross_ds.reset_index(),
                config.RESULTS_DIR / "cross_dataset_drug_candidates.csv",
                "Cross-dataset drug repurposing candidates",
            )
            log.info(f"\nCross-dataset candidates (found in {len(all_candidates)} datasets):")
            for _, row in cross_ds.head(10).iterrows():
                log.info(
                    f"  {row.name}: NES={row['mean_NES']:.2f}, "
                    f"datasets={row['n_datasets']}, FDR={row['best_FDR']:.2e}"
                )

    log.info("\nStage 9 complete.")
