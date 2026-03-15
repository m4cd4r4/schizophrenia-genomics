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
      <div style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>Natural Language Query</h1>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
          Ask questions about the genomics data. Hybrid retrieval: SQL for structured queries, vector search for biological explanations.
        </p>
      </div>

      {/* Input */}
      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, marginBottom: "1rem" }}>
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
            padding: "0.75rem",
            color: "var(--foreground)",
            fontSize: "0.875rem",
            resize: "none",
            outline: "none",
            fontFamily: "inherit",
            boxSizing: "border-box",
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.75rem", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <label style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Dataset filter:</label>
            <select
              value={dataset}
              onChange={e => setDataset(e.target.value)}
              style={{ background: "var(--card-highlight)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "0.75rem", padding: "0.2rem 0.4rem", borderRadius: 3 }}
            >
              <option value="">All datasets</option>
              <option value="GSE38484">GSE38484 (Whole Blood)</option>
              <option value="GSE27383">GSE27383 (PBMC)</option>
              <option value="GSE21138">GSE21138 (Brain PFC)</option>
            </select>
          </div>
          <button
            onClick={submit}
            disabled={loading || !query.trim()}
            style={{
              padding: "0.35rem 1rem",
              background: loading ? "var(--border)" : "var(--blue)",
              border: "none",
              borderRadius: 4,
              color: "white",
              fontSize: "0.78rem",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {loading ? "Searching..." : "Query (Ctrl+Enter)"}
          </button>
        </div>
      </div>

      {/* Examples */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "1.25rem" }}>
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            onClick={() => { setQuery(ex); textareaRef.current?.focus(); }}
            style={{ padding: "0.25rem 0.6rem", background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer" }}
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <div style={{ color: "var(--red)", background: "var(--card)", border: "1px solid var(--red)", borderRadius: 4, padding: "0.75rem", marginBottom: "1rem", fontSize: "0.82rem" }}>{error}</div>}

      {result && (
        <div>
          {/* Classification */}
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.75rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>
            <span>Query type:</span>
            <span style={{ color: "var(--blue-bright)", fontWeight: 600 }}>{result.classification.type}</span>
            {result.classification.gene && <span>Gene: <span style={{ fontFamily: "monospace", color: "var(--blue)" }}>{result.classification.gene}</span></span>}
            {result.classification.dataset_id && <span>Dataset: <span style={{ fontFamily: "monospace" }}>{result.classification.dataset_id}</span></span>}
            {result.evidence_tiers.map(t => <span key={t} className={tierBadge(t)}>{t}</span>)}
          </div>

          {/* Answer */}
          <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, padding: "1rem", marginBottom: "1rem" }}>
            <div className="summary-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
            </div>
          </div>

          {/* SQL collapsible */}
          {result.sql && (
            <div style={{ marginBottom: "0.75rem" }}>
              <button onClick={() => setShowSQL(!showSQL)} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer", padding: "0.25rem 0", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                {showSQL ? "Hide" : "Show"} SQL ({result.sql_method})
              </button>
              {showSQL && (
                <div style={{ marginTop: "0.4rem" }}>
                  <pre style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.75rem", fontSize: "0.75rem", overflowX: "auto", color: "var(--foreground)", fontFamily: "monospace" }}>
                    {result.sql}
                  </pre>
                  {result.sql_results && (
                    <div style={{ overflowX: "auto", marginTop: "0.4rem", background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4 }}>
                      <table className="data-table">
                        <thead>
                          <tr>{result.sql_results[0] && Object.keys(result.sql_results[0]).map(k => <th key={k}>{k}</th>)}</tr>
                        </thead>
                        <tbody>
                          {result.sql_results.slice(0, 20).map((row, i) => (
                            <tr key={i}>
                              {Object.values(row).map((v, j) => (
                                <td key={j} style={{ fontFamily: "monospace" }}>
                                  {typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(v ?? "N/A")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {result.sql_results.length > 20 && <div style={{ padding: "0.4rem 0.75rem", fontSize: "0.7rem", color: "var(--text-dim)" }}>... and {result.sql_results.length - 20} more rows</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Evidence chunks collapsible */}
          {result.chunks.length > 0 && (
            <div>
              <button onClick={() => setShowChunks(!showChunks)} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "0.72rem", cursor: "pointer", padding: "0.25rem 0", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                {showChunks ? "Hide" : "Show"} {result.chunks.length} evidence chunks
              </button>
              {showChunks && (
                <div style={{ marginTop: "0.4rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                  {result.chunks.map((c, i) => (
                    <div key={i} style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.6rem 0.75rem" }}>
                      <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.3rem" }}>
                        <span className={tierBadge(c.metadata.evidence_tier ?? "SINGLE_DATASET")}>{c.metadata.evidence_tier ?? "SINGLE_DATASET"}</span>
                        <span style={{ fontSize: "0.65rem", color: "var(--text-dim)", fontFamily: "monospace" }}>{c.metadata.source}</span>
                        <span style={{ fontSize: "0.65rem", color: "var(--text-dim)" }}>score={c.score.toFixed(3)}</span>
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>{c.text}</p>
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
