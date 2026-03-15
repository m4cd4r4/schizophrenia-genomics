"use client";
import { useState } from "react";

interface Stage {
  number: number;
  name: string;
  script: string;
  method: string;
  params: string[];
  inputs: string[];
  outputs: string[];
  keyResult: string;
}

const STAGES: Stage[] = [
  {
    number: 1,
    name: "Data Download & Preprocessing",
    script: "stage1_download.py",
    method: "GEOparse + probe-to-gene mapping",
    params: [
      "GEO IDs: GSE38484, GSE27383, GSE21138",
      "Probe mapping: GPL6947, GPL570",
      "Output: log2-normalized expression matrices",
    ],
    inputs: ["GEO FTP (public)", "GPL platform files"],
    outputs: ["data/{dataset}_expression.csv", "data/{dataset}_metadata.csv"],
    keyResult: "202 + 72 + 59 samples loaded. Expression matrices: 25,142 / 23,520 / 15,706 probes mapped to genes.",
  },
  {
    number: 2,
    name: "Differential Expression",
    script: "stage2_de.py",
    method: "Welch's t-test + Benjamini-Hochberg FDR + Fisher meta-analysis",
    params: [
      "Test: Welch's t-test (unequal variance)",
      "FDR threshold: 0.05",
      "Meta: Fisher combined p-value",
      "Log2 data; no additional normalization",
    ],
    inputs: ["data/{dataset}_expression.csv", "data/{dataset}_metadata.csv"],
    outputs: ["results/{dataset}_de_results.csv", "results/meta_de_results.csv", "figures/{dataset}_volcano.png"],
    keyResult: "GSE38484: 4,777 DE genes. GSE27383: 825 DE genes. GSE21138: 0 (n=59, underpowered). Meta: 3,219 genes, 888 direction-consistent.",
  },
  {
    number: 3,
    name: "Co-expression Networks (WGCNA)",
    script: "stage3_wgcna.py",
    method: "Weighted Gene Co-expression Network Analysis",
    params: [
      "Input: top 5,000 variable genes (MAD)",
      "Soft-thresholding: R² > 0.85",
      "Dissimilarity: 1 - TOM",
      "Clustering: hierarchical + dynamic tree cut",
      "Min module size: 30 genes",
    ],
    inputs: ["data/{dataset}_expression.csv"],
    outputs: ["results/{dataset}_modules.csv", "results/{dataset}_module_trait.csv", "results/{dataset}_hub_genes.csv"],
    keyResult: "GSE38484: 10 modules (soft power=6). GSE27383: 13 modules (soft power=4). M1, M3, M6 correlated with SCZ status.",
  },
  {
    number: 4,
    name: "Risk Loci Mapping",
    script: "stage4_risk.py",
    method: "Overlap test against curated GWAS + family study gene lists",
    params: [
      "PGC3 GWAS: 113 prioritized genes (Trubetskoy 2022)",
      "Family/candidate genes: 41 (CHRNA7, DISC1, NRG1, COMT, ...)",
      "Enrichment: Fisher's exact test per module",
      "High-evidence threshold: DE + hub + risk",
    ],
    inputs: ["results/{dataset}_de_results.csv", "results/{dataset}_hub_genes.csv", "data/pgc3_genes.txt"],
    outputs: ["results/{dataset}_risk_de_overlap.csv", "results/{dataset}_module_risk_overlap.csv", "results/high_evidence_genes.csv"],
    keyResult: "GSE38484: 145 risk genes DE. GSE27383: 153. GSE21138: 119. High-evidence genes (DE+hub+risk): 92. Notable: SP4, SETD1A, FURIN, FBXO11.",
  },
  {
    number: 5,
    name: "Pathway Enrichment",
    script: "stage5_pathways.py",
    method: "GSEA preranked + Enrichr overrepresentation",
    params: [
      "Ranking metric: t-statistic",
      "Libraries: KEGG, GO Biological Process, Reactome",
      "FDR threshold: 0.05",
      "SCZ-specific keywords: immune, synapse, glutamate, dopamine, NMDA",
    ],
    inputs: ["results/{dataset}_de_results.csv", "results/{dataset}_modules.csv"],
    outputs: ["results/{dataset}_gsea_{library}.csv", "results/scz_pathway_enrichment.csv"],
    keyResult: "Immune system (NES=2.14), Neutrophil degranulation (1.98) up in blood. Synapse assembly (-1.87), Glutamatergic synapse (-1.74) down in PBMC.",
  },
  {
    number: 6,
    name: "Module Preservation",
    script: "stage6_preservation.py",
    method: "Zsummary preservation statistic (Langfelder & Horvath 2011)",
    params: [
      "Reference: GSE38484 (blood)",
      "Test datasets: GSE27383 (PBMC), GSE21138 (brain)",
      "Z > 10: highly preserved",
      "Z 2-10: moderately preserved",
      "Z < 2: not preserved",
    ],
    inputs: ["results/GSE38484_modules.csv", "data/{dataset}_expression.csv"],
    outputs: ["results/module_preservation_blood_pbmc.csv", "results/module_preservation_blood_brain.csv"],
    keyResult: "M1, M3, M6, M9 highly preserved blood->PBMC (Z > 14). Only M9 moderately preserved blood->brain (Z=8.2). Cross-tissue coexpression intact for large modules.",
  },
  {
    number: 7,
    name: "Cell Type Deconvolution",
    script: "stage7_celltype.py",
    method: "MCPcounter-style marker gene scoring",
    params: [
      "Markers: 7-10 genes per cell type",
      "Cell types: NK, CD8 T, CD4 T, B cells, monocytes, neutrophils, platelets",
      "Score: mean z-scored expression of markers",
      "Test: t-test SCZ vs. control, BH-FDR",
    ],
    inputs: ["data/{dataset}_expression.csv", "data/cell_type_markers.csv"],
    outputs: ["results/{dataset}_cell_type_de.csv"],
    keyResult: "NK cells (FDR=0.001) and CD8 T cells (FDR=0.031) significantly reduced in GSE38484. REPLICATED in GSE27383 (NK FDR=0.010, CD8 FDR=0.007).",
  },
  {
    number: 8,
    name: "PPI Network Construction",
    script: "stage8_ppi.py",
    method: "STRING DB query + greedy modularity community detection",
    params: [
      "Gene set: hub genes + DE risk genes",
      "STRING confidence threshold: 700",
      "Metrics: degree, betweenness, eigenvector centrality",
      "Community detection: greedy modularity (networkx)",
    ],
    inputs: ["results/{dataset}_hub_genes.csv", "results/{dataset}_risk_de_overlap.csv"],
    outputs: ["results/{dataset}_ppi_nodes.csv", "results/{dataset}_ppi_edges.csv", "figures/{dataset}_ppi_network.png"],
    keyResult: "GSE38484: 73 nodes (ribosomal cluster). GSE27383: 36 nodes (TBX21-PRF1 cytotoxic axis). GSE21138: 8 nodes (C1QA/C1QB complement).",
  },
  {
    number: 9,
    name: "Drug Repurposing (CMap/LINCS)",
    script: "stage9_drugs.py",
    method: "GSEA against drug perturbation libraries via gseapy/Enrichr",
    params: [
      "Libraries: LINCS_L1000 (~10,850), Drug_Perturbations_GEO, Old_CMAP, DrugMatrix",
      "Candidate criterion: negative NES (reverses SCZ signature)",
      "Cross-dataset: drug present in all 3 with FDR < 0.25",
      "Known psychiatric drugs used for validation",
    ],
    inputs: ["results/{dataset}_de_results.csv"],
    outputs: ["results/{dataset}_drug_candidates.csv", "results/cross_dataset_drugs.csv"],
    keyResult: "Known antipsychotics validated (haloperidol NES=-2.20, clozapine NES=-2.09). Top novel: hesperidin, amantadine (NMDA antagonist), tacrine (AChE inhibitor).",
  },
  {
    number: 10,
    name: "Medication Dose-Response & Confounding",
    script: "stage10_confounding.py",
    method: "Spearman correlation + blood-brain confounding flag",
    params: [
      "Dataset: GSE21138 only (medication records available)",
      "Metric: chlorpromazine equivalents (CPZ-eq)",
      "Test: Spearman rho, BH-FDR",
      "Confounding flag: |logFC| > 0.1 in blood AND |rho| > 0.3 in brain",
    ],
    inputs: ["results/GSE21138_de_results.csv", "data/GSE21138_metadata.csv"],
    outputs: ["results/dose_response.csv", "results/blood_brain_confounding.csv", "results/confounding_report.csv"],
    keyResult: "15,706 genes tested for dose-correlation. Confounding risk genes flagged where blood DE signal may reflect medication rather than disease. Key: PRF1, GZMA show dose correlation.",
  },
];

const techColor: Record<string, string> = {
  "Python": "#3b82f6",
  "pandas": "#f59e0b",
  "scipy": "#10b981",
  "gseapy": "#8b5cf6",
  "networkx": "#f97316",
  "requests": "#6b7280",
};

export default function PipelinePage() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div>
      <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Analysis Pipeline</h1>
      <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        10 computational stages from raw GEO data to drug repurposing candidates. Each stage reads from disk and writes independently.
      </p>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {[
          { label: "Datasets", value: "3", sub: "blood, PBMC, brain" },
          { label: "Samples", value: "333", sub: "202 + 72 + 59" },
          { label: "Result files", value: "64", sub: "CSVs + 39 figures" },
          { label: "Data rows", value: "316K", sub: "across 22 tables" },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.6rem 1rem", minWidth: 110 }}>
            <div style={{ fontFamily: "monospace", fontSize: "1.1rem", fontWeight: 700, color: "var(--foreground)" }}>{s.value}</div>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</div>
            <div style={{ fontSize: "0.6rem", color: "var(--text-dim)", marginTop: "0.1rem" }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div>
        {STAGES.map((stage) => {
          const isOpen = expanded === stage.number;
          return (
            <div
              key={stage.number}
              style={{
                background: "var(--card)",
                border: `1px solid ${isOpen ? "var(--border-accent)" : "var(--border)"}`,
                borderRadius: 6,
                marginBottom: "0.5rem",
                overflow: "hidden",
              }}
            >
              <button
                onClick={() => setExpanded(isOpen ? null : stage.number)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem 1rem",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <span style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: isOpen ? "var(--blue)" : "var(--border-accent)",
                  color: isOpen ? "#fff" : "var(--text-muted)",
                  fontFamily: "monospace",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  flexShrink: 0,
                }}>
                  {stage.number}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--foreground)" }}>{stage.name}</span>
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.1rem" }}>{stage.script}</div>
                </div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 0.15s", flexShrink: 0 }}>▼</span>
              </button>

              {isOpen && (
                <div style={{ padding: "0 1rem 1rem 1rem", borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.75rem" }}>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.4rem" }}>Method</div>
                      <div style={{ fontSize: "0.78rem", color: "var(--foreground)" }}>{stage.method}</div>

                      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: "0.75rem", marginBottom: "0.4rem" }}>Parameters</div>
                      <ul style={{ margin: 0, paddingLeft: "1rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
                        {stage.params.map((p, i) => <li key={i} style={{ marginBottom: "0.15rem" }}>{p}</li>)}
                      </ul>
                    </div>

                    <div>
                      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.4rem" }}>Inputs</div>
                      {stage.inputs.map((inp, i) => (
                        <div key={i} style={{ fontFamily: "monospace", fontSize: "0.68rem", color: "var(--text-dim)", marginBottom: "0.15rem" }}>{inp}</div>
                      ))}

                      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: "0.75rem", marginBottom: "0.4rem" }}>Outputs</div>
                      {stage.outputs.map((out, i) => (
                        <div key={i} style={{ fontFamily: "monospace", fontSize: "0.68rem", color: "var(--blue)", marginBottom: "0.15rem" }}>{out}</div>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginTop: "0.75rem", padding: "0.5rem 0.75rem", background: "rgba(39,174,96,0.08)", border: "1px solid rgba(39,174,96,0.2)", borderRadius: 4, fontSize: "0.75rem", color: "var(--foreground)" }}>
                    <span style={{ fontSize: "0.65rem", color: "var(--green)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginRight: "0.4rem" }}>Result:</span>
                    {stage.keyResult}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "1rem", marginTop: "1.5rem" }}>
        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>Technology Stack</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
          {["Python 3.11", "pandas", "scipy", "numpy", "gseapy", "networkx", "GEOparse", "requests", "matplotlib"].map(tech => (
            <span key={tech} style={{
              padding: "0.2rem 0.5rem",
              background: "var(--card-highlight)",
              border: "1px solid var(--border)",
              borderRadius: 3,
              fontSize: "0.7rem",
              fontFamily: "monospace",
              color: "var(--text-muted)",
            }}>{tech}</span>
          ))}
        </div>

        <div style={{ marginTop: "1rem", fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.4rem" }}>Run Commands</div>
        <div style={{ fontFamily: "monospace", fontSize: "0.72rem", background: "var(--background)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.75rem", color: "var(--foreground)" }}>
          <div style={{ color: "var(--text-dim)", marginBottom: "0.3rem" }}># Run all stages</div>
          <div style={{ marginBottom: "0.5rem" }}>python run.py</div>
          <div style={{ color: "var(--text-dim)", marginBottom: "0.3rem" }}># Run specific stages</div>
          <div style={{ marginBottom: "0.5rem" }}>python run.py --stages 2,3</div>
          <div style={{ color: "var(--text-dim)", marginBottom: "0.3rem" }}># Skip download (data already cached)</div>
          <div>python run.py --stages 2,3,4,5,6,7,8,9,10</div>
        </div>
      </div>
    </div>
  );
}
