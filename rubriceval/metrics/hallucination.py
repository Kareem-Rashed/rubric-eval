"""
Hallucination detection metric.

Measures how faithful the actual output is to the provided context.
Score of 1.0 = fully faithful (no hallucination).
Score of 0.0 = fully hallucinated (nothing grounded in context).

Two modes:
- With judge_fn: uses an LLM to detect hallucinations. No extra dependencies.
- Without judge_fn: uses an NLI model (requires pip install transformers torch).
"""

from __future__ import annotations

from typing import Callable, Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult
from rubriceval.metrics.base import BaseMetric


_HALLUCINATION_PROMPT = """You are a hallucination detection expert. Your job is to determine whether an AI response is faithful to the provided context, or whether it contains hallucinated claims — statements not supported by or contradicting the context.

CONTEXT (the only source of truth):
{context}

AI RESPONSE TO EVALUATE:
{actual_output}

Instructions:
1. Identify every factual claim in the AI response.
2. Check each claim against the context.
3. A claim is hallucinated if it contradicts the context OR introduces information not present in the context.
4. Assign a faithfulness score from 0.0 to 1.0:
   - 1.0 = every claim is fully supported by the context
   - 0.5 = roughly half the claims are hallucinated or unsupported
   - 0.0 = the response is entirely hallucinated / contradicts the context

Respond ONLY with valid JSON:
{{"score": <0.0-1.0>, "passed": <true/false>, "reason": "<brief explanation listing any hallucinated claims>", "hallucinated_claims": [<list of hallucinated statements, empty if none>]}}

Pass threshold: {threshold}"""


class HallucinationScore(BaseMetric):
    """
    Detects hallucinations by checking if the actual output contains claims
    not supported by or contradicting the provided context.

    Score convention: higher is better.
        1.0 = fully faithful to context (no hallucination)
        0.0 = completely hallucinated

    Requires test_case.context to be set — hallucination detection without
    a reference context is undefined.

    Two modes:

    Mode 1 — LLM judge (no extra deps, requires API access):
        def my_judge(prompt: str) -> str: ...

        metric = HallucinationScore(judge_fn=my_judge, threshold=0.7)

    Mode 2 — NLI model (no API key, local inference):
        metric = HallucinationScore(threshold=0.7)
        # Requires: pip install transformers torch
        # Uses cross-encoder/nli-deberta-v3-small by default

    Example:
        context = "The Eiffel Tower is located in Paris, France. It was built in 1889."

        test = TestCase(
            input="Where is the Eiffel Tower?",
            actual_output="The Eiffel Tower is in Paris. It was built in 1889 and is 330 metres tall.",
            context=context,
        )

        metric = HallucinationScore(judge_fn=my_llm, threshold=0.5)
        result = metric.measure(test)
        # score < 1.0 because "330 metres tall" is not in context
    """

    name = "hallucination"

    def __init__(
        self,
        judge_fn: Optional[Callable[[str], str]] = None,
        threshold: float = 0.7,
        nli_model: str = "cross-encoder/nli-deberta-v3-small",
    ):
        self.judge_fn = judge_fn
        self.threshold = threshold
        self.nli_model = nli_model
        self._nli_pipeline = None

    # ── LLM judge mode ────────────────────────────────────────────────────────

    def _parse_llm_response(self, response: str) -> dict:
        import json
        import re

        response = response.strip()
        if "```json" in response:
            m = re.search(r"```json\s*([\s\S]*?)```", response)
            if m:
                response = m.group(1)
        elif "```" in response:
            m = re.search(r"```\s*([\s\S]*?)```", response)
            if m:
                response = m.group(1)

        m = re.search(r"\{[\s\S]*\}", response)
        if m:
            return json.loads(m.group())

        raise ValueError(f"Could not parse JSON from judge response: {response[:200]}")

    def _measure_with_judge(
        self, test_case: Union[TestCase, AgentTestCase]
    ) -> MetricResult:
        prompt = _HALLUCINATION_PROMPT.format(
            context=test_case.context,
            actual_output=test_case.actual_output,
            threshold=self.threshold,
        )
        response = self.judge_fn(prompt)
        parsed = self._parse_llm_response(response)

        score = float(parsed.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        passed = bool(parsed.get("passed", score >= self.threshold))
        reason = parsed.get("reason", "")
        hallucinated_claims = parsed.get("hallucinated_claims", [])

        metadata = {"hallucinated_claims": hallucinated_claims}
        if hallucinated_claims:
            reason = f"{reason} Hallucinated claims: {hallucinated_claims}"

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason=reason,
            metadata=metadata,
        )

    # ── NLI mode ──────────────────────────────────────────────────────────────

    def _load_nli_pipeline(self):
        if self._nli_pipeline is None:
            from transformers import pipeline
            self._nli_pipeline = pipeline(
                "zero-shot-classification",
                model=self.nli_model,
            )
        return self._nli_pipeline

    def _split_into_sentences(self, text: str) -> list[str]:
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _measure_with_nli(
        self, test_case: Union[TestCase, AgentTestCase]
    ) -> MetricResult:
        pipe = self._load_nli_pipeline()
        sentences = self._split_into_sentences(test_case.actual_output)

        if not sentences:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason="Empty output — no claims to hallucinate.",
            )

        hallucinated = []
        scores = []

        for sentence in sentences:
            result = pipe(
                sentence,
                candidate_labels=["supported by context", "not supported by context"],
                hypothesis_template="This statement is {} given the following context: " + test_case.context,
            )
            label_scores = dict(zip(result["labels"], result["scores"]))
            supported_score = label_scores.get("supported by context", 0.5)
            scores.append(supported_score)
            if supported_score < 0.5:
                hallucinated.append(sentence)

        faithfulness = sum(scores) / len(scores)
        faithfulness = max(0.0, min(1.0, faithfulness))
        passed = faithfulness >= self.threshold

        if hallucinated:
            reason = (
                f"Faithfulness: {faithfulness:.3f}. "
                f"Potentially hallucinated: {hallucinated}"
            )
        else:
            reason = f"Faithfulness: {faithfulness:.3f}. All claims appear grounded in context."

        return MetricResult(
            metric_name=self.name,
            score=faithfulness,
            passed=passed,
            reason=reason,
            metadata={"hallucinated_sentences": hallucinated},
        )

    # ── measure ───────────────────────────────────────────────────────────────

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if not test_case.context:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=(
                    "HallucinationScore requires test_case.context to be set. "
                    "Provide the reference context the LLM was given."
                ),
            )

        try:
            if self.judge_fn is not None:
                return self._measure_with_judge(test_case)
            else:
                return self._measure_with_nli(test_case)

        except ImportError:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=(
                    "NLI mode requires transformers and torch. "
                    "Run: pip install transformers torch\n"
                    "Or pass a judge_fn to use LLM-based detection instead."
                ),
                skipped=True,
            )
        except Exception as e:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=f"HallucinationScore error: {e}",
            )
