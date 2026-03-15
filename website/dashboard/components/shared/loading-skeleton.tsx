export default function LoadingSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div style={{ padding: "1rem" }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 20,
            background: "var(--card-highlight)",
            borderRadius: 3,
            marginBottom: 8,
            opacity: 1 - i * 0.1,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
      <style>{`@keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:.8} }`}</style>
    </div>
  );
}
