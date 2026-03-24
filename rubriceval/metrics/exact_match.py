"""
Exact match and fuzzy string matching metrics.
"""

from __future__ import annotations

from typing import Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult
from rubriceval.metrics.base import BaseMetric


class ExactMatch(BaseMetric):
    """
    Checks if the actual output exactly matches the expected output.
    Optionally case-insensitive and strip-whitespace.

    Example:
        metric = ExactMatch(case_sensitive=False)
    """

    name = "exact_match"

    def __init__(
        self,
        case_sensitive: bool = False,
        strip: bool = True,
        threshold: float = 1.0,
    ):
        self.case_sensitive = case_sensitive
        self.strip = strip
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if test_case.expected_output is None:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason="No expected_output provided for ExactMatch.",
            )

        actual = test_case.actual_output
        expected = test_case.expected_output

        if self.strip:
            actual = actual.strip()
            expected = expected.strip()

        if not self.case_sensitive:
            actual = actual.lower()
            expected = expected.lower()

        passed = actual == expected
        score = 1.0 if passed else 0.0

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=(
                "Output matches expected."
                if passed
                else f"Expected: {expected!r}\nActual:   {actual!r}"
            ),
        )


class Contains(BaseMetric):
    """
    Checks if the actual output contains a given substring or any of a list of substrings.

    Example:
        metric = Contains("Paris")
        metric = Contains(["Paris", "France"], require_all=False)  # any match
    """

    name = "contains"

    def __init__(
        self,
        substring: Union[str, list[str]],
        case_sensitive: bool = False,
        require_all: bool = True,
        threshold: float = 1.0,
    ):
        self.substrings = [substring] if isinstance(substring, str) else substring
        self.case_sensitive = case_sensitive
        self.require_all = require_all
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        actual = test_case.actual_output
        if not self.case_sensitive:
            actual = actual.lower()
            subs = [s.lower() for s in self.substrings]
        else:
            subs = self.substrings

        found = [s for s in subs if s in actual]

        if self.require_all:
            passed = len(found) == len(subs)
            score = len(found) / len(subs)
        else:
            passed = len(found) > 0
            score = 1.0 if passed else 0.0

        missing = [s for s in subs if s not in found]
        reason = (
            f"Found all required substrings."
            if passed
            else f"Missing: {missing}"
        )

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=reason,
        )


class NotContains(BaseMetric):
    """
    Checks that the actual output does NOT contain forbidden strings.
    Useful for safety / hallucination checks.

    Example:
        metric = NotContains(["I don't know", "As an AI", "I cannot"])
    """

    name = "not_contains"

    def __init__(
        self,
        forbidden: Union[str, list[str]],
        case_sensitive: bool = False,
        threshold: float = 1.0,
    ):
        self.forbidden = [forbidden] if isinstance(forbidden, str) else forbidden
        self.case_sensitive = case_sensitive
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        actual = test_case.actual_output
        if not self.case_sensitive:
            actual = actual.lower()
            forbidden = [f.lower() for f in self.forbidden]
        else:
            forbidden = self.forbidden

        found = [f for f in forbidden if f in actual]
        passed = len(found) == 0
        score = 1.0 if passed else 0.0

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=(
                "No forbidden strings found."
                if passed
                else f"Found forbidden strings: {found}"
            ),
        )


class RegexMatch(BaseMetric):
    """
    Checks if the actual output matches a regular expression.

    Example:
        metric = RegexMatch(r"\\d{4}-\\d{2}-\\d{2}")  # ISO date format
    """

    name = "regex_match"

    def __init__(self, pattern: str, threshold: float = 1.0):
        import re
        self.pattern = pattern
        self._regex = re.compile(pattern)
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        match = self._regex.search(test_case.actual_output)
        passed = match is not None
        score = 1.0 if passed else 0.0

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=(
                f"Pattern matched at position {match.start()}."
                if passed
                else f"Pattern {self.pattern!r} not found in output."
            ),
        )
