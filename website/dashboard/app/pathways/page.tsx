"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGSEA, fetchSCZPathways, fetchPreservation } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import { fmtPval, fmtNES, nesColor, pvalColor, datasetLabel, datasetColor } from "@/lib/format";

export default function PathwaysPage() {
  const [dataset, setDataset] = useState("");
  const [library, setLibrary] = useState("");

  const { data: gsea, isLoading: l1 } = useQuery({
    queryKey: ["gsea_all", dataset, library],
    queryFn: () => fetchGSEA(dataset || undefined, library || undefined, 0.05, 100),
  });
  const { data: sczPaths, isLoading: l2 } = useQuery({ queryKey: ["scz_paths"], queryFn: fetchSCZPathways });
  const { data: preservation, isLoading: l3 } = useQuery({ queryKey: ["preservation"], queryFn: fetchPreservation });

  return (
    <div>
      <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Pathway Enrichment</h1>
      <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        GSEA prerank results (KEGG, GO, Reactome) per dataset. FDR &lt; 0.05 shown by default.
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "0.3rem" }}>
          {["", "GSE38484", "GSE27383", "GSE21138"].map(d => (
            <button key={d} onClick={() => setDataset(d)} style={{
              padding: "0.2rem 0.5rem", background: dataset === d ? "var(--card-highlight)" : "none",
              border: `1px solid ${dataset === d ? "var(--border-accent)" : "var(--border)"}`,
              borderRadius: 3, color: d ? datasetColor(d) : (dataset === "" ? "var(--foreground)" : "var(--text-muted)"), fontSize: "0.72rem", cursor: "pointer",
            }}>{d ? datasetLabel(d) : "All"}</button>
          ))}
        </div>
        <div style={{ display: "flex", gap: "0.3rem" }}>
          {["", "KEGG", "GO", "Reactome"].map(l => (
            <button key={l} onClick={() => setLibrary(l)} style={{
              padding: "0.2rem 0.5rem", background: library === l ? "var(--card-highlight)" : "none",
              border: `1px solid ${library === l ? "var(--border-accent)" : "var(--border)"}`,
              borderRadius: 3, color: library === l ? "var(--foreground)" : "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer",
            }}>{l || "All libs"}</button>
          ))}
        </div>
      </div>

      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "auto", maxHeight: 450, marginBottom: "1.25rem" }}>
        {l1 ? <LoadingSkeleton /> : (
          <table className="data-table">
            <thead><tr><th>Dataset</th><th>Library</th><th>Term</th><th>NES</th><th>FDR</th><th>Leading Genes</th></tr></thead>
            <tbody>
              {(gsea ?? []).map((r, i) => (
                <tr key={i}>
                  <td style={{ color: datasetColor(r.dataset_id ?? ""), fontSize: "0.72rem" }}>{datasetLabel(r.dataset_id ?? "")}</td>
                  <td style={{ color: "var(--text-dim)", fontSize: "0.7rem" }}>{r.gene_set_library}</td>
                  <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>{r.term}</td>
                  <td style={{ color: nesColor(r.NES), fontFamily: "monospace" }}>{fmtNES(r.NES)}</td>
                  <td style={{ color: pvalColor(r.fdr_qval), fontFamily: "monospace" }}>{fmtPval(r.fdr_qval)}</td>
                  <td style={{ color: "var(--text-dim)", fontSize: "0.7rem", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {(r.lead_genes ?? "").split(";").slice(0, 4).join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <Section title="SCZ-Specific Pathways">
          {l2 ? <LoadingSkeleton /> : (
            <table className="data-table">
              <thead><tr><th>Term</th><th>NES</th><th>FDR</th></tr></thead>
              <tbody>
                {(sczPaths ?? []).slice(0, 15).map((r, i) => (
                  <tr key={i}>
                    <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>{r.term}</td>
                    <td style={{ color: nesColor(r.NES), fontFamily: "monospace" }}>{fmtNES(r.NES)}</td>
                    <td style={{ color: pvalColor(r.FDR), fontFamily: "monospace" }}>{fmtPval(r.FDR)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        <Section title="Module Preservation (Blood -> PBMC)">
          {l3 ? <LoadingSkeleton /> : (
            <table className="data-table">
              <thead><tr><th>Module</th><th>Zsummary</th><th>Genes Ref</th><th>Genes Common</th></tr></thead>
              <tbody>
                {(preservation ?? []).map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: "monospace" }}>{r.module}</td>
                    <td style={{ color: (r.Zsummary ?? 0) > 10 ? "var(--green-bright)" : (r.Zsummary ?? 0) > 5 ? "var(--amber)" : "var(--text-muted)", fontFamily: "monospace", fontWeight: 700 }}>
                      {r.Zsummary?.toFixed(1) ?? "N/A"}
                    </td>
                    <td style={{ fontFamily: "monospace" }}>{r.n_genes_ref}</td>
                    <td style={{ fontFamily: "monospace" }}>{r.n_genes_common}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      <div style={{ padding: "0.5rem 0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {title}
      </div>
      <div style={{ overflowX: "auto" }}>{children}</div>
    </div>
  );
}
