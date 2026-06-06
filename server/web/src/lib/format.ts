export const pad = (n: number) => String(n).padStart(2, '0')

export function fmtNum(n: number | null | undefined, max = 2): string {
  if (n == null || Number.isNaN(n)) return '—'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: max })
}

export function fmtFixed(n: number | null | undefined, d = 4): string {
  if (n == null || Number.isNaN(n)) return '—'
  return Number(n).toFixed(d)
}

export function fmtAgo(epoch: number | null | undefined): string {
  if (!epoch) return 'never'
  const d = Date.now() / 1000 - epoch
  if (d < 60) return `${Math.round(d)}s ago`
  if (d < 3600) return `${Math.round(d / 60)}m ago`
  if (d < 86400) return `${Math.round(d / 3600)}h ago`
  return `${Math.round(d / 86400)}d ago`
}

export function fmtUptime(s: number | null | undefined): string {
  if (!s) return '—'
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function fmtPct(v: number | null | undefined): string {
  return v == null ? '—' : `${Number(v).toFixed(1)}%`
}

export function shortHash(h: string | null | undefined, head = 8, tail = 6): string {
  if (!h) return '—'
  if (h.length <= head + tail + 1) return h
  return `${h.slice(0, head)}…${h.slice(-tail)}`
}

export function uptimeColor(p: number | null | undefined): string {
  if (p == null) return 'var(--muted)'
  if (p >= 99) return 'var(--green)'
  if (p >= 90) return 'var(--text)'
  return 'var(--red)'
}

// A round that finished within the last ~10 min whose reward hasn't landed
// on-chain yet is "pending" rather than unrewarded.
export function roundPending(hms: string | null | undefined): boolean {
  const m = /^(\d{2}):(\d{2}):(\d{2})$/.exec(hms || '')
  if (!m) return false
  const roundSec = +m[1] * 3600 + +m[2] * 60 + +m[3]
  const d = new Date()
  const nowSec = d.getUTCHours() * 3600 + d.getUTCMinutes() * 60 + d.getUTCSeconds()
  let age = nowSec - roundSec
  if (age < 0) age += 86400
  return age < 600
}
