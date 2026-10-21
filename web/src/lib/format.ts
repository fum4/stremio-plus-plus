const UNITS = ["B", "KB", "MB", "GB", "TB"];

export function bytes(n: number, digits = 1): string {
  let i = 0;
  while (Math.abs(n) >= 1024 && i < UNITS.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(i === 0 ? 0 : digits)} ${UNITS[i]}`;
}

export const speed = (bps: number) => `${bytes(bps)}/s`;

export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const pad = (v: number) => String(v).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(s % 60)}` : `${m}:${pad(s % 60)}`;
}

export function ago(epochSeconds: number): string {
  const s = Math.max(0, Date.now() / 1000 - epochSeconds);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

/** "Show.Name.S01E03.1080p.WEB.mkv" → "Show Name S01E03" (best effort, display only). */
export function prettyName(file: string): string {
  const base = file.split("/").pop() ?? file;
  const stem = base.replace(/\.[a-z0-9]{2,4}$/i, "").replace(/[._]+/g, " ");
  const cut = stem.search(/\b(19|20)\d{2}\b|\b(480|720|1080|2160)p\b|\bWEB|\bBluRay|\bHDTV/i);
  return (cut > 0 ? stem.slice(0, cut) : stem).trim();
}
