"""
Classifies incoming queries into 4 types to route to the correct retrieval path.

Type A - GENE_LOOKUP:       Gene-specific queries -> SQL first, vector supplement
Type B - DATASET_AGG:       Counting/aggregation queries -> SQL only
Type C - BIOLOGICAL:        Mechanism/pathway/explanation -> vector first
Type D - CROSS_EVIDENCE:    Multi-source evidence queries -> hybrid
"""
import re
from dataclasses import dataclass
from enum import Enum


class QueryType(str, Enum):
    GENE_LOOKUP = "GENE_LOOKUP"
    DATASET_AGG = "DATASET_AGG"
    BIOLOGICAL = "BIOLOGICAL"
    CROSS_EVIDENCE = "CROSS_EVIDENCE"


@dataclass
class Classification:
    query_type: QueryType
    dataset_id: str | None   # Detected dataset filter if any
    gene: str | None          # Detected gene name if any
    confidence: float


# Gene pattern: 2-8 uppercase letters optionally followed by digits
_GENE_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")

_DATASET_KEYWORDS = {
    "blood": "GSE38484",
    "whole blood": "GSE38484",
    "GSE38484": "GSE38484",
    "PBMC": "GSE27383",
    "peripheral blood": "GSE27383",
    "GSE27383": "GSE27383",
    "brain": "GSE21138",
    "cortex": "GSE21138",
    "prefrontal": "GSE21138",
    "post-mortem": "GSE21138",
    "postmortem": "GSE21138",
    "GSE21138": "GSE21138",
}

# Known gene names to avoid false positives on common words
_COMMON_WORDS = {
    "SCZ", "DE", "FC", "FDR", "NES", "GO", "OR", "IS", "IN", "OF", "AT",
    "THE", "AND", "FOR", "TOP", "ALL", "ANY", "NOT", "ARE", "BUT", "IF",
    "CAN", "HOW", "WHY", "WHAT", "DOES", "HAS", "HAVE",
}

_AGG_SIGNALS = [
    r"\bhow many\b", r"\bcount\b", r"\bnumber of\b", r"\btotal\b",
    r"\blist all\b", r"\bshow all\b", r"\bwhich datasets?\b",
    r"\bstatistics?\b", r"\bhow many genes?\b",
]

_BIOLOGICAL_SIGNALS = [
    r"\bwhy\b", r"\bexplain\b", r"\bmechanism\b", r"\bpathway[s]?\b",
    r"\bbiolog", r"\bfunction\b", r"\bprocess\b", r"\benrich", r"\bsignaling\b",
    r"\bimmune\b", r"\bnmda\b", r"\bdopamine\b", r"\bsynapt", r"\bneuro",
    r"\binflam", r"\bcelll? type", r"\bwgcna\b", r"\bmodule[s]?\b",
    r"\bhow does\b", r"\bwhat is\b", r"\bwhat are\b",
]

_CROSS_EVIDENCE_SIGNALS = [
    r"\bacross datasets?\b", r"\breplicat", r"\bconsistent\b",
    r"\bmultiple\b.*\bdataset", r"\ball.*dataset", r"\bboth\b",
    r"\bblood and brain\b", r"\bbrain and blood\b",
    r"\bhigh.?evidence\b", r"\bconverg", r"\bgene.*drug\b",
    r"\bdrug.*gene\b",
]

_DRUG_SIGNALS = [
    r"\bdrug[s]?\b", r"\bmedic", r"\brepurpos", r"\btherapy\b",
    r"\btreatment\b", r"\bantipsychot", r"\bcompound[s]?\b",
    r"\bcandidates?\b",
]


def classify(query: str) -> Classification:
    q_lower = query.lower()
    q_upper = query.upper()

    # Detect dataset filter
    dataset_id = None
    for kw, ds in _DATASET_KEYWORDS.items():
        if kw.lower() in q_lower:
            dataset_id = ds
            break

    # Detect gene name
    gene = None
    gene_matches = _GENE_PATTERN.findall(query)
    valid_genes = [g for g in gene_matches if g not in _COMMON_WORDS and len(g) >= 3]
    if valid_genes:
        gene = valid_genes[0]

    # Score each type
    agg_score = sum(1 for p in _AGG_SIGNALS if re.search(p, q_lower))
    bio_score = sum(1 for p in _BIOLOGICAL_SIGNALS if re.search(p, q_lower))
    cross_score = sum(1 for p in _CROSS_EVIDENCE_SIGNALS if re.search(p, q_lower))
    drug_score = sum(1 for p in _DRUG_SIGNALS if re.search(p, q_lower))

    # A gene name + aggregation = lookup
    if gene and not agg_score and not bio_score:
        return Classification(QueryType.GENE_LOOKUP, dataset_id, gene, 0.9)

    if gene and q_lower.startswith("what") or "tell me about" in q_lower and gene:
        return Classification(QueryType.GENE_LOOKUP, dataset_id, gene, 0.85)

    if agg_score >= 1:
        return Classification(QueryType.DATASET_AGG, dataset_id, gene, 0.85)

    if cross_score >= 1 or (drug_score >= 1 and not dataset_id):
        return Classification(QueryType.CROSS_EVIDENCE, dataset_id, gene, 0.8)

    if bio_score >= 1:
        return Classification(QueryType.BIOLOGICAL, dataset_id, gene, 0.8)

    # Default: if gene detected, lean to lookup; else biological
    if gene:
        return Classification(QueryType.GENE_LOOKUP, dataset_id, gene, 0.6)

    return Classification(QueryType.BIOLOGICAL, dataset_id, gene, 0.5)


if __name__ == "__main__":
    tests = [
        "Tell me about NRGN",
        "How many DE genes are in GSE38484?",
        "What pathways are enriched in schizophrenia?",
        "Which drugs work across blood and brain datasets?",
        "What is the role of NMDA receptors?",
        "List all high-evidence genes",
        "Is SNAP25 a hub gene?",
        "What immune cell types are reduced in SCZ?",
    ]
    for t in tests:
        c = classify(t)
        print(f"{c.query_type.value:<20} | {str(c.dataset_id):<10} | {str(c.gene):<10} | {t}")
