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
]

# --- Plotting ---
FIGURE_DPI = 300
FIGURE_FORMAT = "png"
