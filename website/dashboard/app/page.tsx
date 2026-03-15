"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "@/lib/api";
import StatBox from "@/components/shared/stat-box";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  ScatterChart, Scatter, CartesianGrid,
} from "recharts";
import { datasetColor, datasetLabel, fmtNES } from "@/lib/format";
import Link from "next/link";

const KEY_FINDINGS = [
  {
    title: "Immune Dysregulation",
    color: "var(--blue)",
    body: "CD8 T cells and NK cells are consistently reduced in SCZ across both blood datasets (GSE38484, GSE27383). Immune-related modules M2/M3 correlate with SCZ status. Replicated in 2 independent cohorts.",
    tier: "REPLICATED",
  },
  {
    title: "NMDA Receptor Pathway",
    color: "var(--green)",
    body: "GSEA reveals consistent enrichment of glutamate/NMDA receptor signaling. Top brain drug candidate d-serine (NMDA co-agonist) supports NMDA hypofunction hypothesis. Hub gene NRGN regulates NMDA downstream signaling.",
    tier: "REPLICATED",
  },
  {
    title: "Risk Gene Convergence",
    color: "var(--amber)",
    body: "92 high-evidence genes supported by DE + hub gene + GWAS risk convergence. TCF4, NRG1, HTR2A, FOXP1 validated as schizophrenia markers. 0 genes identified as medication confounders.",
    tier: "REPLICATED",
  },
];

export default function HomePage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });

  if (isLoading) return <LoadingSkeleton rows={12} />;
  if (error) return <div style={{ color: "var(--red)", padding: "2rem" }}>Failed to load stats. Is the API running?</div>;
  if (!stats) return null;

  const deData = stats.de_by_dataset.map(d => ({
    name: datasetLabel(d.dataset_id),
    id: d.dataset_id,
    up: d.n_up,
    down: d.n_down,
  }));

  const drugData = stats.top_cross_drugs.slice(0, 15).map(d => ({
    name: d.drug_name,
    nes: Math.abs(d.mean_NES),
    datasets: d.n_datasets,
    known: d.is_known,
  }));

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.4rem" }}>
          Schizophrenia Transcriptomics
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: 700 }}>
          10-stage genomics pipeline across 3 GEO datasets: whole blood (GSE38484, n=202),
          PBMC (GSE27383, n=72), and post-mortem prefrontal cortex (GSE21138, n=59).
          Differential expression, WGCNA co-expression, drug repurposing, and medication confounding analysis.
        </p>
      </div>

      {/* Stat boxes */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <StatBox label="Datasets" value={stats.n_datasets} color="var(--blue)" />
        <StatBox label="Genes Tested" value={stats.n_genes_tested} color="var(--foreground)" />
        <StatBox label="Meta-Sig Genes" value={stats.n_meta_sig_genes} sub="FDR < 0.05" color="var(--blue-bright)" />
        <StatBox label="High-Evidence" value={stats.n_high_evidence_genes} sub="2-3 lines of evidence" color="var(--amber)" />
        <StatBox label="Drug Candidates" value={stats.n_drug_candidates} sub="2+ datasets" color="var(--purple)" />
        <StatBox label="Preserved Modules" value={stats.n_preserved_modules} sub="Zsummary > 10" color="var(--green)" />
        <StatBox label="Validated APs" value={stats.n_validated_antipsychotics} sub="known antipsychotics recovered" color="var(--green-bright)" />
        <StatBox label="Pipeline Stages" value={stats.n_pipeline_stages} color="var(--text-muted)" />
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        {/* DE genes by dataset */}
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "1rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            DE Genes by Dataset (FDR &lt; 0.05)
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={deData} margin={{ top: 0, right: 10, bottom: 0, left: -10 }}>
              <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 11 }}
                formatter={(val, name) => [(val as number).toLocaleString(), name === "up" ? "Upregulated" : "Downregulated"]}
              />
              <Bar dataKey="up" stackId="a" fill="var(--red)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="down" stackId="a" fill="var(--blue)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top cross-dataset drugs */}
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "1rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Top Cross-Dataset Drug Candidates
          </div>
          <div style={{ maxHeight: 160, overflowY: "auto" }}>
            {drugData.slice(0, 10).map(d => (
              <div key={d.name} style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.3rem" }}>
                <div style={{ width: 120, fontSize: "0.75rem", fontFamily: "monospace", color: d.known ? "var(--green-bright)" : "var(--foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {d.name}
                </div>
                <div style={{ flex: 1, height: 8, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.min(100, d.nes * 50)}%`, background: d.known ? "var(--green)" : "var(--purple)", borderRadius: 2 }} />
                </div>
                <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", width: 20, textAlign: "right" }}>{d.datasets}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Key findings */}
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem", color: "var(--text-muted)" }}>
          Key Findings
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          {KEY_FINDINGS.map(f => (
            <div key={f.title} style={{
              background: "var(--card)",
              border: `1px solid var(--border)`,
              borderTop: `3px solid ${f.color}`,
              borderRadius: 6,
              padding: "1rem",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>{f.title}</span>
                <span className="tier-replicated">{f.tier}</span>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>{f.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick links */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {[
          { href: "/genes", label: "Browse Genes" },
          { href: "/datasets", label: "Dataset Comparison" },
          { href: "/drugs", label: "Drug Candidates" },
          { href: "/query", label: "Ask a Question" },
        ].map(l => (
          <Link key={l.href} href={l.href} style={{
            display: "inline-block",
            padding: "0.35rem 0.75rem",
            background: "var(--card-highlight)",
            border: "1px solid var(--border)",
            borderRadius: 4,
            fontSize: "0.78rem",
            color: "var(--blue-bright)",
            textDecoration: "none",
          }}>
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
