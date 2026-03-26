"""
Core evaluation engine for Rubric.
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import EvalReport, MetricResult, TestResult
from rubriceval.metrics.base import BaseMetric


def evaluate(
    test_cases: list[Union[TestCase, AgentTestCase]],
    metrics: list[BaseMetric],
    *,
    verbose: bool = True,
    max_workers: int = 1,
    run_name: Optional[str] = None,
    raise_on_failure: bool = False,
    output_json: Optional[str] = None,
    output_html: Optional[str] = None,
) -> EvalReport:
    """
    Run evaluation across all test cases with the given metrics.

    This is Rubric's main entry point.

    Args:
        test_cases: List of TestCase or AgentTestCase to evaluate.
        metrics: List of metric instances to apply to each test case.
        verbose: Print progress and results to stdout.
        max_workers: Number of parallel workers (1 = sequential).
        run_name: Optional label for this evaluation run.
        raise_on_failure: Call sys.exit(1) if any test case fails (for CI).
        output_json: If set, write JSON report to this file path.
        output_html: If set, write HTML report to this file path.

    Returns:
        EvalReport with all results.

    Example:
        from rubriceval import evaluate, TestCase, ExactMatch, SemanticSimilarity

        results = evaluate(
            test_cases=[
                TestCase(
                    input="What is 2+2?",
                    actual_output=my_llm("What is 2+2?"),
                    expected_output="4",
                )
            ],
            metrics=[ExactMatch(), SemanticSimilarity(threshold=0.9)],
        )
        results.print_summary()
    """
    # Pick up CLI-injected env vars when flags aren't set directly
    import os as _os
    if output_html is None:
        output_html = _os.environ.get("RUBRIC_OUTPUT_HTML") or None
    if output_json is None:
        output_json = _os.environ.get("RUBRIC_OUTPUT_JSON") or None
    if not raise_on_failure:
        raise_on_failure = _os.environ.get("RUBRIC_RAISE_ON_FAILURE") == "1"
    if _os.environ.get("RUBRIC_QUIET") == "1":
        verbose = False

    report = EvalReport(
        metadata={"run_name": run_name or "rubric-eval"},
    )
    report.started_at = datetime.now().isoformat()

    if verbose:
        print(f"\n🔍 Rubric — Running {len(test_cases)} test case(s) "
              f"with {len(metrics)} metric(s)...\n")

    def _evaluate_one(test_case: Union[TestCase, AgentTestCase]) -> TestResult:
        metric_results = []
        for metric in metrics:
            try:
                result = metric.measure(test_case)
                metric_results.append(result)
            except Exception as e:
                metric_results.append(MetricResult(
                    metric_name=getattr(metric, "name", "unknown"),
                    score=0.0,
                    passed=False,
                    reason=f"Metric error: {e}",
                ))

        test_result = TestResult(
            test_case=test_case,
            metric_results=metric_results,
        )
        active = [r for r in metric_results if not r.skipped]
        test_result.passed = all(r.passed for r in active) if active else True
        return test_result

    if max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_evaluate_one, tc): tc for tc in test_cases}
            for future in as_completed(futures):
                result = future.result()
                report.results.append(result)
                if verbose:
                    _print_test_result(result)
    else:
        for i, test_case in enumerate(test_cases, 1):
            if verbose:
                name = test_case.name or f"Test #{i}"
                print(f"  [{i}/{len(test_cases)}] {name}")
            result = _evaluate_one(test_case)
            report.results.append(result)
            if verbose:
                _print_test_result(result)

    report.finished_at = datetime.now().isoformat()

    if verbose:
        report.print_summary()

    # Write outputs
    if output_json:
        import json
        with open(output_json, "w") as f:
            f.write(report.to_json())
        if verbose:
            print(f"  📄 JSON report written to: {output_json}")

    if output_html:
        from rubriceval.report.reporter import generate_html_report
        generate_html_report(report, output_html)
        if verbose:
            print(f"  🌐 HTML report written to: {output_html}")

    if raise_on_failure and report.failed > 0:
        print(
            f"\n❌ Rubric: {report.failed}/{report.total} test cases failed "
            f"(pass rate: {report.pass_rate:.1%})"
        )
        sys.exit(1)

    return report


def _print_test_result(result: TestResult):
    """Print a single test result with metric details."""
    status = "✅" if result.passed else "❌"
    print(f"    {status} Score: {result.overall_score:.3f}")
    for mr in result.metric_results:
        if mr.skipped:
            reason = mr.reason.split("\n")[0] if mr.reason else "missing dependency"
            print(f"      ⚠  {mr.metric_name}: skipped — {reason}")
        else:
            icon = "  ✓" if mr.passed else "  ✗"
            reason = f" — {mr.reason}" if mr.reason else ""
            reason_display = reason.split('\n')[0][:120] if reason else ""
            print(f"      {icon} {mr.metric_name}: {mr.score:.3f}{reason_display}")
    print()
