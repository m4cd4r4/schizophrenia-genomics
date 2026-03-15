// Skeleton with varied widths to hint at content shape — not identical gray bars
export default function LoadingSkeleton({ rows = 5 }: { rows?: number }) {
  const widths = [92, 78, 85, 65, 88, 72, 95, 70, 83, 60, 90, 75];

  return (
    <div style={{ padding: "0.5rem 0" }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 14,
            background: "var(--surface-raised)",
            borderRadius: 3,
            marginBottom: 10,
            width: `${widths[i % widths.length]}%`,
            animation: "scz-pulse 1.8s ease-in-out infinite",
            animationDelay: `${i * 80}ms`,
          }}
        />
      ))}
      <style>{`
        @keyframes scz-pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}
