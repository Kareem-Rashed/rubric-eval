"""
pytest plugin for Rubric.
Enables writing LLM/agent evaluations as native pytest tests.

Usage:
    # conftest.py
    pytest_plugins = ["rubriceval.integrations.pytest_plugin"]

    # test_my_llm.py
    def test_factual_accuracy(rubric_eval):
        rubric_eval.add(
            TestCase(
                input="What year was Egypt founded?",
                actual_output=my_llm("What year was Egypt founded?"),
                expected_output="3100 BC",
            ),
            metrics=[Contains("3100"), SemanticSimilarity(threshold=0.8)],
        )

    def test_agent_books_flight(rubric_eval):
        result = agent.run("Book a flight to Paris")
        rubric_eval.add(
            AgentTestCase(
                input="Book a flight to Paris",
                actual_output=result.output,
                expected_tools=["search_flights", "book_flight"],
                tool_calls=result.tool_calls,
            ),
            metrics=[ToolCallAccuracy(), TaskCompletion()],
        )
"""

from __future__ import annotations

from typing import Union

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult, TestResult
from rubriceval.metrics.base import BaseMetric


class RubricEvaluator:
    """
    In-test evaluator injected via the `rubric_eval` fixture.
    Collects test cases during the test, evaluates them at teardown.
    """

    def __init__(self):
        self._cases: list[tuple[Union[TestCase, AgentTestCase], list[BaseMetric]]] = []
        self._results: list[TestResult] = []

    def add(
        self,
        test_case: Union[TestCase, AgentTestCase],
        metrics: list[BaseMetric],
    ):
        """Add a test case to evaluate."""
        self._cases.append((test_case, metrics))

    def run(self) -> list[TestResult]:
        """Run all registered evaluations and return results."""
        results = []
        for test_case, metrics in self._cases:
            metric_results = []
            for metric in metrics:
                try:
                    mr = metric.measure(test_case)
                    metric_results.append(mr)
                except Exception as e:
                    metric_results.append(MetricResult(
                        metric_name=getattr(metric, "name", "unknown"),
                        score=0.0,
                        passed=False,
                        reason=f"Metric error: {e}",
                    ))

            result = TestResult(
                test_case=test_case,
                metric_results=metric_results,
            )
            result.passed = all(r.passed for r in metric_results)
            results.append(result)

        self._results = results
        return results

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self._results)

    def assert_all_passed(self):
        """Assert all evaluations passed. Call this at the end of your test."""
        results = self.run()
        failures = [r for r in results if not r.passed]
        if failures:
            msgs = []
            for r in failures:
                msgs.append(f"\n  ❌ {r.test_case.name}")
                for mr in r.failed_metrics:
                    msgs.append(f"     {mr.metric_name}: {mr.score:.3f} — {mr.reason}")
            raise AssertionError("Rubric evaluation failed:" + "".join(msgs))


@pytest.fixture
def rubric_eval():
    """
    pytest fixture that provides a RubricEvaluator.
    Automatically asserts all evaluations pass at teardown.

    Example:
        def test_my_llm(rubric_eval):
            rubric_eval.add(
                TestCase(input="hi", actual_output="Hello!", expected_output="Hello"),
                metrics=[ExactMatch()],
            )
            # Automatically asserts at end of test
    """
    evaluator = RubricEvaluator()
    yield evaluator
    evaluator.assert_all_passed()


@pytest.fixture
def rubric_eval_manual():
    """
    Like rubric_eval, but does NOT auto-assert. Call .assert_all_passed() yourself.
    Useful when you want to inspect results before asserting.
    """
    return RubricEvaluator()
