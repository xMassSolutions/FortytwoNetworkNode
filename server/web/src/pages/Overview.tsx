import { useState } from 'react'
import { Link } from 'react-router-dom'
import TopBar from '../components/ui/TopBar'
import GlassCard from '../components/ui/GlassCard'
import { Badge, StatTile } from '../components/ui/Primitives'
import { usePoll } from '../hooks/usePoll'
import { getOverview, IS_MOCK } from '../lib/api'
import type { OverviewData, OverviewNode } from '../lib/types'
import { fmtAgo, fmtNum, fmtPct, uptimeColor } from '../lib/format'

function nodeStatus(n: OverviewNode): { kind: 'ok' | 'down' | 'warn' | 'muted'; label: string } {
  if (n.received_at == null) return { kind: 'muted', label: 'No data' }
  const age = Math.max(0, Date.now() / 1000 - n.received_at)
  if (age > 180) return { kind: 'warn', label: 'Stale' }
  if (n.capsule_alive && n.protocol_alive) return { kind: 'ok', label: 'Up' }
  return { kind: 'down', label: 'Down' }
}

export default function Overview() {
  const { data, error, lastUpdated } = usePoll<OverviewData>(getOverview, 5000, 'overview')
  const [showEmpty, setShowEmpty] = useState<boolean>(() => {
    try {
      return localStorage.getItem('ft.overview.showEmpty') === '1'
    } catch {
      return false
    }
  })

  const toggleEmpty = () => {
    const next = !showEmpty
    setShowEmpty(next)
    try {
      localStorage.setItem('ft.overview.showEmpty', next ? '1' : '0')
    } catch {
      /* ignore */
    }
  }

  let nodes = data?.nodes || []
  if (!showEmpty) nodes = nodes.filter((n) => n.received_at != null)
  const t = data?.totals
  const visibleKnown = showEmpty ? t?.nodes_known ?? 0 : nodes.length

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
        <Link className="navlink active" to="/dashboard">Overview</Link>
        <Link className="navlink" to="/">Landing</Link>
      </TopBar>

      <main className="container page">
        <div className="page-head spread wrap">
          <div>
            <h1 className="page-title">All nodes</h1>
            <div className="muted row gap-8" style={{ fontSize: 13, marginTop: 4 }}>
              <span className="live-dot" />
              {error ? `connection error: ${error}` : lastUpdated ? `updated ${new Date(lastUpdated).toLocaleTimeString()}` : 'loading…'}
              {IS_MOCK && <Badge kind="accent">preview data</Badge>}
            </div>
          </div>
          <label className="row gap-8 muted" style={{ fontSize: 13, cursor: 'pointer' }}>
            <input type="checkbox" checked={showEmpty} onChange={toggleEmpty} /> show empty nodes
          </label>
        </div>

        <div className="totals-grid" style={{ marginBottom: 18 }}>
          <StatTile
            label="Today's FOR"
            accent
            value={fmtNum(t?.earned_today)}
            sub={`${t?.distinct_wallets ?? 0} wallet${t?.distinct_wallets === 1 ? '' : 's'}`}
          />
          <StatTile
            label="Active nodes"
            value={
              <>
                {t?.nodes_active ?? 0} <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>of {visibleKnown}</span>
              </>
            }
            sub={t && t.nodes_active === visibleKnown ? 'all up' : `${visibleKnown - (t?.nodes_active ?? 0)} missing`}
          />
          <StatTile label="Rounds today" value={fmtNum(t?.rounds_participated_today)} sub="summed across nodes" />
        </div>

        {nodes.length ? (
          <div className="node-grid">
            {nodes.map((n) => {
              const st = nodeStatus(n)
              return (
                <Link key={n.node_id} to={`/node/${n.node_id}`} style={{ display: 'block' }}>
                  <GlassCard hover bodyClass="node-tile">
                    <div className="name">
                      Node {n.node_id} <Badge kind={st.kind} dot>{st.label}</Badge>
                    </div>
                    <div className="wallet">{n.wallet_short || 'no wallet bound'}</div>
                    <div className="big">
                      {fmtNum(n.earned_today)} <span className="u">FOR today</span>
                    </div>
                    <div className="sub">
                      {n.tps_current != null ? fmtNum(n.tps_current) : '—'} TPS · {n.rounds_participated_today || 0} rounds ·{' '}
                      {n.received_at ? fmtAgo(n.received_at) : 'no push yet'}
                    </div>
                    <div className="sub">
                      24h uptime <span style={{ color: uptimeColor(n.uptime_pct_24h) }}>{fmtPct(n.uptime_pct_24h)}</span>
                    </div>
                  </GlassCard>
                </Link>
              )
            })}
          </div>
        ) : (
          <GlassCard>
            <div className="muted" style={{ textAlign: 'center', padding: 24, fontSize: 13 }}>
              No nodes have pushed yet. Tick "show empty nodes" to see placeholders.
            </div>
          </GlassCard>
        )}
      </main>
    </>
  )
}
