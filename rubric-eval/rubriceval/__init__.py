"""
Rubric — The independent LLM & AI agent evaluation framework.

Not owned by any AI company. Open source forever.

Quick start:
    pip install rubric-eval

    from rubriceval import evaluate, TestCase, ExactMatch, SemanticSimilarity

    results = evaluate(
        test_cases=[
            TestCase(
                input="What is the capital of France?",
                actual_output=my_llm("What is the capital of France?"),
                expected_output="The capital of France is Paris.",
            )
        ],
        metrics=[
            ExactMatch(),
            SemanticSimilarity(threshold=0.8),
        ],
    )
    results.print_summary()
"""

__version__ = "0.1.0"
__author__ = "Kareem Rashed"
__license__ = "MIT"

# Core
from rubriceval.core.test_case import TestCase, AgentTestCase, ToolCall, TraceStep
from rubriceval.core.results import EvalReport, TestResult, MetricResult
from rubriceval.core.evaluator import evaluate

# Metrics — string matching
from rubriceval.metrics.exact_match import ExactMatch, Contains, NotContains, RegexMatch

# Metrics — semantic
from rubriceval.metrics.semantic import SemanticSimilarity, RougeScore

# Metrics — LLM judge
from rubriceval.metrics.llm_judge import LLMJudge, GEval

# Metrics — agent & performance
from rubriceval.metrics.agent import (
    ToolCallAccuracy,
    TraceQuality,
    TaskCompletion,
    LatencyMetric,
    CostMetric,
)

# Base for custom metrics
from rubriceval.metrics.base import BaseMetric

__all__ = [
    # Core
    "evaluate",
    "TestCase",
    "AgentTestCase",
    "ToolCall",
    "TraceStep",
    "EvalReport",
    "TestResult",
    "MetricResult",
    # String metrics
    "ExactMatch",
    "Contains",
    "NotContains",
    "RegexMatch",
    # Semantic metrics
    "SemanticSimilarity",
    "RougeScore",
    # LLM judge
    "LLMJudge",
    "GEval",
    # Agent metrics
    "ToolCallAccuracy",
    "TraceQuality",
    "TaskCompletion",
    "LatencyMetric",
    "CostMetric",
    # Base
    "BaseMetric",
]
