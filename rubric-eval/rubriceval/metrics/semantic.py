"""
Semantic similarity metric using sentence-transformers or cosine similarity.
Falls back gracefully if sentence-transformers is not installed.
"""

from __future__ import annotations

from typing import Optional, Union

from rubriceval.core.test_case import AgentTestCase, TestCase
from rubriceval.core.results import MetricResult
from rubriceval.metrics.base import BaseMetric


class SemanticSimilarity(BaseMetric):
    """
    Measures semantic similarity between actual and expected output
    using sentence-transformers embeddings and cosine similarity.

    Much more robust than exact match — handles paraphrasing, synonyms,
    and different phrasing of the same answer.

    Requires: pip install sentence-transformers

    Example:
        metric = SemanticSimilarity(threshold=0.8)
        metric = SemanticSimilarity(model="all-MiniLM-L6-v2", threshold=0.75)
    """

    name = "semantic_similarity"

    def __init__(
        self,
        threshold: float = 0.8,
        model: str = "all-MiniLM-L6-v2",
    ):
        self.threshold = threshold
        self.model_name = model
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for SemanticSimilarity.\n"
                    "Install it with: pip install sentence-transformers"
                )
        return self._model

    def _cosine_similarity(self, a, b) -> float:
        import numpy as np
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if test_case.expected_output is None:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason="No expected_output provided for SemanticSimilarity.",
            )

        try:
            model = self._load_model()
            embeddings = model.encode(
                [test_case.actual_output, test_case.expected_output]
            )
            score = self._cosine_similarity(embeddings[0], embeddings[1])
            score = max(0.0, min(1.0, score))
            passed = score >= self.threshold

            return MetricResult(
                metric_name=self.name,
                score=score,
                passed=passed,
                reason=(
                    f"Semantic similarity: {score:.3f} (threshold: {self.threshold})"
                ),
            )

        except ImportError as e:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=str(e),
            )
        except Exception as e:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=f"Error computing semantic similarity: {e}",
            )


class RougeScore(BaseMetric):
    """
    ROUGE score metric for text summarization / generation quality.
    Measures n-gram overlap between actual and expected output.

    Requires: pip install rouge-score

    Example:
        metric = RougeScore(rouge_type="rouge1", threshold=0.5)
        metric = RougeScore(rouge_type="rougeL", threshold=0.4)
    """

    name = "rouge_score"

    def __init__(
        self,
        rouge_type: str = "rougeL",
        score_key: str = "fmeasure",
        threshold: float = 0.5,
    ):
        self.rouge_type = rouge_type
        self.score_key = score_key
        self.threshold = threshold

    def measure(self, test_case: Union[TestCase, AgentTestCase]) -> MetricResult:
        if test_case.expected_output is None:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason="No expected_output provided for RougeScore.",
            )

        try:
            from rouge_score import rouge_scorer

            scorer = rouge_scorer.RougeScorer([self.rouge_type], use_stemmer=True)
            scores = scorer.score(
                test_case.expected_output, test_case.actual_output
            )
            score = getattr(scores[self.rouge_type], self.score_key)
            passed = score >= self.threshold

            return MetricResult(
                metric_name=f"{self.name}_{self.rouge_type}",
                score=score,
                passed=passed,
                reason=f"ROUGE-{self.rouge_type} {self.score_key}: {score:.3f}",
            )

        except ImportError:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason="rouge-score not installed. Run: pip install rouge-score",
            )
