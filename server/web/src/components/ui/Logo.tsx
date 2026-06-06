export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <linearGradient id="ftring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5b8cff" />
          <stop offset="1" stopColor="#38e1c6" />
        </linearGradient>
      </defs>
      <g transform="rotate(-20 32 32)">
        <circle cx="32" cy="32" r="28" fill="none" stroke="url(#ftring)" strokeWidth="2.5" />
        <circle cx="52" cy="32" r="3.2" fill="#4ade80" />
      </g>
      <circle cx="32" cy="32" r="22" fill="rgba(10,12,18,0.9)" />
      <text
        x="32"
        y="42"
        textAnchor="middle"
        fontFamily="'JetBrains Mono', ui-monospace, monospace"
        fontWeight="700"
        fontSize="26"
        fill="#eef1f8"
      >
        42
      </text>
    </svg>
  )
}

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <span className="row gap-12" style={{ alignItems: 'center' }}>
      <LogoMark size={size} />
      <span style={{ lineHeight: 1.1 }}>
        <span style={{ fontWeight: 800, letterSpacing: '-0.3px', display: 'block', fontSize: 15 }}>
          FortyTwo<span className="grad-text"> Node Analysis</span>
        </span>
        <span className="muted hide-sm" style={{ fontSize: 11 }}>
          Network telemetry &amp; rewards
        </span>
      </span>
    </span>
  )
}
