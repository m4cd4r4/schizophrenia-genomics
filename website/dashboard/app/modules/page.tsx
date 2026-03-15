"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDatasetModules, fetchDatasetHubGenes, fetchPreservation, fetchModuleEnrichment } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import { fmtPval, datasetLabel, datasetColor } from "@/lib/format";
import type { Module, HubGene, Preservation } from "@/lib/api";

const DATASETS = ["GSE38484", "GSE27383", "GSE21138"];

function preservationBadge(z: number | null | undefined) {
  if (z == null) return <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>N/A</span>;
  if (z > 10) return <span style={{ background: "rgba(39,174,96,0.15)", color: "var(--green-bright)", border: "1px solid rgba(39,174,96,0.3)", padding: "0.1rem 0.35rem", borderRadius: 3, fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase" as const }}>Strong Z={z.toFixed(1)}</span>;
  if (z > 5) return <span style={{ background: "rgba(212,147,13,0.15)", color: "var(--amber-bright)", border: "1px solid rgba(212,147,13,0.3)", padding: "0.1rem 0.35rem", borderRadius: 3, fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase" as const }}>Moderate Z={z.toFixed(1)}</span>;
  return <span style={{ background: "rgba(136,136,136,0.1)", color: "var(--text-muted)", border: "1px solid var(--border)", padding: "0.1rem 0.35rem", borderRadius: 3, fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase" as const }}>Weak Z={z.toFixed(1)}</span>;
}

function correlationBar(cor: number) {
  const pct = Math.abs(cor) * 100;
  const color = cor > 0 ? "var(--red-bright)" : "var(--blue-bright)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
      <div style={{ width: 60, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontFamily: "monospace", fontSize: "0.72rem", color: cor > 0 ? "var(--red-bright)" : "var(--blue-bright)" }}>
        {cor > 0 ? "+" : ""}{cor.toFixed(3)}
      </span>
    </div>
  );
}

function DatasetModulesSection({ datasetId, preservation }: { datasetId: string; preservation: Preservation[] }) {
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  const { data: modules, isLoading } = useQuery({
    queryKey: ["modules", datasetId],
    queryFn: () => fetchDatasetModules(datasetId),
  });

  const { data: hubs } = useQuery({
    queryKey: ["hub_genes", datasetId, selectedModule],
    queryFn: () => fetchDatasetHubGenes(datasetId, selectedModule ?? undefined),
    enabled: !!selectedModule,
  });

  const { data: enrichment } = useQuery({
    queryKey: ["mod_enrich", datasetId, selectedModule],
    queryFn: () => fetchModuleEnrichment(datasetId, selectedModule ?? undefined),
    enabled: !!selectedModule,
  });

  const dsPreservation = preservation.filter(p => p.ref_dataset === datasetId || p.test_dataset === datasetId);

  const getPreservation = (module: string) =>
    dsPreservation.find(p => p.module === module);

  return (
    <div style={{ marginBottom: "2rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: datasetColor(datasetId), display: "inline-block" }} />
        <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1rem", fontWeight: 700, color: datasetColor(datasetId) }}>
          {datasetLabel(datasetId)}
        </h2>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
          {datasetId === "GSE38484" ? "whole blood" : datasetId === "GSE27383" ? "PBMC" : "prefrontal cortex"}
        </span>
      </div>

      {isLoading ? <LoadingSkeleton /> : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "0.75rem" }}>
          {(modules ?? []).map((mod: Module) => {
            const pres = getPreservation(mod.module);
            const isSelected = selectedModule === mod.module;
            return (
              <div
                key={mod.module}
                onClick={() => setSelectedModule(isSelected ? null : mod.module)}
                style={{
                  background: isSelected ? "var(--card-highlight)" : "var(--card)",
                  border: `1px solid ${isSelected ? "var(--border-accent)" : "var(--border)"}`,
                  borderRadius: 6,
                  padding: "0.75rem",
                  cursor: "pointer",
                  transition: "border-color 0.15s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "0.75rem", fontWeight: 700, color: "var(--foreground)" }}>
                    {mod.module}
                  </span>
                  {preservationBadge(pres?.Zsummary)}
                </div>

                <div style={{ marginBottom: "0.4rem" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginBottom: "0.2rem", textTransform: "uppercase" as const, letterSpacing: "0.05em" }}>SCZ correlation</div>
                  {correlationBar(mod.correlation ?? 0)}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.25rem", marginTop: "0.4rem" }}>
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: 700, fontFamily: "monospace", color: "var(--foreground)" }}>{mod.n_genes ?? 0}</div>
                    <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", textTransform: "uppercase" as const }}>genes</div>
                  </div>
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: 700, fontFamily: "monospace", color: "var(--amber)" }}>{mod.risk_genes_count ?? 0}</div>
                    <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", textTransform: "uppercase" as const }}>risk</div>
                  </div>
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: 700, fontFamily: "monospace", color: "var(--text-muted)" }}>{fmtPval(mod.pvalue)}</div>
                    <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", textTransform: "uppercase" as const }}>p-val</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedModule && (
        <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
            <div style={{ padding: "0.5rem 0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.08em" }}>
              Hub Genes - {selectedModule}
            </div>
            <div style={{ overflowX: "auto" as const, maxHeight: 200 }}>
              <table className="data-table">
                <thead><tr><th>Gene</th><th>kME</th></tr></thead>
                <tbody>
                  {(hubs ?? []).slice(0, 10).map((h: HubGene, i: number) => (
                    <tr key={i}>
                      <td style={{ fontFamily: "monospace", fontSize: "0.75rem", fontWeight: 600, color: "var(--blue-bright)", textTransform: "uppercase" as const }}>{h.gene}</td>
                      <td style={{ fontFamily: "monospace", color: h.kME_signed > 0 ? "var(--red)" : "var(--blue)" }}>{h.kME_signed?.toFixed(3) ?? h.kME?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
            <div style={{ padding: "0.5rem 0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.08em" }}>
              Pathway Enrichment - {selectedModule}
            </div>
            <div style={{ overflowX: "auto" as const, maxHeight: 200 }}>
              <table className="data-table">
                <thead><tr><th>Term</th><th>Score</th><th>FDR</th></tr></thead>
                <tbody>
                  {(enrichment ?? []).slice(0, 8).map((e, i) => (
                    <tr key={i}>
                      <td style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", fontSize: "0.7rem" }}>{e.term}</td>
                      <td style={{ fontFamily: "monospace", color: "var(--amber)" }}>{e.combined_score?.toFixed(0)}</td>
                      <td style={{ fontFamily: "monospace", color: "var(--text-muted)", fontSize: "0.7rem" }}>{fmtPval(e.adjusted_pvalue)}</td>
                    </tr>
                  ))}
                  {(enrichment ?? []).length === 0 && (
                    <tr><td colSpan={3} style={{ color: "var(--text-muted)", fontSize: "0.7rem", textAlign: "center" as const, padding: "0.5rem" }}>No significant enrichment</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ModulesPage() {
  const { data: preservation, isLoading: presLoading } = useQuery({
    queryKey: ["preservation"],
    queryFn: fetchPreservation,
  });

  return (
    <div>
      <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Co-expression Modules</h1>
      <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
        WGCNA modules per dataset. Click a module card to expand hub genes and pathway enrichment.
      </p>

      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>Module Preservation (Blood to PBMC)</div>
        {presLoading ? <LoadingSkeleton /> : (
          <table className="data-table">
            <thead><tr><th>Module</th><th>Ref Dataset</th><th>Test Dataset</th><th>Zsummary</th><th>Genes Ref</th><th>Common</th></tr></thead>
            <tbody>
              {(preservation ?? []).map((p, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: "monospace", fontWeight: 600 }}>{p.module}</td>
                  <td style={{ color: datasetColor(p.ref_dataset), fontSize: "0.7rem" }}>{datasetLabel(p.ref_dataset)}</td>
                  <td style={{ color: datasetColor(p.test_dataset), fontSize: "0.7rem" }}>{datasetLabel(p.test_dataset)}</td>
                  <td style={{ fontFamily: "monospace", fontWeight: 700 }}>
                    {preservationBadge(p.Zsummary)}
                  </td>
                  <td style={{ fontFamily: "monospace" }}>{p.n_genes_ref}</td>
                  <td style={{ fontFamily: "monospace" }}>{p.n_genes_common}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {DATASETS.map(ds => (
        <DatasetModulesSection key={ds} datasetId={ds} preservation={preservation ?? []} />
      ))}
    </div>
  );
}
