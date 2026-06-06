import type { ReactNode } from 'react'

export function Badge({
  kind = 'muted',
  dot = false,
  children,
}: {
  kind?: 'ok' | 'down' | 'warn' | 'muted' | 'accent'
  dot?: boolean
  children: ReactNode
}) {
  return (
    <span className={`badge ${kind}`}>
      {dot && <span className="dot" />}
      {children}
    </span>
  )
}

export function DataRow({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="drow">
      <span className="k">{k}</span>
      <span className="v">{children}</span>
    </div>
  )
}

export interface SegOption<T extends string> {
  value: T
  label: string
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: SegOption<T>[]
  onChange: (v: T) => void
}) {
  return (
    <div className="seg" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          className={o.value === value ? 'active' : ''}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function StatTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  accent?: boolean
}) {
  return (
    <div className="glass" style={{ padding: '16px 18px' }}>
      <div className="card-label">{label}</div>
      <div
        className="kpi"
        style={{ fontSize: 26, marginTop: 6, color: accent ? 'var(--accent)' : 'var(--text)' }}
      >
        {value}
      </div>
      {sub != null && (
        <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  )
}
