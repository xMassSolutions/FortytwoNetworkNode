DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FortyTwo Node Status</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --bg:#0a0a0a; --card:#141414; --text:#e8e8e8; --muted:#888; --green:#4ade80; --red:#f87171; --blue:#60a5fa; --border:#2a2a2a; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 16px; line-height: 1.5; }
.container { max-width: 1200px; margin: 0 auto; }
header { margin-bottom: 24px; }
h1 { font-size: 22px; font-weight: 600; }
.meta { color: var(--muted); font-size: 13px; margin-top: 4px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 16px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.card h2 { font-size: 11px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; letter-spacing: 0.5px; font-weight: 600; }
.row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; font-size: 14px; gap: 12px; }
.row .label { color: var(--muted); flex-shrink: 0; }
.row .value { font-family: ui-monospace, "SF Mono", Menlo, monospace; text-align: right; word-break: break-all; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge.ok { background: rgba(74,222,128,0.15); color: var(--green); }
.badge.down { background: rgba(248,113,113,0.15); color: var(--red); }
.chart-wrap { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.chart-wrap canvas { max-height: 240px; }
.rounds-list { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--muted); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 8px; font-family: ui-monospace, "SF Mono", Menlo, monospace; border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
.balance-big { font-size: 30px; font-weight: 600; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.balance-reward { color: var(--green); font-size: 13px; margin-top: 6px; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 24px; padding-bottom: 16px; }
a { color: var(--blue); text-decoration: none; }
.section-title { font-size: 11px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; letter-spacing: 0.5px; font-weight: 600; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>FortyTwo Node Status</h1>
    <div class="meta" id="meta">Loading…</div>
  </header>
  <div class="grid">
    <div class="card"><h2>Node</h2><div id="node-content">…</div></div>
    <div class="card"><h2>Today (UTC)</h2><div id="today-content">…</div></div>
    <div class="card"><h2>FOR Balance (Monad Testnet)</h2><div id="balance-content">…</div></div>
  </div>
  <div class="chart-wrap">
    <div class="section-title">Rounds per hour (today UTC)</div>
    <canvas id="hourChart"></canvas>
  </div>
  <div class="rounds-list">
    <div class="section-title">Recent rounds</div>
    <table>
      <thead><tr><th>Time UTC</th><th>Duration</th><th>Request hash</th></tr></thead>
      <tbody id="rounds-body"></tbody>
    </table>
  </div>
  <footer>Auto-refresh every 30s · <span id="updated"></span></footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
let chart;
function fmt(v){return v==null?'—':v;}
function fmtNum(n){return n==null?'—':Number(n).toLocaleString(undefined,{maximumFractionDigits:2});}
function fmtAgo(epoch){if(!epoch)return'never';const d=Date.now()/1000-epoch;if(d<60)return`${Math.round(d)}s ago`;if(d<3600)return`${Math.round(d/60)}m ago`;if(d<86400)return`${Math.round(d/3600)}h ago`;return`${Math.round(d/86400)}d ago`;}
function fmtUp(s){if(!s)return'—';const d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);if(d>0)return`${d}d ${h}h`;if(h>0)return`${h}h ${m}m`;return`${m}m`;}
function row(l,v){return`<div class="row"><span class="label">${l}</span><span class="value">${v}</span></div>`;}

async function refresh(){
  let data;
  try { const r = await fetch('/v1/dashboard-data',{cache:'no-store'}); data = await r.json(); }
  catch(e){ document.getElementById('meta').textContent='fetch error: '+e.message; return; }

  const s = data.snapshot;
  document.getElementById('updated').textContent = 'updated '+new Date().toLocaleTimeString();

  document.getElementById('meta').innerHTML = s
    ? `Wallet <span style="font-family:monospace">${data.wallet_short}</span> · last push ${fmtAgo(s.received_at)} (UTC ${s.ts?s.ts.slice(11,19):'—'})`
    : '<span class="badge down">No data</span> — workstation agent has not pushed yet';

  if(!s){
    document.getElementById('node-content').innerHTML = row('Status','<span class="badge down">No data</span>');
    document.getElementById('today-content').innerHTML = row('Status','—');
    document.getElementById('rounds-body').innerHTML = '<tr><td colspan="3" style="color:var(--muted);text-align:center">No data</td></tr>';
  } else {
    const alive = (s.capsule_alive && s.protocol_alive) ? '<span class="badge ok">ALIVE</span>' : '<span class="badge down">DOWN</span>';
    document.getElementById('node-content').innerHTML =
        row('Status', alive)
      + row('Model', `<span style="font-size:11px">${s.model_short||'—'}</span>`)
      + row('Max TPS', fmt(s.capsule_max_tps))
      + row('Capsule', `${s.capsule_version||'—'} <span style="color:var(--muted)">PID ${s.capsule_pid||'—'}</span>`)
      + row('Protocol', `${s.protocol_version||'—'} <span style="color:var(--muted)">PID ${s.protocol_pid||'—'}</span>`)
      + row('Uptime', fmtUp(s.capsule_uptime_seconds));

    document.getElementById('today-content').innerHTML =
        row('Participated', `<strong style="font-size:18px">${s.rounds_participated_today}</strong>`)
      + row('Observed', s.rounds_observed_today)
      + row('Errors', s.errors_today)
      + row('First round', s.first_round_today_iso||'—')
      + row('Last round', `${s.last_round_today_iso||'—'} <span style="color:var(--muted)">${s.last_round_duration_s?s.last_round_duration_s+'s':''}</span>`);

    const recent = s.recent_rounds || [];
    document.getElementById('rounds-body').innerHTML = recent.length
      ? recent.map(r=>`<tr><td>${r.completed_iso}</td><td>${r.duration_s}s</td><td style="color:var(--muted)">${(r.hash||'').slice(0,16)}…</td></tr>`).join('')
      : '<tr><td colspan="3" style="color:var(--muted);text-align:center">No rounds today</td></tr>';
  }

  if(data.balance!=null){
    document.getElementById('balance-content').innerHTML =
      `<div class="balance-big">${fmtNum(data.balance)} <span style="color:var(--muted);font-size:14px;font-weight:400">FOR</span></div>`
      + (s && s.last_reward_amount ? `<div class="balance-reward">+${fmtNum(s.last_reward_amount)} FOR at ${s.last_reward_iso} UTC</div>` : '');
  } else {
    document.getElementById('balance-content').innerHTML = `<div style="color:var(--red);font-size:13px">RPC error: ${data.balance_error||'unknown'}</div>`;
  }

  const hourly = new Array(24).fill(0);
  ((s && s.all_rounds_today) || []).forEach(r => { if(typeof r.hour === 'number') hourly[r.hour]++; });
  const labels = Array.from({length:24}, (_,i)=>String(i).padStart(2,'0'));
  if(!chart){
    const ctx = document.getElementById('hourChart').getContext('2d');
    chart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{ data: hourly, backgroundColor: '#60a5fa', borderColor: '#3b82f6', borderWidth: 1, borderRadius: 3 }] },
      options: { responsive: true, maintainAspectRatio: true, aspectRatio: 4,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => `${c.parsed.y} round(s)` } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#888', font: { size: 10 } } },
          y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#888', precision: 0 } }
        }
      }
    });
  } else {
    chart.data.datasets[0].data = hourly;
    chart.update('none');
  }
}
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""
