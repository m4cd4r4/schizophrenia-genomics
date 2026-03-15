"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGenes } from "@/lib/api";
import type { GeneSummary } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import GeneLink from "@/components/shared/gene-link";
import { fmtPval, fmtLogFC, logFCColor, pvalColor } from "@/lib/format";

type SortKey = "combined_padj" | "mean_logFC" | "evidence_count" | "n_datasets";

export default function GenesPage() {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("combined_padj");
  const [filterHighEv, setFilterHighEv] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["genes", sort],
    queryFn: () => fetchGenes(300, sort),
  });

  const filtered = (data ?? []).filter(g => {
    if (filterHighEv && !g.evidence_count) return false;
    if (search && !g.gene.toUpperCase().includes(search.toUpperCase())) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sort === "combined_padj") return (a.combined_padj ?? 1) - (b.combined_padj ?? 1);
    if (sort === "mean_logFC") return Math.abs(b.mean_logFC ?? 0) - Math.abs(a.mean_logFC ?? 0);
    if (sort === "evidence_count") return (b.evidence_count ?? 0) - (a.evidence_count ?? 0);
    if (sort === "n_datasets") return (b.n_datasets ?? 0) - (a.n_datasets ?? 0);
    return 0;
  });

  const ColHeader = ({ label, key: k }: { label: string; key: SortKey }) => (
    <th onClick={() => setSort(k)} style={{ color: sort === k ? "var(--foreground)" : undefined }}>
      {label}{sort === k ? " ↓" : ""}
    </th>
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1rem" }}>
        <div>
          <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Gene Browser</h1>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Meta-analysis results across all 3 datasets. Click a gene for full evidence.</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="text"
            placeholder="Search gene..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ padding: "0.3rem 0.6rem", background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "0.78rem", borderRadius: 4, width: 180, fontFamily: "monospace" }}
          />
          <label style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.75rem", color: "var(--text-muted)", cursor: "pointer" }}>
            <input type="checkbox" checked={filterHighEv} onChange={e => setFilterHighEv(e.target.checked)} />
            High-evidence only
          </label>
        </div>
      </div>

      {isLoading ? <LoadingSkeleton /> : (
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <ColHeader label="Gene" key="combined_padj" />
                <ColHeader label="Mean logFC" key="mean_logFC" />
                <ColHeader label="Meta FDR" key="combined_padj" />
                <ColHeader label="Datasets" key="n_datasets" />
                <th>Direction</th>
                <th>Hub</th>
                <th>Risk</th>
                <ColHeader label="Evidence" key="evidence_count" />
              </tr>
            </thead>
            <tbody>
              {sorted.slice(0, 200).map(g => (
                <tr key={g.gene}>
                  <td><GeneLink gene={g.gene} /></td>
                  <td style={{ color: logFCColor(g.mean_logFC), fontFamily: "monospace" }}>{fmtLogFC(g.mean_logFC)}</td>
                  <td style={{ color: pvalColor(g.combined_padj), fontFamily: "monospace" }}>{fmtPval(g.combined_padj)}</td>
                  <td style={{ color: "var(--text-muted)" }}>{g.n_datasets}</td>
                  <td>
                    {g.direction_consistent
                      ? <span style={{ color: "var(--green)", fontSize: "0.7rem" }}>consistent</span>
                      : <span style={{ color: "var(--amber)", fontSize: "0.7rem" }}>mixed</span>}
                  </td>
                  <td style={{ color: g.is_hub ? "var(--amber-bright)" : "var(--text-dim)" }}>{g.is_hub ? "hub" : "-"}</td>
                  <td style={{ color: g.is_risk_gene ? "var(--red-bright)" : "var(--text-dim)" }}>{g.is_risk_gene ? "risk" : "-"}</td>
                  <td>
                    {g.evidence_count
                      ? <span style={{ color: g.evidence_count >= 3 ? "var(--amber-bright)" : "var(--blue)", fontSize: "0.75rem", fontWeight: 700 }}>{g.evidence_count}</span>
                      : <span style={{ color: "var(--text-dim)" }}>-</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ padding: "0.5rem 0.75rem", fontSize: "0.7rem", color: "var(--text-dim)", borderTop: "1px solid var(--border)" }}>
            {sorted.length} genes{search ? ` matching "${search}"` : ""}
          </div>
        </div>
      )}
    </div>
  );
}
