"""
Result types for Rubric evaluations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase


@dataclass
class MetricResult:
    """Result from a single metric evaluation."""

    metric_name: str
    score: float  # 0.0 to 1.0
    passed: bool
    reason: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "✅" if self.passed else "❌"
        return f"{status} {self.metric_name}: {self.score:.2f}"


@dataclass
class TestResult:
    """Result from evaluating a single TestCase or AgentTestCase."""

    test_case: Union[TestCase, AgentTestCase]
    metric_results: list[MetricResult] = field(default_factory=list)
    passed: bool = True
    error: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if self.metric_results:
            self.passed = all(r.passed for r in self.metric_results)

    @property
    def overall_score(self) -> float:
        """Average score across all metrics."""
        if not self.metric_results:
            return 0.0
        return sum(r.score for r in self.metric_results) / len(self.metric_results)

    @property
    def failed_metrics(self) -> list[MetricResult]:
        return [r for r in self.metric_results if not r.passed]

    def to_dict(self) -> dict:
        return {
            "name": self.test_case.name,
            "input": self.test_case.input,
            "actual_output": self.test_case.actual_output,
            "expected_output": getattr(self.test_case, "expected_output", None),
            "passed": self.passed,
            "overall_score": round(self.overall_score, 4),
            "error": self.error,
            "evaluated_at": self.evaluated_at,
            "metrics": [
                {
                    "name": r.metric_name,
                    "score": round(r.score, 4),
                    "passed": r.passed,
                    "reason": r.reason,
                }
                for r in self.metric_results
            ],
        }

    def __repr__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"TestResult({status}, score={self.overall_score:.2f}, name={self.test_case.name!r})"


@dataclass
class EvalReport:
    """Full evaluation report across all test cases."""

    results: list[TestResult] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.overall_score for r in self.results) / len(self.results)

    def metric_summary(self) -> dict[str, dict]:
        """Per-metric pass rate and average score."""
        metric_data: dict[str, list] = {}
        for result in self.results:
            for mr in result.metric_results:
                if mr.metric_name not in metric_data:
                    metric_data[mr.metric_name] = []
                metric_data[mr.metric_name].append(mr)

        summary = {}
        for name, mresults in metric_data.items():
            summary[name] = {
                "pass_rate": sum(1 for r in mresults if r.passed) / len(mresults),
                "avg_score": sum(r.score for r in mresults) / len(mresults),
                "total": len(mresults),
            }
        return summary

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.pass_rate, 4),
                "avg_score": round(self.avg_score, 4),
            },
            "metrics": self.metric_summary(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self):
        """Print a human-readable summary to stdout."""
        print("\n" + "=" * 60)
        print("  RUBRIC EVALUATION REPORT")
        print("=" * 60)
        print(f"  Total:     {self.total}")
        print(f"  ✅ Passed:  {self.passed}")
        print(f"  ❌ Failed:  {self.failed}")
        print(f"  Pass Rate: {self.pass_rate * 100:.1f}%")
        print(f"  Avg Score: {self.avg_score:.3f}")
        print()

        ms = self.metric_summary()
        if ms:
            print("  Per-Metric Breakdown:")
            for metric_name, stats in ms.items():
                bar = "█" * int(stats["pass_rate"] * 20)
                print(
                    f"    {metric_name:<30} {stats['pass_rate']*100:5.1f}%  {bar}"
                )
        print()

        failures = [r for r in self.results if not r.passed]
        if failures:
            print(f"  Failed Cases ({len(failures)}):")
            for r in failures:
                print(f"    ❌ {r.test_case.name}")
                for mr in r.failed_metrics:
                    reason = f" — {mr.reason}" if mr.reason else ""
                    print(f"       {mr.metric_name}: {mr.score:.2f}{reason}")
            print()

        print("=" * 60 + "\n")

    def __repr__(self) -> str:
        return (
            f"EvalReport(total={self.total}, passed={self.passed}, "
            f"pass_rate={self.pass_rate:.1%}, avg_score={self.avg_score:.3f})"
        )
