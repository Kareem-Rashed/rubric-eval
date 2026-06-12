"""
Regression diffing between two Rubric JSON reports.

Powers `rubric compare` and the Rubric GitHub Action: compare the current
eval run against a baseline (e.g. from main) and render a PR-comment-ready
markdown diff — which tests regressed, which metrics dropped, and why.

Usage:
    rubric compare current.json --baseline evals/baseline.json
    rubric compare current.json --baseline evals/baseline.json --output-md comment.md
    rubric compare current.json --baseline evals/baseline.json --fail-on-regression
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

# Marker the GitHub Action uses to find and update its own PR comment.
COMMENT_MARKER = "<!-- rubric-eval-report -->"


@dataclass
class MetricDelta:
    """Score change for one metric within one test."""

    name: str
    baseline_score: Optional[float]
    current_score: float
    reason: Optional[str] = None  # current failure reason, if any


@dataclass
class TestDelta:
    """How a single test changed between baseline and current."""

    name: str
    status: str  # "regressed" | "fixed" | "score_drop" | "new" | "removed" | "unchanged"
    baseline_passed: Optional[bool] = None
    current_passed: Optional[bool] = None
    baseline_score: Optional[float] = None
    current_score: Optional[float] = None
    metric_deltas: list[MetricDelta] = field(default_factory=list)


@dataclass
class ReportDiff:
    """Full diff between two reports (or a summary of one, if no baseline)."""

    current_summary: dict
    baseline_summary: Optional[dict] = None
    regressed: list[TestDelta] = field(default_factory=list)
    fixed: list[TestDelta] = field(default_factory=list)
    score_drops: list[TestDelta] = field(default_factory=list)
    new_tests: list[TestDelta] = field(default_factory=list)
    removed_tests: list[TestDelta] = field(default_factory=list)
    unchanged: int = 0
    current_failures: list[dict] = field(default_factory=list)  # used when no baseline

    @property
    def has_baseline(self) -> bool:
        return self.baseline_summary is not None

    @property
    def has_regressions(self) -> bool:
        return bool(self.regressed)


def load_report(path: str) -> dict:
    """Load a Rubric JSON report written by evaluate(output_json=...)."""
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    if "summary" not in report or "results" not in report:
        raise ValueError(
            f"{path} doesn't look like a Rubric report — expected 'summary' and "
            "'results' keys. Generate one with: rubric run evals.py --output-json report.json"
        )
    return report


def _metric_deltas(baseline_result: Optional[dict], current_result: dict,
                   only_changed: bool = True) -> list[MetricDelta]:
    baseline_metrics = {}
    if baseline_result:
        baseline_metrics = {m["name"]: m for m in baseline_result.get("metrics", [])
                            if not m.get("skipped")}
    deltas = []
    for m in current_result.get("metrics", []):
        if m.get("skipped"):
            continue
        base = baseline_metrics.get(m["name"])
        base_score = base["score"] if base else None
        changed = base_score is None or abs(m["score"] - base_score) > 1e-9
        if only_changed and not changed:
            continue
        deltas.append(MetricDelta(
            name=m["name"],
            baseline_score=base_score,
            current_score=m["score"],
            reason=m.get("reason") if not m.get("passed") else None,
        ))
    return deltas


def diff_reports(
    baseline: Optional[dict],
    current: dict,
    *,
    score_drop_threshold: float = 0.1,
) -> ReportDiff:
    """
    Compare two Rubric reports. Tests are matched by name.

    Classification per test:
        regressed  — passed in baseline, fails now
        fixed      — failed in baseline, passes now
        score_drop — passes in both, but score fell by more than score_drop_threshold
        new        — only in current
        removed    — only in baseline
    """
    diff = ReportDiff(current_summary=current["summary"])

    if baseline is None:
        diff.current_failures = [r for r in current["results"] if not r["passed"]]
        return diff

    diff.baseline_summary = baseline["summary"]
    baseline_by_name = {r["name"]: r for r in baseline["results"]}
    current_by_name = {r["name"]: r for r in current["results"]}

    for name, cur in current_by_name.items():
        base = baseline_by_name.get(name)
        if base is None:
            diff.new_tests.append(TestDelta(
                name=name, status="new",
                current_passed=cur["passed"], current_score=cur["overall_score"],
                metric_deltas=_metric_deltas(None, cur) if not cur["passed"] else [],
            ))
            continue

        delta = TestDelta(
            name=name,
            status="unchanged",
            baseline_passed=base["passed"],
            current_passed=cur["passed"],
            baseline_score=base["overall_score"],
            current_score=cur["overall_score"],
        )
        if base["passed"] and not cur["passed"]:
            delta.status = "regressed"
            delta.metric_deltas = _metric_deltas(base, cur)
            diff.regressed.append(delta)
        elif not base["passed"] and cur["passed"]:
            delta.status = "fixed"
            diff.fixed.append(delta)
        elif (base["passed"] and cur["passed"]
              and base["overall_score"] - cur["overall_score"] > score_drop_threshold):
            delta.status = "score_drop"
            delta.metric_deltas = _metric_deltas(base, cur)
            diff.score_drops.append(delta)
        else:
            diff.unchanged += 1

    for name, base in baseline_by_name.items():
        if name not in current_by_name:
            diff.removed_tests.append(TestDelta(
                name=name, status="removed",
                baseline_passed=base["passed"], baseline_score=base["overall_score"],
            ))

    return diff


# ── Rendering ──────────────────────────────────────────────────────────────────

def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _arrow(before: float, after: float) -> str:
    if after > before:
        return "🟢 +" + f"{after - before:.2f}".lstrip("+")
    if after < before:
        return f"🔻 -{before - after:.2f}"
    return "—"


def _fmt_metric_line(md: MetricDelta) -> str:
    if md.baseline_score is None:
        line = f"`{md.name}`: {md.current_score:.2f}"
    else:
        line = f"`{md.name}`: {md.baseline_score:.2f} → {md.current_score:.2f}"
    if md.reason:
        reason = md.reason.split("\n")[0][:160]
        line += f" — {reason}"
    return line


def render_markdown(diff: ReportDiff, *, title: str = "Rubric eval") -> str:
    """Render a PR-comment-ready markdown diff (starts with COMMENT_MARKER)."""
    cur = diff.current_summary
    lines = [COMMENT_MARKER]

    if not diff.has_baseline:
        status = "✅ all passing" if cur["failed"] == 0 else f"❌ {cur['failed']} failing"
        lines += [
            f"## 🧪 {title} — {status}",
            "",
            f"**{cur['passed']}/{cur['total']} passed** · pass rate {_pct(cur['pass_rate'])} "
            f"· avg score {cur['avg_score']:.2f}",
            "",
            "_No baseline found — this run's report can serve as your baseline. "
            "Commit it (e.g. as `evals/baseline.json`) to get regression diffs on future PRs._",
        ]
        for r in diff.current_failures:
            lines.append(f"- ❌ **{r['name']}** (score {r['overall_score']:.2f})")
            for m in r.get("metrics", []):
                if not m.get("passed") and not m.get("skipped"):
                    reason = (m.get("reason") or "").split("\n")[0][:160]
                    lines.append(f"  - `{m['name']}`: {m['score']:.2f}" + (f" — {reason}" if reason else ""))
        return "\n".join(lines) + "\n"

    base = diff.baseline_summary
    if diff.has_regressions:
        headline = f"🔻 {len(diff.regressed)} regression{'s' if len(diff.regressed) != 1 else ''}"
    elif diff.score_drops:
        headline = f"⚠️ {len(diff.score_drops)} score drop{'s' if len(diff.score_drops) != 1 else ''}"
    else:
        headline = "✅ no regressions"

    lines += [
        f"## 🧪 {title} — {headline}",
        "",
        "| | Baseline | Current | Δ |",
        "|---|---|---|---|",
        f"| Pass rate | {_pct(base['pass_rate'])} ({base['passed']}/{base['total']}) "
        f"| {_pct(cur['pass_rate'])} ({cur['passed']}/{cur['total']}) "
        f"| {_arrow(base['pass_rate'], cur['pass_rate'])} |",
        f"| Avg score | {base['avg_score']:.2f} | {cur['avg_score']:.2f} "
        f"| {_arrow(base['avg_score'], cur['avg_score'])} |",
    ]

    if diff.regressed:
        lines += ["", f"### 🔻 Regressions ({len(diff.regressed)})"]
        for t in diff.regressed:
            lines.append(f"- **{t.name}** — pass → **fail** "
                         f"(score {t.baseline_score:.2f} → {t.current_score:.2f})")
            for md in t.metric_deltas:
                lines.append(f"  - {_fmt_metric_line(md)}")

    if diff.score_drops:
        lines += ["", f"### ⚠️ Score drops ({len(diff.score_drops)}) — still passing, worth a look"]
        for t in diff.score_drops:
            lines.append(f"- **{t.name}** — score {t.baseline_score:.2f} → {t.current_score:.2f}")
            for md in t.metric_deltas:
                lines.append(f"  - {_fmt_metric_line(md)}")

    if diff.fixed:
        lines += ["", f"### ✅ Fixed ({len(diff.fixed)})"]
        for t in diff.fixed:
            lines.append(f"- **{t.name}** — fail → **pass** "
                         f"(score {t.baseline_score:.2f} → {t.current_score:.2f})")

    if diff.new_tests:
        failing_new = [t for t in diff.new_tests if not t.current_passed]
        lines += ["", f"### 🆕 New tests ({len(diff.new_tests)}"
                      + (f", {len(failing_new)} failing)" if failing_new else ")")]
        for t in diff.new_tests:
            icon = "✅" if t.current_passed else "❌"
            lines.append(f"- {icon} **{t.name}** (score {t.current_score:.2f})")
            for md in t.metric_deltas:
                lines.append(f"  - {_fmt_metric_line(md)}")

    if diff.removed_tests:
        lines += ["", f"### 🗑 Removed tests ({len(diff.removed_tests)})"]
        for t in diff.removed_tests:
            lines.append(f"- {t.name}")

    lines += ["", f"<sub>{diff.unchanged} unchanged · generated by "
                  "[Rubric](https://github.com/Kareem-Rashed/rubric-eval)</sub>"]
    return "\n".join(lines) + "\n"


def render_terminal(diff: ReportDiff) -> str:
    """Render a compact human-readable diff for the terminal."""
    cur = diff.current_summary
    out = ["", "=" * 60, "  RUBRIC REGRESSION DIFF", "=" * 60]

    if not diff.has_baseline:
        out += [
            f"  Current: {cur['passed']}/{cur['total']} passed "
            f"({_pct(cur['pass_rate'])}, avg {cur['avg_score']:.2f})",
            "  ⚠️  No baseline — nothing to compare against.",
            "  Save this run as your baseline to enable regression detection.",
            "=" * 60, "",
        ]
        return "\n".join(out)

    base = diff.baseline_summary
    out += [
        f"  Baseline: {base['passed']}/{base['total']} passed ({_pct(base['pass_rate'])})",
        f"  Current:  {cur['passed']}/{cur['total']} passed ({_pct(cur['pass_rate'])})",
        "",
    ]
    if diff.regressed:
        out.append(f"  🔻 Regressions ({len(diff.regressed)}):")
        for t in diff.regressed:
            out.append(f"     ❌ {t.name}  ({t.baseline_score:.2f} → {t.current_score:.2f})")
            for md in t.metric_deltas:
                out.append(f"        {_fmt_metric_line(md).replace('`', '')}")
    if diff.score_drops:
        out.append(f"  ⚠️  Score drops ({len(diff.score_drops)}):")
        for t in diff.score_drops:
            out.append(f"     {t.name}  ({t.baseline_score:.2f} → {t.current_score:.2f})")
    if diff.fixed:
        out.append(f"  ✅ Fixed ({len(diff.fixed)}):")
        for t in diff.fixed:
            out.append(f"     {t.name}")
    if diff.new_tests:
        out.append(f"  🆕 New: {len(diff.new_tests)}")
    if diff.removed_tests:
        out.append(f"  🗑  Removed: {len(diff.removed_tests)}")
    if not (diff.regressed or diff.score_drops or diff.fixed
            or diff.new_tests or diff.removed_tests):
        out.append("  ✅ No changes — all tests match the baseline.")
    out += [f"  ({diff.unchanged} unchanged)", "=" * 60, ""]
    return "\n".join(out)


# ── CLI entry point (wired up in cli/main.py) ──────────────────────────────────

def run_compare(args) -> int:
    """Execute `rubric compare`. Returns the process exit code."""
    import os

    try:
        current = load_report(args.current)
    except (OSError, ValueError) as e:
        print(f"❌ {e}")
        return 1

    baseline = None
    if args.baseline:
        if os.path.exists(args.baseline):
            try:
                baseline = load_report(args.baseline)
            except ValueError as e:
                print(f"❌ {e}")
                return 1
        elif not args.quiet:
            print(f"⚠️  Baseline not found at {args.baseline} — reporting current run only.")

    diff = diff_reports(baseline, current, score_drop_threshold=args.score_drop_threshold)

    if not args.quiet:
        print(render_terminal(diff))

    if args.output_md:
        with open(args.output_md, "w", encoding="utf-8") as f:
            f.write(render_markdown(diff))
        if not args.quiet:
            print(f"  📄 Markdown diff written to: {args.output_md}")

    if args.fail_on_regression and diff.has_regressions:
        print(f"\n❌ Rubric: {len(diff.regressed)} test(s) regressed vs baseline.")
        return 1
    return 0
