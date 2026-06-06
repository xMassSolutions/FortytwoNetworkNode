import type { DashboardData, OverviewData, WatchedWallet } from './types'
import { mockDashboard, mockOverview, mockWallets } from './mock'

// Preview mode: ?mock=1 (persisted for the session) or VITE_MOCK=1 at build.
// Lets the UI render fully populated without a running backend.
function detectMock(): boolean {
  try {
    if (import.meta.env.VITE_MOCK === '1') return true
    const u = new URLSearchParams(location.search)
    if (u.has('mock')) {
      sessionStorage.setItem('ft.mock', u.get('mock') === '0' ? '0' : '1')
    }
    return sessionStorage.getItem('ft.mock') === '1'
  } catch {
    return false
  }
}
export const IS_MOCK = detectMock()

export class AuthError extends Error {}

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: 'no-store' })
  if (r.status === 401) throw new AuthError('not logged in')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return (await r.json()) as T
}

const delay = (ms: number) => new Promise((res) => setTimeout(res, ms))

export async function getDashboardData(node: number): Promise<DashboardData> {
  if (IS_MOCK) {
    await delay(120)
    return mockDashboard(node)
  }
  return getJSON<DashboardData>(`/v1/dashboard-data?node=${node}`)
}

export async function getOverview(): Promise<OverviewData> {
  if (IS_MOCK) {
    await delay(120)
    return mockOverview()
  }
  return getJSON<OverviewData>('/v1/dashboard-overview')
}

export async function getWallets(): Promise<WatchedWallet[]> {
  if (IS_MOCK) {
    await delay(120)
    return mockWallets()
  }
  const data = await getJSON<{ wallets: WatchedWallet[] }>('/v1/wallets')
  return data.wallets || []
}

export async function addWallet(address: string, label: string | null): Promise<string> {
  if (IS_MOCK) {
    await delay(120)
    return address
  }
  const r = await fetch('/v1/wallets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address, label }),
  })
  const j = await r.json()
  if (!r.ok) throw new Error(j.detail || 'failed')
  return j.address as string
}

// Where to send the user when a session expires. The legacy login page lives
// at the server root (/login), outside the SPA's /app basename.
export function goToLogin() {
  if (IS_MOCK) return
  location.href = '/login'
}
