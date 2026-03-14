"""
Schizophrenia Blood Expression Analysis Pipeline

Analyzes publicly available GEO blood expression data to identify genes,
modules, and pathways associated with schizophrenia. Cross-references
findings with known risk loci from PGC3 GWAS and family linkage studies.

Usage:
    python run.py                         # Run all stages
    python run.py --stages 1,2            # Run specific stages
    python run.py --stages 3 --datasets GSE38484  # Single dataset
    python run.py --stages 2,3,4,5        # Skip download (use cached)

Stages:
    1: Download GEO datasets + probe-to-gene mapping
    2: Differential expression analysis (SCZ vs control)
    3: WGCNA-style co-expression network analysis
    4: Map to schizophrenia risk loci (PGC3 + family studies)
    5: Pathway enrichment analysis + summary dashboard
"""
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from pipeline.utils import setup_dirs, get_logger, configure_plotting

log = get_logger("pipeline")


def main():
    parser = argparse.ArgumentParser(
        description="Schizophrenia Blood Expression Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--stages", default="1,2,3,4,5",
        help="Comma-separated stage numbers to run (default: 1,2,3,4,5)",
    )
    parser.add_argument(
        "--datasets", default="GSE38484,GSE27383",
        help="Comma-separated GEO dataset IDs (default: GSE38484,GSE27383)",
    )
    parser.add_argument(
        "--primary", default="GSE38484",
        help="Primary dataset for WGCNA (default: GSE38484, the larger dataset)",
    )
    args = parser.parse_args()

    stages = [int(s.strip()) for s in args.stages.split(",")]
    dataset_ids = [d.strip() for d in args.datasets.split(",")]
    primary_ds = args.primary

    # Validate
    for ds_id in dataset_ids:
        if ds_id not in config.DATASETS:
            log.error(f"Unknown dataset: {ds_id}. Available: {list(config.DATASETS.keys())}")
            sys.exit(1)

    setup_dirs()
    configure_plotting()

    log.info("=" * 60)
    log.info("Schizophrenia Blood Expression Analysis Pipeline")
    log.info(f"Stages: {stages}")
    log.info(f"Datasets: {dataset_ids}")
    log.info(f"Primary (WGCNA): {primary_ds}")
    log.info("=" * 60)

    t_start = time.time()

    # Stage 1: Download and process GEO data
    if 1 in stages:
        log.info("\n>>> STAGE 1: Downloading GEO datasets <<<")
        from pipeline import stage1_download
        stage1_download.run(dataset_ids)
        log.info("Stage 1 complete.\n")

    # Stage 2: Differential expression
    if 2 in stages:
        log.info("\n>>> STAGE 2: Differential expression analysis <<<")
        from pipeline import stage2_diffexpr
        stage2_diffexpr.run(dataset_ids)
        log.info("Stage 2 complete.\n")

    # Stage 3: Co-expression networks (primary dataset only - needs decent sample size)
    if 3 in stages:
        log.info("\n>>> STAGE 3: Co-expression network analysis <<<")
        from pipeline import stage3_coexpression
        # Run on primary dataset (larger sample size needed for WGCNA)
        stage3_coexpression.run(primary_ds)
        # Run on secondary datasets only if large enough
        for ds_id in dataset_ids:
            if ds_id != primary_ds:
                ds_config = config.DATASETS[ds_id]
                if ds_config.get("sample_size_approx", 0) >= 50:
                    stage3_coexpression.run(ds_id)
                else:
                    log.info(f"Skipping WGCNA for {ds_id} (n~{ds_config.get('sample_size_approx', '?')}, "
                             f"too small for reliable co-expression analysis)")
        log.info("Stage 3 complete.\n")

    # Stage 4: Risk loci mapping
    if 4 in stages:
        log.info("\n>>> STAGE 4: Risk loci mapping <<<")
        from pipeline import stage4_risk_loci
        stage4_risk_loci.run(dataset_ids)
        log.info("Stage 4 complete.\n")

    # Stage 5: Pathway visualization
    if 5 in stages:
        log.info("\n>>> STAGE 5: Pathway analysis and visualization <<<")
        from pipeline import stage5_pathways
        stage5_pathways.run(dataset_ids)
        log.info("Stage 5 complete.\n")

    elapsed = time.time() - t_start
    log.info("=" * 60)
    log.info(f"Pipeline finished in {elapsed/60:.1f} minutes")
    log.info(f"Results: {config.RESULTS_DIR}")
    log.info(f"Figures: {config.FIGURES_DIR}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
