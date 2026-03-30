"""
Core test case definitions for Rubric.
Supports both simple LLM evaluations and complex agent trace evaluations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    """Represents a single tool/function call made by an agent."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    def __repr__(self) -> str:
        return f"ToolCall(name={self.name!r}, args={self.arguments})"


@dataclass
class TraceStep:
    """A single step in an agent's reasoning/execution trace."""

    type: str  # "llm_call", "tool_call", "thought", "observation"
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[float] = None

    def __repr__(self) -> str:
        return f"TraceStep(type={self.type!r}, content={str(self.content)[:80]})"


@dataclass
class TestCase:
    """
    A single evaluation test case for an LLM call.

    Example:
        test = TestCase(
            input="What is the capital of France?",
            actual_output=my_llm("What is the capital of France?"),
            expected_output="Paris",
            metrics=[Contains("Paris")],  # optional: per-test metrics
        )
    """

    input: str
    actual_output: str
    expected_output: Optional[str] = None
    context: Optional[str] = None  # RAG context, system prompt, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[float] = None
    token_usage: Optional[dict[str, int]] = None  # {"input": 50, "output": 20}
    cost_usd: Optional[float] = None
    name: Optional[str] = None
    metrics: list = field(default_factory=list)  # per-test metrics, merged with evaluate()-level metrics

    def __post_init__(self): #so user doesnt have to name every test, takees from context
        if self.name is None:
            self.name = self.input[:60] + ("..." if len(self.input) > 60 else "")

    def __repr__(self) -> str:
        return f"TestCase(name={self.name!r})"


@dataclass
class AgentTestCase:
    """
    An evaluation test case for an AI agent with tool use and multi-step reasoning.

    Example:
        test = AgentTestCase(
            input="Book a flight from Cairo to Paris on March 30",
            actual_output=agent.run("Book a flight from Cairo to Paris on March 30"),
            expected_tools=["search_flights", "book_flight"],
            expected_output="I've booked your flight to Paris.",
            tool_calls=agent.last_tool_calls,
            trace=agent.last_trace,
        )
    """

    input: str
    actual_output: str
    expected_output: Optional[str] = None
    expected_tools: Optional[list[str]] = None  # tools that MUST be called

    """could potentially add, valid_tools (when more than one could be used)"""
    
    forbidden_tools: Optional[list[str]] = None  # tools that must NOT be called
    tool_calls: list[ToolCall] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    context: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[float] = None
    token_usage: Optional[dict[str, int]] = None
    cost_usd: Optional[float] = None
    name: Optional[str] = None
    max_steps: Optional[int] = None  # expected max reasoning steps
    metrics: list = field(default_factory=list)  # per-test metrics, merged with evaluate()-level metrics

    def __post_init__(self):
        if self.name is None:
            self.name = self.input[:60] + ("..." if len(self.input) > 60 else "")

    @property
    def tool_names_called(self) -> list[str]:
        """Return list of all tool names called."""
        return [tc.name for tc in self.tool_calls]

    @property
    def steps_taken(self) -> int:
        return len(self.trace)

    def __repr__(self) -> str:
        return f"AgentTestCase(name={self.name!r}, tools={self.tool_names_called})"
