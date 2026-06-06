import { pad } from './format'

export type ChartMode = 'hourly' | 'daily' | 'weekly'

export interface Bucket {
  label: string
  rounds: number
  for: number
}

function hourKeyFromDate(d: Date) {
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}`
}

/**
 * Bucket per-hour rounds + FOR into the series the chart shows. Ported from the
 * original dashboard's bucket(): 24 hourly / 7 daily / 4 weekly buckets,
 * anchored to "now" in UTC.
 */
export function bucketSeries(
  history: Record<string, number> | undefined,
  forByHour: Record<string, number> | undefined,
  mode: ChartMode,
): Bucket[] {
  history = history || {}
  forByHour = forByHour || {}
  const now = new Date()
  const out: Bucket[] = []

  if (mode === 'hourly') {
    const anchor = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), now.getUTCHours())
    for (let i = 23; i >= 0; i--) {
      const t = new Date(anchor - i * 3600e3)
      const key = hourKeyFromDate(t)
      out.push({ label: `${pad(t.getUTCHours())}:00`, rounds: history[key] || 0, for: forByHour[key] || 0 })
    }
    return out
  }

  if (mode === 'daily') {
    const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today - i * 86400e3)
      const prefix = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`
      let rounds = 0
      let forSum = 0
      for (let h = 0; h < 24; h++) {
        const k = `${prefix}T${pad(h)}`
        rounds += history[k] || 0
        forSum += forByHour[k] || 0
      }
      out.push({ label: `${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`, rounds, for: forSum })
    }
    return out
  }

  // weekly: 4 ISO-ish weeks
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  const dow = (new Date(today).getUTCDay() + 6) % 7
  const weekStart = today - dow * 86400e3
  for (let w = 3; w >= 0; w--) {
    const start = weekStart - w * 7 * 86400e3
    let rounds = 0
    let forSum = 0
    for (let day = 0; day < 7; day++) {
      const d = new Date(start + day * 86400e3)
      const prefix = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`
      for (let h = 0; h < 24; h++) {
        const k = `${prefix}T${pad(h)}`
        rounds += history[k] || 0
        forSum += forByHour[k] || 0
      }
    }
    const sd = new Date(start)
    out.push({ label: `wk ${pad(sd.getUTCMonth() + 1)}-${pad(sd.getUTCDate())}`, rounds, for: forSum })
  }
  return out
}
