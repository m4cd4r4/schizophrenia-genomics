"""
Build synthesis prompts for Claude from retrieved evidence.
"""
from typing import Any

_SYSTEM_PROMPT = """You are a scientific assistant for a schizophrenia genomics research website.
You answer questions about differential expression, co-expression modules, drug repurposing,
and pathway enrichment findings from 3 GEO datasets:
- GSE38484: whole blood, n=202 (106 SCZ, 96 controls)
- GSE27383: PBMC, n=72 (43 SCZ, 29 controls)
- GSE21138: post-mortem prefrontal cortex, n=59 (30 SCZ, 29 controls)

Evidence tier rules:
- REPLICATED: finding consistent across 2+ datasets - state this clearly
- SINGLE_DATASET: from one dataset only - note this caveat
- UNDERPOWERED: from GSE21138 brain (n=59, no FDR-significant DE genes) - note limitations

Guidelines:
- Be precise: use exact gene names (uppercase), exact statistics (logFC, FDR, NES)
- Distinguish between blood and brain findings
- Acknowledge limitations (underpowered brain dataset, medication confounding)
- Do not extrapolate beyond what the data shows
- Keep answers focused and data-driven (2-4 paragraphs max)
"""


def build_prompt(
    query: str,
    retrieval: dict[str, Any],
) -> tuple[str, str]:
    """
    Build system + user prompt from retrieval results.
    Returns (system_prompt, user_message).
    """
    qtype = retrieval["classification"]["type"]
    sql_results = retrieval.get("sql_results")
    chunks = retrieval.get("chunks", [])

    context_parts = []

    # SQL results
    if sql_results and not isinstance(sql_results, dict):  # not an error
        context_parts.append("## Structured Data (from database query)\n")
        if len(sql_results) > 0:
            # Format as table
            cols = list(sql_results[0].keys())
            header = " | ".join(cols)
            sep = " | ".join(["---"] * len(cols))
            rows = []
            for row in sql_results[:25]:
                values = []
                for v in row.values():
                    if isinstance(v, float):
                        values.append(f"{v:.4g}")
                    else:
                        values.append(str(v) if v is not None else "N/A")
                rows.append(" | ".join(values))
            context_parts.append(f"| {header} |\n| {sep} |")
            for row_str in rows:
                context_parts.append(f"| {row_str} |")
        else:
            context_parts.append("No rows returned.")

    elif isinstance(sql_results, dict) and "error" in sql_results:
        context_parts.append(f"Database query error: {sql_results['error']}")

    # Vector chunks
    if chunks:
        context_parts.append("\n## Evidence Chunks (semantic search)\n")
        for i, chunk in enumerate(chunks[:10], 1):
            tier = chunk["metadata"].get("evidence_tier", "UNKNOWN")
            source = chunk["metadata"].get("source", "unknown")
            context_parts.append(f"[{i}] [{tier}] [{source}]\n{chunk['text']}\n")

    context = "\n".join(context_parts)

    user_message = f"""Question: {query}

Evidence:
{context}

Please answer the question based on the evidence above.
Cite specific genes, statistics, and dataset sources where relevant.
Note evidence tier (REPLICATED/SINGLE_DATASET/UNDERPOWERED) for key claims."""

    return _SYSTEM_PROMPT, user_message
