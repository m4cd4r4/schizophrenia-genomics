"""
Stage 8: Protein-Protein Interaction (PPI) network analysis.

Queries STRING DB API for interactions among high-evidence genes
(convergent DE + hub + risk locus), builds a networkx graph,
identifies hub proteins by degree, and detects network communities.
"""
import time
import json
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import requests

import config
from pipeline.utils import get_logger, save_df, configure_plotting, savefig

log = get_logger("stage8")

STRING_API_BASE = "https://string-db.org/api"
SPECIES_HUMAN = 9606
MIN_SCORE = 700   # STRING confidence 0-1000; 700 = high confidence


def query_string_network(
    genes: list[str],
    min_score: int = MIN_SCORE,
    retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch STRING interaction network for a gene list.

    Returns DataFrame with columns: gene_a, gene_b, score.
    """
    if not genes:
        return pd.DataFrame()

    url = f"{STRING_API_BASE}/json/network"
    params = {
        "identifiers": "\r".join(genes),
        "species": SPECIES_HUMAN,
        "required_score": min_score,
        "caller_identity": "schizophrenia_genomics_pipeline",
    }

    for attempt in range(retries):
        try:
            log.info(f"Querying STRING for {len(genes)} genes (min_score={min_score})...")
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                log.warning("STRING returned empty network")
                return pd.DataFrame()

            edges = pd.DataFrame([
                {
                    "gene_a": d.get("preferredName_A", d.get("stringId_A", "")),
                    "gene_b": d.get("preferredName_B", d.get("stringId_B", "")),
                    "score": d.get("score", 0),
                }
                for d in data
            ])
            log.info(f"STRING returned {len(edges)} interactions")
            return edges

        except requests.Timeout:
            log.warning(f"STRING timeout (attempt {attempt+1}/{retries})")
            time.sleep(5)
        except requests.RequestException as e:
            log.warning(f"STRING request error: {e} (attempt {attempt+1}/{retries})")
            time.sleep(5)

    log.error("STRING query failed after all retries - returning empty network")
    return pd.DataFrame()


def build_network(
    edges: pd.DataFrame,
    gene_metadata: pd.DataFrame | None = None,
) -> nx.Graph:
    """Build networkx graph from STRING edges."""
    G = nx.Graph()

    for _, row in edges.iterrows():
        G.add_edge(row["gene_a"], row["gene_b"], weight=row["score"])

    if gene_metadata is not None and not gene_metadata.empty:
        for gene in G.nodes:
            row = gene_metadata[gene_metadata["gene"] == gene]
            if not row.empty:
                for col in row.columns:
                    if col != "gene":
                        G.nodes[gene][col] = row.iloc[0][col]

    return G


def compute_network_stats(G: nx.Graph) -> pd.DataFrame:
    """Compute centrality metrics per node."""
    if len(G.nodes) == 0:
        return pd.DataFrame()

    degree_centrality = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, normalized=True)

    try:
        # eigenvector centrality can fail on disconnected graphs
        eigen = nx.eigenvector_centrality(G, max_iter=500, weight="weight")
    except nx.PowerIterationFailedConvergence:
        eigen = {n: 0.0 for n in G.nodes}

    rows = []
    for node in G.nodes:
        rows.append({
            "gene": node,
            "degree": G.degree(node),
            "degree_centrality": degree_centrality[node],
            "betweenness": betweenness[node],
            "eigenvector": eigen.get(node, 0.0),
            **{k: v for k, v in G.nodes[node].items() if k != "gene"},
        })

    stats_df = pd.DataFrame(rows).sort_values("degree", ascending=False)
    return stats_df


def detect_communities(G: nx.Graph) -> dict[str, int]:
    """Detect communities using Louvain-style greedy modularity."""
    if len(G.nodes) < 3:
        return {n: 0 for n in G.nodes}

    try:
        communities = nx.community.greedy_modularity_communities(G)
        node_community = {}
        for i, comm in enumerate(communities):
            for node in comm:
                node_community[node] = i
        return node_community
    except Exception as e:
        log.warning(f"Community detection failed: {e}")
        return {n: 0 for n in G.nodes}


def plot_ppi_network(
    G: nx.Graph,
    node_stats: pd.DataFrame,
    communities: dict[str, int],
    title: str,
    output_name: str,
    highlight_genes: list[str] | None = None,
):
    """Visualize PPI network with community coloring and degree-sized nodes."""
    configure_plotting()

    if len(G.nodes) == 0:
        log.warning("Empty graph - skipping PPI plot")
        return

    # Only plot largest connected component if graph is large
    if len(G.nodes) > 200:
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()
        log.info(f"Plotting largest component: {len(G.nodes)} nodes")

    fig, ax = plt.subplots(figsize=(14, 12))

    # Layout
    if len(G.nodes) < 50:
        pos = nx.spring_layout(G, k=2, seed=42)
    else:
        pos = nx.kamada_kawai_layout(G)

    # Node sizes proportional to degree
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) if degrees else 1
    node_sizes = [200 + 1000 * (degrees[n] / max_deg) ** 1.5 for n in G.nodes]

    # Node colors by community
    n_communities = max(communities.values()) + 1 if communities else 1
    cmap = plt.cm.get_cmap("tab20", max(n_communities, 2))
    node_colors = [cmap(communities.get(n, 0)) for n in G.nodes]

    # Edge weights
    edge_weights = [G[u][v].get("weight", 500) / 1000 for u, v in G.edges]

    # Draw
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        alpha=0.3, width=edge_weights, edge_color="grey",
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_size=node_sizes, node_color=node_colors, alpha=0.85,
    )

    # Labels only for hub genes (top by degree) + highlight genes
    top_n = min(20, len(G.nodes))
    top_genes = set(
        node_stats.nlargest(top_n, "degree")["gene"].tolist()
        if "gene" in node_stats.columns else []
    )
    if highlight_genes:
        top_genes |= set(highlight_genes) & set(G.nodes)

    labels = {n: n for n in G.nodes if n in top_genes}
    nx.draw_networkx_labels(
        G, pos, labels=labels, ax=ax,
        font_size=7, font_weight="bold",
    )

    ax.set_title(title, fontsize=13, fontweight="bold", pad=20)
    ax.axis("off")

    # Legend: communities
    if n_communities <= 10:
        from matplotlib.patches import Patch
        handles = [
            Patch(facecolor=cmap(i), label=f"Community {i+1}")
            for i in range(n_communities)
        ]
        ax.legend(
            handles=handles, loc="lower right",
            fontsize=8, framealpha=0.8,
        )

    plt.tight_layout()
    savefig(fig, output_name)


def run(dataset_ids: list[str] | None = None):
    """Run Stage 8 PPI network analysis."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    log.info(f"\n{'='*60}\nStage 8: PPI Network Analysis\n{'='*60}")

    # Load high-evidence genes (cross-dataset convergent genes from stage4)
    he_path = config.RESULTS_DIR / "high_evidence_genes.csv"
    if not he_path.exists():
        log.error("high_evidence_genes.csv not found - run stage4 first")
        return

    he_df = pd.read_csv(he_path)
    log.info(f"Loaded {len(he_df)} high-evidence genes from stage4")

    for ds_id in dataset_ids:
        log.info(f"\n--- {ds_id} ---")

        # Get dataset-specific DE results for additional genes
        de_path = config.RESULTS_DIR / f"{ds_id}_de_results.csv"
        if not de_path.exists():
            log.warning(f"No DE results for {ds_id}")
            continue

        de_df = pd.read_csv(de_path, index_col=0)

        # Combine high-evidence genes + top DE genes (by |logFC| and significance)
        he_genes = he_df[he_df["dataset"] == ds_id]["gene"].tolist() if "dataset" in he_df.columns else he_df["gene"].tolist()
        de_sig = de_df[
            (de_df["padj"] < 0.05) & (de_df["logFC"].abs() > 0.3)
        ].nlargest(50, "logFC")["gene"].tolist()
        de_sig_down = de_df[
            (de_df["padj"] < 0.05) & (de_df["logFC"].abs() > 0.3)
        ].nsmallest(50, "logFC")["gene"].tolist()

        # Load hub genes if available
        hub_path = config.RESULTS_DIR / f"{ds_id}_hub_genes.csv"
        hub_genes = []
        if hub_path.exists():
            hub_df = pd.read_csv(hub_path)
            hub_genes = hub_df["gene"].tolist() if "gene" in hub_df.columns else []

        gene_pool = list(set(he_genes + de_sig + de_sig_down + hub_genes[:30]))
        gene_pool = [g for g in gene_pool if isinstance(g, str) and len(g) > 1]
        gene_pool = gene_pool[:150]  # STRING handles up to ~2000 but keep manageable

        log.info(f"Gene pool size: {len(gene_pool)}")

        # Query STRING
        edges = query_string_network(gene_pool, min_score=MIN_SCORE)

        if edges.empty:
            log.warning(f"{ds_id}: no STRING interactions found - trying lower threshold")
            edges = query_string_network(gene_pool, min_score=400)

        if edges.empty:
            log.warning(f"{ds_id}: STRING returned no interactions - skipping")
            continue

        save_df(
            edges,
            config.RESULTS_DIR / f"{ds_id}_ppi_edges.csv",
            f"{ds_id} PPI edges",
        )

        # Build gene metadata for node annotation
        meta_cols = {"gene": [], "is_DE": [], "logFC": [], "is_hub": [], "is_risk": []}
        risk_genes = set()
        for gf in [config.REFERENCE_DIR / "pgc3_risk_genes.csv",
                   config.REFERENCE_DIR / "family_study_genes.csv"]:
            if gf.exists():
                risk_genes |= set(pd.read_csv(gf)["gene"].tolist())

        all_genes_in_graph = list(
            set(edges["gene_a"].tolist() + edges["gene_b"].tolist())
        )
        for gene in all_genes_in_graph:
            row = de_df[de_df["gene"] == gene] if "gene" in de_df.columns else de_df[de_df.index == gene]
            if not row.empty:
                meta_cols["gene"].append(gene)
                meta_cols["is_DE"].append(bool(row.iloc[0]["padj"] < 0.05))
                meta_cols["logFC"].append(float(row.iloc[0]["logFC"]))
            else:
                meta_cols["gene"].append(gene)
                meta_cols["is_DE"].append(False)
                meta_cols["logFC"].append(0.0)
            meta_cols["is_hub"].append(gene in hub_genes)
            meta_cols["is_risk"].append(gene in risk_genes)

        gene_meta = pd.DataFrame(meta_cols)

        # Build graph
        G = build_network(edges, gene_meta)
        log.info(
            f"Network: {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges"
        )

        if G.number_of_nodes() < 3:
            log.warning("Network too small - skipping")
            continue

        # Stats
        node_stats = compute_network_stats(G)
        save_df(
            node_stats,
            config.RESULTS_DIR / f"{ds_id}_ppi_node_stats.csv",
            f"{ds_id} PPI node stats",
        )

        # Communities
        communities = detect_communities(G)

        log.info(f"Top 10 hub proteins by degree:")
        for _, row in node_stats.head(10).iterrows():
            gene_name = row.get("gene", "?")
            is_risk = row.get("is_risk", False)
            is_hub = row.get("is_hub", False)
            flags = []
            if is_risk:
                flags.append("risk")
            if is_hub:
                flags.append("hub")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            log.info(
                f"  {gene_name}: degree={row['degree']}, "
                f"betweenness={row['betweenness']:.3f}{flag_str}"
            )

        # Plot
        highlight = [g for g in risk_genes if g in G.nodes][:20]
        plot_ppi_network(
            G, node_stats, communities,
            title=f"PPI Network: {ds_id} (n={G.number_of_nodes()} proteins)",
            output_name=f"{ds_id}_ppi_network",
            highlight_genes=highlight,
        )

    log.info("\nStage 8 complete.")
