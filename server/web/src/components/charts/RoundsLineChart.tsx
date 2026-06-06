import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Round } from '../../lib/types'
import { useTheme } from '../../hooks/useTheme'
import { chartColors } from './chartTheme'
import { Segmented } from '../ui/Primitives'
import { fmtNum, pad, roundPending } from '../../lib/format'

type Metric = 'reward' | 'cumulative' | 'duration'

interface Point {
  x: number // seconds of UTC day
  time: string
  reward: number
  cumulative: number
  duration: number
  rewarded: boolean
  pending: boolean
}

function secondsOfDay(hms: string): number {
  const m = /^(\d{2}):(\d{2}):(\d{2})$/.exec(hms || '')
  if (!m) return 0
  return +m[1] * 3600 + +m[2] * 60 + +m[3]
}

const META: Record<Metric, { label: string; unit: string; key: keyof Point }> = {
  reward: { label: 'FOR / round', unit: 'FOR', key: 'reward' },
  cumulative: { label: 'Cumulative FOR', unit: 'FOR', key: 'cumulative' },
  duration: { label: 'Duration', unit: 's', key: 'duration' },
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null
  const p: Point = payload[0].payload
  const c = chartColors(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark')
  return (
    <div
      style={{
        background: c.tooltipBg,
        border: `1px solid ${c.tooltipBorder}`,
        borderRadius: 10,
        padding: '9px 12px',
        boxShadow: '0 12px 28px -12px rgba(0,0,0,0.6)',
        backdropFilter: 'blur(8px)',
        fontSize: 12,
      }}
    >
      <div style={{ fontFamily: 'var(--font-mono)', color: c.text, marginBottom: 4 }}>{p.time} UTC</div>
      <div style={{ color: c.accent2 }}>{fmtNum(p.reward, 3)} FOR reward</div>
      <div style={{ color: c.muted }}>cumulative {fmtNum(p.cumulative, 3)} FOR</div>
      <div style={{ color: c.muted }}>{p.duration}s · {p.pending ? 'pending' : p.rewarded ? 'rewarded' : 'unrewarded'}</div>
    </div>
  )
}

export default function RoundsLineChart({ rounds }: { rounds: Round[] }) {
  const { theme } = useTheme()
  const c = chartColors(theme)
  const [metric, setMetric] = useState<Metric>('reward')

  const data = useMemo<Point[]>(() => {
    let cum = 0
    return (rounds || [])
      .slice()
      .sort((a, b) => secondsOfDay(a.completed_iso) - secondsOfDay(b.completed_iso))
      .map((r) => {
        const reward = r.reward_amount || 0
        cum += reward
        return {
          x: secondsOfDay(r.completed_iso),
          time: r.completed_iso,
          reward,
          cumulative: +cum.toFixed(4),
          duration: r.duration_s,
          rewarded: !!r.tx_hash,
          pending: !r.tx_hash && roundPending(r.completed_iso),
        }
      })
  }, [rounds])

  // Animate the curve only when the metric changes — NOT on every 5s data
  // poll. Re-animating on each refresh makes the line visibly "redraw" (and,
  // mid-animation, a cumulative curve can momentarily look non-monotonic).
  const animatedFor = useRef<string>('')
  const animate = animatedFor.current !== metric
  useEffect(() => {
    animatedFor.current = metric
  }, [metric, data])

  const meta = META[metric]
  const stroke = metric === 'duration' ? c.accent : c.accent2
  const fillId = `roundsfill-${metric}`

  const totalFor = data.reduce((a, p) => a + p.reward, 0)

  if (!data.length) {
    return (
      <div className="muted" style={{ textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
        No rounds today yet — the line populates as your node completes inference rounds.
      </div>
    )
  }

  return (
    <div>
      <div className="spread wrap" style={{ marginBottom: 10 }}>
        <div className="row gap-12 wrap" style={{ alignItems: 'baseline' }}>
          <span className="kpi" style={{ fontSize: 22 }}>
            {fmtNum(totalFor, 3)} <span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>FOR today</span>
          </span>
          <span className="muted" style={{ fontSize: 12 }}>
            {data.length} rounds · {data.filter((d) => d.rewarded).length} rewarded
          </span>
        </div>
        <Segmented
          value={metric}
          onChange={setMetric}
          options={[
            { value: 'reward', label: 'FOR' },
            { value: 'cumulative', label: 'Cumulative' },
            { value: 'duration', label: 'Duration' },
          ]}
        />
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity={0.42} />
              <stop offset="100%" stopColor={stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis
            dataKey="x"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v: number) => `${pad(Math.floor(v / 3600))}:${pad(Math.floor((v % 3600) / 60))}`}
            stroke={c.axis}
            tick={{ fontSize: 11, fill: c.axis }}
            tickLine={false}
            axisLine={{ stroke: c.grid }}
            minTickGap={36}
          />
          <YAxis
            stroke={c.axis}
            tick={{ fontSize: 11, fill: c.axis }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(v: number) => fmtNum(v, metric === 'duration' ? 0 : 2)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey={meta.key as string}
            stroke={stroke}
            strokeWidth={2.4}
            fill={`url(#${fillId})`}
            dot={{ r: 1.6, fill: stroke, strokeWidth: 0 }}
            activeDot={{ r: 4, fill: stroke, stroke: c.tooltipBg, strokeWidth: 2 }}
            isAnimationActive={animate}
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
