"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "@/lib/api";
import StatBox from "@/components/shared/stat-box";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { datasetLabel } from "@/lib/format";
import Link from "next/link";

const KEY_FINDINGS = [
  {
    id: "immune",
    label: "01",
    title: "Immune Dysregulation",
    body: "CD8 T cells and NK cells consistently reduced in schizophrenia across both blood datasets. Immune modules M2 and M3 correlate with case status. Confirmed independently in GSE38484 (n=202) and GSE27383 (n=72).",
    detail: "2 independent cohorts · immune cell type DE · module-trait correlation",
    weight: "primary",
  },
  {
    id: "nmda",
    label: "02",
    title: "NMDA Hypofunction",
    body: "Glutamate and NMDA receptor signalling enriched by GSEA across datasets. Hub gene NRGN regulates NMDA downstream signalling. Top brain drug candidate d-serine directly supports the hypofunction hypothesis.",
    detail: "GSEA enrichment · NRGN hub gene · d-serine drug candidate",
    weight: "secondary",
  },
  {
    id: "risk",
    label: "03",
    title: "Risk Gene Convergence",
    body: "92 high-evidence genes supported by DE, hub gene status, and GWAS risk locus overlap. TCF4, NRG1, HTR2A, and FOXP1 validated as schizophrenia markers. Zero genes flagged as medication confounders.",
    detail: "DE + hub + GWAS convergence · 92 high-evidence · 0 confounders",
    weight: "secondary",
  },
];

export default function HomePage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });

  if (isLoading) return <LoadingSkeleton rows={14} />;
  if (error) return (
    <div style={{ padding: "2rem", color: "var(--red-bright)", fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>
      API unavailable. Is the backend running?
    </div>
  );
  if (!stats) return null;

  const deData = stats.de_by_dataset.map(d => ({
    name: datasetLabel(d.dataset_id),
    up: d.n_up,
    down: d.n_down,
  }));

  const drugData = stats.top_cross_drugs.slice(0, 12).map(d => ({
    name: d.drug_name.replace(/-\d+$/, ""),
    nes: Math.abs(d.mean_NES),
    known: d.is_known,
  }));

  const statItems = [
    { label: "Datasets", value: stats.n_datasets, color: "var(--blue)" },
    { label: "Genes Tested", value: stats.n_genes_tested, color: "var(--text)" },
    { label: "Meta-Sig Genes", value: stats.n_meta_sig_genes, sub: "FDR < 0.05", color: "var(--blue-bright)" },
    { label: "High-Evidence", value: stats.n_high_evidence_genes, sub: "2-3 lines of support", color: "var(--amber)" },
    { label: "Drug Candidates", value: stats.n_drug_candidates, sub: "cross-dataset", color: "var(--purple)" },
    { label: "Preserved Modules", value: stats.n_preserved_modules, sub: "Zsummary > 10", color: "var(--green)" },
    { label: "Validated APs", value: stats.n_validated_antipsychotics, sub: "antipsychotics recovered", color: "var(--green-bright)" },
    { label: "Pipeline Stages", value: stats.n_pipeline_stages, color: "var(--text-dim)" },
  ];

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 400, letterSpacing: "-0.02em", marginBottom: "0.5rem", lineHeight: 1.15 }}>
          Schizophrenia Transcriptomics
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9375rem", maxWidth: 680, lineHeight: 1.65 }}>
          10-stage genomics pipeline across 3 GEO datasets: whole blood (GSE38484, n=202),
          PBMC (GSE27383, n=72), and post-mortem prefrontal cortex (GSE21138, n=59).
          Differential expression, WGCNA, drug repurposing, and medication confounding analysis.
        </p>
      </div>

      {/* Stats: unified grid panel */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", background: "var(--surface)", marginBottom: "2rem" }}>
        {statItems.map((item, i) => (
          <div key={item.label} style={{ borderRight: (i + 1) % 4 !== 0 ? "1px solid var(--border)" : "none", borderBottom: i < 4 ? "1px solid var(--border)" : "none" }}>
            <StatBox {...item} />
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "2rem" }}>
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem", fontFamily: "var(--font-body)", fontWeight: 500 }}>
            Differentially Expressed Genes (FDR &lt; 0.05)
          </div>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={deData} margin={{ top: 0, right: 8, bottom: 0, left: -12 }}>
              <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "var(--text-dim)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "var(--surface-overlay)", border: "1px solid var(--border-strong)", borderRadius: 4, fontSize: 11, fontFamily: "var(--font-body)" }}
                formatter={(val, name) => [(val as number).toLocaleString(), name === "up" ? "Up" : "Down"]}
              />
              <Bar dataKey="up" stackId="a" fill="var(--red)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="down" stackId="a" fill="var(--blue)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem", fontFamily: "var(--font-body)", fontWeight: 500 }}>
            Top Cross-Dataset Drug Candidates (|NES|)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            {drugData.map(d => (
              <div key={d.name} style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                <div style={{ width: 130, fontSize: "0.75rem", fontFamily: "var(--font-data)", color: d.known ? "var(--green-bright)" : "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flexShrink: 0 }}>
                  {d.name}
                </div>
                <div style={{ flex: 1, height: 5, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.min(100, d.nes * 50)}%`, background: d.known ? "var(--green)" : "var(--purple)", borderRadius: 3 }} />
                </div>
                <div style={{ fontSize: "0.6875rem", fontFamily: "var(--font-data)", color: "var(--text-dim)", width: 32, textAlign: "right", flexShrink: 0 }}>
                  {d.nes.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Key findings: asymmetric layout, not identical 3-column card grid */}
      <div style={{ marginBottom: "1.75rem" }}>
        <div style={{ fontSize: "0.6875rem", fontFamily: "var(--font-body)", fontWeight: 500, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem" }}>
          Key Findings
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: "1px", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", background: "var(--border)" }}>
          {/* Primary finding */}
          <div style={{ background: "var(--surface)", padding: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <span style={{ fontFamily: "var(--font-data)", fontSize: "0.6875rem", color: "var(--text-dim)", letterSpacing: "0.06em" }}>01</span>
              <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.125rem", fontWeight: 400, color: "var(--text)", margin: 0 }}>
                {KEY_FINDINGS[0].title}
              </h3>
              <span className="tier-replicated">Replicated</span>
            </div>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", lineHeight: 1.7, margin: "0 0 0.75rem", maxWidth: 520 }}>
              {KEY_FINDINGS[0].body}
            </p>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)" }}>
              {KEY_FINDINGS[0].detail}
            </div>
          </div>

          {/* Secondary findings stacked */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
            {KEY_FINDINGS.slice(1).map(f => (
              <div key={f.id} style={{ background: "var(--surface)", padding: "1.25rem 1.5rem", flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.5rem" }}>
                  <span style={{ fontFamily: "var(--font-data)", fontSize: "0.6875rem", color: "var(--text-dim)", letterSpacing: "0.06em" }}>{f.label}</span>
                  <h3 style={{ fontFamily: "var(--font-display)", fontSize: "0.9375rem", fontWeight: 400, color: "var(--text)", margin: 0 }}>
                    {f.title}
                  </h3>
                  <span className="tier-replicated">Replicated</span>
                </div>
                <p style={{ fontSize: "0.825rem", color: "var(--text-muted)", lineHeight: 1.65, margin: "0 0 0.5rem" }}>
                  {f.body}
                </p>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)" }}>
                  {f.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick navigation */}
      <div style={{ display: "flex", gap: "0.625rem", flexWrap: "wrap" }}>
        {[
          { href: "/genes", label: "Browse Genes" },
          { href: "/datasets", label: "Dataset Comparison" },
          { href: "/drugs", label: "Drug Candidates" },
          { href: "/pathways", label: "Pathways" },
          { href: "/query", label: "Ask a Question" },
        ].map(l => (
          <Link key={l.href} href={l.href} style={{ display: "inline-flex", alignItems: "center", padding: "0.375rem 0.875rem", background: "transparent", border: "1px solid var(--border-strong)", borderRadius: 5, fontSize: "0.8125rem", color: "var(--text-muted)", textDecoration: "none", fontFamily: "var(--font-body)" }}>
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
