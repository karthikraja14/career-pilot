#!/usr/bin/env python3
"""
HTML Dashboard — Visual application tracking dashboard.

Generates a self-contained HTML file with charts showing:
  - Application funnel (Applied → Screening → Interview → Offer)
  - Applications by platform
  - Product vs Service company split
  - Timeline of applications
  - Daily apply stats

Usage:
  python dashboard.py            # Generate and open dashboard
  python dashboard.py --no-open  # Generate only
"""

import os
import json
import webbrowser
from datetime import datetime, date
from collections import Counter

TRACKER_FILE = os.path.join("applications", "tracker.json")
STATE_FILE = os.path.join("data", "apply_state.json")
FOUND_JOBS_FILE = os.path.join("data", "found_jobs.json")
OUTPUT_FILE = os.path.join("output", "dashboard.html")


def _load_json(path: str) -> dict | list:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _gather_stats() -> dict:
    """Gather all stats from tracker and state files."""
    tracker = _load_json(TRACKER_FILE)
    state = _load_json(STATE_FILE)
    found_jobs = _load_json(FOUND_JOBS_FILE)

    apps = tracker.get("applications", []) if isinstance(tracker, dict) else []

    # Status counts
    status_counts = Counter(a.get("status", "Unknown") for a in apps)

    # Platform counts
    platform_counts = Counter(a.get("platform", "Unknown") for a in apps)

    # Product vs Service
    product_count = sum(1 for a in apps if a.get("is_product_company"))
    service_count = len(apps) - product_count

    # Timeline (applications by date)
    date_counts = Counter()
    for a in apps:
        created = a.get("created_at", "")[:10]
        if created:
            date_counts[created] += 1

    # Today's auto-apply stats
    today_stats = {}
    if isinstance(state, dict) and state.get("date") == str(date.today()):
        today_stats = state.get("counts", {})

    # Found jobs stats
    found_count = len(found_jobs) if isinstance(found_jobs, list) else 0
    found_by_verdict = Counter()
    if isinstance(found_jobs, list):
        for j in found_jobs:
            found_by_verdict[j.get("verdict", "Unknown")] += 1

    # Funnel
    funnel = {
        "Applied": status_counts.get("Applied", 0),
        "Screening": status_counts.get("Screening", 0),
        "Interview": status_counts.get("Interview", 0),
        "Offer": status_counts.get("Offer", 0),
        "Rejected": status_counts.get("Rejected", 0),
    }

    return {
        "total_applications": len(apps),
        "status_counts": dict(status_counts),
        "platform_counts": dict(platform_counts),
        "product_count": product_count,
        "service_count": service_count,
        "date_counts": dict(sorted(date_counts.items())),
        "today_stats": today_stats,
        "found_jobs_count": found_count,
        "found_by_verdict": dict(found_by_verdict),
        "funnel": funnel,
        "applications": apps,
    }


def generate_dashboard(stats: dict = None) -> str:
    """Generate a self-contained HTML dashboard."""
    if stats is None:
        stats = _gather_stats()

    total = stats["total_applications"]
    product = stats["product_count"]
    service = stats["service_count"]
    funnel = stats["funnel"]
    platforms = stats["platform_counts"]
    dates = stats["date_counts"]
    today = stats["today_stats"]
    found = stats["found_jobs_count"]

    # Prepare chart data
    date_labels = json.dumps(list(dates.keys()))
    date_values = json.dumps(list(dates.values()))

    platform_labels = json.dumps(list(platforms.keys()))
    platform_values = json.dumps(list(platforms.values()))

    funnel_labels = json.dumps(list(funnel.keys()))
    funnel_values = json.dumps(list(funnel.values()))

    status_counts = stats["status_counts"]
    status_labels = json.dumps(list(status_counts.keys()))
    status_values = json.dumps(list(status_counts.values()))

    # Recent applications table
    recent_apps = stats["applications"][-15:]
    recent_rows = ""
    for a in reversed(recent_apps):
        tag = "🟢" if a.get("is_product_company") else "🔵"
        recent_rows += f"""
            <tr>
                <td>{tag} {_esc(a.get('company', ''))}</td>
                <td>{_esc(a.get('role', ''))}</td>
                <td>{_esc(a.get('platform', ''))}</td>
                <td><span class="badge badge-{a.get('status', '').lower().replace(' ', '-')}">{_esc(a.get('status', ''))}</span></td>
                <td>{_esc(a.get('created_at', '')[:10])}</td>
            </tr>"""

    today_li = today.get("linkedin", 0)
    today_nk = today.get("naukri", 0)
    today_total = today.get("total", 0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Application Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --accent: #3b82f6; --green: #22c55e;
           --red: #ef4444; --yellow: #eab308; --text: #e2e8f0; --muted: #94a3b8; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg);
          color: var(--text); padding: 24px; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 8px; }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; }}
  .grid {{ display: grid; gap: 20px; margin-bottom: 24px; }}
  .grid-4 {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
  .grid-2 {{ grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }}
  .card {{ background: var(--card); border-radius: 12px; padding: 20px; }}
  .stat-card {{ text-align: center; }}
  .stat-number {{ font-size: 2.5rem; font-weight: 700; color: var(--accent); }}
  .stat-label {{ color: var(--muted); font-size: 0.9rem; margin-top: 4px; }}
  .stat-green .stat-number {{ color: var(--green); }}
  .stat-yellow .stat-number {{ color: var(--yellow); }}
  .stat-red .stat-number {{ color: var(--red); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th {{ text-align: left; color: var(--muted); font-size: 0.8rem;
       text-transform: uppercase; padding: 8px; border-bottom: 1px solid #334155; }}
  td {{ padding: 10px 8px; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }}
  tr:hover {{ background: rgba(59,130,246,0.05); }}
  .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
  .badge-applied {{ background: #1d4ed8; color: white; }}
  .badge-screening {{ background: #7c3aed; color: white; }}
  .badge-interview {{ background: #059669; color: white; }}
  .badge-offer {{ background: #22c55e; color: white; }}
  .badge-rejected {{ background: #dc2626; color: white; }}
  .badge-to-apply {{ background: #374151; color: #9ca3af; }}
  canvas {{ max-height: 280px; }}
  .chart-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 12px; }}
  .today-bar {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .today-item {{ background: #334155; padding: 8px 16px; border-radius: 8px; }}
  .today-item span {{ font-weight: 700; color: var(--accent); }}
  footer {{ text-align: center; color: var(--muted); margin-top: 32px; font-size: 0.8rem; }}
</style>
</head>
<body>

<h1>📊 Job Application Dashboard</h1>
<p class="subtitle">Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>

<!-- Summary Cards -->
<div class="grid grid-4">
  <div class="card stat-card">
    <div class="stat-number">{total}</div>
    <div class="stat-label">Total Applications</div>
  </div>
  <div class="card stat-card stat-green">
    <div class="stat-number">{product}</div>
    <div class="stat-label">Product Companies</div>
  </div>
  <div class="card stat-card stat-yellow">
    <div class="stat-number">{found}</div>
    <div class="stat-label">Jobs Found</div>
  </div>
  <div class="card stat-card">
    <div class="stat-number">{funnel.get('Interview', 0)}</div>
    <div class="stat-label">Interviews</div>
  </div>
</div>

<!-- Today's Stats -->
<div class="card" style="margin-bottom:20px">
  <div class="chart-title">Today's Auto-Apply</div>
  <div class="today-bar">
    <div class="today-item">LinkedIn: <span>{today_li}/10</span></div>
    <div class="today-item">Naukri: <span>{today_nk}/12</span></div>
    <div class="today-item">Total: <span>{today_total}/22</span></div>
  </div>
</div>

<!-- Charts -->
<div class="grid grid-2">
  <div class="card">
    <div class="chart-title">Application Funnel</div>
    <canvas id="funnelChart"></canvas>
  </div>
  <div class="card">
    <div class="chart-title">By Platform</div>
    <canvas id="platformChart"></canvas>
  </div>
  <div class="card">
    <div class="chart-title">Applications Over Time</div>
    <canvas id="timelineChart"></canvas>
  </div>
  <div class="card">
    <div class="chart-title">Product vs Service</div>
    <canvas id="typeChart"></canvas>
  </div>
</div>

<!-- Recent Applications -->
<div class="card" style="margin-top:20px">
  <div class="chart-title">Recent Applications</div>
  <table>
    <thead><tr><th>Company</th><th>Role</th><th>Platform</th><th>Status</th><th>Date</th></tr></thead>
    <tbody>{recent_rows if recent_rows else '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No applications tracked yet. Add some via the main menu.</td></tr>'}</tbody>
  </table>
</div>

<footer>Resume Builder & Auto-Apply Suite — Dashboard generated locally. Your data never leaves your machine.</footer>

<script>
const colors = ['#3b82f6','#22c55e','#eab308','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316'];

new Chart(document.getElementById('funnelChart'), {{
  type: 'bar',
  data: {{ labels: {funnel_labels}, datasets: [{{ data: {funnel_values},
    backgroundColor: ['#3b82f6','#8b5cf6','#22c55e','#eab308','#ef4444'] }}] }},
  options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }},
    scales: {{ y:{{ ticks:{{ color:'#94a3b8' }}, grid:{{ color:'#334155' }} }},
              x:{{ ticks:{{ color:'#94a3b8' }}, grid:{{ display:false }} }} }} }}
}});

new Chart(document.getElementById('platformChart'), {{
  type: 'doughnut',
  data: {{ labels: {platform_labels}, datasets: [{{ data: {platform_values},
    backgroundColor: colors }}] }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#94a3b8' }} }} }} }}
}});

new Chart(document.getElementById('timelineChart'), {{
  type: 'line',
  data: {{ labels: {date_labels}, datasets: [{{ label:'Applications', data: {date_values},
    borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,0.1)', fill:true, tension:0.3 }}] }},
  options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }},
    scales: {{ y:{{ ticks:{{ color:'#94a3b8' }}, grid:{{ color:'#334155' }} }},
              x:{{ ticks:{{ color:'#94a3b8', maxRotation:45 }}, grid:{{ display:false }} }} }} }}
}});

new Chart(document.getElementById('typeChart'), {{
  type: 'doughnut',
  data: {{ labels: ['Product','Service'], datasets: [{{ data: [{product},{service}],
    backgroundColor: ['#22c55e','#3b82f6'] }}] }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#94a3b8' }} }} }} }}
}});
</script>
</body>
</html>"""

    return html


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def run_dashboard(open_browser: bool = True) -> str:
    """Generate and optionally open the dashboard."""
    stats = _gather_stats()
    html = generate_dashboard(stats)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  Dashboard saved: {OUTPUT_FILE}")
    print(f"  Applications: {stats['total_applications']}")
    print(f"  Product: {stats['product_count']} | Service: {stats['service_count']}")

    if open_browser:
        abs_path = os.path.abspath(OUTPUT_FILE)
        webbrowser.open(f"file://{abs_path}")
        print(f"  Opened in browser.")

    return OUTPUT_FILE


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate application dashboard")
    parser.add_argument("--no-open", action="store_true", help="Don't open in browser")
    args = parser.parse_args()
    run_dashboard(open_browser=not args.no_open)
