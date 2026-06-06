// Shapes mirror the FastAPI JSON endpoints in server/app.py.

export interface Round {
  hash: string
  completed_iso: string // "HH:MM:SS" UTC
  duration_s: number
  tx_hash?: string | null
  reward_amount?: number | null
}

export interface Snapshot {
  received_at: number
  ts: string | null
  agent_version: string | null
  model_short: string | null
  model_size_gb: number | null
  capsule_max_tps: number | null
  capsule_version: string | null
  protocol_version: string | null
  capsule_uptime_seconds: number | null
  rounds_participated_today: number
  rounds_observed_today: number
  errors_today: number
  first_round_today_iso: string | null
  last_round_today_iso: string | null
  last_round_duration_s: number | null
  last_reward_amount: number | null
  last_reward_iso: string | null
  rewards_today_total: number | null
  wins_today: number
  rewards_logged_today: number
  tps_current: number | null
  symbols_current: number | null
  max_symbols: number | null
  gpu_name: string | null
  gpu_vram_used_mb: number | null
  gpu_vram_total_mb: number | null
  gpu_power_w: number | null
  capsule_pid: number | null
  protocol_pid: number | null
  capsule_alive: boolean
  protocol_alive: boolean
  recent_rounds: Round[]
  all_rounds_today: Round[]
  rounds_history: Record<string, number>
  recent_errors: { iso: string; message: string }[]
  log_extended: string[]
  log_capsule: string[]
}

export interface ChainRewards {
  earned_today?: number | null
  transfers_today?: number | null
  transfers_by_hour?: Record<string, number>
  last_transfer_amount?: number | null
  last_transfer_iso?: string | null
  error?: string | null
}

export interface Projections {
  today_projected_weekly?: number | null
  today_projected_daily?: number | null
  today_projected_monthly?: number | null
  hours_elapsed?: number | null
  avg_7d_daily?: number | null
  days_used_for_avg?: number | null
}

export interface Uptime {
  pct_24h: number | null
  pct_7d: number | null
  samples_24h: number
  samples_7d: number
  alive_now: boolean
  stale_after_secs: number
}

export interface Power {
  current_kw: number | null
  kwh_today: number
  kwh_7d: number
  kwh_4w: number
}

export interface DashboardData {
  snapshot: Snapshot | null
  balance: number | null
  balance_error: string | null
  monad_balance: number | null
  monad_balance_error: string | null
  chain_rewards: ChainRewards | null
  projections: Projections | null
  today: { participated: number; rewarded: number } | null
  power: Power
  node_name: string | null
  uptime: Uptime
  wallet: string | null
  wallet_short: string | null
  known_nodes: number[]
  auth_enabled: boolean
}

export interface OverviewNode {
  node_id: number
  wallet: string | null
  wallet_short: string | null
  received_at: number | null
  ts: string | null
  earned_today: number | null
  tps_current: number | null
  rounds_participated_today: number
  capsule_alive: boolean
  protocol_alive: boolean
  uptime_pct_24h: number | null
}

export interface OverviewData {
  nodes: OverviewNode[]
  totals: {
    earned_today: number
    distinct_wallets: number
    nodes_active: number
    nodes_known: number
    rounds_participated_today: number
  }
  auth_enabled: boolean
}

export interface WatchedWallet {
  address: string
  label: string | null
  added_at?: string | null
  for_balance: number | null
  monad_balance: number | null
  is_operator: boolean
}
