import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import TopBar from '../components/ui/TopBar'
import GlassCard from '../components/ui/GlassCard'
import { Badge, DataRow, Segmented } from '../components/ui/Primitives'
import RoundsLineChart from '../components/charts/RoundsLineChart'
import ParticipationChart from '../components/charts/ParticipationChart'
import TodayDonut from '../components/charts/TodayDonut'
import { usePoll } from '../hooks/usePoll'
import { addWallet, AuthError, getDashboardData, getWallets, goToLogin, IS_MOCK } from '../lib/api'
import type { DashboardData, WatchedWallet } from '../lib/types'
import { fmtAgo, fmtFixed, fmtNum, fmtPct, fmtUptime, shortHash, uptimeColor } from '../lib/format'
import type { ChartMode } from '../lib/buckets'

const LOG_EVENT_RE =
  /Completed inference participation|Inference round \w+ completed|FOR balance (before|after) reward|Submitting intent resolution|Resolution of .* resolved|Node's balance is|Operator Wallet Address| ERROR /

function pref(key: string, node: number, fallback: string): string {
  try {
    return localStorage.getItem(`ft.${key}.node${node}`) ?? fallback
  } catch {
    return fallback
  }
}
function savePref(key: string, node: number, value: string) {
  try {
    localStorage.setItem(`ft.${key}.node${node}`, value)
  } catch {
    /* ignore */
  }
}

export default function NodeDashboard() {
  const params = useParams()
  const node = Math.max(1, parseInt(params.id || '1') || 1)
  const { data, error } = usePoll<DashboardData>(() => getDashboardData(node), 5000, `node-${node}`)

  return (
    <>
      <TopBar
        right={
          data?.auth_enabled ? (
            <form method="post" action="/logout">
              <button className="btn sm ghost" type="submit">Logout</button>
            </form>
          ) : null
        }
      >
        <Link className="navlink" to="/dashboard">← All nodes</Link>
        {(data?.known_nodes || [node]).map((id) => (
          <Link key={id} className={`navlink ${id === node ? 'active' : ''}`} to={`/node/${id}`}>
            Node {id}
          </Link>
        ))}
      </TopBar>

      <main className="container page">
        <Header data={data} error={error} node={node} />

        {/* top row: balance / node / today */}
        <div className="dash-grid" style={{ marginBottom: 16 }}>
          <BalanceCard data={data} />
          <NodeCard data={data} node={node} />
          <GlassCard caption="Today (UTC)">
            <TodayDonut
              participated={data?.today?.participated ?? data?.snapshot?.rounds_participated_today ?? 0}
              rewarded={data?.today?.rewarded ?? 0}
              observed={Math.max(
                0,
                (data?.snapshot?.rounds_observed_today ?? 0) - (data?.snapshot?.rounds_participated_today ?? 0),
              )}
            />
          </GlassCard>
        </div>

        {/* participation chart */}
        <GlassCard caption="Rounds participated" className="stack-16" style={{ marginBottom: 16 }}>
          <ParticipationChart
            history={data?.snapshot?.rounds_history}
            forByHour={data?.chain_rewards?.transfers_by_hour}
            statForMode={(mode) => powerStat(data, mode)}
          />
        </GlassCard>

        {/* THE recent-rounds line graph (was a table) */}
        <GlassCard caption="Recent rounds" style={{ marginBottom: 16 }}>
          <RoundsLineChart rounds={data?.snapshot?.all_rounds_today || []} />
        </GlassCard>

        <LogCard data={data} node={node} />
        <ErrorsCard data={data} />
        <WalletsCard />
      </main>
    </>
  )
}

/* -------------------------------------------------------------------------- */

function Header({ data, error, node }: { data: DashboardData | null; error: string | null; node: number }) {
  const s = data?.snapshot
  const name = data?.node_name || `Node ${node}`
  const ageS = s ? Date.now() / 1000 - s.received_at : null
  const stale = ageS != null && ageS > 180
  const alive = s?.capsule_alive && s?.protocol_alive
  return (
    <div className="page-head">
      <div className="spread wrap">
        <h1 className="page-title row gap-12" style={{ alignItems: 'center' }}>
          {name}
          {s && <Badge kind={alive ? 'ok' : 'down'} dot>{alive ? 'Online' : 'Down'}</Badge>}
          {IS_MOCK && <Badge kind="accent">preview data</Badge>}
        </h1>
      </div>
      <div className="muted row gap-8 wrap" style={{ fontSize: 13, marginTop: 6 }}>
        {error ? (
          <span style={{ color: 'var(--red)' }}>connection error: {error}</span>
        ) : s ? (
          <>
            <span className="live-dot" />
            <span className="mono">{data?.wallet_short}</span>
            <span>· last push {fmtAgo(s.received_at)} (UTC {s.ts ? s.ts.slice(11, 19) : '—'})</span>
            {s.agent_version && <span>· v {s.agent_version}</span>}
            {stale && <Badge kind="warn">STALE</Badge>}
          </>
        ) : (
          <Badge kind="down">No data — workstation agent has not pushed yet</Badge>
        )}
      </div>
    </div>
  )
}

function BalanceCard({ data }: { data: DashboardData | null }) {
  const s = data?.snapshot
  const cr = data?.chain_rewards || {}
  const usingChain = !!(cr.earned_today && !cr.error)
  const earned = usingChain ? cr.earned_today : s?.rewards_today_total
  const lastAmt = usingChain ? cr.last_transfer_amount : s?.last_reward_amount
  const lastIso = usingChain ? (cr.last_transfer_iso ? cr.last_transfer_iso.slice(11, 19) : null) : s?.last_reward_iso
  const p = data?.projections

  return (
    <GlassCard caption="FOR Balance · Monad Testnet">
      {data && data.balance == null && data.balance_error ? (
        <div style={{ color: 'var(--red)', fontSize: 13 }}>RPC error: {data.balance_error}</div>
      ) : (
        <>
          <div className="kpi" style={{ fontSize: 32 }}>
            {fmtNum(data?.balance)} <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>FOR</span>
          </div>
          {data?.monad_balance != null && (
            <div className="muted mono" style={{ fontSize: 13, marginTop: 6 }}>{fmtFixed(data.monad_balance, 4)} MON</div>
          )}
          {earned ? (
            <div style={{ color: 'var(--green)', fontSize: 13, marginTop: 6 }}>
              +{fmtNum(earned)} FOR earned today{!usingChain && <span className="muted"> (agent estimate)</span>}
            </div>
          ) : null}
          {cr.transfers_today ? (
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{cr.transfers_today} distributions today</div>
          ) : null}
          {lastAmt ? (
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>last +{fmtNum(lastAmt)} FOR at {lastIso || '—'} UTC</div>
          ) : null}
        </>
      )}

      <div className="divider" />
      <div className="card-label" style={{ marginBottom: 10 }}>Earnings projection</div>
      <Projection p={p} />
    </GlassCard>
  )
}

function Projection({ p }: { p: DashboardData['projections'] | null | undefined }) {
  if (!p) return <div className="muted" style={{ fontSize: 13 }}>Awaiting on-chain data…</div>
  const hasToday = p.today_projected_weekly != null
  const hasAvg = p.avg_7d_daily != null
  if (!hasToday && !hasAvg) {
    return (
      <div className="muted" style={{ fontSize: 13 }}>
        Not enough history yet — earn FOR through a UTC day to project.
        <div style={{ marginTop: 4 }}>{(p.hours_elapsed ?? 0).toFixed(1)}h into today's UTC day</div>
      </div>
    )
  }
  return (
    <>
      {hasToday ? (
        <>
          <div className="kpi" style={{ fontSize: 24 }}>
            {fmtNum(p.today_projected_weekly)} <span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>FOR / wk</span>
          </div>
          <div style={{ color: 'var(--green)', fontSize: 13, marginTop: 5 }}>
            {fmtNum(p.today_projected_daily)} FOR/day · {fmtNum(p.today_projected_monthly)} FOR/mo
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>today's pace · {(p.hours_elapsed ?? 0).toFixed(1)}h elapsed</div>
        </>
      ) : (
        <div className="muted" style={{ fontSize: 13 }}>Pace projection paused — too early in UTC day.</div>
      )}
      {hasAvg && (
        <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>7-day avg: {fmtNum(p.avg_7d_daily)} FOR/day ({p.days_used_for_avg}d seen)</div>
      )}
    </>
  )
}

function NodeCard({ data, node }: { data: DashboardData | null; node: number }) {
  const s = data?.snapshot
  const u = data?.uptime
  const [tpsMode, setTpsMode] = useState<'actual' | 'max'>(() => pref('tpsMode', node, 'actual') as 'actual' | 'max')
  const setTps = (m: 'actual' | 'max') => {
    setTpsMode(m)
    savePref('tpsMode', node, m)
  }

  const vram =
    s?.gpu_vram_used_mb != null && s?.gpu_vram_total_mb
      ? `${(s.gpu_vram_used_mb / 1024).toFixed(1)} GB / ${(s.gpu_vram_total_mb / 1024).toFixed(1)} GB`
      : '—'

  const uptimeRow = () => {
    if (!u) return null
    if (!u.samples_24h && !u.samples_7d)
      return <DataRow k="Heartbeat uptime"><span className="muted" style={{ fontSize: 12 }}>collecting…</span></DataRow>
    return (
      <DataRow k="Heartbeat uptime">
        <span style={{ color: uptimeColor(u.pct_24h) }}>{fmtPct(u.pct_24h)}</span>
        <span className="muted" style={{ fontSize: 11 }}> 24h </span>·
        <span style={{ color: uptimeColor(u.pct_7d) }}> {fmtPct(u.pct_7d)}</span>
        <span className="muted" style={{ fontSize: 11 }}> 7d</span>
      </DataRow>
    )
  }

  return (
    <GlassCard
      caption="Node"
      actions={
        <Segmented
          value={tpsMode}
          onChange={setTps}
          options={[
            { value: 'actual', label: 'Actual' },
            { value: 'max', label: 'Max' },
          ]}
        />
      }
    >
      {!s ? (
        <DataRow k="Status"><Badge kind="down">No data</Badge></DataRow>
      ) : (
        <>
          <DataRow k="Model">
            <span style={{ fontSize: 12 }}>
              {s.model_short || '—'}
              {s.model_size_gb ? <span className="muted"> ({s.model_size_gb.toFixed(1)} GB)</span> : null}
            </span>
          </DataRow>
          <DataRow k="GPU"><span style={{ fontSize: 12 }}>{s.gpu_name || '—'}</span></DataRow>
          <DataRow k="VRAM">{vram}</DataRow>
          {tpsMode === 'max' ? (
            <>
              <DataRow k="Max TPS">{fmtNum(s.capsule_max_tps)}</DataRow>
              <DataRow k="Max symbols/sec">{fmtNum(s.max_symbols)}</DataRow>
            </>
          ) : (
            <>
              <DataRow k="TPS">{fmtNum(s.tps_current)}</DataRow>
              <DataRow k="Symbols/sec">{fmtNum(s.symbols_current)}</DataRow>
            </>
          )}
          <DataRow k="Capsule">{s.capsule_version || '—'} <span className="muted">PID {s.capsule_pid || '—'}</span></DataRow>
          <DataRow k="Protocol">{s.protocol_version || '—'} <span className="muted">PID {s.protocol_pid || '—'}</span></DataRow>
          <DataRow k="Uptime">{fmtUptime(s.capsule_uptime_seconds)}</DataRow>
          {uptimeRow()}
        </>
      )}
    </GlassCard>
  )
}

function powerStat(data: DashboardData | null, mode: ChartMode) {
  const p = data?.power
  if (!p || (p.current_kw == null && !p.kwh_4w)) return null
  const kw = p.current_kw != null ? `${p.current_kw.toFixed(3)} kW` : '— kW'
  const win =
    mode === 'hourly' ? [p.kwh_today, 'today'] : mode === 'daily' ? [p.kwh_7d, '7d'] : [p.kwh_4w, '4w']
  return `⚡ ${kw} · ${fmtNum(win[0] as number)} kWh ${win[1]}`
}

function LogCard({ data, node }: { data: DashboardData | null; node: number }) {
  const s = data?.snapshot
  const [logMode, setLogMode] = useState<'extended' | 'capsule'>(() => pref('logMode', node, 'extended') as 'extended' | 'capsule')
  const [logFilter, setLogFilter] = useState<'all' | 'events'>(() => pref('logFilter', node, 'all') as 'all' | 'events')
  const ref = useRef<HTMLPreElement>(null)
  const atBottom = useRef(true)

  const lines = useMemo(() => {
    let l = (logMode === 'extended' ? s?.log_extended : s?.log_capsule) || []
    if (logFilter === 'events') l = l.filter((ln) => LOG_EVENT_RE.test(ln))
    return l
  }, [s, logMode, logFilter])

  useEffect(() => {
    const el = ref.current
    if (el && atBottom.current) el.scrollTop = el.scrollHeight
  }, [lines])

  const onScroll = () => {
    const el = ref.current
    if (el) atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24
  }

  return (
    <GlassCard
      caption="Node log (last 500 lines)"
      style={{ marginBottom: 16 }}
      actions={
        <div className="row gap-8">
          <Segmented
            value={logMode}
            onChange={(m) => {
              setLogMode(m)
              savePref('logMode', node, m)
            }}
            options={[
              { value: 'extended', label: 'extended' },
              { value: 'capsule', label: 'capsule' },
            ]}
          />
          <Segmented
            value={logFilter}
            onChange={(m) => {
              setLogFilter(m)
              savePref('logFilter', node, m)
            }}
            options={[
              { value: 'all', label: 'All' },
              { value: 'events', label: 'Events' },
            ]}
          />
        </div>
      }
    >
      <pre className="logview" ref={ref} onScroll={onScroll}>
        {lines.length ? lines.join('\n') : logFilter === 'events' ? '(no matching events in this window)' : '(no log lines received)'}
      </pre>
    </GlassCard>
  )
}

function ErrorsCard({ data }: { data: DashboardData | null }) {
  const errs = data?.snapshot?.recent_errors || []
  return (
    <GlassCard caption="Last errors" style={{ marginBottom: 16 }}>
      {errs.length ? (
        <table className="tbl">
          <thead>
            <tr>
              <th>Time UTC</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {errs.map((e, i) => (
              <tr key={i}>
                <td style={{ whiteSpace: 'nowrap' }}>{e.iso || '—'}</td>
                <td style={{ color: 'var(--red)', wordBreak: 'break-word' }}>{e.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="muted" style={{ textAlign: 'center', fontSize: 13, padding: 14 }}>No errors today</div>
      )}
    </GlassCard>
  )
}

function WalletsCard() {
  const [wallets, setWallets] = useState<WatchedWallet[]>([])
  const [addr, setAddr] = useState('')
  const [label, setLabel] = useState('')
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const refresh = useCallback(async () => {
    try {
      setWallets(await getWallets())
    } catch (e) {
      if (e instanceof AuthError) goToLogin()
    }
  }, [])

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 30000)
    return () => clearInterval(t)
  }, [refresh])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setMsg({ text: 'Adding…', ok: true })
    try {
      const a = await addWallet(addr.trim(), label.trim() || null)
      setMsg({ text: `Added ${a}`, ok: true })
      setAddr('')
      setLabel('')
      refresh()
    } catch (err) {
      setMsg({ text: `Error: ${(err as Error).message}`, ok: false })
    }
  }

  return (
    <GlassCard caption="Watched wallets">
      <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
        Add any Monad Testnet wallet to watch its FOR + MONAD balance.
      </p>
      <form onSubmit={submit} className="row gap-8 wrap" style={{ marginBottom: 12 }}>
        <input
          className="input"
          style={{ flex: 1, minWidth: 220 }}
          placeholder="0x… wallet address"
          pattern="^0x[0-9a-fA-F]{40}$"
          required
          value={addr}
          onChange={(e) => setAddr(e.target.value)}
        />
        <input
          className="input"
          style={{ width: 170 }}
          placeholder="label (optional)"
          maxLength={40}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
        <button className="btn primary" type="submit">Add</button>
      </form>
      {msg && (
        <div style={{ fontSize: 12, marginBottom: 8, color: msg.ok ? 'var(--green)' : 'var(--red)' }}>{msg.text}</div>
      )}
      {wallets.length ? (
        <table className="tbl">
          <thead>
            <tr>
              <th>Wallet</th>
              <th>Label</th>
              <th>FOR</th>
              <th>MONAD</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {wallets.map((w) => (
              <tr key={w.address}>
                <td style={{ fontSize: 12 }}>
                  {shortHash(w.address)} {w.is_operator && <Badge kind="ok">OPERATOR</Badge>}
                </td>
                <td>{w.label || <span className="muted">—</span>}</td>
                <td>{fmtNum(w.for_balance)}</td>
                <td>{fmtFixed(w.monad_balance, 4)}</td>
                <td>
                  <button className="btn sm ghost" onClick={() => navigator.clipboard?.writeText(w.address)}>copy</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="muted" style={{ textAlign: 'center', fontSize: 13, padding: 10 }}>No wallets watched yet</div>
      )}
    </GlassCard>
  )
}
