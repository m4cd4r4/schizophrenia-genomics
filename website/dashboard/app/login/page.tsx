"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (res.ok) {
      router.push("/");
      router.refresh();
    } else {
      setError("Incorrect password.");
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 380, padding: "0 1.25rem" }}>
        {/* Branding */}
        <div style={{ marginBottom: "2.5rem", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", fontWeight: 400, letterSpacing: "-0.015em", color: "var(--text)", marginBottom: "0.375rem" }}>
            SCZ<span style={{ color: "var(--blue)", fontStyle: "italic" }}>Genomics</span>
          </div>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-dim)", fontFamily: "var(--font-body)" }}>
            Research access — enter site password to continue
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "0.75rem" }}>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              autoFocus
              style={{
                width: "100%",
                padding: "0.625rem 0.875rem",
                background: "var(--surface)",
                border: `1px solid ${error ? "var(--red)" : "var(--border-strong)"}`,
                borderRadius: 6,
                color: "var(--text)",
                fontSize: "0.9375rem",
                outline: "none",
                fontFamily: "var(--font-body)",
                boxSizing: "border-box",
                transition: "border-color 0.12s",
              }}
            />
            {error && (
              <p style={{ fontSize: "0.8rem", color: "var(--red-bright)", margin: "0.375rem 0 0", fontFamily: "var(--font-body)" }}>
                {error}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !password}
            style={{
              width: "100%",
              padding: "0.625rem",
              background: loading || !password ? "var(--border)" : "var(--blue)",
              border: "none",
              borderRadius: 6,
              color: loading || !password ? "var(--text-dim)" : "white",
              fontSize: "0.9rem",
              fontWeight: 500,
              cursor: loading || !password ? "not-allowed" : "pointer",
              fontFamily: "var(--font-body)",
              transition: "background 0.12s",
            }}
          >
            {loading ? "Verifying..." : "Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}
