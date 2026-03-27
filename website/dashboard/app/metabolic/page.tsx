"use client";
import { useState } from "react";
import Link from "next/link";

const TRIALS = [
  { id: "NCT03935854", title: "Stanford Pilot (Sethi)", institution: "Stanford University", status: "completed", n: 23, design: "Single-arm, 4 months", result: "32% BPRS reduction; zero met MetS criteria at end; visceral fat -36%, HOMA-IR -27%", color: "var(--green)" },
  { id: "NCT05268809", title: "VA Neural Network Stability", institution: "Northern California VA", status: "completed", n: 71, design: "Very low carb KD, 4 weeks", result: "Results pending publication", color: "var(--green)" },
  { id: "NCT05968638", title: "University of Maryland KD", institution: "University of Maryland", status: "active", n: 50, design: "Inpatient KD, PANSS primary", result: "Case report: 69% HOMA-IR decrease, 80% EPS resolution, 61% CRP reduction", color: "var(--amber)" },
  { id: "NCT03873922", title: "Finnish RCT", institution: "Kuopio University Hospital", status: "recruiting", n: 40, design: "RCT, modified KD, 6 weeks", result: "First European RCT", color: "var(--blue)" },
  { id: "NCT06748950", title: "Stanford Deep Omics", institution: "Stanford University", status: "planned", n: 120, design: "RCT with metabolomics/proteomics", result: "Largest planned KMT trial; completion 2028", color: "var(--purple)" },
  { id: "NCT07309172", title: "KetoBrain (Denmark)", institution: "University of Aarhus", status: "recruiting", n: 34, design: "PET imaging, first-episode drug-naive", result: "First brain imaging study in antipsychotic-naive patients", color: "var(--blue)" },
  { id: "NCT06221852", title: "McLean Hospital (Palmer)", institution: "McLean / Harvard", status: "recruiting", n: 50, design: "RCT, brain NAD+/NADH via MRS", result: "Palmer lab; measuring brain energy metabolism directly", color: "var(--blue)" },
  { id: "JCU-2024", title: "James Cook University RCT", institution: "JCU Australia", status: "planned", n: 100, design: "RCT vs healthy eating, 14 weeks", result: "Comprehensive: PANSS, cognition, microbiome, wearables", color: "var(--purple)" },
];

const MECHANISMS = [
  { name: "Mitochondrial rescue", strength: 0.9, desc: "Ketones bypass impaired glucose metabolism. Brain uses ~20% of body energy at 2% mass - uniquely vulnerable to metabolic disruption.", overlap: "Mitochondrial respiration downregulated in SCZ amygdala gene expression" },
  { name: "NLRP3 inflammasome inhibition", strength: 0.85, desc: "BHB directly inhibits the NLRP3 inflammasome. Reduces microglial activation and pro-inflammatory cytokines.", overlap: "Immune/inflammatory pathways enriched in SCZ GSEA; C1QA/C1QB altered in brain PPI" },
  { name: "GABA:glutamate rebalancing", strength: 0.7, desc: "KD increases GABA synthesis and suppresses catabolism. Campbell pilot: 11.6% decrease in brain glutamate+glutamine (MRS).", overlap: "Glutamatergic synapse pathway downregulated in GSE27383" },
  { name: "Insulin resistance correction", strength: 0.9, desc: "Drug-naive first-episode SCZ patients show IR independent of medication. Stanford pilot: HOMA-IR -27%.", overlap: "Metabolic syndrome 2-3x more prevalent in SCZ; 26+ studies in drug-naive patients" },
  { name: "Epigenetic HDAC inhibition", strength: 0.6, desc: "BHB inhibits class I/IIa HDACs. Upregulates BDNF, SOD2, catalase, FOXO3a.", overlap: "BDNF is a family study candidate gene; SOD2 in oxidative stress defense" },
  { name: "Adenosine-dopamine modulation", strength: 0.5, desc: "KD increases adenosine which functionally antagonises dopamine via receptor heteromers - without direct D2 blockade.", overlap: "DRD2 is PGC3 risk gene; dopamine pathway central to SCZ" },
  { name: "Astrocyte modulation", strength: 0.6, desc: "Ketones modify astrocyte glutamate recycling, KATP channels, aquaporin-4, connexins.", overlap: "Layer 1 astrocytes altered in SCZ (PsychENCODE); glial dysfunction hypothesis" },
];

const CASE_REPORTS = [
  { authors: "Palmer 2017", desc: "2 schizoaffective patients improved on KD", pmid: "28162810" },
  { authors: "Palmer 2019", desc: "2 SCZ patients achieved psychotic symptom remission on KD", pmid: "30962118" },
  { authors: "Danan et al. 2022", desc: "31 inpatients - 10 schizoaffective: PANSS 91.4 to 49.3 (p<0.001)", pmid: "35873236" },
  { authors: "Murray et al. 2025", desc: "Treatment-resistant SCZ on clozapine+olanzapine: 69% HOMA-IR decrease, 80% EPS resolution", pmid: "41356674" },
  { authors: "Schlimme 2025", desc: "Ketosis protected against psychotic relapse during antipsychotic tapering", pmid: "40849111" },
  { authors: "Newiss 2025", desc: "SCZ remission with carnivore ketogenic diet + practitioner support", pmid: "40630169" },
];

const MTHFR_CONTENT = {
  title: "MTHFR and Folate: Low-Hanging Fruit",
  body: `The MTHFR C677T polymorphism is one of the most replicated genetic associations in schizophrenia: TT homozygotes have 36-48% higher SCZ risk (Yadav 2016 meta-analysis, 38 studies, 10,069 cases). Each 5 umol/L increase in homocysteine raises SCZ risk by 70% (Muntjewerff 2006, Mendelian randomisation confirmed by Nishi 2014). The folate pathway affects DNA methylation, neurotransmitter synthesis, and NMDA receptor function.`,
  why: [
    "MTHFR C677T TT: OR=1.40 (1.20-1.64) for SCZ (38 studies, 10,069 cases, PMID:27025471)",
    "5 umol/L higher homocysteine = 70% higher SCZ risk (PMID:16172608)",
    "L-methylfolate 15mg improved PANSS total (d=0.61, p=0.03) regardless of genotype (Roffman 2018, PMID:28289280)",
    "Folate pathway variants (MTHFR + MTR + FOLH1 + COMT) predict negative symptom severity (Roffman 2013)",
    "MRI changes confirmed: increased vmPFC deactivation, altered limbic connectivity, increased cortical thickness",
    "Meta-analysis of 10 RCTs (925 patients): folate/methylfolate significantly improves negative symptoms (Sakuma 2018)",
  ],
  action: `L-methylfolate 15mg/day should be considered for all schizophrenia patients with persistent negative symptoms. It bypasses MTHFR entirely, so formal genotyping ($325+) is optional - the bioactive form works regardless of genotype (Roffman 2018). L-methylfolate costs ~$30/month and has no meaningful side effects. Use L-methylfolate, NOT folic acid (which requires MTHFR to convert). ACMG does not recommend routine MTHFR testing, but the clinical trial evidence for L-methylfolate supplementation is strong independently of genotype.`,
  nuance: `Note: While MTHFR genotyping can identify high-risk individuals and guide dosing, the Roffman 2018 RCT showed L-methylfolate improved negative symptoms regardless of genotype when given at 15mg. The cost-effective approach is empirical supplementation with the bioactive form rather than test-then-treat. However, testing remains informative for understanding individual folate metabolism and homocysteine management.`,
};

type Tab = "trials" | "mechanisms" | "cases" | "mthfr";

export default function MetabolicPage() {
  const [tab, setTab] = useState<Tab>("trials");

  const tabs: { id: Tab; label: string }[] = [
    { id: "trials", label: "Clinical Trials" },
    { id: "mechanisms", label: "Mechanisms" },
    { id: "cases", label: "Case Reports" },
    { id: "mthfr", label: "MTHFR Testing" },
  ];

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 400, letterSpacing: "-0.02em", marginBottom: "0.375rem" }}>
          Metabolic Psychiatry
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9375rem", maxWidth: 720, lineHeight: 1.65 }}>
          Ketogenic diet, metabolic interventions, and the brain energy hypothesis. Schizophrenia
          shows intrinsic metabolic dysfunction even in drug-naive patients - these therapies target the root cause.
        </p>
      </div>

      {/* Key stat banner */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1px", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", background: "var(--border)", marginBottom: "1.5rem" }}>
        {[
          { label: "Active Trials", value: "10+", color: "var(--blue)" },
          { label: "Completed", value: "2", color: "var(--green)" },
          { label: "Total Enrolled", value: "~550", color: "var(--text)" },
          { label: "Mechanisms", value: "7", color: "var(--purple)" },
          { label: "Case Reports", value: "6+", color: "var(--amber)" },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--surface)", padding: "1rem 1.25rem", textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-data)", fontSize: "1.5rem", fontWeight: 500, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: "0.25rem" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "0.25rem", borderBottom: "1px solid var(--border)", marginBottom: "1.5rem" }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "0.5rem 1rem",
              background: "transparent",
              border: "none",
              borderBottom: tab === t.id ? "2px solid var(--blue)" : "2px solid transparent",
              color: tab === t.id ? "var(--text)" : "var(--text-muted)",
              fontSize: "0.8125rem",
              fontWeight: tab === t.id ? 500 : 400,
              cursor: "pointer",
              fontFamily: "var(--font-body)",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "trials" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {TRIALS.map(t => (
            <div key={t.id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.625rem" }}>
                <span style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: t.color,
                  flexShrink: 0,
                }} />
                <span style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 400, color: "var(--text)" }}>{t.title}</span>
                <span style={{
                  fontSize: "0.6875rem",
                  padding: "0.125rem 0.5rem",
                  borderRadius: 4,
                  border: `1px solid ${t.color}`,
                  color: t.color,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  fontFamily: "var(--font-data)",
                }}>
                  {t.status}
                </span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-data)", fontSize: "0.75rem", color: "var(--text-dim)" }}>
                  n={t.n}
                </span>
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "0.375rem" }}>
                {t.institution} - {t.design}
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text)", lineHeight: 1.6 }}>
                {t.result}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)", marginTop: "0.5rem" }}>
                {t.id}
              </div>
            </div>
          ))}
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontStyle: "italic", marginTop: "0.5rem" }}>
            Historical note: The earliest known KD pilot for schizophrenia was Pacheco et al. 1965 (Am J Psychiatry) - this is a 60-year rediscovery.
          </div>
        </div>
      )}

      {tab === "mechanisms" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "0.25rem", lineHeight: 1.65 }}>
            Palmer's "Brain Energy" thesis (2022): mental illnesses are metabolic disorders rooted in mitochondrial dysfunction.
            The brain consumes ~20% of body energy at 2% of mass - uniquely vulnerable to metabolic disruption.
            KD provides alternative fuel, enhances mitochondrial biogenesis, and acts as an endogenous HDAC inhibitor.
          </div>
          {MECHANISMS.map(m => (
            <div key={m.name} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                <span style={{ fontFamily: "var(--font-display)", fontSize: "0.9375rem", fontWeight: 400 }}>{m.name}</span>
                <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden", maxWidth: 120 }}>
                  <div style={{ height: "100%", width: `${m.strength * 100}%`, background: "var(--blue)", borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)" }}>
                  {m.strength >= 0.8 ? "Strong" : m.strength >= 0.6 ? "Moderate" : "Emerging"}
                </span>
              </div>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.6, margin: "0 0 0.5rem" }}>{m.desc}</p>
              <div style={{ fontSize: "0.75rem", color: "var(--blue-bright)", fontFamily: "var(--font-data)", padding: "0.375rem 0.625rem", background: "rgba(96,165,250,0.08)", borderRadius: 4 }}>
                Pipeline overlap: {m.overlap}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "cases" && (
        <div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1.5rem" }}>
            {CASE_REPORTS.map(c => (
              <div key={c.pmid} style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", padding: "0.75rem 1rem", border: "1px solid var(--border)", borderRadius: 6, background: "var(--surface)" }}>
                <span style={{ fontFamily: "var(--font-data)", fontSize: "0.75rem", color: "var(--text-dim)", width: 120, flexShrink: 0 }}>{c.authors}</span>
                <span style={{ fontSize: "0.8125rem", color: "var(--text)", flex: 1 }}>{c.desc}</span>
                <span style={{ fontFamily: "var(--font-data)", fontSize: "0.6875rem", color: "var(--text-dim)" }}>PMID:{c.pmid}</span>
              </div>
            ))}
          </div>
          <div style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)", marginBottom: "1rem" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.625rem" }}>
              Combination Therapy Evidence
            </div>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.65, margin: 0 }}>
              <strong style={{ color: "var(--text)" }}>KD + Olanzapine (Kraeuter 2019, PMID:31405622):</strong> In female mice, KD was as effective as olanzapine at normalising MK-801-induced PPI disruption.
              Combination produced similar effect to either alone - no antagonistic interaction. Supports safe co-administration.
              <br /><br />
              <strong style={{ color: "var(--text)" }}>KD protects against antipsychotic metabolic harm (Shamshoum 2022, PMID:35507699):</strong> Short-term KD protected against olanzapine-induced hyperglycaemia in mice,
              independent of whole-body insulin action. Notably, exogenous BHB or ketone esters did NOT replicate this, meaning the mechanism goes beyond circulating ketones.
              <br /><br />
              <strong style={{ color: "var(--text)" }}>BHB alone (Kraeuter 2020, PMID:31993694):</strong> Chronic beta-hydroxybutyrate alone (no full KD) normalised hyperlocomotion and PPI disruption,
              suggesting the ketone body itself has direct therapeutic action.
              <br /><br />
              <strong style={{ color: "var(--text)" }}>Stanford pilot - all on antipsychotics (Sethi 2024):</strong> All 23 participants continued their medications.
              KD reversed metabolic syndrome in 100% while maintaining psychiatric improvement. 48% of antipsychotic-treated patients lost 5%+ body weight.
              <br /><br />
              <strong style={{ color: "var(--text)" }}>Delphi Consensus 2026 (PMID:41816235):</strong> 33/33 expert consensus statements on implementing KMT for serious mental illness,
              explicitly endorsing KD as adjunct to standard pharmacotherapy.
            </p>
          </div>
          <div style={{ border: "1px solid var(--purple)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--purple)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.625rem" }}>
              Optimal combination protocol (emerging consensus)
            </div>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.65, margin: 0 }}>
              <strong style={{ color: "var(--text)" }}>Tier 1 (strong evidence):</strong> Continue antipsychotics + add ketogenic diet (reverses metabolic side effects while maintaining/improving psychiatric outcomes)
              <br />
              <strong style={{ color: "var(--text)" }}>Tier 2 (moderate evidence):</strong> Add L-methylfolate 15mg/day for persistent negative symptoms (Roffman 2018, d=0.61)
              <br />
              <strong style={{ color: "var(--text)" }}>Tier 3 (preclinical/emerging):</strong> Consider COBENFY (muscarinic agonist, FDA approved Sep 2024) which has cognitive benefits and less metabolic burden than D2-blockers
              <br />
              <strong style={{ color: "var(--text)" }}>Research gap:</strong> No published trials combining KD with CBTp, exercise, or specific supplements. These represent opportunities.
            </p>
          </div>
        </div>
      )}

      {tab === "mthfr" && (
        <div>
          <div style={{ border: "1px solid var(--amber)", borderRadius: 8, padding: "1.5rem", background: "var(--surface)", marginBottom: "1.25rem" }}>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.125rem", fontWeight: 400, marginTop: 0, marginBottom: "0.75rem", color: "var(--amber)" }}>
              {MTHFR_CONTENT.title}
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.7, margin: "0 0 1rem" }}>
              {MTHFR_CONTENT.body}
            </p>
            <ul style={{ margin: 0, padding: "0 0 0 1.25rem", display: "flex", flexDirection: "column", gap: "0.375rem" }}>
              {MTHFR_CONTENT.why.map((item, i) => (
                <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text)", lineHeight: 1.5 }}>{item}</li>
              ))}
            </ul>
          </div>
          <div style={{ border: "1px solid var(--green)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)", marginBottom: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--green)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem", fontFamily: "var(--font-body)", fontWeight: 500 }}>
              Clinical Recommendation
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text)", lineHeight: 1.7, margin: 0 }}>
              {MTHFR_CONTENT.action}
            </p>
          </div>
          <div style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem", background: "var(--surface)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem", fontFamily: "var(--font-body)", fontWeight: 500 }}>
              Testing vs Empirical Supplementation
            </div>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.7, margin: 0 }}>
              {MTHFR_CONTENT.nuance}
            </p>
          </div>
        </div>
      )}

      {/* Link to RAG query */}
      <div style={{ marginTop: "2rem", padding: "1rem 1.25rem", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text)", marginBottom: "0.25rem" }}>
            Ask questions about metabolic psychiatry, KD trials, or MTHFR
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
            RAG-powered search across all pipeline results and research data
          </div>
        </div>
        <Link href="/query" style={{ padding: "0.375rem 0.875rem", background: "transparent", border: "1px solid var(--border-strong)", borderRadius: 5, fontSize: "0.8125rem", color: "var(--text-muted)", textDecoration: "none" }}>
          Open Query
        </Link>
      </div>
    </div>
  );
}
