"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { use } from "react";
import {
  fetchDatasetDE, fetchDatasetModules, fetchDatasetHubGenes,
  fetchDatasetRiskOverlap, fetchDatasetPathways, fetchDatasetCellTypes,
  fetchDatasetPPI, fetchDatasetDrugs,
} from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import GeneLink from "@/components/shared/gene-link";
import { fmtPval, fmtLogFC, fmtNum, fmtNES, logFCColor, pvalColor, nesColor, datasetLabel, datasetColor } from "@/lib/format";

const TABS = ["DE Results", "Modules", "Hub Genes", "Risk Overlap", "Pathways", "Cell Types", "Drugs"] as const;
type Tab = typeof TABS[number];

export default function DatasetPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [tab, setTab] = useState<Tab>("DE Results");

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <h1 style={{ fontFamily: "monospace", fontSize: "1.25rem", fontWeight: 700, color: datasetColor(id) }}>
          {id}
        </h1>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{datasetLabel(id)}</div>
      </div>

      <div style={{ display: "flex", gap: "0.25rem", borderBottom: "1px solid var(--border)", marginBottom: "1rem" }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "0.4rem 0.75rem",
            background: "none",
            border: "none",
            borderBottom: tab === t ? `2px solid ${datasetColor(id)}` : "2px solid transparent",
            color: tab === t ? "var(--foreground)" : "var(--text-muted)",
            fontSize: "0.78rem",
            cursor: "pointer",
            fontWeight: tab === t ? 600 : 400,
          }}>
            {t}
          </button>
        ))}
      </div>

      {tab === "DE Results" && <DETab id={id} />}
      {tab === "Modules" && <ModulesTab id={id} />}
      {tab === "Hub Genes" && <HubGenesTab id={id} />}
      {tab === "Risk Overlap" && <RiskTab id={id} />}
      {tab === "Pathways" && <PathwaysTab id={id} />}
      {tab === "Cell Types" && <CellTypesTab id={id} />}
      {tab === "Drugs" && <DrugsTab id={id} />}
    </div>
  );
}

function DETab({ id }: { id: string }) {
  const [padj, setPadj] = useState(0.05);
  const { data, isLoading } = useQuery({ queryKey: ["de", id, padj], queryFn: () => fetchDatasetDE(id, padj, 200) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.75rem" }}>
        <label style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>FDR threshold:</label>
        {[0.05, 0.1, 0.25].map(v => (
          <button key={v} onClick={() => setPadj(v)} style={{
            padding: "0.2rem 0.5rem", background: padj === v ? "var(--card-highlight)" : "none",
            border: `1px solid ${padj === v ? "var(--border-accent)" : "var(--border)"}`,
            borderRadius: 3, color: padj === v ? "var(--foreground)" : "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer",
          }}>{v}</button>
        ))}
        <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>{data?.length ?? 0} genes</span>
      </div>
      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto", maxHeight: 500 }}>
        <table className="data-table">
          <thead><tr><th>Gene</th><th>logFC</th><th>Mean SCZ</th><th>Mean Ctrl</th><th>Stat</th><th>p-value</th><th>FDR</th></tr></thead>
          <tbody>
            {(data ?? []).map(g => (
              <tr key={g.gene}>
                <td><GeneLink gene={g.gene} /></td>
                <td style={{ color: logFCColor(g.logFC), fontFamily: "monospace" }}>{fmtLogFC(g.logFC)}</td>
                <td style={{ fontFamily: "monospace" }}>{fmtNum(g.mean_SCZ)}</td>
                <td style={{ fontFamily: "monospace" }}>{fmtNum(g.mean_control)}</td>
                <td style={{ fontFamily: "monospace" }}>{fmtNum(g.stat)}</td>
                <td style={{ fontFamily: "monospace" }}>{fmtPval(g.pvalue)}</td>
                <td style={{ color: pvalColor(g.padj), fontFamily: "monospace" }}>{fmtPval(g.padj)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ModulesTab({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["modules", id], queryFn: () => fetchDatasetModules(id) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
      <table className="data-table">
        <thead><tr><th>Module</th><th>Genes</th><th>SCZ Cor</th><th>p-value</th><th>Risk Genes</th><th>Fraction Risk</th></tr></thead>
        <tbody>
          {(data ?? []).map(m => (
            <tr key={m.module}>
              <td style={{ fontFamily: "monospace", fontWeight: 600 }}>{m.module}</td>
              <td>{m.n_genes?.toLocaleString()}</td>
              <td style={{ color: Math.abs(m.correlation ?? 0) > 0.3 ? (m.correlation ?? 0) > 0 ? "var(--red-bright)" : "var(--blue-bright)" : "var(--text-muted)", fontFamily: "monospace" }}>{fmtNum(m.correlation)}</td>
              <td style={{ color: pvalColor(m.pvalue), fontFamily: "monospace" }}>{fmtPval(m.pvalue)}</td>
              <td>{m.risk_genes_count ?? "-"}</td>
              <td style={{ fontFamily: "monospace" }}>{m.fraction_risk != null ? (m.fraction_risk * 100).toFixed(1) + "%" : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HubGenesTab({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["hub_genes", id], queryFn: () => fetchDatasetHubGenes(id) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
      <table className="data-table">
        <thead><tr><th>Gene</th><th>Module</th><th>kME</th><th>kME Signed</th></tr></thead>
        <tbody>
          {(data ?? []).map(h => (
            <tr key={`${h.gene}_${h.module}`}>
              <td><GeneLink gene={h.gene} /></td>
              <td style={{ fontFamily: "monospace" }}>{h.module}</td>
              <td style={{ color: "var(--amber)", fontFamily: "monospace" }}>{fmtNum(h.kME)}</td>
              <td style={{ color: logFCColor(h.kME_signed), fontFamily: "monospace" }}>{fmtNum(h.kME_signed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskTab({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["risk", id], queryFn: () => fetchDatasetRiskOverlap(id) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
      <table className="data-table">
        <thead><tr><th>Gene</th><th>logFC</th><th>FDR</th><th>Significant</th><th>PGC3</th><th>Family</th><th>Source</th></tr></thead>
        <tbody>
          {(data ?? []).map(r => (
            <tr key={r.gene}>
              <td><GeneLink gene={r.gene} /></td>
              <td style={{ color: logFCColor(r.logFC), fontFamily: "monospace" }}>{fmtLogFC(r.logFC)}</td>
              <td style={{ color: pvalColor(r.padj), fontFamily: "monospace" }}>{fmtPval(r.padj)}</td>
              <td style={{ color: r.is_significant ? "var(--green)" : "var(--text-dim)" }}>{r.is_significant ? "yes" : "no"}</td>
              <td style={{ color: r.in_PGC3 ? "var(--red-bright)" : "var(--text-dim)" }}>{r.in_PGC3 ? "yes" : "-"}</td>
              <td style={{ color: r.in_family_study ? "var(--amber-bright)" : "var(--text-dim)" }}>{r.in_family_study ? "yes" : "-"}</td>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{r.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PathwaysTab({ id }: { id: string }) {
  const [lib, setLib] = useState<string>("");
  const { data, isLoading } = useQuery({ queryKey: ["pathways", id, lib], queryFn: () => fetchDatasetPathways(id, lib || undefined, 0.05) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div>
      <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.75rem" }}>
        {["", "KEGG", "GO", "Reactome"].map(l => (
          <button key={l} onClick={() => setLib(l)} style={{
            padding: "0.2rem 0.5rem", background: lib === l ? "var(--card-highlight)" : "none",
            border: `1px solid ${lib === l ? "var(--border-accent)" : "var(--border)"}`,
            borderRadius: 3, color: lib === l ? "var(--foreground)" : "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer",
          }}>{l || "All"}</button>
        ))}
      </div>
      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto", maxHeight: 500 }}>
        <table className="data-table">
          <thead><tr><th>Library</th><th>Term</th><th>NES</th><th>FDR</th><th>Leading Genes</th></tr></thead>
          <tbody>
            {(data ?? []).slice(0, 100).map((r, i) => (
              <tr key={i}>
                <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{r.gene_set_library}</td>
                <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>{r.term}</td>
                <td style={{ color: nesColor(r.NES), fontFamily: "monospace" }}>{fmtNES(r.NES)}</td>
                <td style={{ color: pvalColor(r.fdr_qval), fontFamily: "monospace" }}>{fmtPval(r.fdr_qval)}</td>
                <td style={{ color: "var(--text-dim)", fontSize: "0.7rem", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {(r.lead_genes ?? "").split(";").slice(0, 5).join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CellTypesTab({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["cell_types", id], queryFn: () => fetchDatasetCellTypes(id) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
      <table className="data-table">
        <thead><tr><th>Cell Type</th><th>Mean SCZ</th><th>Mean Ctrl</th><th>logFC</th><th>p-value</th><th>FDR</th></tr></thead>
        <tbody>
          {(data ?? []).map(c => (
            <tr key={c.cell_type}>
              <td style={{ fontWeight: 600 }}>{c.cell_type}</td>
              <td style={{ fontFamily: "monospace" }}>{fmtNum(c.mean_score_SCZ)}</td>
              <td style={{ fontFamily: "monospace" }}>{fmtNum(c.mean_score_ctrl)}</td>
              <td style={{ color: logFCColor(c.logFC), fontFamily: "monospace" }}>{fmtLogFC(c.logFC)}</td>
              <td style={{ fontFamily: "monospace" }}>{fmtPval(c.pvalue)}</td>
              <td style={{ color: pvalColor(c.padj), fontFamily: "monospace" }}>{fmtPval(c.padj)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DrugsTab({ id }: { id: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["ds_drugs", id], queryFn: () => fetchDatasetDrugs(id) });
  if (isLoading) return <LoadingSkeleton />;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
      <table className="data-table">
        <thead><tr><th>Drug</th><th>NES</th><th>FDR</th><th>Libraries</th><th>Known AP</th><th>Repurpose</th><th>Score</th></tr></thead>
        <tbody>
          {(data ?? []).map(d => (
            <tr key={d.drug_name}>
              <td style={{ fontFamily: "monospace", color: d.is_known_psychiatric ? "var(--green-bright)" : d.is_repurposing_interest ? "var(--purple-bright)" : "var(--foreground)" }}>
                {d.drug_name}
              </td>
              <td style={{ color: nesColor(d.mean_NES), fontFamily: "monospace" }}>{fmtNES(d.mean_NES)}</td>
              <td style={{ color: pvalColor(d.min_FDR), fontFamily: "monospace" }}>{fmtPval(d.min_FDR)}</td>
              <td style={{ color: "var(--text-muted)" }}>{d.n_libraries}</td>
              <td style={{ color: d.is_known_psychiatric ? "var(--green)" : "var(--text-dim)" }}>{d.is_known_psychiatric ? "yes" : "-"}</td>
              <td style={{ color: d.is_repurposing_interest ? "var(--purple)" : "var(--text-dim)" }}>{d.is_repurposing_interest ? "yes" : "-"}</td>
              <td style={{ fontFamily: "monospace", color: "var(--text-muted)" }}>{fmtNum(d.composite_score, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
