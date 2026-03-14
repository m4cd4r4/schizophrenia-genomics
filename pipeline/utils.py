"""Shared utilities for the pipeline: I/O, logging, plotting defaults."""
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import config


def setup_dirs():
    """Create all output directories if they don't exist."""
    for d in [config.DATA_RAW, config.DATA_PROCESSED, config.RESULTS_DIR,
              config.FIGURES_DIR, config.REFERENCE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def save_df(df: pd.DataFrame, path: Path, description: str = ""):
    """Save DataFrame to CSV with logging."""
    log = get_logger("io")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    log.info(f"Saved {description}: {path} ({df.shape[0]} rows x {df.shape[1]} cols)")


def load_df(path: Path) -> pd.DataFrame:
    """Load DataFrame from CSV, raising clear error if missing."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}\n"
            f"Run the earlier pipeline stage that produces this file first."
        )
    return pd.read_csv(path, index_col=0)


def configure_plotting():
    """Set matplotlib defaults for publication-quality figures."""
    plt.rcParams.update({
        "figure.dpi": config.FIGURE_DPI,
        "savefig.dpi": config.FIGURE_DPI,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.figsize": (10, 8),
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def savefig(fig, name: str):
    """Save figure to the figures directory."""
    path = config.FIGURES_DIR / f"{name}.{config.FIGURE_FORMAT}"
    fig.savefig(path, dpi=config.FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    get_logger("plot").info(f"Saved figure: {path}")


def stage_outputs_exist(paths: list[Path]) -> bool:
    """Check if all expected output files from a stage exist."""
    return all(Path(p).exists() for p in paths)
