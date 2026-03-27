"""Metabolic psychiatry / ketogenic diet research data endpoints."""
import csv
import os
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/metabolic", tags=["metabolic"])

_data_dir = os.environ.get("SCZ_DATA_DIR")
if _data_dir:
    REFERENCE_DIR = Path(_data_dir)
else:
    REFERENCE_DIR = Path(__file__).resolve().parents[3] / "reference"


def _load_csv(filename: str) -> list[dict]:
    path = REFERENCE_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@router.get("/trials")
def get_trials():
    return _load_csv("ketogenic_studies.csv")


@router.get("/mechanisms")
def get_mechanisms():
    return _load_csv("ketogenic_mechanisms.csv")


@router.get("/datasets")
def get_queued_datasets():
    return _load_csv("additional_datasets.csv")
