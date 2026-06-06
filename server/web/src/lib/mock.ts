import type { DashboardData, OverviewData, Round, WatchedWallet } from './types'
import { pad } from './format'

// Deterministic-ish pseudo-random so re-renders look stable within a session.
function rng(seed: number) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

function hourKey(d: Date) {
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}`
}

function buildHistory(seed: number) {
  const rand = rng(seed)
  const history: Record<string, number> = {}
  const forByHour: Record<string, number> = {}
  const now = new Date()
  const anchor = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), now.getUTCHours())
  for (let i = 27 * 24; i >= 0; i--) {
    const t = new Date(anchor - i * 3600e3)
    const k = hourKey(t)
    const base = 6 + Math.round(rand() * 10)
    history[k] = base
    forByHour[k] = +(base * (0.04 + rand() * 0.05)).toFixed(3)
  }
  return { history, forByHour }
}

function buildRounds(seed: number, count: number): Round[] {
  const rand = rng(seed)
  const rounds: Round[] = []
  const now = new Date()
  let sec = now.getUTCHours() * 3600 + now.getUTCMinutes() * 60 + now.getUTCSeconds()
  for (let i = 0; i < count; i++) {
    sec -= Math.round(120 + rand() * 400)
    if (sec < 0) break
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = sec % 60
    const rewarded = rand() > 0.35
    const hex = (n: number) =>
      Array.from({ length: n }, () => Math.floor(rand() * 16).toString(16)).join('')
    rounds.push({
      hash: '0x' + hex(40),
      completed_iso: `${pad(h)}:${pad(m)}:${pad(s)}`,
      duration_s: 4 + Math.round(rand() * 22),
      tx_hash: rewarded ? '0x' + hex(40) : null,
      reward_amount: rewarded ? +(0.02 + rand() * 0.18).toFixed(3) : null,
    })
  }
  return rounds.reverse()
}

// Cache the heavy arrays per node so polling returns STABLE references. Without
// this, every 5s poll rebuilds rounds/history with new identity, which makes
// Recharts re-run its enter animation each tick (the "bouncing cumulative"
// artifact). Live-feel fields (balance, tps) can still jitter per call.
const _histCache = new Map<number, ReturnType<typeof buildHistory>>()
const _roundsCache = new Map<number, ReturnType<typeof buildRounds>>()

export function mockDashboard(node: number): DashboardData {
  const seed = 1000 + node
  if (!_histCache.has(seed)) _histCache.set(seed, buildHistory(seed))
  if (!_roundsCache.has(seed)) _roundsCache.set(seed, buildRounds(seed, 60))
  const { history, forByHour } = _histCache.get(seed)!
  const rounds = _roundsCache.get(seed)!
  const participated = rounds.length
  const rewarded = rounds.filter((r) => r.tx_hash).length
  const earnedToday = +rounds.reduce((a, r) => a + (r.reward_amount || 0), 0).toFixed(3)
  const wallet = node === 1 ? '0x8a3f9c2b71e04d5a6f8b21c4e9d0a7b3c5e6f428' : '0x42d7e1b9a0c3f5628d4e7a1b8c9f0e2d3a6b5c10'
  return {
    snapshot: {
      received_at: Date.now() / 1000 - 12,
      ts: new Date().toISOString().replace('T', 'T').slice(0, 19),
      agent_version: 'a1b2c3d',
      model_short: 'Qwen2.5-7B-Instruct',
      model_size_gb: 4.7,
      capsule_max_tps: 64,
      capsule_version: '1.8.2',
      protocol_version: '0.42.0',
      capsule_uptime_seconds: 183600 + node * 3600,
      rounds_participated_today: participated,
      rounds_observed_today: participated + 14,
      errors_today: 1,
      first_round_today_iso: '00:04:11',
      last_round_today_iso: rounds[rounds.length - 1]?.completed_iso || null,
      last_round_duration_s: 9,
      last_reward_amount: 0.087,
      last_reward_iso: '14:51:02',
      rewards_today_total: earnedToday,
      wins_today: rewarded,
      rewards_logged_today: rewarded,
      tps_current: +(38 + node * 4 + Math.random() * 6).toFixed(1),
      symbols_current: +(120 + Math.random() * 40).toFixed(1),
      max_symbols: 210,
      gpu_name: node === 1 ? 'NVIDIA GeForce RTX 4090' : 'NVIDIA GeForce RTX 4080',
      gpu_vram_used_mb: 14820,
      gpu_vram_total_mb: 24564,
      gpu_power_w: 312 - node * 40,
      capsule_pid: 4821,
      protocol_pid: 4822,
      capsule_alive: true,
      protocol_alive: true,
      recent_rounds: rounds.slice(-12),
      all_rounds_today: rounds,
      rounds_history: history,
      recent_errors: [
        { iso: '11:02:55', message: 'RPC timeout while fetching balance (retried, recovered)' },
      ],
      log_extended: [
        '2026-05-30T14:51:02Z Completed inference participation round 0x9f…2a',
        '2026-05-30T14:51:02Z FOR balance after reward: 1284.51',
        '2026-05-30T14:50:41Z Submitting intent resolution…',
        '2026-05-30T14:50:39Z Inference round 0x9f2a completed in 9s',
      ],
      log_capsule: [
        '2026-05-30T14:51:00Z [capsule] tps=41.2 symbols/s=132',
        '2026-05-30T14:50:30Z [capsule] round accepted',
      ],
    },
    balance: 1284.51 + node * 210,
    balance_error: null,
    monad_balance: 3.8421,
    monad_balance_error: null,
    chain_rewards: {
      earned_today: earnedToday,
      transfers_today: rewarded,
      transfers_by_hour: forByHour,
      last_transfer_amount: 0.087,
      last_transfer_iso: '2026-05-30T14:51:02Z',
      error: null,
    },
    projections: {
      today_projected_weekly: +(earnedToday * 7 * 1.6).toFixed(2),
      today_projected_daily: +(earnedToday * 1.6).toFixed(2),
      today_projected_monthly: +(earnedToday * 30 * 1.6).toFixed(2),
      hours_elapsed: new Date().getUTCHours() + new Date().getUTCMinutes() / 60,
      avg_7d_daily: +(earnedToday * 1.4).toFixed(2),
      days_used_for_avg: 7,
    },
    today: { participated, rewarded },
    power: {
      current_kw: +((312 - node * 40) / 1000).toFixed(3),
      kwh_today: +(3.2 + node).toFixed(2),
      kwh_7d: +(22 + node * 4).toFixed(1),
      kwh_4w: +(88 + node * 12).toFixed(1),
    },
    node_name: node === 1 ? 'brave-orbit-falcon' : 'calm-river-quartz',
    uptime: {
      pct_24h: node === 1 ? 99.8 : 97.4,
      pct_7d: node === 1 ? 99.2 : 95.1,
      samples_24h: 1440,
      samples_7d: 10080,
      alive_now: true,
      stale_after_secs: 90,
    },
    wallet,
    wallet_short: `${wallet.slice(0, 6)}…${wallet.slice(-4)}`,
    known_nodes: [1, 2],
    auth_enabled: false,
  }
}

export function mockOverview(): OverviewData {
  const n1 = mockDashboard(1)
  const n2 = mockDashboard(2)
  const mk = (id: number, d: DashboardData) => ({
    node_id: id,
    wallet: d.wallet,
    wallet_short: d.wallet_short,
    received_at: d.snapshot!.received_at,
    ts: d.snapshot!.ts,
    earned_today: d.chain_rewards!.earned_today!,
    tps_current: d.snapshot!.tps_current,
    rounds_participated_today: d.snapshot!.rounds_participated_today,
    capsule_alive: true,
    protocol_alive: true,
    uptime_pct_24h: d.uptime.pct_24h,
  })
  const nodes = [mk(1, n1), mk(2, n2)]
  return {
    nodes,
    totals: {
      earned_today: +(nodes.reduce((a, n) => a + (n.earned_today || 0), 0)).toFixed(3),
      distinct_wallets: 2,
      nodes_active: 2,
      nodes_known: 2,
      rounds_participated_today: nodes.reduce((a, n) => a + n.rounds_participated_today, 0),
    },
    auth_enabled: false,
  }
}

export function mockWallets(): WatchedWallet[] {
  const d = mockDashboard(1)
  return [
    { address: d.wallet!, label: 'Operator', for_balance: d.balance, monad_balance: 3.84, is_operator: true },
    {
      address: '0x1234abcd5678ef901234abcd5678ef901234abcd',
      label: 'Cold storage',
      for_balance: 9120.4,
      monad_balance: 0.21,
      is_operator: false,
    },
  ]
}
