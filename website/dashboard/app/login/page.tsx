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
    <div style={{
      minHeight: "100vh",
      background: "var(--background)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}>
      <div style={{
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "2rem",
        width: "100%",
        maxWidth: 360,
      }}>
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.25rem", color: "var(--foreground)" }}>
          SCZ Genomics Dashboard
        </h1>
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          Research access only. Enter the site password to continue.
        </p>

        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Password"
            autoFocus
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              background: "var(--background)",
              border: `1px solid ${error ? "var(--red)" : "var(--border)"}`,
              borderRadius: 4,
              color: "var(--foreground)",
              fontSize: "0.875rem",
              outline: "none",
              fontFamily: "inherit",
              boxSizing: "border-box",
            }}
          />

          {error && (
            <p style={{ fontSize: "0.72rem", color: "var(--red-bright)", margin: "0.4rem 0 0" }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            style={{
              marginTop: "1rem",
              width: "100%",
              padding: "0.5rem",
              background: loading || !password ? "var(--border)" : "var(--blue)",
              border: "none",
              borderRadius: 4,
              color: "var(--foreground)",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: loading || !password ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Verifying..." : "Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}
