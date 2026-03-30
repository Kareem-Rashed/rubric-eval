"""
Capture — zero-friction LLM call recording for developers building new apps.

Two ways to use:

1. Context manager — wrap a block of code:

    with rubric.capture() as session:
        answer = my_llm("What is the capital of France?")
        session.record(
            input="What is the capital of France?",
            actual_output=answer,
            context="France is a country in Western Europe.",
        )

    report = session.evaluate(metrics=[HallucinationScore(judge_fn=...)])
    report.print_summary()

2. Decorator — wrap an LLM function, captures every call automatically:

    @rubric.track
    def ask(prompt, context=None):
        return my_llm(prompt)

    ask("What is the capital of France?", context="France is in Europe.")
    ask("Who wrote Hamlet?")

    report = rubric.get_session().evaluate(metrics=[Contains("Paris")])
    report.print_summary()

    # Reset between test runs
    rubric.reset_session()
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, List, Optional, Union

from rubriceval.core.test_case import TestCase, AgentTestCase


# ── Global session (used by @rubric.track) ────────────────────────────────────

_global_session: Optional["CaptureSession"] = None


def get_session() -> "CaptureSession":
    """Return the current global session, creating one if it doesn't exist."""
    global _global_session
    if _global_session is None:
        _global_session = CaptureSession()
    return _global_session


def reset_session() -> None:
    """Clear the global session. Call between test runs."""
    global _global_session
    _global_session = CaptureSession()


# ── CaptureSession ─────────────────────────────────────────────────────────────

class CaptureSession:
    """
    Holds recorded LLM calls and runs evaluation on them.

    Use via rubric.capture() context manager or rubric.track decorator.
    """

    def __init__(self):
        self._test_cases: List[Union[TestCase, AgentTestCase]] = []

    def record(
        self,
        input: str,
        actual_output: str,
        expected_output: Optional[str] = None,
        context: Optional[str] = None,
        latency_ms: Optional[float] = None,
        cost_usd: Optional[float] = None,
        token_usage: Optional[dict] = None,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record a single LLM call.

        Args:
            input:           The prompt / user message sent to the LLM.
            actual_output:   The LLM's response.
            expected_output: Ground truth answer, if you have one.
            context:         The context/documents the LLM was given (for RAG evals).
            latency_ms:      How long the call took in milliseconds.
            cost_usd:        API cost for this call.
            token_usage:     Dict with "input" and "output" token counts.
            name:            Optional label for this test case in the report.
            metadata:        Any extra data you want attached to this test case.
        """
        self._test_cases.append(
            TestCase(
                input=input,
                actual_output=actual_output,
                expected_output=expected_output,
                context=context,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                token_usage=token_usage,
                name=name,
                metadata=metadata or {},
            )
        )

    def evaluate(self, metrics: list, verbose: bool = True):
        """
        Run evaluation on all recorded calls.

        Args:
            metrics: List of Rubric metric instances to evaluate with.
            verbose: Whether to print per-test output.

        Returns:
            EvalReport
        """
        from rubriceval.core.evaluator import evaluate as _evaluate

        if not self._test_cases:
            raise RuntimeError(
                "No calls recorded. Use session.record() or the @rubric.track decorator "
                "to capture LLM calls before evaluating."
            )

        return _evaluate(
            test_cases=self._test_cases,
            metrics=metrics,
            verbose=verbose,
        )

    @property
    def recorded(self) -> int:
        """Number of calls recorded so far."""
        return len(self._test_cases)

    def __repr__(self) -> str:
        return f"CaptureSession(recorded={self.recorded})"


# ── Context manager ────────────────────────────────────────────────────────────

@contextmanager
def capture():
    """
    Context manager that returns a CaptureSession.

    Example:
        with rubric.capture() as session:
            answer = my_llm(prompt)
            session.record(input=prompt, actual_output=answer, context=doc)

        report = session.evaluate(metrics=[HallucinationScore(judge_fn=...)])
    """
    session = CaptureSession()
    yield session


# ── Decorator ─────────────────────────────────────────────────────────────────

def track(fn: Callable) -> Callable:
    """
    Decorator that automatically captures every call to an LLM function.

    The decorated function must:
    - Accept a prompt/input as its first positional argument
    - Return the LLM response as a string

    Optional keyword arguments that are captured automatically if present:
    - context:         str — RAG context passed to the LLM
    - expected_output: str — ground truth answer

    Example:
        @rubric.track
        def ask(prompt, context=None):
            return my_llm(prompt)

        ask("What is the capital of France?", context="France is in Europe.")

        report = rubric.get_session().evaluate(metrics=[...])
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        input_text = args[0] if args else kwargs.get("prompt", "")
        context = kwargs.get("context")
        expected_output = kwargs.get("expected_output")

        start = time.perf_counter()
        result = fn(*args, **kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        get_session().record(
            input=str(input_text),
            actual_output=str(result),
            context=context,
            expected_output=expected_output,
            latency_ms=latency_ms,
            name=f"{fn.__name__}({str(input_text)[:40]})",
        )

        return result

    return wrapper
