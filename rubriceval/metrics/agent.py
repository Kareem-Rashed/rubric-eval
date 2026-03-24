"""
Agent-specific metrics for evaluating multi-step AI agents.
These are Rubric's biggest differentiator vs competitors.
"""

from __future__ import annotations

from typing import Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult
from rubriceval.metrics.base import BaseMetric


class ToolCallAccuracy(BaseMetric):
    """
    Evaluates whether the agent called the correct tools in the right order.

    Checks:
    - Were all expected_tools called?
    - Were no forbidden_tools called?
    - Optionally: were tools called in the correct order?

    Example:
        metric = ToolCallAccuracy()
        # With expected_tools=["search_web", "summarize"] in AgentTestCase,
        # checks that both tools were called.
    """

    name = "tool_call_accuracy"

    def __init__(
        self,
        check_order: bool = False,
        threshold: float = 1.0,
    ):
        self.check_order = check_order
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if not isinstance(test_case, AgentTestCase):
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason="ToolCallAccuracy only applies to AgentTestCase. Skipped.",
            )

        expected = test_case.expected_tools or []
        forbidden = test_case.forbidden_tools or []
        actual_tools = test_case.tool_names_called

        issues = []
        score_components = []

        # Check expected tools
        if expected:
            missing = [t for t in expected if t not in actual_tools]
            coverage = (len(expected) - len(missing)) / len(expected)
            score_components.append(coverage)
            if missing:
                issues.append(f"Missing expected tools: {missing}")
        else:
            score_components.append(1.0)

        # Check forbidden tools
        if forbidden:
            violations = [t for t in actual_tools if t in forbidden]
            forbidden_score = 1.0 if not violations else 0.0
            score_components.append(forbidden_score)
            if violations:
                issues.append(f"Called forbidden tools: {violations}")
        else:
            score_components.append(1.0)

        # Check order (optional)
        if self.check_order and expected and len(expected) > 1:
            expected_subsequence = self._is_subsequence(expected, actual_tools)
            order_score = 1.0 if expected_subsequence else 0.5
            score_components.append(order_score)
            if not expected_subsequence:
                issues.append(
                    f"Tools not called in expected order. Expected: {expected}, Got: {actual_tools}"
                )

        score = sum(score_components) / len(score_components) if score_components else 1.0
        passed = score >= self.threshold and len(issues) == 0

        reason = (
            f"All tool requirements met. Called: {actual_tools}"
            if not issues
            else "; ".join(issues)
        )

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=reason,
            metadata={
                "expected_tools": expected,
                "forbidden_tools": forbidden,
                "actual_tools": actual_tools,
            },
        )

    @staticmethod
    def _is_subsequence(sub: list, full: list) -> bool:
        """Check if sub appears in order within full."""
        it = iter(full)
        return all(item in it for item in sub)


class TraceQuality(BaseMetric):
    """
    Evaluates the quality and efficiency of an agent's reasoning trace.

    Checks:
    - Did the agent complete within max_steps?
    - Did the agent avoid loops (repeated identical steps)?
    - Did the agent use the minimum required steps?

    Example:
        metric = TraceQuality(max_steps=10, penalize_loops=True)
    """

    name = "trace_quality"

    def __init__(
        self,
        max_steps: Optional[int] = None,
        penalize_loops: bool = True,
        threshold: float = 0.7,
    ):
        self.max_steps = max_steps
        self.penalize_loops = penalize_loops
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if not isinstance(test_case, AgentTestCase):
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason="TraceQuality only applies to AgentTestCase. Skipped.",
            )

        trace = test_case.trace
        steps = len(trace)
        issues = []
        score_components = []

        # Check max steps
        max_steps = self.max_steps or test_case.max_steps
        if max_steps:
            if steps <= max_steps:
                step_score = 1.0
            else:
                step_score = max(0.0, 1.0 - (steps - max_steps) / max_steps)
                issues.append(
                    f"Exceeded max steps: {steps} > {max_steps}"
                )
            score_components.append(step_score)

        # Check for loops (repeated identical content)
        if self.penalize_loops and trace:
            contents = [str(step.content) for step in trace]
            unique = len(set(contents))
            loop_score = unique / len(contents) if contents else 1.0
            if loop_score < 1.0:
                issues.append(f"Detected repeated trace steps ({steps - unique} duplicates)")
            score_components.append(loop_score)

        if not score_components:
            score = 1.0
        else:
            score = sum(score_components) / len(score_components)

        passed = score >= self.threshold

        reason = (
            f"Trace looks clean. {steps} steps taken."
            if not issues
            else "; ".join(issues)
        )

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=reason,
            metadata={"steps_taken": steps, "max_steps": max_steps},
        )


class TaskCompletion(BaseMetric):
    """
    Binary metric: Did the agent complete its task?

    Uses a simple heuristic check based on output quality,
    or delegates to an LLM judge if provided.

    Example:
        # Simple heuristic (checks for success-indicating phrases)
        metric = TaskCompletion()

        # With LLM judge
        metric = TaskCompletion(judge_fn=my_llm)
    """

    name = "task_completion"

    _SUCCESS_PHRASES = [
        "i've completed", "i have completed", "done!", "task complete",
        "successfully", "i've booked", "i've sent", "here is", "here are",
        "the answer is", "i found", "i've created", "i've updated",
    ]

    _FAILURE_PHRASES = [
        "i'm unable", "i cannot", "i can't", "i don't know",
        "i'm sorry, but", "unfortunately", "i was unable",
        "could not", "failed to",
    ]

    def __init__(
        self,
        judge_fn=None,
        threshold: float = 0.7,
        use_heuristic_fallback: bool = True,
    ):
        self.judge_fn = judge_fn
        self.threshold = threshold
        self.use_heuristic_fallback = use_heuristic_fallback

    def _heuristic_score(self, output: str) -> float:
        output_lower = output.lower()
        success_hits = sum(1 for p in self._SUCCESS_PHRASES if p in output_lower)
        failure_hits = sum(1 for p in self._FAILURE_PHRASES if p in output_lower)

        if failure_hits > 0 and success_hits == 0:
            return 0.2
        if success_hits > 0:
            return min(1.0, 0.6 + success_hits * 0.1)
        return 0.5  # neutral

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if self.judge_fn:
            # Delegate to LLM judge
            from rubriceval.metrics.llm_judge import LLMJudge
            judge = LLMJudge(
                criteria="Did the AI agent successfully complete the requested task?",
                judge_fn=self.judge_fn,
                threshold=self.threshold,
            )
            result = judge.measure(test_case)
            result.metric_name = self.name
            return result

        if self.use_heuristic_fallback:
            score = self._heuristic_score(test_case.actual_output)
            passed = score >= self.threshold
            return MetricResult(
                metric_name=self.name,
                score=score,
                passed=passed,
                reason=(
                    f"Heuristic task completion score: {score:.2f}. "
                    "Pass a judge_fn for LLM-based evaluation."
                ),
            )

        return MetricResult(
            metric_name=self.name,
            score=0.0,
            passed=False,
            reason="No judge_fn provided and use_heuristic_fallback=False.",
        )


class LatencyMetric(BaseMetric):
    """
    Checks that the LLM/agent response was within a latency budget.

    Example:
        # Fail if response took > 3000ms
        metric = LatencyMetric(max_ms=3000)
    """

    name = "latency"

    def __init__(self, max_ms: float = 5000.0, threshold: float = 1.0):
        self.max_ms = max_ms
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if test_case.latency_ms is None:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason="No latency data provided. Set test_case.latency_ms to use this metric.",
            )

        latency = test_case.latency_ms
        if latency <= self.max_ms:
            score = 1.0
            passed = True
            reason = f"Latency {latency:.0f}ms is within budget ({self.max_ms:.0f}ms)."
        else:
            score = max(0.0, 1.0 - (latency - self.max_ms) / self.max_ms)
            passed = False
            reason = f"Latency {latency:.0f}ms exceeded budget ({self.max_ms:.0f}ms)."

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=reason,
            metadata={"latency_ms": latency, "max_ms": self.max_ms},
        )


class CostMetric(BaseMetric):
    """
    Checks that the LLM API cost was within budget.

    Example:
        metric = CostMetric(max_cost_usd=0.01)  # fail if > 1 cent
    """

    name = "cost"

    def __init__(self, max_cost_usd: float = 0.01, threshold: float = 1.0):
        self.max_cost_usd = max_cost_usd
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if test_case.cost_usd is None:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason="No cost data provided. Set test_case.cost_usd to use this metric.",
            )

        cost = test_case.cost_usd
        passed = cost <= self.max_cost_usd
        score = min(1.0, self.max_cost_usd / cost) if cost > 0 else 1.0

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=(
                f"Cost ${cost:.5f} is within budget (${self.max_cost_usd:.5f})."
                if passed
                else f"Cost ${cost:.5f} exceeded budget (${self.max_cost_usd:.5f})."
            ),
            metadata={"cost_usd": cost, "max_cost_usd": self.max_cost_usd},
        )
