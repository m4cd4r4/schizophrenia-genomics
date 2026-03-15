"""
Central configuration for the genomics website backend.
Paths resolved from env vars so the app runs on Linux without hardcoded Windows paths.
"""
import os
from pathlib import Path

# ── Deployment-configurable paths ──────────────────────────────────────────
# DATA_DIR: directory containing genomics.duckdb and chroma_store/
# FIGURES_DIR: directory containing PNG figure files
# OLLAMA_BASE_URL: Ollama server (default localhost)

_data_dir_env = os.environ.get("SCZ_DATA_DIR")
_figures_dir_env = os.environ.get("SCZ_FIGURES_DIR")

if _data_dir_env:
    # Deployed on Linux: paths set via env vars
    QUERY_DIR = Path(_data_dir_env)
    FIGURES_DIR = Path(_figures_dir_env) if _figures_dir_env else QUERY_DIR / "figures"
else:
    # Local development (Windows)
    PIPELINE_ROOT = Path("I:/Scratch/schizophrenia-genomics")
    RESULTS_DIR = PIPELINE_ROOT / "results"
    FIGURES_DIR = Path(_figures_dir_env) if _figures_dir_env else PIPELINE_ROOT / "figures"
    REFERENCE_DIR = PIPELINE_ROOT / "reference"
    README_PATH = PIPELINE_ROOT / "README.md"
    WEBSITE_ROOT = PIPELINE_ROOT / "website"
    QUERY_DIR = WEBSITE_ROOT / "query"

# DuckDB database path
DUCKDB_PATH = QUERY_DIR / "genomics.duckdb"

# ChromaDB path
CHROMA_PATH = QUERY_DIR / "chroma_store"
CHROMA_COLLECTION = "genomics_findings"

# Embedding model
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768

# LLM for SQL generation and synthesis
LLM_MODEL = "claude-sonnet-4-6"

# Retrieval settings
TOP_K_VECTOR = 12
TOP_K_SQL_ROWS = 50
MMR_LAMBDA = 0.6

# Evidence tiers
EVIDENCE_TIERS = {
    "REPLICATED": "Finding consistent across 2+ datasets",
    "SINGLE_DATASET": "From one dataset only",
    "UNDERPOWERED": "From GSE21138 brain (n=59, no FDR-significant genes)",
}

# Datasets
DATASETS = {
    "GSE38484": {"tissue": "whole_blood", "platform": "Illumina HT-12 V3 (GPL6947)", "n_scz": 106, "n_ctrl": 96},
    "GSE27383": {"tissue": "PBMC", "platform": "Affymetrix HG-U133+2 (GPL570)", "n_scz": 43, "n_ctrl": 29},
    "GSE21138": {"tissue": "prefrontal_cortex", "platform": "Affymetrix HG-U133+2 (GPL570)", "n_scz": 30, "n_ctrl": 29},
}

DATASET_KEYWORDS = {
    "blood": "GSE38484", "whole blood": "GSE38484",
    "GSE38484": "GSE38484",
    "PBMC": "GSE27383", "peripheral blood": "GSE27383",
    "GSE27383": "GSE27383",
    "brain": "GSE21138", "cortex": "GSE21138", "prefrontal": "GSE21138",
    "post-mortem": "GSE21138", "GSE21138": "GSE21138",
}
