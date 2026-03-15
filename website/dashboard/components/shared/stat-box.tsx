interface StatBoxProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}

export default function StatBox({ label, value, sub, color = "var(--blue)" }: StatBoxProps) {
  return (
    <div style={{
      background: "var(--card)",
      border: "1px solid var(--border)",
      borderRadius: 6,
      padding: "1rem 1.25rem",
      minWidth: 140,
    }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color, fontFamily: "monospace", lineHeight: 1 }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.4rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: "0.65rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>{sub}</div>}
    </div>
  );
}
