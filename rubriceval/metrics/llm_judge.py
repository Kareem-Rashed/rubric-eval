"""
LLM-as-Judge metric — uses any LLM to evaluate output quality.
Model-agnostic: works with OpenAI, Anthropic, Ollama, or any callable.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Callable, Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult
from rubriceval.metrics.base import BaseMetric


_DEFAULT_SYSTEM_PROMPT = """You are an expert AI evaluator. Your job is to score an AI assistant's response based on the provided criteria.

You MUST respond with a valid JSON object in this exact format:
{
  "score": <float between 0.0 and 1.0>,
  "passed": <true or false>,
  "reason": "<brief explanation of your score>"
}

Be objective and consistent. Use the full 0–1 scale."""

_DEFAULT_EVAL_PROMPT = """Evaluate the following AI response.

CRITERIA: {criteria}

USER INPUT:
{input}

{expected_section}
AI RESPONSE:
{actual_output}

Score the response from 0.0 (completely wrong/bad) to 1.0 (perfect).
Pass threshold: {threshold}

Respond ONLY with JSON: {{"score": ..., "passed": ..., "reason": "..."}}"""


class LLMJudge(BaseMetric):
    """
    Uses an LLM to evaluate the quality of an AI response against custom criteria.

    Works with any LLM via a simple callable interface. Supports OpenAI, Anthropic,
    Ollama, or any function that takes a prompt and returns a string.

    Example (OpenAI):
        from openai import OpenAI
        client = OpenAI()

        def my_judge(prompt):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content

        metric = LLMJudge(
            criteria="Is the response accurate, helpful, and concise?",
            judge_fn=my_judge,
            threshold=0.7,
        )

    Example (Anthropic):
        import anthropic
        client = anthropic.Anthropic()

        def my_judge(prompt):
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text

        metric = LLMJudge(criteria="Is the answer factually correct?", judge_fn=my_judge)

    Example (Ollama / local model):
        import ollama

        def my_judge(prompt):
            return ollama.generate(model="llama3", prompt=prompt)["response"]

        metric = LLMJudge(criteria="Is the response safe and helpful?", judge_fn=my_judge)
    """

    name = "llm_judge"

    def __init__(
        self,
        criteria: str,
        judge_fn: Optional[Callable[[str], str]] = None,
        threshold: float = 0.7,
        model: str = "gpt-4o-mini",
        include_expected: bool = True,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
        num_runs: int = 1,
        flakiness_threshold: float = 0.15,
    ):
        self.criteria = criteria
        self.judge_fn = judge_fn
        self.threshold = threshold
        self.model = model
        self.include_expected = include_expected
        self.system_prompt = system_prompt
        self.num_runs = max(1, num_runs)
        self.flakiness_threshold = flakiness_threshold
        self._auto_client = None

    def _get_auto_judge(self) -> Callable[[str], str]:
        """
        Auto-detect an available LLM if no judge_fn was provided.
        Tries OpenAI first, then Anthropic, then raises a helpful error.
        """
        try:
            from openai import OpenAI
            client = OpenAI()

            def openai_judge(prompt: str) -> str:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=256,
                    temperature=0.0,
                )
                return resp.choices[0].message.content

            return openai_judge
        except Exception:
            pass

        try:
            import anthropic
            client = anthropic.Anthropic()

            def anthropic_judge(prompt: str) -> str:
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=256,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text

            return anthropic_judge
        except Exception:
            pass

        raise RuntimeError(
            "LLMJudge: No judge_fn provided and could not auto-detect an LLM client.\n"
            "Please pass a judge_fn callable, or install openai/anthropic:\n"
            "  pip install openai\n"
            "  pip install anthropic"
        )

    def _build_prompt(self, test_case: Union[TestCase, AgentTestCase]) -> str:
        expected_section = ""
        if self.include_expected and test_case.expected_output:
            expected_section = f"EXPECTED OUTPUT (for reference):\n{test_case.expected_output}\n\n"

        return _DEFAULT_EVAL_PROMPT.format(
            criteria=self.criteria,
            input=test_case.input,
            expected_section=expected_section,
            actual_output=test_case.actual_output,
            threshold=self.threshold,
        )

    def _parse_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        response = response.strip()

        # Strip markdown code blocks if present
        if "```json" in response:
            response = re.search(r"```json\s*([\s\S]*?)```", response).group(1)
        elif "```" in response:
            response = re.search(r"```\s*([\s\S]*?)```", response).group(1)

        # Try to find JSON object in response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            return json.loads(json_match.group())

        raise ValueError(f"Could not parse JSON from LLM response: {response[:200]}")

    def _run_once(self, judge: Callable[[str], str], prompt: str) -> tuple[float, str]:
        """Call the judge once and return (score, reason)."""
        response = judge(prompt)
        parsed = self._parse_response(response)
        score = float(parsed.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        reason = parsed.get("reason", "")
        return score, reason

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        try:
            judge = self.judge_fn or self._get_auto_judge()
            prompt = self._build_prompt(test_case)

            if self.num_runs == 1:
                score, reason = self._run_once(judge, prompt)
                passed = score >= self.threshold
                return MetricResult(
                    metric_name=self.name,
                    score=score,
                    passed=passed,
                    reason=reason,
                    metadata={"criteria": self.criteria},
                )

            # Multi-run: collect scores and detect flakiness
            scores: list[float] = []
            reasons: list[str] = []
            errors: list[str] = []

            for _ in range(self.num_runs):
                try:
                    s, r = self._run_once(judge, prompt)
                    scores.append(s)
                    reasons.append(r)
                except Exception as e:
                    errors.append(str(e))

            if not scores:
                return MetricResult(
                    metric_name=self.name,
                    score=0.0,
                    passed=False,
                    reason=f"All {self.num_runs} runs failed: {'; '.join(errors)}",
                )

            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)
            flaky = std_dev > self.flakiness_threshold

            # Pick the reason from the run whose score is closest to the mean
            closest_idx = min(range(len(scores)), key=lambda i: abs(scores[i] - mean_score))
            reason = reasons[closest_idx]
            if flaky:
                reason = f"[⚡ flaky: std_dev={std_dev:.3f} over {len(scores)} runs] {reason}"
            if errors:
                reason += f" ({len(errors)} run(s) errored)"

            return MetricResult(
                metric_name=self.name,
                score=round(mean_score, 4),
                passed=mean_score >= self.threshold,
                reason=reason,
                flakiness=round(std_dev, 4),
                metadata={
                    "criteria": self.criteria,
                    "num_runs": self.num_runs,
                    "all_scores": scores,
                    "all_reasons": reasons,
                    "flaky": flaky,
                    "flakiness_threshold": self.flakiness_threshold,
                    "run_errors": errors,
                },
            )

        except Exception as e:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=f"LLMJudge error: {e}",
            )


class GEval(BaseMetric):
    """
    G-Eval: chain-of-thought LLM evaluation with step-by-step reasoning.
    More reliable than simple LLM judge — asks the model to reason before scoring.

    Based on the paper: "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment"

    Example:
        metric = GEval(
            name="coherence",
            criteria="The response is logically consistent and flows naturally.",
            judge_fn=my_llm,
            threshold=0.7,
        )
    """

    _GEVAL_PROMPT = """You are an expert evaluator. Evaluate the AI response step-by-step.

EVALUATION CRITERIA: {criteria}

USER INPUT: {input}

AI RESPONSE: {actual_output}

Step 1: Identify what the criteria requires.
Step 2: Analyze the response against each requirement.
Step 3: Note any failures or successes.
Step 4: Assign a score from 0.0 to 1.0.

Finally, respond ONLY with JSON:
{{"score": <0.0-1.0>, "passed": <true/false>, "reason": "<your final reasoning>"}}"""

    def __init__(
        self,
        name: str,
        criteria: str,
        judge_fn: Optional[Callable[[str], str]] = None,
        threshold: float = 0.7,
        num_runs: int = 1,
        flakiness_threshold: float = 0.15,
    ):
        self.name = name
        self.criteria = criteria
        self.judge_fn = judge_fn
        self.threshold = threshold
        self.num_runs = max(1, num_runs)
        self.flakiness_threshold = flakiness_threshold
        self._llm_judge = LLMJudge(
            criteria=criteria,
            judge_fn=judge_fn,
            threshold=threshold,
        )

    def _run_once(self, judge: Callable[[str], str], prompt: str) -> tuple[float, str]:
        response = judge(prompt)
        parsed = self._llm_judge._parse_response(response)
        score = float(parsed.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        reason = parsed.get("reason", "")
        return score, reason

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        try:
            judge = self.judge_fn or self._llm_judge._get_auto_judge()
            prompt = self._GEVAL_PROMPT.format(
                criteria=self.criteria,
                input=test_case.input,
                actual_output=test_case.actual_output,
            )

            if self.num_runs == 1:
                score, reason = self._run_once(judge, prompt)
                return MetricResult(
                    metric_name=self.name,
                    score=score,
                    passed=score >= self.threshold,
                    reason=reason,
                )

            # Multi-run: collect scores and detect flakiness
            scores: list[float] = []
            reasons: list[str] = []
            errors: list[str] = []

            for _ in range(self.num_runs):
                try:
                    s, r = self._run_once(judge, prompt)
                    scores.append(s)
                    reasons.append(r)
                except Exception as e:
                    errors.append(str(e))

            if not scores:
                return MetricResult(
                    metric_name=self.name,
                    score=0.0,
                    passed=False,
                    reason=f"All {self.num_runs} runs failed: {'; '.join(errors)}",
                )

            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)
            flaky = std_dev > self.flakiness_threshold

            closest_idx = min(range(len(scores)), key=lambda i: abs(scores[i] - mean_score))
            reason = reasons[closest_idx]
            if flaky:
                reason = f"[⚡ flaky: std_dev={std_dev:.3f} over {len(scores)} runs] {reason}"
            if errors:
                reason += f" ({len(errors)} run(s) errored)"

            return MetricResult(
                metric_name=self.name,
                score=round(mean_score, 4),
                passed=mean_score >= self.threshold,
                reason=reason,
                flakiness=round(std_dev, 4),
                metadata={
                    "num_runs": self.num_runs,
                    "all_scores": scores,
                    "all_reasons": reasons,
                    "flaky": flaky,
                    "flakiness_threshold": self.flakiness_threshold,
                    "run_errors": errors,
                },
            )

        except Exception as e:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=f"GEval error: {e}",
            )
