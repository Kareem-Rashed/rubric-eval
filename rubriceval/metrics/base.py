"""
Base metric class for Rubric.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult


class BaseMetric(ABC):
    """
    Abstract base class for all Rubric metrics.

    To create a custom metric, subclass this and implement `measure()`.

    Example:
        class MyMetric(BaseMetric):
            name = "my_metric"
            threshold = 0.5

            def measure(self, test_case):
                score = ... # your logic
                return MetricResult(
                    metric_name=self.name,
                    score=score,
                    passed=score >= self.threshold,
                    reason="Why it passed or failed",
                )
    """

    name: str = "base_metric"
    threshold: float = 0.5

    @abstractmethod
    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        """Evaluate a test case and return a MetricResult."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(threshold={self.threshold})"
