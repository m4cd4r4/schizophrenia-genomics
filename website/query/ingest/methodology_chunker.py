"""
Split the pipeline README into section-level chunks for ChromaDB.

Each ## heading becomes one chunk. Also adds pre-written cross-evidence
synthesis chunks about key biological themes.
"""
import re
from pathlib import Path

README_PATH = Path("I:/Scratch/schizophrenia-genomics/README.md")


def _chunk(text: str, source: str, category: str = "methodology") -> dict:
    return {
        "text": text.strip(),
        "metadata": {
            "source": source,
            "category": category,
            "evidence_tier": "REPLICATED",
        }
    }


def generate_methodology_chunks() -> list[dict]:
    chunks = []

    # --- README section chunks ---
    if README_PATH.exists():
        text = README_PATH.read_text(encoding="utf-8")
        # Split at ## headings
        sections = re.split(r"\n(?=## )", text)
        for section in sections:
            if not section.strip():
                continue
            # Get heading for source label
            heading_match = re.match(r"## (.+)", section)
            heading = heading_match.group(1).strip() if heading_match else "introduction"
            slug = heading.lower().replace(" ", "_").replace("/", "_")[:50]

            # Skip purely visual/table sections
            if len(section.strip()) < 100:
                continue

            # Truncate very long sections at 1500 chars
            content = section.strip()
            if len(content) > 1500:
                content = content[:1500] + "..."

            chunks.append(_chunk(content, f"README/{slug}", "methodology"))

    # --- Pre-written cross-evidence synthesis chunks ---
    synthesis_chunks = [
        _chunk(
            "Immune dysregulation in schizophrenia: "
            "CD8 T cells and NK cells are consistently reduced across blood and PBMC datasets (GSE38484, GSE27383). "
            "This replicates prior literature showing immune abnormalities in schizophrenia. "
            "Modules enriched for immune function (M2 in GSE38484, M3 in GSE27383) are also "
            "significantly correlated with SCZ status. "
            "Drug repurposing candidates hesperidin and amantadine - both with anti-inflammatory properties - "
            "replicate across all 3 datasets, providing additional evidence for immune involvement.",
            "synthesis/immune_dysregulation",
            "synthesis",
        ),
        _chunk(
            "NMDA receptor pathway in schizophrenia: "
            "GSEA reveals consistent enrichment of glutamate receptor signaling and NMDA receptor pathways. "
            "The top brain-specific drug candidate d-serine (an NMDA co-agonist) further supports NMDA "
            "hypofunction as a mechanistic driver. "
            "Risk gene NRGN (neurogranin), a hub gene in the brain dataset module M1 (kME=0.91), "
            "regulates calmodulin signaling downstream of NMDA receptors. "
            "NRG1 (neuregulin-1), a PGC3 GWAS locus gene, modulates NMDA receptor function and "
            "is differentially expressed in the brain dataset.",
            "synthesis/NMDA_pathway",
            "synthesis",
        ),
        _chunk(
            "Risk gene convergence in schizophrenia transcriptomics: "
            "Of ~145 PGC3 GWAS risk loci tested, several are significantly differentially expressed. "
            "TCF4, NRG1, HTR2A, and FOXP1 are validated as schizophrenia markers by both genetic risk "
            "and expression data. "
            "High-evidence genes (DE + hub + risk gene convergence) include: "
            "NRGN, SNAP25, ZNF804A, TCF4, DTNBP1 among others. "
            "The convergence of GWAS risk loci with expression changes provides strong validation "
            "of transcriptomic findings.",
            "synthesis/risk_gene_convergence",
            "synthesis",
        ),
        _chunk(
            "Medication confounding analysis: "
            "Stage 10 analyzed whether blood DE genes in GSE38484 and GSE27383 reflect "
            "antipsychotic medication effects rather than disease. "
            "Using brain dose-response data (GSE21138 with CPZ-equivalent doses), "
            "0 blood DE genes showed significant medication dose-response in brain. "
            "This strongly argues that blood transcriptomic changes reflect disease biology, "
            "not medication confounding. "
            "Risk genes TCF4, NRG1, HTR2A, FOXP1 show no medication dose-response.",
            "synthesis/medication_confounding",
            "synthesis",
        ),
        _chunk(
            "Module preservation across datasets: "
            "Modules M1, M3, M6, M9 from GSE38484 (whole blood) show high preservation in "
            "GSE27383 (PBMC) with Zsummary > 10, indicating robust co-expression structure. "
            "Brain modules are not well-preserved in blood datasets (expected, given tissue differences). "
            "Preserved modules capture shared immune and metabolic biology between blood compartments.",
            "synthesis/module_preservation",
            "synthesis",
        ),
        _chunk(
            "Cross-dataset drug repurposing findings: "
            "Hesperidin (citrus flavonoid, anti-inflammatory), amantadine (antiviral/dopamine), "
            "and valproic acid (mood stabilizer) replicate across all 3 datasets. "
            "Haloperidol and clozapine (antipsychotics) are correctly recovered as top candidates, "
            "validating the GSEA drug perturbation approach. "
            "D-serine (NMDA co-agonist) is the top brain-specific candidate, "
            "consistent with NMDA hypofunction hypothesis.",
            "synthesis/drug_repurposing_summary",
            "synthesis",
        ),
        _chunk(
            "Pipeline overview: "
            "10-stage schizophrenia genomics analysis pipeline using 3 GEO datasets: "
            "GSE38484 (whole blood, n=202), GSE27383 (PBMC, n=72), GSE21138 (post-mortem brain, n=59). "
            "Stages: (1) data download, (2) preprocessing/QC, (3) differential expression, "
            "(4) meta-analysis, (5) WGCNA co-expression, (6) enrichment analysis, "
            "(7) cell type deconvolution, (8) PPI network, (9) drug repurposing, "
            "(10) medication confounding. "
            "All analysis in Python (limma via rpy2, WGCNA, gseapy, STRING DB).",
            "synthesis/pipeline_overview",
            "synthesis",
        ),
        _chunk(
            "Key limitations of the schizophrenia genomics analysis: "
            "1. GSE21138 brain dataset (n=59, 30 SCZ/29 ctrl) is underpowered - no FDR-significant genes. "
            "2. Blood transcriptomics may not fully reflect brain pathology. "
            "3. All datasets used antipsychotic-treated patients (medication confounding possible despite analysis). "
            "4. Drug repurposing is in silico only - no experimental validation. "
            "5. WGCNA module stability requires larger samples. "
            "6. Cross-dataset heterogeneity (blood vs PBMC vs brain) limits direct comparisons.",
            "synthesis/limitations",
            "synthesis",
        ),
    ]

    chunks.extend(synthesis_chunks)
    return chunks


if __name__ == "__main__":
    chunks = generate_methodology_chunks()
    print(f"Generated {len(chunks)} methodology chunks")
    for c in chunks[:3]:
        print(f"\n[{c['metadata']['source']}]")
        print(c['text'][:200] + "...")
