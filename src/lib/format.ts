export function fmtMw(n: number | null | undefined, digits = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function fmtK(n: number, digits = 1) {
  const abs = Math.abs(n);
  if (abs >= 1000) return `${(n / 1000).toFixed(digits)}k`;
  return fmtMw(n, 0);
}

export function hourLabel(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    weekday: "short",
    hour: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function clockLabel(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function dayKey(iso: string) {
  return iso.slice(0, 10);
}
