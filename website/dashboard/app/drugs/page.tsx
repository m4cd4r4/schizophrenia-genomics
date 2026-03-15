"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchCrossDatasetDrugs, fetchValidatedDrugs, fetchConfounding } from "@/lib/api";
import LoadingSkeleton from "@/components/shared/loading-skeleton";
import { fmtNES, fmtPval } from "@/lib/format";

function DrugTable({ data, showSource = false }: { data: import("@/lib/api").CrossDrug[]; showSource?: boolean }) {
  return (
    <table className="data-table" style={{ marginTop: "0.5rem" }}>
      <thead>
        <tr>
          <th>Drug</th>
          <th>Datasets</th>
          <th>Mean NES</th>
          <th>Best FDR</th>
          <th>Known AP</th>
          <th>Repurpose</th>
          {showSource && <th>Source Datasets</th>}
        </tr>
      </thead>
      <tbody>
        {data.map(d => (
          <tr key={d.drug_name}>
            <td style={{ fontFamily: "monospace", fontWeight: 600, color: d.is_known ? "var(--green-bright)" : d.is_repurpose ? "var(--purple-bright)" : "var(--foreground)" }}>
              {d.drug_name}
            </td>
            <td style={{ color: d.n_datasets >= 3 ? "var(--amber-bright)" : "var(--blue-bright)" }}>{d.n_datasets}</td>
            <td style={{ fontFamily: "monospace", color: Math.abs(d.mean_NES ?? 0) > 2 ? "var(--red-bright)" : "var(--text-muted)" }}>
              {fmtNES(d.mean_NES)}
            </td>
            <td style={{ fontFamily: "monospace", color: (d.best_FDR ?? 1) < 0.05 ? "var(--green-bright)" : "var(--text-muted)" }}>
              {fmtPval(d.best_FDR)}
            </td>
            <td style={{ color: d.is_known ? "var(--green-bright)" : "var(--text-dim)" }}>{d.is_known ? "yes" : "-"}</td>
            <td style={{ color: d.is_repurpose ? "var(--purple-bright)" : "var(--text-dim)" }}>{d.is_repurpose ? "yes" : "-"}</td>
            {showSource && <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{d.datasets}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DrugsPage() {
  const { data: crossDrugs, isLoading: l1 } = useQuery({ queryKey: ["cross_drugs"], queryFn: () => fetchCrossDatasetDrugs(3) });
  const { data: validated, isLoading: l2 } = useQuery({ queryKey: ["validated_drugs"], queryFn: fetchValidatedDrugs });
  const { data: confounding, isLoading: l3 } = useQuery({ queryKey: ["confounding"], queryFn: fetchConfounding });

  return (
    <div>
      <div style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Drug Repurposing</h1>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", maxWidth: 700 }}>
          GSEA prerank against 6 LINCS/CMap drug perturbation libraries. Drugs with NES reversal of SCZ signature are candidates.
          Known antipsychotics (haloperidol, clozapine) are recovered as validation.
        </p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.75rem 1rem" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--amber-bright)", fontFamily: "monospace" }}>
            {crossDrugs?.length ?? 0}
          </div>
          <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Drugs in all 3 datasets
          </div>
        </div>
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.75rem 1rem" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--green-bright)", fontFamily: "monospace" }}>
            {validated?.length ?? 0}
          </div>
          <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Known APs validated
          </div>
        </div>
      </div>

      <Section title="All-3-Dataset Candidates">
        {l1 ? <LoadingSkeleton rows={5} /> : (crossDrugs && <DrugTable data={crossDrugs} showSource />)}
      </Section>

      <Section title="Validated Antipsychotics (Recovered by Analysis)">
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
          These known psychiatric drugs are correctly identified by our approach, validating the transcriptomic drug repurposing method.
        </p>
        {l2 ? <LoadingSkeleton rows={3} /> : (validated && <DrugTable data={validated} showSource />)}
      </Section>

      <Section title="Medication Confounding Analysis">
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
          Blood DE genes were cross-referenced with brain medication dose-response data from GSE21138.
          Low confounding risk = finding reflects disease, not antipsychotic exposure.
        </p>
        {l3 ? <LoadingSkeleton rows={3} /> : confounding && (
          <table className="data-table">
            <thead><tr><th>Dataset</th><th>Confounding Risk</th><th>Note</th></tr></thead>
            <tbody>
              {confounding.report.map(r => (
                <tr key={r.dataset}>
                  <td style={{ fontFamily: "monospace" }}>{r.dataset}</td>
                  <td>
                    <span style={{
                      color: r.confounding_risk === "low" ? "var(--green)" : r.confounding_risk === "high" ? "var(--red)" : "var(--amber)",
                      fontWeight: 600,
                      fontSize: "0.75rem",
                    }}>
                      {r.confounding_risk}
                    </span>
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, marginBottom: "1rem", overflow: "hidden" }}>
      <div style={{ padding: "0.5rem 0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {title}
      </div>
      <div style={{ padding: "0.75rem", overflowX: "auto" }}>{children}</div>
    </div>
  );
}
