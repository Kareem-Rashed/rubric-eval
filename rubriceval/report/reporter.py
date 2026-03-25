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

    html = _HTML_TEMPLATE.replace("{{DATA_JSON}}", data_json)
    html = html.replace("{{PASS_RATE}}", f"{report.pass_rate * 100:.1f}")
    html = html.replace("{{TOTAL}}", str(report.total))
    html = html.replace("{{PASSED}}", str(report.passed))
    html = html.replace("{{FAILED}}", str(report.failed))
    html = html.replace("{{AVG_SCORE}}", f"{report.avg_score:.3f}")
    html = html.replace("{{STARTED_AT}}", report.started_at or "")
    html = html.replace("{{RUN_NAME}}", report.metadata.get("run_name", "Rubric Eval"))

    Path(output_path).write_text(html, encoding="utf-8")


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rubric — {{RUN_NAME}}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0c0c10;
      --surface:   #13131a;
      --surface2:  #1a1a24;
      --border:    #252535;
      --border2:   #1e1e2c;
      --text:      #e2e2ea;
      --muted:     #72728a;
      --accent:    #7c6fff;
      --accent2:   #4ecdc4;
      --green:     #34d399;
      --yellow:    #fbbf24;
      --red:       #f87171;
      --radius:    10px;
      --radius-lg: 16px;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      font-size: 14px;
      line-height: 1.6;
    }

    /* ── Header ── */
    .header {
      background: linear-gradient(135deg, #1a1040 0%, #0e2a2a 100%);
      border-bottom: 1px solid var(--border);
      padding: 36px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }
    .header-left {}
    .header-logo {
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header-subtitle {
      color: var(--muted);
      font-size: 0.82rem;
      margin-top: 4px;
      letter-spacing: 0.3px;
    }
    .header-meta {
      text-align: right;
    }
    .header-run-name {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text);
    }
    .header-date {
      font-size: 0.78rem;
      color: var(--muted);
      margin-top: 3px;
    }

    /* ── Layout ── */
    .main { max-width: 1200px; margin: 0 auto; padding: 32px 48px 64px; }

    /* ── Stat Cards ── */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 20px 24px;
      position: relative;
      overflow: hidden;
    }
    .stat-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }
    .stat-card.pass-rate::before  { background: linear-gradient(90deg, var(--accent), var(--accent2)); }
    .stat-card.score::before      { background: var(--accent); }
    .stat-card.passed::before     { background: var(--green); }
    .stat-card.failed::before     { background: var(--red); }
    .stat-card.total::before      { background: var(--muted); }
    .stat-value {
      font-size: 2rem;
      font-weight: 700;
      line-height: 1;
      margin-bottom: 6px;
    }
    .stat-card.pass-rate .stat-value { color: var(--accent2); }
    .stat-card.score .stat-value     { color: var(--accent); }
    .stat-card.passed .stat-value    { color: var(--green); }
    .stat-card.failed .stat-value    { color: var(--red); }
    .stat-card.total .stat-value     { color: var(--text); }
    .stat-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--muted);
    }

    /* ── Progress bar ── */
    .pass-progress {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .pass-progress-label {
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      white-space: nowrap;
    }
    .pass-progress-bar {
      flex: 1;
      height: 8px;
      background: var(--border);
      border-radius: 4px;
      overflow: hidden;
    }
    .pass-progress-fill {
      height: 100%;
      border-radius: 4px;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
      width: 0%;
    }
    .pass-progress-pct {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--accent2);
      min-width: 44px;
      text-align: right;
    }

    /* ── Section headers ── */
    .section-header {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--muted);
      margin-bottom: 12px;
      margin-top: 32px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .section-header::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }

    /* ── Metrics Overview ── */
    .metrics-overview {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      overflow: hidden;
    }
    .metrics-table { width: 100%; border-collapse: collapse; }
    .metrics-table th {
      background: var(--surface2);
      color: var(--muted);
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    .metrics-table td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border2);
      font-size: 0.85rem;
    }
    .metrics-table tr:last-child td { border-bottom: none; }
    .metrics-table tr:hover td { background: var(--surface2); }
    .metric-pass-bar-outer {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .metric-pass-bar {
      flex: 1;
      height: 5px;
      background: var(--border);
      border-radius: 3px;
      overflow: hidden;
      max-width: 200px;
    }
    .metric-pass-bar-fill {
      height: 100%;
      border-radius: 3px;
    }

    /* ── Filter bar ── */
    .filter-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      margin-top: 32px;
    }
    .filter-label {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--muted);
      margin-right: 4px;
    }
    .filter-btn {
      padding: 5px 14px;
      border-radius: 20px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .filter-btn:hover { border-color: var(--accent); color: var(--text); }
    .filter-btn.active { background: var(--accent); border-color: var(--accent); color: white; }
    .filter-btn.active-pass { background: rgba(52,211,153,0.15); border-color: var(--green); color: var(--green); }
    .filter-btn.active-fail { background: rgba(248,113,113,0.15); border-color: var(--red); color: var(--red); }
    .filter-count {
      margin-left: auto;
      font-size: 0.78rem;
      color: var(--muted);
    }

    /* ── Results table ── */
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
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    .results-table .data-row td {
      padding: 13px 16px;
      border-bottom: 1px solid var(--border2);
      vertical-align: middle;
    }
    .results-table .data-row:hover td { background: var(--surface2); cursor: pointer; }
    .results-table .data-row.is-expanded td { background: var(--surface2); }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .badge-pass { background: rgba(52,211,153,0.12); color: var(--green); border: 1px solid rgba(52,211,153,0.25); }
    .badge-fail { background: rgba(248,113,113,0.12); color: var(--red); border: 1px solid rgba(248,113,113,0.25); }

    .test-name {
      font-weight: 500;
      color: var(--text);
      max-width: 320px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .test-name-sub {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 2px;
      max-width: 320px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .score-cell {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 130px;
    }
    .score-bar-track {
      flex: 1;
      height: 5px;
      background: var(--border);
      border-radius: 3px;
      overflow: hidden;
    }
    .score-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
    .score-num {
      font-weight: 700;
      font-size: 0.85rem;
      min-width: 40px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    .metric-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }
    .metric-pill {
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .metric-pill-pass { background: rgba(52,211,153,0.1); color: var(--green); }
    .metric-pill-fail { background: rgba(248,113,113,0.1); color: var(--red); }

    .expand-icon {
      font-size: 0.65rem;
      color: var(--muted);
      transition: transform 0.2s;
      user-select: none;
    }
    .is-expanded .expand-icon { transform: rotate(180deg); }

    /* ── Detail row ── */
    .detail-row td { padding: 0 !important; border-bottom: 1px solid var(--border) !important; }
    .detail-inner {
      display: none;
      padding: 20px;
      background: #0f0f16;
    }
    .detail-inner.open { display: block; }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .io-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px;
    }
    .io-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .io-content {
      font-size: 0.82rem;
      color: #c9c9d8;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 200px;
      overflow-y: auto;
      line-height: 1.5;
    }
    .io-content::-webkit-scrollbar { width: 4px; }
    .io-content::-webkit-scrollbar-track { background: transparent; }
    .io-content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

    .metric-breakdown {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .metric-breakdown-header {
      padding: 10px 14px;
      background: var(--surface2);
      border-bottom: 1px solid var(--border);
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--muted);
    }
    .metric-breakdown-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border2);
      font-size: 0.82rem;
    }
    .metric-breakdown-row:last-child { border-bottom: none; }
    .metric-breakdown-name { flex: 1; color: var(--text); }
    .metric-breakdown-bar {
      width: 80px;
      height: 4px;
      background: var(--border);
      border-radius: 2px;
      overflow: hidden;
    }
    .metric-breakdown-bar-fill { height: 100%; border-radius: 2px; }
    .metric-breakdown-score {
      font-weight: 700;
      font-size: 0.82rem;
      min-width: 38px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .metric-breakdown-reason {
      font-size: 0.75rem;
      color: var(--muted);
      font-style: italic;
      padding: 0 14px 8px;
      margin-top: -4px;
    }

    /* ── Footer ── */
    .footer {
      text-align: center;
      padding: 40px 48px 32px;
      color: var(--muted);
      font-size: 0.78rem;
      border-top: 1px solid var(--border);
    }
    .footer a { color: var(--accent); text-decoration: none; }
    .footer a:hover { text-decoration: underline; }

    /* ── Empty state ── */
    .empty-state {
      text-align: center;
      padding: 48px 24px;
      color: var(--muted);
    }
    .empty-state-icon { font-size: 2rem; margin-bottom: 8px; }
    .empty-state-text { font-size: 0.9rem; }
  </style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <div class="header-logo">◈ Rubric</div>
      <div class="header-subtitle">Independent LLM &amp; Agent Evaluation Framework</div>
    </div>
    <div class="header-meta">
      <div class="header-run-name">{{RUN_NAME}}</div>
      <div class="header-date" id="headerDate">{{STARTED_AT}}</div>
    </div>
  </div>

  <div class="main">

    <!-- Stat Cards -->
    <div class="stats-grid">
      <div class="stat-card pass-rate">
        <div class="stat-value">{{PASS_RATE}}%</div>
        <div class="stat-label">Pass Rate</div>
      </div>
      <div class="stat-card score">
        <div class="stat-value">{{AVG_SCORE}}</div>
        <div class="stat-label">Avg Score</div>
      </div>
      <div class="stat-card passed">
        <div class="stat-value">{{PASSED}}</div>
        <div class="stat-label">Passed</div>
      </div>
      <div class="stat-card failed">
        <div class="stat-value">{{FAILED}}</div>
        <div class="stat-label">Failed</div>
      </div>
      <div class="stat-card total">
        <div class="stat-value">{{TOTAL}}</div>
        <div class="stat-label">Total Tests</div>
      </div>
    </div>

    <!-- Pass Rate Progress -->
    <div class="pass-progress">
      <span class="pass-progress-label">Pass Rate</span>
      <div class="pass-progress-bar">
        <div class="pass-progress-fill" id="progressFill"></div>
      </div>
      <span class="pass-progress-pct">{{PASS_RATE}}%</span>
    </div>

    <!-- Metrics Overview -->
    <div id="metricsSection"></div>

    <!-- Filter + Results -->
    <div class="filter-bar" id="filterBar">
      <span class="filter-label">Show</span>
      <button class="filter-btn active" id="btn-all" onclick="setFilter('all')">All</button>
      <button class="filter-btn" id="btn-pass" onclick="setFilter('pass')">Passed</button>
      <button class="filter-btn" id="btn-fail" onclick="setFilter('fail')">Failed</button>
      <span class="filter-count" id="filterCount"></span>
    </div>

    <div class="results-card">
      <table class="results-table" id="resultsTable">
        <thead>
          <tr>
            <th style="width:80px">Status</th>
            <th>Test Case</th>
            <th style="width:160px">Score</th>
            <th>Metrics</th>
            <th style="width:28px"></th>
          </tr>
        </thead>
        <tbody id="resultsBody"></tbody>
      </table>
      <div class="empty-state" id="emptyState" style="display:none">
        <div class="empty-state-icon">🔍</div>
        <div class="empty-state-text">No results match the current filter.</div>
      </div>
    </div>

  </div>

  <div class="footer">
    Generated by <a href="https://github.com/kareemrashed/rubric-eval" target="_blank">Rubric</a>
    &nbsp;·&nbsp; The independent LLM evaluation framework
  </div>

  <script>
    const DATA = {{DATA_JSON}};
    const PASS_RATE = {{PASS_RATE}};
    let currentFilter = 'all';

    // Animate progress bar
    setTimeout(() => {
      document.getElementById('progressFill').style.width = PASS_RATE + '%';
    }, 100);

    // Format date nicely
    const rawDate = document.getElementById('headerDate').textContent;
    if (rawDate) {
      try {
        const d = new Date(rawDate);
        document.getElementById('headerDate').textContent =
          d.toLocaleDateString(undefined, { year:'numeric', month:'long', day:'numeric' }) +
          ' · ' + d.toLocaleTimeString(undefined, { hour:'2-digit', minute:'2-digit' });
      } catch(_) {}
    }

    function scoreColor(s) {
      if (s >= 0.8) return 'var(--green)';
      if (s >= 0.5) return 'var(--yellow)';
      return 'var(--red)';
    }

    function escHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    // ── Metrics Overview ──────────────────────────────────────────────────────
    const metricsSection = document.getElementById('metricsSection');
    const metricsData = DATA.metrics || {};
    const metricNames = Object.keys(metricsData);

    if (metricNames.length > 0) {
      let rows = metricNames.map(name => {
        const m = metricsData[name];
        const pct = (m.pass_rate * 100).toFixed(1);
        const color = scoreColor(m.avg_score);
        return `
          <tr>
            <td><strong>${escHtml(name)}</strong></td>
            <td>
              <div class="metric-pass-bar-outer">
                <div class="metric-pass-bar">
                  <div class="metric-pass-bar-fill" style="width:${m.pass_rate*100}%; background:${color};"></div>
                </div>
                <span style="color:${color}; font-weight:700; font-size:0.82rem;">${pct}%</span>
              </div>
            </td>
            <td style="font-variant-numeric:tabular-nums; font-weight:600; color:${scoreColor(m.avg_score)}">
              ${m.avg_score.toFixed(3)}
            </td>
            <td style="color:var(--muted)">${m.total}</td>
          </tr>`;
      }).join('');

      metricsSection.innerHTML = `
        <div class="section-header">Metrics Overview</div>
        <div class="metrics-overview">
          <table class="metrics-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Pass Rate</th>
                <th>Avg Score</th>
                <th>Tests</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }

    // ── Results Table ─────────────────────────────────────────────────────────
    const tbody = document.getElementById('resultsBody');

    DATA.results.forEach((result, idx) => {
      const color = scoreColor(result.overall_score);
      const badge = result.passed
        ? '<span class="badge badge-pass">✓ PASS</span>'
        : '<span class="badge badge-fail">✗ FAIL</span>';

      const pills = result.metrics.map(m => {
        const cls = m.passed ? 'metric-pill-pass' : 'metric-pill-fail';
        return `<span class="metric-pill ${cls}">${escHtml(m.name)}</span>`;
      }).join('');

      const nameText = result.name || ('Test #' + (idx + 1));
      const subText = result.name ? escHtml(result.input) : '';

      // Main data row
      const dataRow = document.createElement('tr');
      dataRow.className = 'data-row';
      dataRow.dataset.idx = idx;
      dataRow.dataset.passed = result.passed ? '1' : '0';
      dataRow.innerHTML = `
        <td>${badge}</td>
        <td>
          <div class="test-name">${escHtml(nameText)}</div>
          ${subText ? `<div class="test-name-sub">${subText}</div>` : ''}
        </td>
        <td>
          <div class="score-cell">
            <div class="score-bar-track">
              <div class="score-bar-fill" style="width:${result.overall_score*100}%; background:${color};"></div>
            </div>
            <span class="score-num" style="color:${color}">${result.overall_score.toFixed(3)}</span>
          </div>
        </td>
        <td><div class="metric-pills">${pills}</div></td>
        <td><span class="expand-icon">▼</span></td>
      `;
      dataRow.onclick = () => toggleDetail(idx);
      tbody.appendChild(dataRow);

      // Build metric breakdown HTML
      const metricBreakdownRows = result.metrics.map(m => {
        const c = scoreColor(m.score);
        const reasonHtml = m.reason
          ? `<div class="metric-breakdown-reason">${escHtml(m.reason)}</div>`
          : '';
        return `
          <div class="metric-breakdown-row">
            <span class="metric-breakdown-name">${escHtml(m.name)}</span>
            <div class="metric-breakdown-bar">
              <div class="metric-breakdown-bar-fill" style="width:${m.score*100}%; background:${c};"></div>
            </div>
            <span class="metric-breakdown-score" style="color:${c}">${m.score.toFixed(3)}</span>
            ${m.passed
              ? '<span class="badge badge-pass" style="font-size:0.65rem; padding:1px 7px;">PASS</span>'
              : '<span class="badge badge-fail" style="font-size:0.65rem; padding:1px 7px;">FAIL</span>'}
          </div>
          ${reasonHtml}`;
      }).join('');

      // IO boxes
      const expectedHtml = result.expected_output
        ? `<div class="io-box">
             <div class="io-label">Expected Output</div>
             <div class="io-content">${escHtml(result.expected_output)}</div>
           </div>`
        : '';

      // Detail row
      const detailRow = document.createElement('tr');
      detailRow.className = 'detail-row';
      detailRow.dataset.idx = idx;
      detailRow.dataset.passed = result.passed ? '1' : '0';
      detailRow.innerHTML = `
        <td colspan="5">
          <div class="detail-inner" id="detail-${idx}">
            <div class="detail-grid">
              <div class="io-box">
                <div class="io-label">Input</div>
                <div class="io-content">${escHtml(result.input)}</div>
              </div>
              <div class="io-box">
                <div class="io-label">Actual Output</div>
                <div class="io-content">${escHtml(result.actual_output)}</div>
              </div>
              ${expectedHtml}
            </div>
            <div class="metric-breakdown">
              <div class="metric-breakdown-header">Metric Breakdown</div>
              ${metricBreakdownRows}
            </div>
          </div>
        </td>`;
      tbody.appendChild(detailRow);
    });

    function toggleDetail(idx) {
      const inner = document.getElementById('detail-' + idx);
      const dataRow = tbody.querySelector('.data-row[data-idx="' + idx + '"]');
      const isOpen = inner.classList.contains('open');
      inner.classList.toggle('open', !isOpen);
      dataRow.classList.toggle('is-expanded', !isOpen);
    }

    // ── Filter ────────────────────────────────────────────────────────────────
    function setFilter(f) {
      currentFilter = f;
      ['all','pass','fail'].forEach(id => {
        const btn = document.getElementById('btn-' + id);
        btn.className = 'filter-btn' + (id === f ? (
          id === 'pass' ? ' active-pass' : id === 'fail' ? ' active-fail' : ' active'
        ) : '');
      });
      applyFilter();
    }

    function applyFilter() {
      const dataRows = tbody.querySelectorAll('.data-row');
      const detailRows = tbody.querySelectorAll('.detail-row');
      let visible = 0;

      dataRows.forEach((row, i) => {
        const passed = row.dataset.passed === '1';
        const show = currentFilter === 'all'
          || (currentFilter === 'pass' && passed)
          || (currentFilter === 'fail' && !passed);
        row.style.display = show ? '' : 'none';
        if (detailRows[i]) detailRows[i].style.display = show ? '' : 'none';
        if (show) visible++;
      });

      const total = dataRows.length;
      document.getElementById('filterCount').textContent =
        currentFilter === 'all' ? `${total} tests` : `${visible} of ${total} tests`;
      document.getElementById('emptyState').style.display = visible === 0 ? 'block' : 'none';
    }

    // Init filter count
    applyFilter();

  </script>
</body>
</html>"""
