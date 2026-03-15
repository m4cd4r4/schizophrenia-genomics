"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchGene } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import { fmtPval, fmtLogFC, fmtNum, logFCColor, pvalColor, datasetLabel, datasetColor } from "@/lib/format";
import { use } from "react";

export default function GenePage({ params }: { params: Promise<{ gene: string }> }) {
  const { gene } = use(params);
  const geneUpper = gene.toUpperCase();

  const { data, isLoading, error } = useQuery({
    queryKey: ["gene", geneUpper],
    queryFn: () => fetchGene(geneUpper),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <div style={{ color: "var(--red)", padding: "1rem" }}>Gene {geneUpper} not found.</div>;
  if (!data) return null;

  const meta = data.meta as Record<string, unknown> | null;
  const highEv = data.high_evidence as Record<string, unknown> | null;

  return (
    <div>
      <div style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ fontFamily: "monospace", fontSize: "1.5rem", fontWeight: 700, color: "var(--blue-bright)", marginBottom: "0.25rem" }}>
          {geneUpper}
        </h1>
        {highEv && (
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span className="tier-replicated">{highEv.evidence_count as number} lines of evidence</span>
            {(highEv.is_DE as boolean) && <span className="tier-single">DE</span>}
            {(highEv.is_hub as boolean) && <span style={{ color: "var(--amber)" }} className="tier-single">Hub Gene</span>}
            {(highEv.is_risk_gene as boolean) && <span className="tier-underpowered">Risk Gene ({highEv.risk_source as string})</span>}
          </div>
        )}
      </div>

      {/* Meta-analysis */}
      {meta && (
        <Section title="Meta-Analysis (3 Datasets)">
          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
            <Metric label="Mean logFC" value={fmtLogFC(meta.mean_logFC as number)} color={logFCColor(meta.mean_logFC as number)} />
            <Metric label="Combined FDR" value={fmtPval(meta.combined_padj as number)} color={pvalColor(meta.combined_padj as number)} />
            <Metric label="Datasets" value={`${meta.n_datasets}/3`} />
            <Metric label="Direction" value={(meta.direction_consistent as boolean) ? "Consistent" : "Mixed"} color={(meta.direction_consistent as boolean) ? "var(--green)" : "var(--amber)"} />
          </div>
        </Section>
      )}

      {/* DE per dataset */}
      {data.de_results.length > 0 && (
        <Section title="Differential Expression">
          <table className="data-table">
            <thead><tr><th>Dataset</th><th>logFC</th><th>Mean SCZ</th><th>Mean Ctrl</th><th>Stat</th><th>p-value</th><th>FDR</th></tr></thead>
            <tbody>
              {(data.de_results as Record<string, unknown>[]).map((r, i) => (
                <tr key={i}>
                  <td style={{ color: datasetColor(r.dataset_id as string) }}>{datasetLabel(r.dataset_id as string)}</td>
                  <td style={{ color: logFCColor(r.logFC as number), fontFamily: "monospace" }}>{fmtLogFC(r.logFC as number)}</td>
                  <td style={{ fontFamily: "monospace" }}>{fmtNum(r.mean_SCZ as number)}</td>
                  <td style={{ fontFamily: "monospace" }}>{fmtNum(r.mean_control as number)}</td>
                  <td style={{ fontFamily: "monospace" }}>{fmtNum(r.stat as number)}</td>
                  <td style={{ fontFamily: "monospace" }}>{fmtPval(r.pvalue as number)}</td>
                  <td style={{ color: pvalColor(r.padj as number), fontFamily: "monospace" }}>{fmtPval(r.padj as number)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {/* Hub genes */}
        {data.hub_genes.length > 0 && (
          <Section title="Module Hub Gene">
            {(data.hub_genes as Record<string, unknown>[]).map((h, i) => (
              <div key={i} style={{ display: "flex", gap: "1rem", marginBottom: "0.4rem" }}>
                <span style={{ color: datasetColor(h.dataset_id as string), fontSize: "0.8rem" }}>{datasetLabel(h.dataset_id as string)}</span>
                <span style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>Module {h.module as string}</span>
                <span style={{ color: "var(--amber)", fontSize: "0.8rem" }}>kME={fmtNum(h.kME as number)}</span>
              </div>
            ))}
          </Section>
        )}

        {/* Risk overlap */}
        {data.risk_overlap.length > 0 && (
          <Section title="Risk Gene Status">
            {(data.risk_overlap as Record<string, unknown>[]).map((r, i) => (
              <div key={i} style={{ fontSize: "0.78rem", marginBottom: "0.3rem" }}>
                <span style={{ color: datasetColor(r.dataset_id as string) }}>{datasetLabel(r.dataset_id as string)}: </span>
                <span style={{ color: (r.in_PGC3 as boolean) ? "var(--red-bright)" : "var(--text-muted)" }}>
                  {(r.in_PGC3 as boolean) ? "PGC3 locus" : ""}{(r.in_family_study as boolean) ? " family study" : ""}
                </span>
                <span style={{ color: (r.is_significant as boolean) ? "var(--green)" : "var(--text-dim)", marginLeft: "0.5rem" }}>
                  {(r.is_significant as boolean) ? `sig DE (FDR=${fmtPval(r.padj as number)})` : "not sig DE"}
                </span>
              </div>
            ))}
          </Section>
        )}
      </div>

      {/* PPI neighbors */}
      {data.ppi_neighbors.length > 0 && (
        <Section title="PPI Network Neighbors">
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
            {(data.ppi_neighbors as Record<string, unknown>[]).slice(0, 20).map((n, i) => (
              <span key={i} style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--blue)", background: "var(--card-highlight)", padding: "0.15rem 0.4rem", borderRadius: 3 }}>
                {n.neighbor as string}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Dose response */}
      {data.dose_response && (
        <Section title="Medication Dose-Response (Brain, GSE21138)">
          <div style={{ display: "flex", gap: "1.5rem" }}>
            <Metric label="Spearman rho" value={fmtNum((data.dose_response as Record<string, unknown>).spearman_rho as number)} />
            <Metric label="p-value" value={fmtPval((data.dose_response as Record<string, unknown>).pvalue as number)} />
            <Metric label="FDR" value={fmtPval((data.dose_response as Record<string, unknown>).padj as number)} />
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, marginBottom: "1rem", overflow: "hidden" }}>
      <div style={{ padding: "0.5rem 0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {title}
      </div>
      <div style={{ padding: "0.75rem" }}>{children}</div>
    </div>
  );
}

function Metric({ label, value, color = "var(--foreground)" }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: "1.1rem", fontFamily: "monospace", fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: "0.65rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}
