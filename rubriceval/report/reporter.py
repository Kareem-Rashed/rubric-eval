"""
HTML and JSON report generation for Rubric.
"""

from __future__ import annotations

import json
from pathlib import Path

from rubriceval.core.results import EvalReport


def generate_html_report(report: EvalReport, output_path: str) -> None:
    """Generate a self-contained HTML evaluation report."""
    data = report.to_dict()
    data_json = json.dumps(data, indent=2)

    duration = report.duration_seconds
    if duration is not None:
        if duration < 60:
            duration_str = f"{duration:.1f}s"
        else:
            duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    else:
        duration_str = ""

    html = _HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    html = html.replace("__PASS_RATE__", f"{report.pass_rate * 100:.1f}")
    html = html.replace("__TOTAL__", str(report.total))
    html = html.replace("__PASSED__", str(report.passed))
    html = html.replace("__FAILED__", str(report.failed))
    html = html.replace("__AVG_SCORE__", f"{report.avg_score:.3f}")
    html = html.replace("__STARTED_AT__", report.started_at or "")
    html = html.replace("__DURATION__", duration_str)
    html = html.replace("__RUN_NAME__", report.metadata.get("run_name", "Rubric Eval"))

    Path(output_path).write_text(html, encoding="utf-8")


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rubric — __RUN_NAME__</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:          #080810;
      --surface:     #0f0f18;
      --surface2:    #14141f;
      --surface3:    #1a1a28;
      --border:      #1e1e30;
      --border2:     #252538;
      --text:        #e4e4f0;
      --text2:       #b0b0c8;
      --muted:       #606078;
      --accent:      #7c6fff;
      --accent2:     #4ecdc4;
      --accent3:     #a78bfa;
      --green:       #34d399;
      --green2:      #10b981;
      --yellow:      #fbbf24;
      --orange:      #f97316;
      --red:         #f87171;
      --red2:        #ef4444;
      --blue:        #60a5fa;
      --radius:      8px;
      --radius-lg:   14px;
      --radius-xl:   20px;
      --shadow:      0 4px 24px rgba(0,0,0,0.5);
      --shadow-sm:   0 2px 8px rgba(0,0,0,0.3);
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      font-size: 14px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }

    /* ─── Scrollbar ─────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--muted); }

    /* ─── Header ────────────────────────────────────────────────── */
    .header {
      background: linear-gradient(135deg, #0d0a1f 0%, #080f1a 50%, #050d10 100%);
      border-bottom: 1px solid var(--border);
      padding: 28px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(12px);
    }
    .header-left { display: flex; align-items: center; gap: 16px; }
    .header-logo {
      font-size: 1.5rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header-divider { width: 1px; height: 28px; background: var(--border2); }
    .header-subtitle { color: var(--muted); font-size: 0.8rem; letter-spacing: 0.3px; }
    .header-right { display: flex; align-items: center; gap: 20px; }
    .header-run-name { font-size: 0.9rem; font-weight: 600; color: var(--text2); }
    .header-date { font-size: 0.75rem; color: var(--muted); }
    .header-duration {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      background: rgba(124,111,255,0.1);
      border: 1px solid rgba(124,111,255,0.2);
      color: var(--accent3);
    }

    /* ─── Layout ────────────────────────────────────────────────── */
    .main { max-width: 1280px; margin: 0 auto; padding: 36px 48px 80px; }

    /* ─── Stat Cards ────────────────────────────────────────────── */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
    @media (max-width: 600px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }

    .stat-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 20px 22px;
      position: relative;
      overflow: hidden;
      transition: border-color 0.2s, transform 0.15s;
    }
    .stat-card:hover { border-color: var(--border2); transform: translateY(-1px); }
    .stat-card::before {
      content: '';
      position: absolute;
      inset: 0;
      opacity: 0.04;
      pointer-events: none;
    }
    .stat-card::after {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 2px;
    }
    .stat-card.pass-rate::after { background: linear-gradient(90deg, var(--accent), var(--accent2)); }
    .stat-card.avg-score::after { background: var(--accent3); }
    .stat-card.s-passed::after  { background: var(--green); }
    .stat-card.s-failed::after  { background: var(--red); }
    .stat-card.s-total::after   { background: var(--muted); }

    .stat-value {
      font-size: 2.2rem;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 6px;
      letter-spacing: -1px;
      font-variant-numeric: tabular-nums;
    }
    .stat-card.pass-rate .stat-value { background: linear-gradient(135deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .stat-card.avg-score .stat-value { color: var(--accent3); }
    .stat-card.s-passed .stat-value  { color: var(--green); }
    .stat-card.s-failed .stat-value  { color: var(--red); }
    .stat-card.s-total .stat-value   { color: var(--text2); }
    .stat-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.4px;
      color: var(--muted);
    }

    /* ─── Overview Row ──────────────────────────────────────────── */
    .overview-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 20px;
    }
    @media (max-width: 700px) { .overview-row { grid-template-columns: 1fr; } }

    /* ─── Donut Chart ───────────────────────────────────────────── */
    .donut-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 20px 24px;
      display: flex;
      align-items: center;
      gap: 28px;
    }
    .donut-wrap { position: relative; flex-shrink: 0; }
    .donut-svg { width: 110px; height: 110px; transform: rotate(-90deg); }
    .donut-bg   { fill: none; stroke: var(--border2); stroke-width: 14; }
    .donut-pass { fill: none; stroke: var(--green); stroke-width: 14; stroke-linecap: round; transition: stroke-dasharray 1s cubic-bezier(0.4,0,0.2,1); }
    .donut-fail { fill: none; stroke: var(--red); stroke-width: 14; stroke-linecap: round; transition: stroke-dasharray 1s cubic-bezier(0.4,0,0.2,1); }
    .donut-center {
      position: absolute; inset: 0;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
    }
    .donut-pct { font-size: 1.4rem; font-weight: 800; color: var(--text); line-height: 1; }
    .donut-sub { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-top: 2px; }
    .donut-legend { flex: 1; }
    .donut-legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 0.82rem; }
    .donut-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .donut-legend-label { color: var(--text2); }
    .donut-legend-count { margin-left: auto; font-weight: 700; font-variant-numeric: tabular-nums; }

    /* ─── Per-metric bar chart ──────────────────────────────────── */
    .metric-chart-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 20px 24px;
      overflow: hidden;
    }
    .chart-title {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.4px;
      color: var(--muted);
      margin-bottom: 16px;
    }
    .metric-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .metric-bar-row:last-child { margin-bottom: 0; }
    .metric-bar-name {
      width: 140px;
      flex-shrink: 0;
      font-size: 0.78rem;
      color: var(--text2);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metric-bar-track {
      flex: 1;
      height: 7px;
      background: var(--border);
      border-radius: 4px;
      overflow: hidden;
    }
    .metric-bar-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.8s cubic-bezier(0.4,0,0.2,1);
      width: 0%;
    }
    .metric-bar-pct {
      width: 44px;
      text-align: right;
      font-size: 0.78rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }

    /* ─── Section headers ───────────────────────────────────────── */
    .section-header {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.6px;
      color: var(--muted);
      margin-bottom: 10px;
      margin-top: 28px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .section-header::after { content: ''; flex: 1; height: 1px; background: var(--border); }

    /* ─── Metrics table ─────────────────────────────────────────── */
    .metrics-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      overflow: hidden;
    }
    .metrics-table { width: 100%; border-collapse: collapse; }
    .metrics-table th {
      background: var(--surface2);
      color: var(--muted);
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.1px;
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    .metrics-table td { padding: 11px 16px; border-bottom: 1px solid var(--border); font-size: 0.83rem; }
    .metrics-table tr:last-child td { border-bottom: none; }
    .metrics-table tbody tr:hover td { background: var(--surface2); }
    .mbar-wrap { display: flex; align-items: center; gap: 10px; }
    .mbar { flex: 1; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; max-width: 180px; }
    .mbar-fill { height: 100%; border-radius: 3px; }

    /* ─── Search + filter ───────────────────────────────────────── */
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      margin-top: 28px;
      flex-wrap: wrap;
    }
    .search-wrap { position: relative; flex: 1; min-width: 180px; max-width: 320px; }
    .search-input {
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 7px 12px 7px 32px;
      font-size: 0.82rem;
      color: var(--text);
      outline: none;
      transition: border-color 0.2s;
    }
    .search-input::placeholder { color: var(--muted); }
    .search-input:focus { border-color: var(--accent); }
    .search-icon {
      position: absolute;
      left: 10px; top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      font-size: 0.75rem;
      pointer-events: none;
    }
    .filter-label {
      font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 1.2px; color: var(--muted);
    }
    .filter-btn {
      padding: 5px 14px;
      border-radius: 20px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      white-space: nowrap;
    }
    .filter-btn:hover { border-color: var(--accent); color: var(--text); }
    .filter-btn.active     { background: rgba(124,111,255,0.15); border-color: var(--accent); color: var(--accent3); }
    .filter-btn.active-pass { background: rgba(52,211,153,0.12); border-color: var(--green); color: var(--green); }
    .filter-btn.active-fail { background: rgba(248,113,113,0.12); border-color: var(--red); color: var(--red); }
    .filter-count { margin-left: auto; font-size: 0.75rem; color: var(--muted); white-space: nowrap; }

    /* ─── Results table ─────────────────────────────────────────── */
    .results-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      overflow: hidden;
    }
    .results-table { width: 100%; border-collapse: collapse; }
    .results-table th {
      background: var(--surface2);
      color: var(--muted);
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.1px;
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    .results-table .data-row td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
    }
    .results-table .data-row:last-of-type td { border-bottom: none; }
    .results-table .data-row:hover td { background: var(--surface2); cursor: pointer; }
    .results-table .data-row.is-expanded td { background: var(--surface2); border-bottom-color: transparent; }

    .badge {
      display: inline-flex; align-items: center; gap: 3px;
      padding: 3px 9px; border-radius: 20px;
      font-size: 0.68rem; font-weight: 700; letter-spacing: 0.5px; white-space: nowrap;
    }
    .badge-pass { background: rgba(52,211,153,0.1); color: var(--green); border: 1px solid rgba(52,211,153,0.2); }
    .badge-fail { background: rgba(248,113,113,0.1); color: var(--red); border: 1px solid rgba(248,113,113,0.2); }
    .badge-agent { background: rgba(124,111,255,0.1); color: var(--accent3); border: 1px solid rgba(124,111,255,0.2); font-size: 0.62rem; }

    .test-name {
      font-weight: 500; color: var(--text);
      max-width: 340px; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap;
    }
    .test-sub {
      font-size: 0.72rem; color: var(--muted); margin-top: 2px;
      max-width: 340px; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap;
    }
    .score-cell { display: flex; align-items: center; gap: 8px; min-width: 130px; }
    .score-track { flex: 1; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; }
    .score-fill { height: 100%; border-radius: 3px; }
    .score-num {
      font-weight: 700; font-size: 0.82rem; min-width: 40px;
      text-align: right; font-variant-numeric: tabular-nums;
    }
    .metric-pills { display: flex; flex-wrap: wrap; gap: 4px; }
    .mpill {
      font-size: 0.67rem; font-weight: 600;
      padding: 2px 7px; border-radius: 4px;
    }
    .mpill-pass { background: rgba(52,211,153,0.08); color: var(--green2); }
    .mpill-fail { background: rgba(248,113,113,0.08); color: var(--red2); }
    .expand-btn {
      width: 22px; height: 22px; border-radius: 50%;
      background: var(--surface3); border: 1px solid var(--border2);
      display: flex; align-items: center; justify-content: center;
      color: var(--muted); font-size: 0.6rem;
      transition: all 0.2s; cursor: pointer; flex-shrink: 0;
    }
    .is-expanded .expand-btn {
      transform: rotate(180deg);
      background: rgba(124,111,255,0.15);
      border-color: var(--accent);
      color: var(--accent);
    }

    /* ─── Detail panel ──────────────────────────────────────────── */
    .detail-row td {
      padding: 0 !important;
      border-bottom: 1px solid var(--border) !important;
    }
    .detail-inner {
      display: none;
      padding: 20px 20px 24px;
      background: #0a0a14;
      border-top: 1px solid var(--border);
    }
    .detail-inner.open { display: block; }

    .detail-tabs {
      display: flex; gap: 2px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0;
    }
    .dtab {
      padding: 7px 14px;
      font-size: 0.75rem; font-weight: 600;
      color: var(--muted);
      border-bottom: 2px solid transparent;
      cursor: pointer;
      transition: all 0.15s;
      user-select: none;
      margin-bottom: -1px;
    }
    .dtab:hover { color: var(--text2); }
    .dtab.active { color: var(--accent3); border-bottom-color: var(--accent); }

    .dtab-panel { display: none; }
    .dtab-panel.active { display: block; }

    /* IO boxes */
    .io-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .io-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .io-label {
      font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 1.2px; color: var(--muted);
      padding: 8px 12px 6px;
      border-bottom: 1px solid var(--border);
      background: var(--surface2);
    }
    .io-content {
      font-size: 0.8rem; color: #c4c4d8;
      white-space: pre-wrap; word-break: break-word;
      max-height: 180px; overflow-y: auto;
      line-height: 1.55; padding: 10px 12px;
      font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
    }
    .io-empty { color: var(--muted); font-style: italic; }

    /* Metric breakdown */
    .metric-breakdown {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .breakdown-header {
      padding: 8px 14px;
      background: var(--surface2);
      border-bottom: 1px solid var(--border);
      font-size: 0.62rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1.2px; color: var(--muted);
    }
    .breakdown-row {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      display: grid;
      grid-template-columns: 1fr 100px 52px 60px;
      align-items: center;
      gap: 10px;
      font-size: 0.82rem;
    }
    .breakdown-row:last-child { border-bottom: none; }
    .bd-name { color: var(--text); }
    .bd-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
    .bd-bar-fill { height: 100%; border-radius: 2px; }
    .bd-score { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
    .bd-reason {
      grid-column: 1 / -1;
      font-size: 0.75rem; color: var(--muted);
      font-style: italic; padding: 0 0 2px;
      display: none;
    }
    .breakdown-row.has-reason .bd-reason { display: block; }
    .breakdown-row.has-reason { grid-template-rows: auto auto; }

    /* Agent meta strip */
    .agent-strip {
      display: flex; flex-wrap: wrap; gap: 10px;
      margin-bottom: 14px;
    }
    .agent-chip {
      display: flex; align-items: center; gap: 6px;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 6px 12px;
      font-size: 0.78rem;
    }
    .agent-chip-icon { font-size: 0.9rem; }
    .agent-chip-label { color: var(--muted); margin-right: 2px; }
    .agent-chip-value { font-weight: 600; color: var(--text2); }

    /* ─── Trace Tree ─────────────────────────────────────────────── */
    .trace-tree { position: relative; padding-left: 24px; }
    .trace-tree::before {
      content: '';
      position: absolute;
      left: 11px; top: 20px; bottom: 20px;
      width: 2px;
      background: linear-gradient(180deg, var(--accent) 0%, var(--border2) 100%);
      border-radius: 1px;
    }
    .trace-step {
      position: relative;
      margin-bottom: 8px;
    }
    .trace-step:last-child { margin-bottom: 0; }
    .trace-dot {
      position: absolute;
      left: -18px; top: 14px;
      width: 12px; height: 12px;
      border-radius: 50%;
      border: 2px solid var(--bg);
      z-index: 1;
    }
    .step-thought    .trace-dot { background: var(--accent3); }
    .step-tool_call  .trace-dot { background: var(--green); }
    .step-observation .trace-dot { background: var(--blue); }
    .step-llm_call   .trace-dot { background: var(--accent); }
    .step-default    .trace-dot { background: var(--muted); }

    .trace-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .step-thought    .trace-card { border-left: 3px solid var(--accent3); }
    .step-tool_call  .trace-card { border-left: 3px solid var(--green); }
    .step-observation .trace-card { border-left: 3px solid var(--blue); }
    .step-llm_call   .trace-card { border-left: 3px solid var(--accent); }

    .trace-card-header {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 12px;
      background: var(--surface2);
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      user-select: none;
    }
    .trace-type-badge {
      font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.8px; padding: 2px 7px; border-radius: 4px;
    }
    .step-thought    .trace-type-badge { background: rgba(167,139,250,0.15); color: var(--accent3); }
    .step-tool_call  .trace-type-badge { background: rgba(52,211,153,0.12); color: var(--green); }
    .step-observation .trace-type-badge { background: rgba(96,165,250,0.12); color: var(--blue); }
    .step-llm_call   .trace-type-badge { background: rgba(124,111,255,0.12); color: var(--accent); }
    .step-default    .trace-type-badge { background: rgba(96,96,120,0.15); color: var(--muted); }

    .trace-step-num { font-size: 0.68rem; color: var(--muted); margin-right: 2px; }
    .trace-latency {
      margin-left: auto;
      font-size: 0.68rem; font-weight: 600;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .trace-expand { font-size: 0.55rem; color: var(--muted); margin-left: 6px; transition: transform 0.2s; }
    .trace-card.expanded .trace-expand { transform: rotate(180deg); }

    .trace-card-body {
      padding: 10px 12px;
      display: none;
    }
    .trace-card.expanded .trace-card-body { display: block; }
    .trace-content {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 0.78rem; color: #c4c4d8;
      white-space: pre-wrap; word-break: break-word;
      max-height: 220px; overflow-y: auto;
      line-height: 1.5;
    }
    .trace-meta {
      margin-top: 8px;
      font-size: 0.72rem; color: var(--muted);
    }
    .trace-meta-kv { display: inline-flex; gap: 4px; margin-right: 12px; }
    .trace-meta-key { color: var(--muted); }
    .trace-meta-val { color: var(--text2); font-weight: 600; }

    /* ─── Tool Calls Panel ──────────────────────────────────────── */
    .tool-calls-list { display: flex; flex-direction: column; gap: 8px; }
    .tool-call-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid var(--green2);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .tool-call-card.has-error { border-left-color: var(--red); }
    .tool-call-header {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 12px;
      background: var(--surface2);
      cursor: pointer;
      user-select: none;
    }
    .tool-call-name {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 0.82rem; font-weight: 600; color: var(--green);
    }
    .tool-call-card.has-error .tool-call-name { color: var(--red); }
    .tool-call-latency { margin-left: auto; font-size: 0.68rem; color: var(--muted); font-variant-numeric: tabular-nums; }
    .tool-call-expand { font-size: 0.55rem; color: var(--muted); margin-left: 6px; transition: transform 0.2s; }
    .tool-call-card.expanded .tool-call-expand { transform: rotate(180deg); }
    .tool-call-body { display: none; padding: 12px; border-top: 1px solid var(--border); }
    .tool-call-card.expanded .tool-call-body { display: block; }
    .tool-section-label {
      font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 1px; color: var(--muted); margin-bottom: 6px;
    }
    .tool-json {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 0.75rem; color: #c4c4d8;
      white-space: pre-wrap; word-break: break-word;
      background: var(--surface2); border: 1px solid var(--border);
      border-radius: 6px; padding: 8px 10px;
      max-height: 180px; overflow-y: auto;
      line-height: 1.5; margin-bottom: 10px;
    }
    .tool-error {
      background: rgba(248,113,113,0.06);
      border: 1px solid rgba(248,113,113,0.2);
      border-radius: 6px; padding: 8px 10px;
      font-size: 0.78rem; color: var(--red);
      font-family: 'SF Mono', 'Fira Code', monospace;
      white-space: pre-wrap;
    }

    /* ─── Empty / no-data states ────────────────────────────────── */
    .empty-state {
      text-align: center; padding: 48px 24px; color: var(--muted);
    }
    .empty-icon { font-size: 2rem; margin-bottom: 8px; }
    .empty-text { font-size: 0.88rem; }

    .no-data {
      font-size: 0.8rem; color: var(--muted);
      font-style: italic; padding: 16px 0;
      text-align: center;
    }

    /* ─── Footer ────────────────────────────────────────────────── */
    .footer {
      text-align: center; padding: 36px 48px 28px;
      color: var(--muted); font-size: 0.75rem;
      border-top: 1px solid var(--border);
      margin-top: 60px;
    }
    .footer a { color: var(--accent); text-decoration: none; }
    .footer a:hover { text-decoration: underline; }

    /* ─── Animations ────────────────────────────────────────────── */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .anim { animation: fadeUp 0.3s ease both; }
  </style>
</head>
<body>

  <!-- ── Header ─────────────────────────────────────────────── -->
  <header class="header">
    <div class="header-left">
      <div class="header-logo">◈ Rubric</div>
      <div class="header-divider"></div>
      <div class="header-subtitle">LLM &amp; Agent Evaluation</div>
    </div>
    <div class="header-right">
      <div>
        <div class="header-run-name" id="runName">__RUN_NAME__</div>
        <div class="header-date" id="headerDate">__STARTED_AT__</div>
      </div>
      <div class="header-duration" id="headerDuration" style="display:none">__DURATION__</div>
    </div>
  </header>

  <div class="main">

    <!-- ── Stat Cards ──────────────────────────────────────── -->
    <div class="stats-grid">
      <div class="stat-card pass-rate">
        <div class="stat-value" id="statPassRate">—</div>
        <div class="stat-label">Pass Rate</div>
      </div>
      <div class="stat-card avg-score">
        <div class="stat-value">__AVG_SCORE__</div>
        <div class="stat-label">Avg Score</div>
      </div>
      <div class="stat-card s-passed">
        <div class="stat-value">__PASSED__</div>
        <div class="stat-label">Passed</div>
      </div>
      <div class="stat-card s-failed">
        <div class="stat-value">__FAILED__</div>
        <div class="stat-label">Failed</div>
      </div>
      <div class="stat-card s-total">
        <div class="stat-value">__TOTAL__</div>
        <div class="stat-label">Total Tests</div>
      </div>
    </div>

    <!-- ── Overview Row: Donut + Metric Bars ─────────────── -->
    <div class="overview-row">

      <!-- Donut Chart -->
      <div class="donut-card">
        <div class="donut-wrap">
          <svg class="donut-svg" viewBox="0 0 110 110">
            <circle class="donut-bg" cx="55" cy="55" r="40"/>
            <circle class="donut-fail" cx="55" cy="55" r="40" id="donutFail"
              stroke-dasharray="0 251.2" stroke-dashoffset="0"/>
            <circle class="donut-pass" cx="55" cy="55" r="40" id="donutPass"
              stroke-dasharray="0 251.2" stroke-dashoffset="0"/>
          </svg>
          <div class="donut-center">
            <div class="donut-pct" id="donutPct">—</div>
            <div class="donut-sub">pass</div>
          </div>
        </div>
        <div class="donut-legend">
          <div class="donut-legend-item">
            <div class="donut-dot" style="background:var(--green)"></div>
            <span class="donut-legend-label">Passed</span>
            <span class="donut-legend-count" style="color:var(--green)" id="legendPassed">—</span>
          </div>
          <div class="donut-legend-item">
            <div class="donut-dot" style="background:var(--red)"></div>
            <span class="donut-legend-label">Failed</span>
            <span class="donut-legend-count" style="color:var(--red)" id="legendFailed">—</span>
          </div>
          <div class="donut-legend-item">
            <div class="donut-dot" style="background:var(--muted)"></div>
            <span class="donut-legend-label">Total</span>
            <span class="donut-legend-count" id="legendTotal">—</span>
          </div>
        </div>
      </div>

      <!-- Per-metric bar chart -->
      <div class="metric-chart-card">
        <div class="chart-title">Pass Rate per Metric</div>
        <div id="metricBarsContainer"></div>
      </div>
    </div>

    <!-- ── Metrics Overview Table ───────────────────────── -->
    <div id="metricsSection"></div>

    <!-- ── Toolbar ──────────────────────────────────────── -->
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" class="search-input" id="searchInput" placeholder="Search test cases…" oninput="applyFilter()"/>
      </div>
      <span class="filter-label">Show</span>
      <button class="filter-btn active" id="btn-all"  onclick="setFilter('all')">All</button>
      <button class="filter-btn" id="btn-pass" onclick="setFilter('pass')">Passed</button>
      <button class="filter-btn" id="btn-fail" onclick="setFilter('fail')">Failed</button>
      <span class="filter-count" id="filterCount"></span>
    </div>

    <!-- ── Results Table ─────────────────────────────────── -->
    <div class="results-card">
      <table class="results-table" id="resultsTable">
        <thead>
          <tr>
            <th style="width:84px">Status</th>
            <th>Test Case</th>
            <th style="width:160px">Score</th>
            <th>Metrics</th>
            <th style="width:36px"></th>
          </tr>
        </thead>
        <tbody id="resultsBody"></tbody>
      </table>
      <div class="empty-state" id="emptyState" style="display:none">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">No results match the current filter.</div>
      </div>
    </div>

  </div>

  <!-- ── Footer ────────────────────────────────────────────── -->
  <div class="footer">
    Generated by <a href="https://github.com/kareemrashed/rubric-eval" target="_blank">◈ Rubric</a>
    &nbsp;·&nbsp; The independent LLM &amp; agent evaluation framework
  </div>

  <script>
    const DATA = __DATA_JSON__;
    const summary = DATA.summary || {};
    const passRate = summary.pass_rate || 0;
    const PASS_RATE_PCT = Math.round(passRate * 1000) / 10;
    let currentFilter = 'all';
    let searchQuery = '';

    // ── Helpers ────────────────────────────────────────────────────────────────
    function escHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function scoreColor(s) {
      if (s >= 0.8) return 'var(--green)';
      if (s >= 0.5) return 'var(--yellow)';
      return 'var(--red)';
    }

    function fmtMs(ms) {
      if (ms === null || ms === undefined) return null;
      if (ms < 1000) return ms.toFixed(0) + 'ms';
      return (ms / 1000).toFixed(2) + 's';
    }

    function fmtJson(obj) {
      if (!obj || Object.keys(obj).length === 0) return '{}';
      return JSON.stringify(obj, null, 2);
    }

    // ── Header setup ───────────────────────────────────────────────────────────
    document.getElementById('statPassRate').textContent = PASS_RATE_PCT + '%';

    const rawDate = document.getElementById('headerDate').textContent;
    if (rawDate) {
      try {
        const d = new Date(rawDate);
        document.getElementById('headerDate').textContent =
          d.toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' }) +
          ' · ' + d.toLocaleTimeString(undefined, { hour:'2-digit', minute:'2-digit' });
      } catch(_) {}
    }

    const durEl = document.getElementById('headerDuration');
    if (durEl.textContent.trim()) durEl.style.display = '';

    // ── Donut Chart ────────────────────────────────────────────────────────────
    const total   = summary.total   || 0;
    const passed  = summary.passed  || 0;
    const failed  = summary.failed  || 0;
    const CIRC = 2 * Math.PI * 40; // circumference

    document.getElementById('legendPassed').textContent = passed;
    document.getElementById('legendFailed').textContent = failed;
    document.getElementById('legendTotal').textContent  = total;
    document.getElementById('donutPct').textContent = PASS_RATE_PCT + '%';

    setTimeout(() => {
      if (total > 0) {
        const passArc  = (passed / total) * CIRC;
        const failArc  = (failed / total) * CIRC;
        const passOffset = 0;
        const failOffset = -passArc;

        const passEl = document.getElementById('donutPass');
        const failEl = document.getElementById('donutFail');

        passEl.style.strokeDasharray  = passArc + ' ' + (CIRC - passArc);
        passEl.style.strokeDashoffset = '0';

        failEl.style.strokeDasharray  = failArc + ' ' + (CIRC - failArc);
        failEl.style.strokeDashoffset = -(passArc) + '';
      }
    }, 150);

    // ── Per-Metric bar chart ───────────────────────────────────────────────────
    const metricsData = DATA.metrics || {};
    const metricNames = Object.keys(metricsData);
    const barsContainer = document.getElementById('metricBarsContainer');

    if (metricNames.length === 0) {
      barsContainer.innerHTML = '<div class="no-data">No metrics data.</div>';
    } else {
      const bars = metricNames.map(name => {
        const m = metricsData[name];
        const pct = (m.pass_rate * 100).toFixed(1);
        const col = scoreColor(m.avg_score);
        return `<div class="metric-bar-row">
          <div class="metric-bar-name" title="${escHtml(name)}">${escHtml(name)}</div>
          <div class="metric-bar-track">
            <div class="metric-bar-fill" style="background:${col}" data-width="${m.pass_rate * 100}"></div>
          </div>
          <div class="metric-bar-pct" style="color:${col}">${pct}%</div>
        </div>`;
      }).join('');
      barsContainer.innerHTML = bars;

      setTimeout(() => {
        barsContainer.querySelectorAll('.metric-bar-fill').forEach(el => {
          el.style.width = el.dataset.width + '%';
        });
      }, 200);
    }

    // ── Metrics Overview Table ─────────────────────────────────────────────────
    const metricsSection = document.getElementById('metricsSection');
    if (metricNames.length > 0) {
      const rows = metricNames.map(name => {
        const m = metricsData[name];
        const pct = (m.pass_rate * 100).toFixed(1);
        const col = scoreColor(m.avg_score);
        return `<tr>
          <td><strong>${escHtml(name)}</strong></td>
          <td>
            <div class="mbar-wrap">
              <div class="mbar">
                <div class="mbar-fill" style="width:${m.pass_rate*100}%;background:${col}"></div>
              </div>
              <span style="color:${col};font-weight:700;font-size:0.8rem">${pct}%</span>
            </div>
          </td>
          <td style="font-variant-numeric:tabular-nums;font-weight:600;color:${col}">${m.avg_score.toFixed(3)}</td>
          <td style="color:var(--muted)">${m.total}</td>
        </tr>`;
      }).join('');

      metricsSection.innerHTML = `
        <div class="section-header">Metrics Overview</div>
        <div class="metrics-card">
          <table class="metrics-table">
            <thead><tr>
              <th>Metric</th><th>Pass Rate</th><th>Avg Score</th><th>Tests</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }

    // ── Results Table ──────────────────────────────────────────────────────────
    const tbody = document.getElementById('resultsBody');

    function buildTraceTree(trace) {
      if (!trace || trace.length === 0) {
        return '<div class="no-data">No trace steps recorded.</div>';
      }
      const ICONS = {
        thought: '🧠', tool_call: '🔧', observation: '👁', llm_call: '🤖'
      };
      const steps = trace.map((step, i) => {
        const typeClass = 'step-' + (step.type || 'default').replace(/[^a-z_]/g,'');
        const icon = ICONS[step.type] || '◦';
        const latencyStr = step.latency_ms != null ? fmtMs(step.latency_ms) : '';
        const contentPreview = step.content ? step.content.slice(0, 80) + (step.content.length > 80 ? '…' : '') : '';
        const metaEntries = step.metadata ? Object.entries(step.metadata) : [];
        const metaHtml = metaEntries.length > 0
          ? metaEntries.map(([k,v]) => `<span class="trace-meta-kv"><span class="trace-meta-key">${escHtml(k)}:</span><span class="trace-meta-val">${escHtml(String(v))}</span></span>`).join('')
          : '';

        return `<div class="trace-step ${typeClass}">
          <div class="trace-dot"></div>
          <div class="trace-card" id="tc-${i}">
            <div class="trace-card-header" onclick="toggleTrace(${i})">
              <span class="trace-step-num">#${i+1}</span>
              <span class="trace-type-badge">${icon} ${escHtml(step.type || 'step')}</span>
              <span style="font-size:0.78rem;color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-left:8px">${escHtml(contentPreview)}</span>
              ${latencyStr ? `<span class="trace-latency">${latencyStr}</span>` : ''}
              <span class="trace-expand">▼</span>
            </div>
            <div class="trace-card-body">
              <div class="trace-content">${escHtml(step.content || '')}</div>
              ${metaHtml ? `<div class="trace-meta">${metaHtml}</div>` : ''}
            </div>
          </div>
        </div>`;
      }).join('');
      return `<div class="trace-tree">${steps}</div>`;
    }

    function buildToolCalls(toolCalls) {
      if (!toolCalls || toolCalls.length === 0) {
        return '<div class="no-data">No tool calls recorded.</div>';
      }
      const cards = toolCalls.map((tc, i) => {
        const hasError = !!tc.error;
        const latencyStr = tc.latency_ms != null ? fmtMs(tc.latency_ms) : null;
        const argsJson = fmtJson(tc.arguments);
        const errorHtml = hasError
          ? `<div class="tool-section-label">Error</div><div class="tool-error">${escHtml(tc.error)}</div>`
          : '';
        const outputHtml = tc.output != null
          ? `<div class="tool-section-label" style="margin-top:10px">Output</div>
             <div class="tool-json">${escHtml(tc.output)}</div>`
          : '';
        return `<div class="tool-call-card ${hasError ? 'has-error' : ''}" id="tcc-${i}">
          <div class="tool-call-header" onclick="toggleToolCall(${i})">
            <span class="tool-call-name">${escHtml(tc.name)}()</span>
            ${latencyStr ? `<span class="tool-call-latency">${latencyStr}</span>` : ''}
            ${hasError ? '<span class="badge badge-fail" style="margin-left:4px">error</span>' : ''}
            <span class="tool-call-expand">▼</span>
          </div>
          <div class="tool-call-body">
            <div class="tool-section-label">Arguments</div>
            <div class="tool-json">${escHtml(argsJson)}</div>
            ${outputHtml}
            ${errorHtml}
          </div>
        </div>`;
      }).join('');
      return `<div class="tool-calls-list">${cards}</div>`;
    }

    DATA.results.forEach((result, idx) => {
      const color = scoreColor(result.overall_score);
      const badge = result.passed
        ? '<span class="badge badge-pass">✓ PASS</span>'
        : '<span class="badge badge-fail">✗ FAIL</span>';
      const agentBadge = result.is_agent
        ? '<span class="badge badge-agent" style="margin-left:4px">AGENT</span>'
        : '';

      const pills = result.metrics.map(m => {
        const cls = m.passed ? 'mpill-pass' : 'mpill-fail';
        return `<span class="mpill ${cls}">${escHtml(m.name)}</span>`;
      }).join('');

      const nameText = result.name || ('Test #' + (idx + 1));
      const subText  = result.name ? result.input : '';

      // ── Data row ──
      const dataRow = document.createElement('tr');
      dataRow.className = 'data-row';
      dataRow.dataset.idx    = idx;
      dataRow.dataset.passed = result.passed ? '1' : '0';
      dataRow.dataset.name   = (result.name || result.input || '').toLowerCase();
      dataRow.innerHTML = `
        <td>${badge}${agentBadge}</td>
        <td>
          <div class="test-name">${escHtml(nameText)}</div>
          ${subText ? `<div class="test-sub">${escHtml(subText)}</div>` : ''}
        </td>
        <td>
          <div class="score-cell">
            <div class="score-track">
              <div class="score-fill" style="width:${result.overall_score*100}%;background:${color}"></div>
            </div>
            <span class="score-num" style="color:${color}">${result.overall_score.toFixed(3)}</span>
          </div>
        </td>
        <td><div class="metric-pills">${pills}</div></td>
        <td><div class="expand-btn">▼</div></td>`;
      dataRow.onclick = () => toggleDetail(idx);
      tbody.appendChild(dataRow);

      // ── Build detail tabs ──
      const hasMeta = result.latency_ms != null || result.cost_usd != null || result.token_usage;
      const agentMetaHtml = result.is_agent ? buildAgentMeta(result) : '';
      const hasTrace = result.is_agent && result.trace && result.trace.length > 0;
      const hasTools = result.is_agent && result.tool_calls && result.tool_calls.length > 0;

      let tabs = `<div class="dtab active" onclick="switchTab(${idx},'io',this)">I/O</div>`;
      tabs += `<div class="dtab" onclick="switchTab(${idx},'metrics',this)">Metrics</div>`;
      if (hasTrace) tabs += `<div class="dtab" onclick="switchTab(${idx},'trace',this)">Trace (${result.trace.length})</div>`;
      if (hasTools) tabs += `<div class="dtab" onclick="switchTab(${idx},'tools',this)">Tool Calls (${result.tool_calls.length})</div>`;

      // Metric breakdown rows
      const breakdownRows = result.metrics.map(m => {
        const c = scoreColor(m.score);
        const hasReason = !!m.reason;
        return `<div class="breakdown-row ${hasReason ? 'has-reason' : ''}">
          <span class="bd-name">${escHtml(m.name)}</span>
          <div class="bd-bar"><div class="bd-bar-fill" style="width:${m.score*100}%;background:${c}"></div></div>
          <span class="bd-score" style="color:${c}">${m.score.toFixed(3)}</span>
          ${m.passed
            ? '<span class="badge badge-pass" style="font-size:0.62rem;padding:2px 7px">PASS</span>'
            : '<span class="badge badge-fail" style="font-size:0.62rem;padding:2px 7px">FAIL</span>'}
          ${hasReason ? `<div class="bd-reason">${escHtml(m.reason)}</div>` : ''}
        </div>`;
      }).join('');

      const expectedBox = result.expected_output != null
        ? `<div class="io-box">
             <div class="io-label">Expected</div>
             <div class="io-content">${escHtml(result.expected_output)}</div>
           </div>`
        : '';

      // ── Detail row ──
      const detailRow = document.createElement('tr');
      detailRow.className = 'detail-row';
      detailRow.dataset.idx    = idx;
      detailRow.dataset.passed = result.passed ? '1' : '0';
      detailRow.dataset.name   = dataRow.dataset.name;
      detailRow.innerHTML = `
        <td colspan="5">
          <div class="detail-inner" id="detail-${idx}">
            ${agentMetaHtml}
            <div class="detail-tabs" id="tabs-${idx}">${tabs}</div>

            <!-- I/O Panel -->
            <div class="dtab-panel active" id="panel-${idx}-io">
              <div class="io-grid">
                <div class="io-box">
                  <div class="io-label">Input</div>
                  <div class="io-content ${result.input ? '' : 'io-empty'}">${result.input ? escHtml(result.input) : '(none)'}</div>
                </div>
                <div class="io-box">
                  <div class="io-label">Actual Output</div>
                  <div class="io-content ${result.actual_output ? '' : 'io-empty'}">${result.actual_output ? escHtml(result.actual_output) : '(none)'}</div>
                </div>
                ${expectedBox}
              </div>
            </div>

            <!-- Metrics Panel -->
            <div class="dtab-panel" id="panel-${idx}-metrics">
              <div class="metric-breakdown">
                <div class="breakdown-header">Metric Breakdown</div>
                ${breakdownRows}
              </div>
            </div>

            <!-- Trace Panel -->
            ${hasTrace ? `<div class="dtab-panel" id="panel-${idx}-trace">${buildTraceTree(result.trace)}</div>` : ''}

            <!-- Tool Calls Panel -->
            ${hasTools ? `<div class="dtab-panel" id="panel-${idx}-tools">${buildToolCalls(result.tool_calls)}</div>` : ''}
          </div>
        </td>`;
      tbody.appendChild(detailRow);
    });

    function buildAgentMeta(result) {
      const chips = [];
      if (result.latency_ms != null) {
        chips.push(`<div class="agent-chip"><span class="agent-chip-icon">⏱</span><span class="agent-chip-label">Latency</span><span class="agent-chip-value">${fmtMs(result.latency_ms)}</span></div>`);
      }
      if (result.cost_usd != null) {
        chips.push(`<div class="agent-chip"><span class="agent-chip-icon">💵</span><span class="agent-chip-label">Cost</span><span class="agent-chip-value">$${result.cost_usd.toFixed(5)}</span></div>`);
      }
      if (result.token_usage) {
        const t = result.token_usage;
        const parts = [];
        if (t.input  != null) parts.push(`in: ${t.input}`);
        if (t.output != null) parts.push(`out: ${t.output}`);
        if (parts.length)
          chips.push(`<div class="agent-chip"><span class="agent-chip-icon">🔢</span><span class="agent-chip-label">Tokens</span><span class="agent-chip-value">${parts.join(' / ')}</span></div>`);
      }
      if (result.trace && result.trace.length > 0) {
        chips.push(`<div class="agent-chip"><span class="agent-chip-icon">📋</span><span class="agent-chip-label">Steps</span><span class="agent-chip-value">${result.trace.length}</span></div>`);
      }
      if (result.tool_calls && result.tool_calls.length > 0) {
        chips.push(`<div class="agent-chip"><span class="agent-chip-icon">🔧</span><span class="agent-chip-label">Tool Calls</span><span class="agent-chip-value">${result.tool_calls.length}</span></div>`);
      }
      if (result.expected_tools && result.expected_tools.length > 0) {
        chips.push(`<div class="agent-chip"><span class="agent-chip-icon">✅</span><span class="agent-chip-label">Expected Tools</span><span class="agent-chip-value">${result.expected_tools.join(', ')}</span></div>`);
      }
      return chips.length > 0 ? `<div class="agent-strip">${chips.join('')}</div>` : '';
    }

    // ── Tab switching ──────────────────────────────────────────────────────────
    function switchTab(idx, panelName, tabEl) {
      const detail = document.getElementById('detail-' + idx);
      detail.querySelectorAll('.dtab-panel').forEach(p => p.classList.remove('active'));
      detail.querySelectorAll('.dtab').forEach(t => t.classList.remove('active'));
      const panel = document.getElementById(`panel-${idx}-${panelName}`);
      if (panel) panel.classList.add('active');
      if (tabEl) tabEl.classList.add('active');
    }

    // ── Row expand/collapse ────────────────────────────────────────────────────
    function toggleDetail(idx) {
      const inner = document.getElementById('detail-' + idx);
      const dataRow = tbody.querySelector('.data-row[data-idx="' + idx + '"]');
      const isOpen = inner.classList.contains('open');
      inner.classList.toggle('open', !isOpen);
      dataRow.classList.toggle('is-expanded', !isOpen);
    }

    // ── Trace card expand ──────────────────────────────────────────────────────
    function toggleTrace(i) {
      const card = document.getElementById('tc-' + i);
      if (card) card.classList.toggle('expanded');
    }

    // ── Tool call expand ───────────────────────────────────────────────────────
    function toggleToolCall(i) {
      const card = document.getElementById('tcc-' + i);
      if (card) card.classList.toggle('expanded');
    }

    // ── Filter & Search ────────────────────────────────────────────────────────
    function setFilter(f) {
      currentFilter = f;
      ['all','pass','fail'].forEach(id => {
        const btn = document.getElementById('btn-' + id);
        if (id === f) {
          btn.className = 'filter-btn' + (id === 'pass' ? ' active-pass' : id === 'fail' ? ' active-fail' : ' active');
        } else {
          btn.className = 'filter-btn';
        }
      });
      applyFilter();
    }

    function applyFilter() {
      searchQuery = document.getElementById('searchInput').value.toLowerCase();
      const dataRows   = tbody.querySelectorAll('.data-row');
      const detailRows = tbody.querySelectorAll('.detail-row');
      let visible = 0;

      dataRows.forEach((row, i) => {
        const passed = row.dataset.passed === '1';
        const name   = row.dataset.name || '';
        const matchFilter = currentFilter === 'all'
          || (currentFilter === 'pass' && passed)
          || (currentFilter === 'fail' && !passed);
        const matchSearch = !searchQuery || name.includes(searchQuery);
        const show = matchFilter && matchSearch;
        row.style.display = show ? '' : 'none';
        if (detailRows[i]) detailRows[i].style.display = show ? '' : 'none';
        if (show) visible++;
      });

      const total = dataRows.length;
      document.getElementById('filterCount').textContent =
        (currentFilter === 'all' && !searchQuery) ? `${total} tests` : `${visible} of ${total} tests`;
      document.getElementById('emptyState').style.display = visible === 0 ? 'block' : 'none';
    }

    // Init
    applyFilter();
  </script>
</body>
</html>"""
