"""Pydantic response models for the API."""
from pydantic import BaseModel
from typing import Any


class StatsResponse(BaseModel):
    n_datasets: int
    n_genes_tested: int
    n_meta_sig_genes: int
    n_high_evidence_genes: int
    n_drug_candidates: int
    n_preserved_modules: int
    n_validated_antipsychotics: int
    n_pipeline_stages: int
    de_by_dataset: list[dict]
    top_cross_drugs: list[dict]


class DatasetSummary(BaseModel):
    dataset_id: str
    tissue: str
    platform: str
    n_scz: int
    n_ctrl: int
    n_de_genes: int
    n_modules: int
    n_hub_genes: int
    n_risk_overlaps: int
    n_drug_candidates: int


class QueryRequest(BaseModel):
    query: str
    dataset_id: str | None = None
    stream: bool = False


class QueryResponse(BaseModel):
    query: str
    classification: dict
    sql: str
    sql_method: str
    sql_results: list[dict] | None
    chunks: list[dict]
    answer: str
    evidence_tiers: list[str]
