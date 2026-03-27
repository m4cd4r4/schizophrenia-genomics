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
  { href: "/metabolic", label: "Metabolic" },
  { href: "/query", label: "Query" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--bg)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}>
        <div style={{
          maxWidth: 1400,
          margin: "0 auto",
          padding: "0 1.75rem",
          display: "flex",
          alignItems: "stretch",
          height: 52,
        }}>
          {/* Logo */}
          <Link href="/" style={{
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            marginRight: "2.5rem",
            flexShrink: 0,
          }}>
            <span style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.05rem",
              color: "var(--text)",
              fontWeight: 400,
              letterSpacing: "-0.01em",
            }}>
              SCZ<span style={{ color: "var(--blue)", fontStyle: "italic" }}>Genomics</span>
            </span>
          </Link>

          {/* Nav links */}
          <nav style={{ display: "flex", alignItems: "stretch", flex: 1 }}>
            {NAV.map(({ href, label }) => {
              const active = href === "/" ? path === "/" : path.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "0 0.75rem",
                    fontSize: "0.8125rem",
                    textDecoration: "none",
                    color: active ? "var(--text)" : "var(--text-muted)",
                    fontWeight: active ? 500 : 400,
                    borderBottom: active
                      ? "2px solid var(--blue)"
                      : "2px solid transparent",
                    transition: "color 0.12s, border-color 0.12s",
                    whiteSpace: "nowrap",
                  }}
                >
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Meta info */}
          <div style={{
            display: "flex",
            alignItems: "center",
            fontSize: "0.6875rem",
            color: "var(--text-dim)",
            fontFamily: "var(--font-data)",
            letterSpacing: "0.02em",
            flexShrink: 0,
          }}>
            3 datasets · 333K rows
          </div>
        </div>
      </header>

      <main style={{
        flex: 1,
        maxWidth: 1400,
        margin: "0 auto",
        padding: "2rem 1.75rem",
        width: "100%",
      }}>
        {children}
      </main>

      <footer style={{
        borderTop: "1px solid var(--border)",
        padding: "0.875rem 1.75rem",
        textAlign: "center",
      }}>
        <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontFamily: "var(--font-body)" }}>
          Schizophrenia Transcriptomics Pipeline · GSE38484 · GSE27383 · GSE21138 · 10-stage analysis
        </span>
      </footer>
    </div>
  );
}
