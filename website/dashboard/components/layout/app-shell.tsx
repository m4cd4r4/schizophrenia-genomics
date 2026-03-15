"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/datasets", label: "Datasets" },
  { href: "/genes", label: "Genes" },
  { href: "/modules", label: "Modules" },
  { href: "/pathways", label: "Pathways" },
  { href: "/drugs", label: "Drugs" },
  { href: "/query", label: "Query" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--background)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}>
        <div style={{ maxWidth: 1400, margin: "0 auto", padding: "0 1.5rem", display: "flex", alignItems: "center", height: 48 }}>
          <Link href="/" style={{ textDecoration: "none", marginRight: "2rem" }}>
            <span style={{ fontFamily: "Georgia, serif", fontSize: "0.95rem", color: "var(--foreground)", fontWeight: 700, letterSpacing: "0.02em" }}>
              SCZ<span style={{ color: "var(--blue)" }}>Genomics</span>
            </span>
          </Link>
          <nav style={{ display: "flex", gap: "0.1rem", flex: 1 }}>
            {NAV.map(({ href, label }) => {
              const active = href === "/" ? path === "/" : path.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  style={{
                    padding: "0.25rem 0.6rem",
                    fontSize: "0.75rem",
                    borderRadius: 3,
                    textDecoration: "none",
                    color: active ? "var(--foreground)" : "var(--text-muted)",
                    background: active ? "var(--card-highlight)" : "transparent",
                    fontWeight: active ? 600 : 400,
                    letterSpacing: "0.03em",
                  }}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <span style={{ fontSize: "0.65rem", color: "var(--text-dim)", fontFamily: "monospace" }}>
            3 datasets · 333K rows · RAG
          </span>
        </div>
      </header>
      <main style={{ flex: 1, maxWidth: 1400, margin: "0 auto", padding: "1.5rem", width: "100%" }}>
        {children}
      </main>
      <footer style={{ borderTop: "1px solid var(--border)", padding: "0.75rem 1.5rem", textAlign: "center" }}>
        <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
          Schizophrenia Genomics Pipeline · GSE38484 · GSE27383 · GSE21138 · 10-stage analysis
        </span>
      </footer>
    </div>
  );
}
