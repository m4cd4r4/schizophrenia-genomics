"""
FastAPI application for the schizophrenia genomics website.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "website"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import stats, datasets, genes, drugs, pathways, figures, query

app = FastAPI(
    title="Schizophrenia Genomics API",
    description="REST API for schizophrenia transcriptomics pipeline results + RAG query",
    version="1.0.0",
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://schizophrenia-genomics.vercel.app",
    "https://schizophrenia-genomics-m4cd4r4s-projects.vercel.app",
    "https://donnacha.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router)
app.include_router(datasets.router)
app.include_router(genes.router)
app.include_router(drugs.router)
app.include_router(pathways.router)
app.include_router(figures.router)
app.include_router(query.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
