"""
Central configuration for the schizophrenia blood expression analysis pipeline.
All paths, parameters, dataset configs, and gene lists live here.
"""
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path("I:/Scratch/schizophrenia-genomics")
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
REFERENCE_DIR = PROJECT_ROOT / "reference"

# --- GEO Datasets ---
DATASETS = {
    "GSE38484": {
        "geo_id": "GSE38484",
        "platform": "GPL6947",
        "tissue": "whole_blood",
        "description": "Whole blood co-expression network in schizophrenia",
        "sample_size_approx": 202,
        "stat_test": "ttest",
    },
    "GSE27383": {
        "geo_id": "GSE27383",
        "platform": "GPL570",
        "tissue": "PBMC",
        "description": "PBMC expression in acutely psychotic schizophrenia (Affymetrix)",
        "sample_size_approx": 72,
        "stat_test": "ttest",
    },
    "GSE21138": {
        "geo_id": "GSE21138",
        "platform": "GPL570",
        "tissue": "prefrontal_cortex",
        "description": "Post-mortem prefrontal cortex BA46 (30 SCZ / 29 ctrl, medicated)",
        "sample_size_approx": 59,
        "stat_test": "ttest",
    },
}

# --- Queued Datasets (not yet downloaded/processed) ---
DATASETS_QUEUED = {
    "GSE53987": {
        "geo_id": "GSE53987",
        "platform": "GPL570",
        "tissue": "PFC_hippocampus_striatum",
        "description": "Three brain regions (19 SCZ / 19 ctrl per region, also BD + MDD)",
        "sample_size_approx": 205,
        "priority": 1,
    },
    "GSE92538": {
        "geo_id": "GSE92538",
        "platform": "GPL570",
        "tissue": "DLPFC",
        "description": "Pritzker Consortium DLPFC (363 total, SCZ + BD + MDD + ctrl)",
        "sample_size_approx": 363,
        "priority": 1,
    },
    "GSE12649": {
        "geo_id": "GSE12649",
        "platform": "GPL96",
        "tissue": "prefrontal_cortex",
        "description": "PFC BA46 mitochondrial dysfunction focus (34 SCZ / 34 ctrl / 34 BD)",
        "sample_size_approx": 102,
        "priority": 1,
        "notes": "Mitochondrial focus - relevant to ketogenic/metabolic hypothesis",
    },
    "GSE17612": {
        "geo_id": "GSE17612",
        "platform": "GPL570",
        "tissue": "prefrontal_cortex",
        "description": "Anterior PFC BA10 (28 SCZ / 23 ctrl)",
        "sample_size_approx": 51,
        "priority": 2,
    },
    "GSE35978": {
        "geo_id": "GSE35978",
        "platform": "GPL6244",
        "tissue": "cerebellum_parietal",
        "description": "SMRI collections: cerebellum + parietal cortex (312 total)",
        "sample_size_approx": 312,
        "priority": 2,
    },
}

# --- Differential Expression ---
DE_PVALUE_THRESHOLD = 0.05
DE_LOGFC_THRESHOLD = 0.5
DE_TOP_GENES_LABEL = 10

# --- WGCNA Parameters ---
WGCNA_TOP_VARIABLE_GENES = 5000
WGCNA_POWER_RANGE = range(1, 21)
WGCNA_SFT_R2_THRESHOLD = 0.85
WGCNA_MIN_MODULE_SIZE = 30
WGCNA_MERGE_CUT_HEIGHT = 0.25
WGCNA_HUB_GENES_PER_MODULE = 10

# --- Pathway Analysis ---
GSEA_GENE_SETS = [
    "KEGG_2021_Human",
    "GO_Biological_Process_2021",
    "Reactome_2022",
]

SCZ_PATHWAY_KEYWORDS = [
    "glutam",
    "dopamin",
    "GABA",
    "serotonin",
    "synap",
    "neurotrophin",
    "inflamm",
    "oxidative stress",
    "calcium signal",
    "MAPK",
    "Wnt",
    "mTOR",
    "BDNF",
    "NMDA",
    "nicotinic",
    "cholinergic",
    "immune",
    "complement",
    "myelin",
    "axon guid",
    "mitochond",
    "ketone",
    "fatty acid oxid",
    "insulin",
    "glucose metabol",
    "HDAC",
    "histone deacetyl",
    "adenosine",
    "folate",
    "one carbon",
    "methyl",
]

# --- Plotting ---
FIGURE_DPI = 300
FIGURE_FORMAT = "png"
