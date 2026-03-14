"""
Stage 1: Download GEO blood expression datasets.

Downloads SOFT files from NCBI GEO, extracts expression matrices and phenotype
data, maps probes to gene symbols, and saves processed data to disk.
"""
import re
from pathlib import Path

import GEOparse
import numpy as np
import pandas as pd
from tqdm import tqdm

import config
from pipeline.utils import get_logger, save_df

log = get_logger("stage1")


def _geo_path(destdir: Path) -> str:
    """Convert path to forward slashes for GEOparse (Windows bug workaround)."""
    return str(destdir).replace("\\", "/")


def download_geo(geo_id: str, destdir: Path) -> GEOparse.GEOTypes.GSE:
    """Download a GEO dataset, using cached SOFT file if available."""
    destdir.mkdir(parents=True, exist_ok=True)

    # Check for cached files
    cached = list(destdir.glob(f"{geo_id}*soft*"))
    if cached:
        log.info(f"{geo_id}: Using cached file {cached[0].name}")
        gse = GEOparse.get_GEO(filepath=_geo_path(cached[0]))
    else:
        log.info(f"{geo_id}: Downloading from GEO (this may take a few minutes)...")
        gse = GEOparse.get_GEO(geo=geo_id, destdir=_geo_path(destdir))

    log.info(f"{geo_id}: {len(gse.gsms)} samples, platforms: {list(gse.gpls.keys())}")
    return gse


def extract_expression_matrix(gse: GEOparse.GEOTypes.GSE) -> pd.DataFrame:
    """Build a probes-by-samples expression matrix from GSM tables."""
    sample_data = {}
    for gsm_name, gsm in tqdm(gse.gsms.items(), desc="Extracting samples"):
        table = gsm.table
        if table.empty:
            log.warning(f"Skipping {gsm_name}: empty table")
            continue
        # Identify value column (varies by dataset)
        value_col = None
        for candidate in ["VALUE", "INTENSITY", "SIGNAL"]:
            if candidate in table.columns:
                value_col = candidate
                break
        if value_col is None:
            log.warning(f"Skipping {gsm_name}: no value column found in {table.columns.tolist()}")
            continue
        series = table.set_index("ID_REF")[value_col]
        series = pd.to_numeric(series, errors="coerce")
        sample_data[gsm_name] = series

    expr_df = pd.DataFrame(sample_data)
    log.info(f"Raw expression matrix: {expr_df.shape[0]} probes x {expr_df.shape[1]} samples")

    # Drop probes with >20% missing values
    max_missing = 0.2 * expr_df.shape[1]
    before = expr_df.shape[0]
    expr_df = expr_df[expr_df.isnull().sum(axis=1) <= max_missing]
    log.info(f"Dropped {before - expr_df.shape[0]} probes with >{int(max_missing)} missing values")

    # Impute remaining NaN with row median
    if expr_df.isnull().any().any():
        row_medians = expr_df.median(axis=1)
        expr_df = expr_df.T.fillna(row_medians).T
        log.info("Imputed remaining NaN with row medians")

    return expr_df


def extract_phenotype(gse: GEOparse.GEOTypes.GSE) -> pd.DataFrame:
    """Parse sample metadata to extract disease status and demographics."""
    records = []
    for gsm_name, gsm in gse.gsms.items():
        meta = gsm.metadata
        record = {"sample_id": gsm_name, "title": meta.get("title", [""])[0]}

        # Parse characteristics_ch1
        chars = meta.get("characteristics_ch1", [])
        for char in chars:
            char = char.strip()
            if ":" in char:
                key, val = char.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                val = val.strip()
                record[key] = val
            else:
                record[f"char_{len(record)}"] = char

        # Also check source_name and description
        record["source"] = meta.get("source_name_ch1", [""])[0]
        records.append(record)

    pheno_df = pd.DataFrame(records).set_index("sample_id")

    # Infer disease status column - try common patterns
    pheno_df["group"] = _infer_disease_group(pheno_df)
    group_counts = pheno_df["group"].value_counts()
    log.info(f"Phenotype groups: {group_counts.to_dict()}")

    return pheno_df


def _infer_disease_group(pheno_df: pd.DataFrame) -> pd.Series:
    """Try to infer SCZ vs control labels from phenotype metadata."""
    scz_patterns = re.compile(
        r"schizo|SCZ|SZ|psychos|EOS|early.onset",
        re.IGNORECASE,
    )
    ctrl_patterns = re.compile(
        r"control|healthy|normal|HC|unaffected",
        re.IGNORECASE,
    )

    groups = pd.Series("unknown", index=pheno_df.index)

    # Search across all string columns
    str_cols = pheno_df.select_dtypes(include="object").columns
    for col in str_cols:
        for idx, val in pheno_df[col].items():
            if pd.isna(val):
                continue
            val_str = str(val)
            if groups[idx] == "unknown":
                if scz_patterns.search(val_str):
                    groups[idx] = "SCZ"
                elif ctrl_patterns.search(val_str):
                    groups[idx] = "control"

    n_unknown = (groups == "unknown").sum()
    if n_unknown > 0:
        log.warning(f"{n_unknown} samples could not be classified as SCZ or control")

    return groups


def map_probes_to_genes(
    expr_df: pd.DataFrame,
    gse: GEOparse.GEOTypes.GSE,
    platform_id: str,
) -> pd.DataFrame:
    """Map probe IDs to gene symbols using GPL annotation, then collapse."""
    if platform_id not in gse.gpls:
        log.warning(f"Platform {platform_id} not in GSE. Trying to download...")
        gpl = GEOparse.get_GEO(geo=platform_id, destdir=_geo_path(config.DATA_RAW))
        annot = gpl.table
    else:
        annot = gse.gpls[platform_id].table

    log.info(f"GPL annotation columns: {annot.columns.tolist()}")

    # Find gene symbol column
    symbol_col = None
    for candidate in ["Symbol", "GENE_SYMBOL", "gene_assignment", "Gene Symbol",
                       "ILMN_Gene", "GeneSymbol", "GENE", "ORF"]:
        if candidate in annot.columns:
            symbol_col = candidate
            break

    if symbol_col is None:
        log.error(f"No gene symbol column found in: {annot.columns.tolist()}")
        log.info("Returning expression matrix with probe IDs as-is")
        return expr_df

    log.info(f"Using gene symbol column: '{symbol_col}'")

    # Find probe ID column
    id_col = None
    for candidate in ["ID", "ID_REF", "PROBE_ID"]:
        if candidate in annot.columns:
            id_col = candidate
            break
    if id_col is None:
        id_col = annot.columns[0]

    # Build probe-to-gene mapping
    probe_to_gene = annot[[id_col, symbol_col]].dropna(subset=[symbol_col])
    probe_to_gene = probe_to_gene[probe_to_gene[symbol_col].str.strip() != ""]
    probe_to_gene = probe_to_gene.set_index(id_col)[symbol_col]

    # Handle gene_assignment column (Affymetrix-style: "NM_001234 // GENE // ...")
    if symbol_col == "gene_assignment":
        probe_to_gene = probe_to_gene.apply(
            lambda x: x.split("//")[1].strip() if isinstance(x, str) and "//" in x else x
        )

    # Map probes in expression matrix
    common_probes = expr_df.index.intersection(probe_to_gene.index)
    log.info(f"Probes mapped to genes: {len(common_probes)} / {len(expr_df)}")

    if len(common_probes) < 1000:
        log.warning(f"Only {len(common_probes)} probes mapped - annotation may be sparse")

    mapped_df = expr_df.loc[common_probes].copy()
    mapped_df["gene"] = probe_to_gene[common_probes].values

    # Remove rows where gene symbol is NaN or empty
    mapped_df = mapped_df[mapped_df["gene"].notna()]
    mapped_df = mapped_df[mapped_df["gene"].str.strip() != ""]

    # Collapse multi-probe genes by averaging
    gene_expr = mapped_df.groupby("gene").mean()
    log.info(f"Gene-level expression matrix: {gene_expr.shape[0]} genes x {gene_expr.shape[1]} samples")

    return gene_expr


def run(dataset_ids: list[str] | None = None) -> dict:
    """Run Stage 1 for specified datasets. Returns {id: (expression_df, phenotype_df)}."""
    if dataset_ids is None:
        dataset_ids = list(config.DATASETS.keys())

    results = {}
    for ds_id in dataset_ids:
        ds_config = config.DATASETS[ds_id]
        log.info(f"\n{'='*60}\nProcessing {ds_id}: {ds_config['description']}\n{'='*60}")

        # Check for cached processed files
        expr_path = config.DATA_PROCESSED / f"{ds_id}_expression.csv"
        pheno_path = config.DATA_PROCESSED / f"{ds_id}_phenotype.csv"
        if expr_path.exists() and pheno_path.exists():
            log.info(f"{ds_id}: Loading from cache")
            expr_df = pd.read_csv(expr_path, index_col=0)
            pheno_df = pd.read_csv(pheno_path, index_col=0)
            results[ds_id] = (expr_df, pheno_df)
            continue

        # Download
        gse = download_geo(ds_config["geo_id"], config.DATA_RAW)

        # Extract expression matrix
        expr_df = extract_expression_matrix(gse)

        # Extract phenotype
        pheno_df = extract_phenotype(gse)

        # Map probes to genes
        expr_df = map_probes_to_genes(expr_df, gse, ds_config["platform"])

        # Align samples between expression and phenotype
        common_samples = expr_df.columns.intersection(pheno_df.index)
        expr_df = expr_df[common_samples]
        pheno_df = pheno_df.loc[common_samples]
        log.info(f"{ds_id}: {len(common_samples)} samples in common")

        # Save processed data
        save_df(expr_df, expr_path, f"{ds_id} expression matrix")
        save_df(pheno_df, pheno_path, f"{ds_id} phenotype")

        results[ds_id] = (expr_df, pheno_df)

    return results
