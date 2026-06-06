import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  Area,
  Bar,
  ComposedChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTheme } from '../../hooks/useTheme'
import { chartColors } from './chartTheme'
import { bucketSeries, type ChartMode } from '../../lib/buckets'
import { Segmented } from '../ui/Primitives'
import { fmtNum } from '../../lib/format'

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null
  const c = chartColors(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark')
  const rounds = payload.find((p: any) => p.dataKey === 'rounds')?.value ?? 0
  const forV = payload.find((p: any) => p.dataKey === 'for')?.value ?? 0
  return (
    <div
      style={{
        background: c.tooltipBg,
        border: `1px solid ${c.tooltipBorder}`,
        borderRadius: 10,
        padding: '9px 12px',
        fontSize: 12,
        backdropFilter: 'blur(8px)',
      }}
    >
      <div style={{ fontFamily: 'var(--font-mono)', color: c.text, marginBottom: 4 }}>{label}</div>
      <div style={{ color: c.accent }}>{rounds} round{rounds === 1 ? '' : 's'}</div>
      <div style={{ color: c.lime }}>{forV > 0 ? `${fmtNum(forV, 2)} FOR` : '— FOR'}</div>
    </div>
  )
}

export default function ParticipationChart({
  history,
  forByHour,
  statForMode,
}: {
  history: Record<string, number> | undefined
  forByHour: Record<string, number> | undefined
  statForMode?: (mode: ChartMode) => ReactNode
}) {
  const { theme } = useTheme()
  const c = chartColors(theme)
  const [mode, setMode] = useState<ChartMode>('hourly')
  const data = useMemo(() => bucketSeries(history, forByHour, mode), [history, forByHour, mode])

  // Animate only when the period toggle changes — not on every 5s data poll.
  const animatedFor = useRef<string>('')
  const animate = animatedFor.current !== mode
  useEffect(() => {
    animatedFor.current = mode
  }, [mode, data])

  return (
    <div>
      <div className="spread wrap" style={{ marginBottom: 10 }}>
        <div className="muted" style={{ fontSize: 12 }}>{statForMode?.(mode)}</div>
        <Segmented
          value={mode}
          onChange={setMode}
          options={[
            { value: 'hourly', label: '24h' },
            { value: 'daily', label: '7d' },
            { value: 'weekly', label: '4w' },
          ]}
        />
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id="partfill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.accent} stopOpacity={0.35} />
              <stop offset="100%" stopColor={c.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis
            dataKey="label"
            stroke={c.axis}
            tick={{ fontSize: 11, fill: c.axis }}
            tickLine={false}
            axisLine={{ stroke: c.grid }}
            minTickGap={20}
          />
          <YAxis
            stroke={c.axis}
            tick={{ fontSize: 11, fill: c.axis }}
            tickLine={false}
            axisLine={false}
            width={36}
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: c.grid }} />
          <Bar dataKey="for" barSize={3} fill={c.lime} radius={[2, 2, 0, 0]} opacity={0.0} isAnimationActive={animate} />
          <Area
            type="monotone"
            dataKey="rounds"
            stroke={c.accent}
            strokeWidth={2.4}
            fill="url(#partfill)"
            dot={false}
            activeDot={{ r: 4, fill: c.accent, stroke: c.tooltipBg, strokeWidth: 2 }}
            isAnimationActive={animate}
            animationDuration={500}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
