"""
Unit tests for Rubric metrics.
Run: pytest tests/
"""

import pytest
import rubriceval as rubric
from rubriceval import TestCase, AgentTestCase, ToolCall, TraceStep


def make_test(input="test", actual="hello world", expected=None):
    return TestCase(input=input, actual_output=actual, expected_output=expected)


# ── ExactMatch ───────────────────────────────────────────────────────────────

def test_exact_match_pass():
    metric = rubric.ExactMatch()
    result = metric.measure(make_test(actual="Paris", expected="Paris"))
    assert result.passed
    assert result.score == 1.0


def test_exact_match_case_insensitive():
    metric = rubric.ExactMatch(case_sensitive=False)
    result = metric.measure(make_test(actual="paris", expected="PARIS"))
    assert result.passed


def test_exact_match_fail():
    metric = rubric.ExactMatch()
    result = metric.measure(make_test(actual="London", expected="Paris"))
    assert not result.passed
    assert result.score == 0.0


def test_exact_match_no_expected():
    metric = rubric.ExactMatch()
    result = metric.measure(make_test(actual="Paris", expected=None))
    assert not result.passed


# ── Contains ─────────────────────────────────────────────────────────────────

def test_contains_single_pass():
    metric = rubric.Contains("Paris")
    result = metric.measure(make_test(actual="The capital is Paris, France."))
    assert result.passed


def test_contains_single_fail():
    metric = rubric.Contains("Paris")
    result = metric.measure(make_test(actual="London is the capital."))
    assert not result.passed


def test_contains_multiple_require_all():
    metric = rubric.Contains(["Paris", "France"], require_all=True)
    result = metric.measure(make_test(actual="Paris is the capital of France."))
    assert result.passed


def test_contains_multiple_any():
    metric = rubric.Contains(["Paris", "France"], require_all=False)
    result = metric.measure(make_test(actual="France is a country."))
    assert result.passed


def test_contains_case_insensitive():
    metric = rubric.Contains("paris", case_sensitive=False)
    result = metric.measure(make_test(actual="PARIS is the capital."))
    assert result.passed


# ── NotContains ──────────────────────────────────────────────────────────────

def test_not_contains_pass():
    metric = rubric.NotContains("I don't know")
    result = metric.measure(make_test(actual="The answer is Paris."))
    assert result.passed


def test_not_contains_fail():
    metric = rubric.NotContains("I don't know")
    result = metric.measure(make_test(actual="I don't know the answer."))
    assert not result.passed


# ── RegexMatch ───────────────────────────────────────────────────────────────

def test_regex_match_pass():
    metric = rubric.RegexMatch(r"\d{4}-\d{2}-\d{2}")
    result = metric.measure(make_test(actual="The date is 2024-03-15."))
    assert result.passed


def test_regex_match_fail():
    metric = rubric.RegexMatch(r"\d{4}-\d{2}-\d{2}")
    result = metric.measure(make_test(actual="No date here."))
    assert not result.passed


# ── ToolCallAccuracy ──────────────────────────────────────────────────────────

def _make_agent_test(
    actual="Done!",
    expected_tools=None,
    forbidden_tools=None,
    called_tools=None,
):
    tool_calls = [ToolCall(name=t) for t in (called_tools or [])]
    return AgentTestCase(
        input="test task",
        actual_output=actual,
        expected_tools=expected_tools,
        forbidden_tools=forbidden_tools,
        tool_calls=tool_calls,
    )


def test_tool_call_accuracy_all_present():
    metric = rubric.ToolCallAccuracy()
    tc = _make_agent_test(
        expected_tools=["search", "book"],
        called_tools=["search", "check", "book"],
    )
    result = metric.measure(tc)
    assert result.passed


def test_tool_call_accuracy_missing_tool():
    metric = rubric.ToolCallAccuracy()
    tc = _make_agent_test(
        expected_tools=["search", "book"],
        called_tools=["search"],
    )
    result = metric.measure(tc)
    assert not result.passed
    assert "book" in result.reason


def test_tool_call_forbidden_tool():
    metric = rubric.ToolCallAccuracy()
    tc = _make_agent_test(
        expected_tools=["search"],
        forbidden_tools=["send_email"],
        called_tools=["search", "send_email"],
    )
    result = metric.measure(tc)
    assert not result.passed


# ── LatencyMetric ─────────────────────────────────────────────────────────────

def test_latency_pass():
    metric = rubric.LatencyMetric(max_ms=5000)
    tc = TestCase(input="hi", actual_output="hello", latency_ms=1200.0)
    result = metric.measure(tc)
    assert result.passed


def test_latency_fail():
    metric = rubric.LatencyMetric(max_ms=1000)
    tc = TestCase(input="hi", actual_output="hello", latency_ms=5000.0)
    result = metric.measure(tc)
    assert not result.passed


def test_latency_no_data():
    metric = rubric.LatencyMetric(max_ms=1000)
    tc = TestCase(input="hi", actual_output="hello")
    result = metric.measure(tc)
    assert result.passed  # passes gracefully when no data


# ── EvalReport ───────────────────────────────────────────────────────────────

def test_evaluate_returns_report():
    test_cases = [
        TestCase(input="Q1", actual_output="Paris", expected_output="Paris"),
        TestCase(input="Q2", actual_output="Wrong", expected_output="Right"),
    ]
    report = rubric.evaluate(
        test_cases=test_cases,
        metrics=[rubric.ExactMatch()],
        verbose=False,
    )
    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
    assert 0.4 < report.pass_rate < 0.6


def test_report_to_json():
    import json
    test_cases = [TestCase(input="Q", actual_output="A", expected_output="A")]
    report = rubric.evaluate(test_cases=test_cases, metrics=[rubric.ExactMatch()], verbose=False)
    data = json.loads(report.to_json())
    assert "summary" in data
    assert "results" in data
    assert data["summary"]["total"] == 1


# ── RougeScore ────────────────────────────────────────────────────────────────

pytest.importorskip("rouge_score", reason="rouge-score not installed")


def test_rouge1_identical_strings():
    metric = rubric.RougeScore(rouge_type="rouge1", threshold=0.9)
    result = metric.measure(make_test(actual="the cat sat on the mat", expected="the cat sat on the mat"))
    assert result.passed
    assert result.score == pytest.approx(1.0, abs=1e-3)


def test_rouge2_partial_overlap():
    metric = rubric.RougeScore(rouge_type="rouge2", threshold=0.0)
    result = metric.measure(make_test(actual="the cat sat on the mat", expected="the cat ate the rat"))
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 1.0


def test_rougeL_pass():
    metric = rubric.RougeScore(rouge_type="rougeL", threshold=0.5)
    result = metric.measure(make_test(actual="the cat sat on the mat", expected="the cat sat on the mat"))
    assert result.passed
    assert result.score >= 0.5


def test_rougeL_fail_below_threshold():
    metric = rubric.RougeScore(rouge_type="rougeL", threshold=0.9)
    result = metric.measure(make_test(actual="completely different text here", expected="the cat sat on the mat"))
    assert not result.passed


def test_rouge_empty_actual():
    metric = rubric.RougeScore(rouge_type="rouge1", threshold=0.5)
    result = metric.measure(make_test(actual="", expected="the cat sat on the mat"))
    assert isinstance(result, rubric.MetricResult)
    assert result.score == pytest.approx(0.0, abs=1e-3)
    assert not result.passed


def test_rouge_no_expected():
    metric = rubric.RougeScore(rouge_type="rouge1", threshold=0.5)
    result = metric.measure(make_test(actual="some text", expected=None))
    assert isinstance(result, rubric.MetricResult)
    assert not result.passed


def test_rouge_returns_metric_result():
    metric = rubric.RougeScore(rouge_type="rougeL", threshold=0.5)
    result = metric.measure(make_test(actual="hello world", expected="hello world"))
    assert isinstance(result, rubric.MetricResult)
    assert result.metric_name is not None
    assert result.reason is not None


# ── GEval ─────────────────────────────────────────────────────────────────────

from unittest.mock import MagicMock


def _mock_judge(score: float, passed: bool, reason: str = "looks good"):
    import json
    return MagicMock(return_value=json.dumps({"score": score, "passed": passed, "reason": reason}))


def test_geval_basic_scoring():
    judge = _mock_judge(0.9, True, "The answer is accurate and concise.")
    metric = rubric.GEval(name="accuracy", criteria="Is the answer accurate?", judge_fn=judge, threshold=0.7)
    result = metric.measure(make_test(actual="Paris is the capital of France.", expected="Paris"))
    assert isinstance(result, rubric.MetricResult)
    assert result.score == pytest.approx(0.9, abs=1e-3)
    assert result.passed


def test_geval_threshold_pass():
    judge = _mock_judge(0.8, True)
    metric = rubric.GEval(name="quality", criteria="Is it high quality?", judge_fn=judge, threshold=0.7)
    result = metric.measure(make_test(actual="good answer"))
    assert result.passed


def test_geval_threshold_fail():
    judge = _mock_judge(0.4, False, "The answer is incomplete.")
    metric = rubric.GEval(name="quality", criteria="Is it high quality?", judge_fn=judge, threshold=0.7)
    result = metric.measure(make_test(actual="bad answer"))
    assert not result.passed
    assert result.score == pytest.approx(0.4, abs=1e-3)


def test_geval_returns_metric_result():
    judge = _mock_judge(0.75, True)
    metric = rubric.GEval(name="coherence", criteria="Is it coherent?", judge_fn=judge, threshold=0.7)
    result = metric.measure(make_test(actual="some response"))
    assert isinstance(result, rubric.MetricResult)
    assert result.metric_name == "coherence"
    assert result.reason is not None


def test_geval_score_clamped_to_range():
    import json
    judge = MagicMock(return_value=json.dumps({"score": 1.5, "passed": True, "reason": "over the top"}))
    metric = rubric.GEval(name="test", criteria="any", judge_fn=judge, threshold=0.5)
    result = metric.measure(make_test(actual="response"))
    assert result.score <= 1.0


def test_geval_calls_judge_once():
    judge = _mock_judge(0.8, True)
    metric = rubric.GEval(name="test", criteria="any", judge_fn=judge, threshold=0.5)
    metric.measure(make_test(actual="response"))
    assert judge.call_count == 1


# ── HallucinationScore ────────────────────────────────────────────────────────

def _make_hallucination_judge(score: float, passed: bool, reason: str = "ok", claims: list = None):
    import json
    return MagicMock(return_value=json.dumps({
        "score": score,
        "passed": passed,
        "reason": reason,
        "hallucinated_claims": claims or [],
    }))


def test_hallucination_faithful_output():
    judge = _make_hallucination_judge(1.0, True, "All claims supported by context.")
    metric = rubric.HallucinationScore(judge_fn=judge, threshold=0.7)
    tc = TestCase(
        input="Where is the Eiffel Tower?",
        actual_output="The Eiffel Tower is in Paris, France.",
        context="The Eiffel Tower is located in Paris, France.",
    )
    result = metric.measure(tc)
    assert result.passed
    assert result.score == pytest.approx(1.0, abs=1e-3)


def test_hallucination_hallucinated_output():
    judge = _make_hallucination_judge(0.2, False, "Claims not in context.", ["built in 1776"])
    metric = rubric.HallucinationScore(judge_fn=judge, threshold=0.7)
    tc = TestCase(
        input="When was the Eiffel Tower built?",
        actual_output="The Eiffel Tower was built in 1776.",
        context="The Eiffel Tower was built in 1889.",
    )
    result = metric.measure(tc)
    assert not result.passed
    assert result.score < 0.7


def test_hallucination_no_context():
    metric = rubric.HallucinationScore(judge_fn=MagicMock(), threshold=0.7)
    tc = TestCase(input="question", actual_output="answer", context=None)
    result = metric.measure(tc)
    assert isinstance(result, rubric.MetricResult)
    assert not result.passed
    assert "context" in result.reason.lower()


def test_hallucination_score_clamped():
    import json
    judge = MagicMock(return_value=json.dumps({"score": 1.8, "passed": True, "reason": "fine", "hallucinated_claims": []}))
    metric = rubric.HallucinationScore(judge_fn=judge, threshold=0.7)
    tc = TestCase(input="q", actual_output="a", context="some context")
    result = metric.measure(tc)
    assert result.score <= 1.0


def test_hallucination_returns_metric_result():
    judge = _make_hallucination_judge(0.9, True)
    metric = rubric.HallucinationScore(judge_fn=judge, threshold=0.7)
    tc = TestCase(input="q", actual_output="a", context="some context")
    result = metric.measure(tc)
    assert isinstance(result, rubric.MetricResult)
    assert result.metric_name == "hallucination"
    assert result.reason is not None


def test_hallucination_partial_score():
    judge = _make_hallucination_judge(0.5, False, "Some claims unsupported.", ["claim X"])
    metric = rubric.HallucinationScore(judge_fn=judge, threshold=0.7)
    tc = TestCase(input="q", actual_output="some answer with mix", context="partial context")
    result = metric.measure(tc)
    assert result.score == pytest.approx(0.5, abs=1e-3)
    assert not result.passed
