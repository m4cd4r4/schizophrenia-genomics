export function fmtPval(p: number | null | undefined): string {
  if (p == null || isNaN(p)) return "N/A";
  if (p < 0.001) return p.toExponential(2);
  return p.toFixed(4);
}

export function fmtLogFC(fc: number | null | undefined): string {
  if (fc == null || isNaN(fc)) return "N/A";
  return (fc >= 0 ? "+" : "") + fc.toFixed(3);
}

export function fmtNES(nes: number | null | undefined): string {
  if (nes == null || isNaN(nes)) return "N/A";
  return (nes >= 0 ? "+" : "") + nes.toFixed(3);
}

export function fmtNum(n: number | null | undefined, decimals = 3): string {
  if (n == null || isNaN(n)) return "N/A";
  return n.toFixed(decimals);
}

export function logFCColor(fc: number | null | undefined): string {
  if (fc == null) return "var(--text-muted)";
  if (fc > 0.2) return "var(--red-bright)";
  if (fc < -0.2) return "var(--blue-bright)";
  return "var(--text-muted)";
}

export function pvalColor(p: number | null | undefined): string {
  if (p == null) return "var(--text-muted)";
  if (p < 0.001) return "var(--green-bright)";
  if (p < 0.05) return "var(--amber-bright)";
  return "var(--text-muted)";
}

export function nesColor(nes: number | null | undefined): string {
  if (nes == null) return "var(--text-muted)";
  if (Math.abs(nes) > 2) return Math.sign(nes) > 0 ? "var(--red-bright)" : "var(--blue-bright)";
  if (Math.abs(nes) > 1) return "var(--amber-bright)";
  return "var(--text-muted)";
}

export function datasetLabel(id: string): string {
  const map: Record<string, string> = {
    GSE38484: "Whole Blood",
    GSE27383: "PBMC",
    GSE21138: "Brain (PFC)",
  };
  return map[id] ?? id;
}

export function datasetColor(id: string): string {
  const map: Record<string, string> = {
    GSE38484: "var(--blue-bright)",
    GSE27383: "var(--green-bright)",
    GSE21138: "var(--purple-bright)",
  };
  return map[id] ?? "var(--text-muted)";
}

export function tierBadge(tier: string): string {
  if (tier === "REPLICATED") return "tier-replicated";
  if (tier === "UNDERPOWERED") return "tier-underpowered";
  return "tier-single";
}
