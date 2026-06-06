import { useState } from 'react'
import { Link } from 'react-router-dom'
import TopBar from '../components/ui/TopBar'
import GlassCard from '../components/ui/GlassCard'
import CodeBlock from '../components/ui/CodeBlock'
import { Badge } from '../components/ui/Primitives'

const REPO = 'https://github.com/xMassSolutions/FortytwoNetworkNode'

function Icon({ name }: { name: string }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  }
  switch (name) {
    case 'nodes':
      return (<svg {...common}><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7.7 7.8 10.6 16M16.3 7.8 13.4 16M8.5 6h7"/></svg>)
    case 'db':
      return (<svg {...common}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></svg>)
    case 'pulse':
      return (<svg {...common}><path d="M2 12h4l3 8 4-16 3 8h6"/></svg>)
    case 'chain':
      return (<svg {...common}><path d="M9 12a3 3 0 0 1 3-3h2a3 3 0 0 1 0 6h-1M15 12a3 3 0 0 1-3 3h-2a3 3 0 0 1 0-6h1"/></svg>)
    case 'uptime':
      return (<svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>)
    case 'chart':
      return (<svg {...common}><path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 4-6"/></svg>)
    case 'refresh':
      return (<svg {...common}><path d="M21 12a9 9 0 1 1-3-6.7M21 4v5h-5"/></svg>)
    case 'wallet':
      return (<svg {...common}><rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M16 12h2"/><path d="M3 9h13a2 2 0 0 1 2 2"/></svg>)
    case 'free':
      return (<svg {...common}><path d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z"/><path d="m9 12 2 2 4-4"/></svg>)
    default:
      return null
  }
}

const FEATURES = [
  { ico: 'nodes', t: 'One dashboard, many nodes', d: 'An aggregate page with a tile per node — today’s FOR, TPS, uptime, last-seen — plus combined totals. Click through to a full per-node view.' },
  { ico: 'chart', t: 'Rounds as a live line graph', d: 'Every inference round plotted over the day — reward, cumulative FOR, or duration — with smooth tooltips instead of a static table.' },
  { ico: 'db', t: 'Durable reward history', d: 'Point the bot at a free Neon Postgres and per-hour FOR + the rolling rounds chart survive every cold start and redeploy.' },
  { ico: 'pulse', t: 'Live node telemetry', d: 'FOR + MONAD balance, today’s on-chain earnings, model, GPU + VRAM, TPS / symbols-per-sec, versions and uptime — refreshed every 5s.' },
  { ico: 'chain', t: 'On-chain truth for rewards', d: '“FOR earned today” is computed by scanning ERC-20 Transfer events on Monad Testnet directly — not derived from the capsule log.' },
  { ico: 'uptime', t: 'Heartbeat uptime', d: 'Per-node 24h / 7d uptime rolled up from one-per-minute samples. “Alive” means an agent push landed in the last 90 seconds.' },
  { ico: 'refresh', t: 'Auto-updating agent', d: 'The workstation agent self-pulls from origin/main every 5 min and restarts on the new code, surfacing its git SHA on the dashboard.' },
  { ico: 'wallet', t: 'Multi-wallet watch', d: 'Add any Monad Testnet address to track its FOR + MONAD balance alongside your operator wallet.' },
  { ico: 'free', t: 'Free-tier friendly', d: 'Designed to run on Render free + Neon free + your own workstation. No paid services required.' },
]

// Higgsfield-generated hero art (holographic UI + isometric 3D blend),
// vendored into public/img. Variant B is animated; A is the still alternate.
// BASE_URL keeps paths correct under the /app/ base.
const ASSET = (p: string) => `${import.meta.env.BASE_URL}img/${p}`

function HeroVisual() {
  return (
    <div className="hero-visual">
      <video
        className="hero-img"
        autoPlay
        muted
        loop
        playsInline
        poster={ASSET('hero-b-poster.jpg')}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
      >
        <source src={ASSET('hero-b.webm')} type="video/webm" />
        <source src={ASSET('hero-b.mp4')} type="video/mp4" />
      </video>
      <div
        aria-hidden
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'inset 0 0 0 1px var(--stroke)',
          background: 'linear-gradient(115deg, rgba(6,7,11,0.55), transparent 55%)',
        }}
      />
      <GlassCard caption="fortytwo · node 1" className="hero-float on-media" style={{ left: 4, top: 12, width: 224 }}>
        <div className="card-label">FOR balance</div>
        <div className="kpi" style={{ fontSize: 24, marginTop: 4 }}>1,284.51</div>
        <div style={{ color: 'var(--green)', fontSize: 12, marginTop: 2 }}>+6.4 FOR today</div>
        <div className="card-label" style={{ marginTop: 12, marginBottom: 6 }}>Recent rounds · FOR</div>
        <svg viewBox="0 0 240 56" width="100%" height="52" preserveAspectRatio="none">
          <defs>
            <linearGradient id="hg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38e1c6" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#38e1c6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,44 L30,39 L60,41 L90,25 L120,29 L150,15 L180,21 L210,9 L240,14 L240,56 L0,56 Z" fill="url(#hg)" />
          <path d="M0,44 L30,39 L60,41 L90,25 L120,29 L150,15 L180,21 L210,9 L240,14" fill="none" stroke="#38e1c6" strokeWidth="2.5" />
        </svg>
      </GlassCard>
      <GlassCard caption="node 2" className="hero-float on-media" style={{ right: -10, bottom: 10, width: 182, animationDelay: '1.2s' }}>
        <div className="card-label">TPS</div>
        <div className="kpi" style={{ fontSize: 20 }}>41.2</div>
        <div className="row gap-8" style={{ marginTop: 8 }}>
          <Badge kind="ok" dot>Online</Badge>
        </div>
      </GlassCard>
    </div>
  )
}

function InstallSection() {
  const [host, setHost] = useState<'render' | 'railway'>('render')
  const [os, setOs] = useState<'windows' | 'mac' | 'linux'>('windows')

  const agentCmd =
    os === 'windows'
      ? 'agent/install-as-task.ps1 -BotUrl <URL> -AgentToken <TOKEN> -ScriptsRoot <PATH>'
      : os === 'mac'
      ? 'agent/install-mac.sh <URL> <TOKEN> <SCRIPTS_ROOT>'
      : 'agent/install-linux.sh <URL> <TOKEN> <SCRIPTS_ROOT>'

  const tokenCmd =
    os === 'windows'
      ? '-join ((48..57)+(97..122) | Get-Random -Count 40 | ForEach-Object {[char]$_})'
      : 'openssl rand -hex 20'

  return (
    <section id="install" className="section">
      <div className="container">
        <div className="section-eyebrow">Install</div>
        <h2 className="section-title">Live in about ten minutes</h2>
        <p className="section-sub" style={{ marginBottom: 30 }}>
          Fork the repo, deploy the server to a free host, then drop the auto-updating agent on the
          workstation running your FortyTwo node. The dashboard is identical on either host.
        </p>

        <div className="install-grid">
          <GlassCard caption={`Step 1 · Deploy the server`}>
            <div className="seg" style={{ marginBottom: 14 }}>
              <button className={host === 'render' ? 'active' : ''} onClick={() => setHost('render')}>Render</button>
              <button className={host === 'railway' ? 'active' : ''} onClick={() => setHost('railway')}>Railway</button>
            </div>
            <ol className="install-steps">
              <li>Fork <a className="grad-text" href={REPO}>the repo</a> to your GitHub account.</li>
              {host === 'render' ? (
                <>
                  <li>In Render: <b>New → Blueprint</b>, connect your fork (auto-detects <code>render.yaml</code>).</li>
                  <li>Set <code>WALLET</code> + <code>AGENT_TOKEN</code>; optionally <code>DATABASE_URL</code> (Neon) and dashboard auth.</li>
                  <li>Apply, then open <code>/healthz</code> → <code>{'{"ok":true}'}</code>.</li>
                </>
              ) : (
                <>
                  <li>In Railway: <b>New Project → Deploy from GitHub repo</b>.</li>
                  <li>Set the service <b>Root Directory</b> to <code>server</code>.</li>
                  <li>Add the same env vars, deploy, then open <code>/healthz</code>.</li>
                </>
              )}
            </ol>
            <CodeBlock label="Generate an AGENT_TOKEN">{tokenCmd}</CodeBlock>
          </GlassCard>

          <GlassCard caption="Step 2 · Install the workstation agent">
            <div className="seg" style={{ marginBottom: 14 }}>
              <button className={os === 'windows' ? 'active' : ''} onClick={() => setOs('windows')}>Windows</button>
              <button className={os === 'mac' ? 'active' : ''} onClick={() => setOs('mac')}>macOS</button>
              <button className={os === 'linux' ? 'active' : ''} onClick={() => setOs('linux')}>Linux</button>
            </div>
            <p className="muted" style={{ fontSize: 14, marginBottom: 12 }}>
              Run on the box hosting your node. It registers a{' '}
              {os === 'windows' ? 'Scheduled Task' : os === 'mac' ? 'launchd job' : 'systemd service'}, pushes
              telemetry every 60s, and self-updates from <code>origin/main</code>.
            </p>
            <CodeBlock label={os === 'windows' ? 'PowerShell' : 'bash'}>{agentCmd}</CodeBlock>
            <p className="muted" style={{ fontSize: 13, marginTop: 12 }}>
              Add a second node by repeating with <code>-NodeId 2 -NodeWallet 0x…</code> (or the Mac/Linux equivalent).
            </p>
          </GlassCard>
        </div>

        <GlassCard caption="Or: hand it to an AI agent" style={{ marginTop: 16 }}>
          <p className="muted" style={{ fontSize: 14, marginBottom: 12 }}>
            Have a coding agent with tool use? Paste this and it can do the whole install — fork, deploy, wire Neon, and install the agent for your OS.
          </p>
          <CodeBlock>{`Install the FortyTwo Network node monitoring stack from
${REPO} for me.

1. Fork the repo to my GitHub account if I haven't already.
2. Deploy the server/ service to Render using render.yaml. Prompt me
   for WALLET (my Monad Testnet operator wallet) and generate a random
   40-char AGENT_TOKEN.
3. Set up free Neon Postgres and set DATABASE_URL so reward history
   survives cold starts. (Skip if I decline -> ephemeral SQLite.)
4. (Ask first.) Lock the dashboard behind a login: random password,
   bcrypt hash, set DASHBOARD_USER / DASHBOARD_PASS_HASH / SESSION_SECRET.
5. Detect my OS and install the workstation agent for node 1.
6. Open the dashboard and confirm stats are populating.

Wallet address must come from me — don't guess or auto-generate.`}</CodeBlock>
        </GlassCard>
      </div>
    </section>
  )
}

export default function Landing() {
  return (
    <>
      <TopBar
        logoTo="/"
        right={
          <>
            <a className="navlink hide-md" href="#features">Features</a>
            <a className="navlink hide-md" href="#inside">Dashboard</a>
            <a className="navlink hide-md" href="#install">Install</a>
            <Link className="btn primary sm" to="/dashboard">Open dashboard</Link>
          </>
        }
      />

      {/* Hero */}
      <section className="hero">
        <div className="container hero-grid">
          <div className="fade-in">
            <span className="eyebrow"><span className="live-dot" /> Monad Testnet · FortyTwo Network</span>
            <h1>
              Watch every node,<br />
              <span className="grad-text">round, and reward.</span>
            </h1>
            <p className="lede">
              A self-hostable dashboard and workstation agent for monitoring your FortyTwo inference
              nodes — on-chain FOR rewards, TPS, GPU telemetry, and uptime, in one sleek view reachable
              from any device.
            </p>
            <div className="hero-cta">
              <Link className="btn primary" to="/dashboard">Open dashboard →</Link>
              <a className="btn" href="/app/dashboard?mock=1">Live preview</a>
              <a className="btn ghost" href={REPO} target="_blank" rel="noopener">View on GitHub</a>
            </div>
            <div className="hero-stats">
              <div><div className="n grad-text">5s</div><div className="l">live refresh</div></div>
              <div><div className="n grad-text">2</div><div className="l">free-tier services</div></div>
              <div><div className="n grad-text">∞</div><div className="l">nodes per dashboard</div></div>
            </div>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="section">
        <div className="container">
          <div className="section-eyebrow">What you get</div>
          <h2 className="section-title">Everything about your nodes, in one place</h2>
          <p className="section-sub">
            Built for FortyTwo operators running one rig or many. Each panel is a focused, glanceable
            window into a slice of node health and earnings.
          </p>
          <div className="feature-grid">
            {FEATURES.map((f) => (
              <GlassCard key={f.t} hover className="feature" bodyClass="feature">
                <div className="ico"><Icon name={f.ico} /></div>
                <h3>{f.t}</h3>
                <p>{f.d}</p>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* What you'll see inside */}
      <section id="inside" className="section">
        <div className="container">
          <div className="section-eyebrow">Inside the dashboard</div>
          <h2 className="section-title">What you’ll see once you’re in</h2>
          <p className="section-sub">
            Two surfaces: an all-nodes overview, and a deep per-node page. Here’s the tour — or jump
            into a live preview populated with sample data.
          </p>
          <div className="dash-grid" style={{ marginTop: 30 }}>
            <GlassCard caption="All-nodes overview">
              <p className="muted" style={{ fontSize: 14 }}>
                One tile per node with today’s FOR, TPS, rounds and 24h uptime, plus summed totals
                across every wallet. Click a tile to drill in.
              </p>
            </GlassCard>
            <GlassCard caption="Balance & projection">
              <p className="muted" style={{ fontSize: 14 }}>
                Live FOR + MONAD balance, on-chain earnings today, and a forward projection from
                today’s pace and your 7-day average.
              </p>
            </GlassCard>
            <GlassCard caption="Rounds line graph">
              <p className="muted" style={{ fontSize: 14 }}>
                The headline view — every round as a smooth line. Toggle between FOR per round,
                cumulative FOR, and round duration.
              </p>
            </GlassCard>
            <GlassCard caption="Telemetry & uptime">
              <p className="muted" style={{ fontSize: 14 }}>
                Model, GPU + VRAM, TPS, capsule/protocol versions and PIDs, plus heartbeat uptime over
                24h and 7d.
              </p>
            </GlassCard>
            <GlassCard caption="Today’s outcomes">
              <p className="muted" style={{ fontSize: 14 }}>
                A donut splitting rewarded, unrewarded and observed-only rounds, with the rewarded
                percentage front and center.
              </p>
            </GlassCard>
            <GlassCard caption="Logs, errors & wallets">
              <p className="muted" style={{ fontSize: 14 }}>
                The last 500 log lines (filterable to key events), recent errors, and a multi-wallet
                watchlist for any Monad address.
              </p>
            </GlassCard>
          </div>
          <div className="row gap-12 wrap" style={{ marginTop: 22 }}>
            <a className="btn primary" href="/app/dashboard?mock=1">Explore live preview →</a>
            <Link className="btn" to="/dashboard">Open my dashboard</Link>
          </div>
        </div>
      </section>

      <InstallSection />

      <footer className="footer">
        <div className="container spread wrap">
          <span>© {new Date().getFullYear()} xMass Solutions · FortyTwo Network Node Analysis</span>
          <span className="row gap-16">
            <a href={REPO} target="_blank" rel="noopener">GitHub</a>
            <a href="https://fortytwo.network/" target="_blank" rel="noopener">FortyTwo Network</a>
            <Link to="/dashboard">Dashboard</Link>
          </span>
        </div>
      </footer>
    </>
  )
}
