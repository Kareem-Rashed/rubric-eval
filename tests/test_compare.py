"""
Unit tests for `rubric compare` — regression diffing between JSON reports.
Run: pytest tests/
"""

import json

import pytest

from rubriceval.cli.compare import (
    COMMENT_MARKER,
    diff_reports,
    load_report,
    render_markdown,
    render_terminal,
)


def make_result(name, passed=True, score=1.0, metrics=None):
    return {
        "name": name,
        "passed": passed,
        "overall_score": score,
        "metrics": metrics or [
            {"name": "tool_call_accuracy", "score": score, "passed": passed,
             "skipped": False, "reason": None if passed else "Missing expected tools: ['lookup_order']"},
        ],
    }


def make_report(results):
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "avg_score": sum(r["overall_score"] for r in results) / total if total else 0.0,
        },
        "results": results,
    }


# ── diff_reports ─────────────────────────────────────────────────────────────

def test_detects_regression():
    baseline = make_report([make_result("order lookup", passed=True, score=1.0)])
    current = make_report([make_result("order lookup", passed=False, score=0.4)])
    diff = diff_reports(baseline, current)
    assert diff.has_regressions
    assert diff.regressed[0].name == "order lookup"
    assert diff.regressed[0].baseline_score == 1.0
    assert diff.regressed[0].current_score == 0.4


def test_regression_includes_metric_reasons():
    baseline = make_report([make_result("t", passed=True, score=1.0)])
    current = make_report([make_result("t", passed=False, score=0.0)])
    diff = diff_reports(baseline, current)
    deltas = diff.regressed[0].metric_deltas
    assert deltas[0].name == "tool_call_accuracy"
    assert "lookup_order" in deltas[0].reason


def test_detects_fixed():
    baseline = make_report([make_result("t", passed=False, score=0.2)])
    current = make_report([make_result("t", passed=True, score=1.0)])
    diff = diff_reports(baseline, current)
    assert not diff.has_regressions
    assert diff.fixed[0].name == "t"


def test_detects_score_drop_without_failure():
    baseline = make_report([make_result("t", passed=True, score=0.95)])
    current = make_report([make_result("t", passed=True, score=0.72)])
    diff = diff_reports(baseline, current, score_drop_threshold=0.1)
    assert not diff.has_regressions
    assert diff.score_drops[0].name == "t"


def test_small_score_change_is_unchanged():
    baseline = make_report([make_result("t", passed=True, score=0.95)])
    current = make_report([make_result("t", passed=True, score=0.90)])
    diff = diff_reports(baseline, current, score_drop_threshold=0.1)
    assert diff.unchanged == 1
    assert not diff.score_drops


def test_detects_new_and_removed():
    baseline = make_report([make_result("old", passed=True)])
    current = make_report([make_result("new", passed=False, score=0.1)])
    diff = diff_reports(baseline, current)
    assert diff.new_tests[0].name == "new"
    assert diff.removed_tests[0].name == "old"
    assert not diff.has_regressions  # new failing test is not a regression


def test_no_baseline_lists_current_failures():
    current = make_report([
        make_result("a", passed=True),
        make_result("b", passed=False, score=0.3),
    ])
    diff = diff_reports(None, current)
    assert not diff.has_baseline
    assert [r["name"] for r in diff.current_failures] == ["b"]


def test_skipped_metrics_ignored_in_deltas():
    baseline = make_report([make_result("t", passed=True, score=1.0)])
    cur_result = make_result("t", passed=False, score=0.0, metrics=[
        {"name": "m1", "score": 0.0, "passed": False, "skipped": False, "reason": "bad"},
        {"name": "m2", "score": 0.0, "passed": False, "skipped": True, "reason": "no dep"},
    ])
    diff = diff_reports(baseline, make_report([cur_result]))
    names = [d.name for d in diff.regressed[0].metric_deltas]
    assert "m2" not in names


# ── rendering ────────────────────────────────────────────────────────────────

def test_markdown_starts_with_marker_and_shows_regressions():
    baseline = make_report([make_result("order lookup", passed=True, score=1.0)])
    current = make_report([make_result("order lookup", passed=False, score=0.4)])
    md = render_markdown(diff_reports(baseline, current))
    assert md.startswith(COMMENT_MARKER)
    assert "1 regression" in md
    assert "order lookup" in md
    assert "1.00 → 0.40" in md
    assert "Missing expected tools" in md


def test_markdown_no_regressions_headline():
    baseline = make_report([make_result("t", passed=True)])
    current = make_report([make_result("t", passed=True)])
    md = render_markdown(diff_reports(baseline, current))
    assert "no regressions" in md


def test_markdown_without_baseline_suggests_creating_one():
    current = make_report([make_result("t", passed=True)])
    md = render_markdown(diff_reports(None, current))
    assert md.startswith(COMMENT_MARKER)
    assert "baseline" in md.lower()


def test_terminal_render_smoke():
    baseline = make_report([
        make_result("a", passed=True),
        make_result("b", passed=False, score=0.2),
    ])
    current = make_report([
        make_result("a", passed=False, score=0.1),
        make_result("b", passed=True),
    ])
    out = render_terminal(diff_reports(baseline, current))
    assert "Regressions (1)" in out
    assert "Fixed (1)" in out


# ── load_report / CLI ────────────────────────────────────────────────────────

def test_load_report_rejects_non_rubric_json(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(ValueError):
        load_report(str(p))


def test_cli_compare_end_to_end(tmp_path, monkeypatch, capsys):
    from rubriceval.cli.main import main

    baseline = make_report([make_result("t", passed=True, score=1.0)])
    current = make_report([make_result("t", passed=False, score=0.3)])
    base_path = tmp_path / "baseline.json"
    cur_path = tmp_path / "current.json"
    md_path = tmp_path / "comment.md"
    base_path.write_text(json.dumps(baseline))
    cur_path.write_text(json.dumps(current))

    monkeypatch.setattr("sys.argv", [
        "rubric", "compare", str(cur_path),
        "--baseline", str(base_path),
        "--output-md", str(md_path),
        "--fail-on-regression",
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert md_path.read_text().startswith(COMMENT_MARKER)
    assert "REGRESSION DIFF" in capsys.readouterr().out


def test_cli_compare_passes_when_clean(tmp_path, monkeypatch):
    from rubriceval.cli.main import main

    report = make_report([make_result("t", passed=True)])
    base_path = tmp_path / "baseline.json"
    cur_path = tmp_path / "current.json"
    base_path.write_text(json.dumps(report))
    cur_path.write_text(json.dumps(report))

    monkeypatch.setattr("sys.argv", [
        "rubric", "compare", str(cur_path),
        "--baseline", str(base_path), "--fail-on-regression", "--quiet",
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
