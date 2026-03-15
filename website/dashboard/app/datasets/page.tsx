"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchDatasets } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import Link from "next/link";
import { datasetColor } from "@/lib/format";

export default function DatasetsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });

  const TISSUE_LABELS: Record<string, string> = {
    whole_blood: "Whole Blood",
    PBMC: "PBMC",
    prefrontal_cortex: "Prefrontal Cortex (BA46)",
  };

  if (isLoading) return <LoadingSkeleton />;

  return (
    <div>
      <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Dataset Comparison</h1>
      <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        Three GEO datasets analyzed: blood, PBMC, and post-mortem brain. Click a dataset for detailed results.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
        {(data ?? []).map(d => (
          <Link key={d.dataset_id} href={`/datasets/${d.dataset_id}`} style={{ textDecoration: "none" }}>
            <div style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderTop: `3px solid ${datasetColor(d.dataset_id)}`,
              borderRadius: 6,
              padding: "1.25rem",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
              onMouseOver={e => (e.currentTarget.style.borderColor = datasetColor(d.dataset_id))}
              onMouseOut={e => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              <div style={{ fontFamily: "monospace", fontSize: "1rem", fontWeight: 700, color: datasetColor(d.dataset_id), marginBottom: "0.25rem" }}>
                {d.dataset_id}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--foreground)", marginBottom: "0.75rem" }}>
                {TISSUE_LABELS[d.tissue] ?? d.tissue}
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
                {d.platform}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                {[
                  { label: "SCZ", value: d.n_scz },
                  { label: "Ctrl", value: d.n_ctrl },
                  { label: "DE Genes", value: d.n_de_genes.toLocaleString() },
                  { label: "Modules", value: d.n_modules },
                  { label: "Hub Genes", value: d.n_hub_genes },
                  { label: "Risk Overlaps", value: d.n_risk_overlaps },
                  { label: "Drug Cands", value: d.n_drug_candidates.toLocaleString() },
                  { label: "Total Samples", value: d.n_scz + d.n_ctrl },
                ].map(m => (
                  <div key={m.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontSize: "0.65rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{m.label}</span>
                    <span style={{ fontFamily: "monospace", fontSize: "0.8rem", fontWeight: 600 }}>{m.value}</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: "0.75rem", fontSize: "0.7rem", color: datasetColor(d.dataset_id) }}>
                View details →
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Cross-dataset module preservation */}
      <div style={{ marginTop: "1.5rem", background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "1rem" }}>
        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>Cross-Dataset Note</div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.6 }}>
          Modules M1, M3, M6, M9 from GSE38484 are highly preserved in GSE27383 (Zsummary &gt; 10),
          confirming robust co-expression structure across blood compartments.
          Brain modules (GSE21138) are not well-preserved in blood datasets, as expected given tissue differences.
          GSE21138 brain dataset has n=59 samples and produces no FDR-significant DE genes individually.
        </p>
      </div>
    </div>
  );
}
