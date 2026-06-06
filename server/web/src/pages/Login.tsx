import { LogoMark } from '../components/ui/Logo'

export default function Login() {
  const error = new URLSearchParams(location.search).get('error') === '1'
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 16 }}>
      <div className="glass fade-in" style={{ width: '100%', maxWidth: 380, padding: 30 }}>
        <div className="row gap-12" style={{ marginBottom: 18 }}>
          <LogoMark size={36} />
          <div>
            <div style={{ fontWeight: 800 }}>FortyTwo Network</div>
            <div className="muted" style={{ fontSize: 12 }}>Sign in to view node dashboards.</div>
          </div>
        </div>
        {error && (
          <div
            style={{
              background: 'rgba(248,113,113,0.12)',
              color: 'var(--red)',
              border: '1px solid rgba(248,113,113,0.3)',
              borderRadius: 'var(--radius-sm)',
              padding: '9px 11px',
              fontSize: 12,
              marginBottom: 14,
            }}
          >
            Wrong username or password.
          </div>
        )}
        {/* Posts to the server's existing /login (outside the /app SPA). */}
        <form method="post" action="/login" autoComplete="on" className="stack gap-12">
          <label className="stack gap-8">
            <span className="card-label">Username</span>
            <input className="input" name="username" type="text" autoComplete="username" required autoFocus />
          </label>
          <label className="stack gap-8">
            <span className="card-label">Password</span>
            <input className="input" name="password" type="password" autoComplete="current-password" required />
          </label>
          <button className="btn primary" type="submit" style={{ marginTop: 4 }}>
            Sign in
          </button>
        </form>
      </div>
    </div>
  )
}
