import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { fmtNum } from '../../lib/format'

const COLORS = { rewarded: '#c3f53b', unrewarded: '#6366f1', observed: '#8a8a8a' }

export default function TodayDonut({
  participated,
  rewarded,
  observed,
}: {
  participated: number
  rewarded: number
  observed: number
}) {
  const unrewarded = Math.max(0, participated - rewarded)
  const segs = [
    { name: 'Rewarded', value: rewarded, color: COLORS.rewarded },
    { name: 'Unrewarded', value: unrewarded, color: COLORS.unrewarded },
    { name: 'Observed', value: observed, color: COLORS.observed },
  ].filter((s) => s.value > 0)

  const pct = participated ? Math.round((100 * rewarded) / participated) : 0

  if (participated === 0 && observed === 0) {
    return (
      <div className="muted" style={{ textAlign: 'center', fontSize: 13, padding: '40px 0' }}>
        No rounds today yet
      </div>
    )
  }

  return (
    <div className="row gap-16 wrap" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'relative', width: 170, height: 170 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={segs}
              dataKey="value"
              innerRadius={58}
              outerRadius={80}
              paddingAngle={2}
              stroke="none"
              startAngle={90}
              endAngle={-270}
              isAnimationActive
              animationDuration={550}
            >
              {segs.map((s) => (
                <Cell key={s.name} fill={s.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <div className="kpi" style={{ fontSize: 30 }}>{pct}%</div>
          <div className="card-label">rewarded</div>
        </div>
      </div>
      <div className="stack gap-8" style={{ fontSize: 13, minWidth: 150 }}>
        {segs.map((s) => (
          <div key={s.name} className="row gap-8" style={{ alignItems: 'center' }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color }} />
            {s.name}
            <span className="muted tnum" style={{ marginLeft: 'auto' }}>{fmtNum(s.value, 0)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
