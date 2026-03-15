interface StatBoxProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}

// Renders as a single stat cell — container in page.tsx manages the grid/borders.
// No card background; the parent panel provides it. Avoids the "hero metric" anti-pattern
// of 8 identical floating cards with identical padding and equal visual weight.
export default function StatBox({ label, value, sub, color = "var(--blue)" }: StatBoxProps) {
  return (
    <div style={{ padding: "0.875rem 1.25rem" }}>
      <div style={{
        fontSize: "1.625rem",
        fontWeight: 600,
        color,
        fontFamily: "var(--font-data)",
        lineHeight: 1,
        letterSpacing: "-0.025em",
        fontVariantNumeric: "tabular-nums",
      }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div style={{
        fontSize: "0.6875rem",
        color: "var(--text-dim)",
        marginTop: "0.3rem",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontFamily: "var(--font-body)",
        fontWeight: 500,
      }}>
        {label}
      </div>
      {sub && (
        <div style={{
          fontSize: "0.625rem",
          color: "var(--text-dim)",
          marginTop: "0.15rem",
          fontFamily: "var(--font-body)",
          opacity: 0.8,
        }}>
          {sub}
        </div>
      )}
    </div>
  );
}
