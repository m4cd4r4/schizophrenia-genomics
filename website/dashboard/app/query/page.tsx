"use client";
import { useState, useRef } from "react";
import { runQuery } from "@/lib/api";
import type { QueryResult } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { tierBadge, fmtPval } from "@/lib/format";

const EXAMPLES = [
  "How many DE genes are in GSE38484?",
  "Tell me about NRGN",
  "What immune cell types are reduced in schizophrenia?",
  "Which drugs replicate across blood and brain datasets?",
  "What NMDA-related pathways are enriched?",
  "List all high-evidence genes",
];

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [dataset, setDataset] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSQL, setShowSQL] = useState(false);
  const [showChunks, setShowChunks] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function submit() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runQuery(query, dataset || undefined);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", fontWeight: 400, letterSpacing: "-0.01em", marginBottom: "0.375rem" }}>
          Natural Language Query
        </h1>
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
          Hybrid retrieval: SQL for structured queries, vector search for biological mechanisms.
        </p>
      </div>

      {/* Input area */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, marginBottom: "1rem" }}>
        <textarea
          ref={textareaRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }}
          placeholder="Ask about genes, pathways, drugs, cell types..."
          rows={3}
          style={{
            width: "100%",
            background: "transparent",
            border: "none",
            padding: "0.875rem 1rem",
            color: "var(--text)",
            fontSize: "0.9375rem",
            resize: "none",
            outline: "none",
            fontFamily: "var(--font-body)",
            boxSizing: "border-box",
            lineHeight: 1.6,
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.625rem 1rem", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <select
              value={dataset}
              onChange={e => setDataset(e.target.value)}
              style={{
                background: "var(--surface-raised)",
                border: "1px solid var(--border)",
                color: "var(--text-muted)",
                fontSize: "0.8125rem",
                padding: "0.25rem 0.5rem",
                borderRadius: 4,
                fontFamily: "var(--font-body)",
                cursor: "pointer",
              }}
            >
              <option value="">All datasets</option>
              <option value="GSE38484">GSE38484 — Whole Blood</option>
              <option value="GSE27383">GSE27383 — PBMC</option>
              <option value="GSE21138">GSE21138 — Brain PFC</option>
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)" }}>
              Ctrl+Enter
            </span>
            <button
              onClick={submit}
              disabled={loading || !query.trim()}
              style={{
                padding: "0.375rem 1.125rem",
                background: loading || !query.trim() ? "var(--border)" : "var(--blue)",
                border: "none",
                borderRadius: 5,
                color: loading || !query.trim() ? "var(--text-dim)" : "white",
                fontSize: "0.8125rem",
                cursor: loading || !query.trim() ? "not-allowed" : "pointer",
                fontWeight: 500,
                fontFamily: "var(--font-body)",
                transition: "background 0.12s",
              }}
            >
              {loading ? "Searching..." : "Query"}
            </button>
          </div>
        </div>
      </div>

      {/* Example queries */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem", marginBottom: "1.5rem" }}>
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            onClick={() => { setQuery(ex); textareaRef.current?.focus(); }}
            style={{
              padding: "0.25rem 0.625rem",
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 4,
              color: "var(--text-dim)",
              fontSize: "0.75rem",
              cursor: "pointer",
              fontFamily: "var(--font-body)",
              transition: "color 0.1s, border-color 0.1s",
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ color: "var(--red-bright)", background: "var(--surface)", border: "1px solid var(--red)", borderRadius: 6, padding: "0.875rem 1rem", marginBottom: "1rem", fontSize: "0.875rem", fontFamily: "var(--font-body)" }}>
          {error}
        </div>
      )}

      {result && (
        <div>
          {/* Query metadata */}
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.875rem", fontSize: "0.75rem", color: "var(--text-dim)", fontFamily: "var(--font-body)" }}>
            <span style={{ color: "var(--blue-bright)", fontWeight: 500, fontFamily: "var(--font-data)" }}>{result.classification.type}</span>
            {result.classification.gene && (
              <span style={{ fontFamily: "var(--font-data)", color: "var(--blue-bright)" }} className="gene-name">{result.classification.gene}</span>
            )}
            {result.classification.dataset_id && (
              <span style={{ fontFamily: "var(--font-data)", color: "var(--text-muted)" }}>{result.classification.dataset_id}</span>
            )}
            {result.evidence_tiers.map(t => <span key={t} className={tierBadge(t)}>{t}</span>)}
          </div>

          {/* Answer */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "1.25rem", marginBottom: "1rem" }}>
            <div className="summary-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
            </div>
          </div>

          {/* SQL (collapsible) */}
          {result.sql && (
            <div style={{ marginBottom: "0.875rem" }}>
              <button onClick={() => setShowSQL(!showSQL)} style={{ background: "none", border: "none", color: "var(--text-dim)", fontSize: "0.75rem", cursor: "pointer", padding: "0.25rem 0", display: "flex", alignItems: "center", gap: "0.375rem", fontFamily: "var(--font-body)" }}>
                <span style={{ fontSize: "0.6875rem" }}>{showSQL ? "▾" : "▸"}</span>
                {showSQL ? "Hide" : "Show"} SQL ({result.sql_method})
              </button>
              {showSQL && (
                <div style={{ marginTop: "0.5rem" }}>
                  <pre style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.875rem", fontSize: "0.8rem", overflowX: "auto", color: "var(--text)", fontFamily: "var(--font-data)", lineHeight: 1.5 }}>
                    {result.sql}
                  </pre>
                  {result.sql_results && (
                    <div style={{ overflowX: "auto", marginTop: "0.5rem", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6 }}>
                      <table className="data-table">
                        <thead>
                          <tr>{result.sql_results[0] && Object.keys(result.sql_results[0]).map(k => <th key={k}>{k}</th>)}</tr>
                        </thead>
                        <tbody>
                          {result.sql_results.slice(0, 20).map((row, i) => (
                            <tr key={i}>
                              {Object.values(row).map((v, j) => (
                                <td key={j}>{typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(v ?? "—")}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {result.sql_results.length > 20 && <div style={{ padding: "0.4rem 0.75rem", fontSize: "0.7rem", color: "var(--text-dim)", fontFamily: "var(--font-body)" }}>... and {result.sql_results.length - 20} more rows</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Evidence chunks (collapsible) */}
          {result.chunks.length > 0 && (
            <div>
              <button onClick={() => setShowChunks(!showChunks)} style={{ background: "none", border: "none", color: "var(--text-dim)", fontSize: "0.75rem", cursor: "pointer", padding: "0.25rem 0", display: "flex", alignItems: "center", gap: "0.375rem", fontFamily: "var(--font-body)" }}>
                <span style={{ fontSize: "0.6875rem" }}>{showChunks ? "▾" : "▸"}</span>
                {showChunks ? "Hide" : "Show"} {result.chunks.length} evidence chunks
              </button>
              {showChunks && (
                <div style={{ marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {result.chunks.map((c, i) => (
                    <div key={i} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem 1rem" }}>
                      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.375rem" }}>
                        <span className={tierBadge(c.metadata.evidence_tier ?? "SINGLE_DATASET")}>{c.metadata.evidence_tier ?? "SINGLE_DATASET"}</span>
                        <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)" }}>{c.metadata.source}</span>
                        <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-data)", marginLeft: "auto" }}>score {c.score.toFixed(3)}</span>
                      </div>
                      <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.6, fontFamily: "var(--font-body)" }}>{c.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
