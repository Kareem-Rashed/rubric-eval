"""
Trace importers for LangFuse and LangSmith.

Converts existing observability traces into Rubric TestCase / AgentTestCase
objects so you can run evals without touching your app code.

Usage:

    from rubriceval.integrations.loaders import load_langfuse, load_langsmith

    # LangFuse — export traces as JSON from the UI, then:
    test_cases = load_langfuse("traces.json")

    # LangSmith — export runs as JSON from the UI or REST API, then:
    test_cases = load_langsmith("runs.json")

    # Run evals on your existing traces
    report = rubric.evaluate(test_cases=test_cases, metrics=[
        HallucinationScore(judge_fn=...),
        ToolCallAccuracy(),
    ])
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Union

from rubriceval.core.test_case import AgentTestCase, TestCase, ToolCall, TraceStep


# ── Text extraction helpers ────────────────────────────────────────────────────

def _extract_text(value) -> str:
    """
    Best-effort extraction of a plain string from LLM input/output fields,
    which are often nested dicts (e.g. OpenAI message format).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        # Common single-key patterns
        for key in ("output", "text", "content", "response", "answer", "result", "query", "input", "question"):
            if key in value and isinstance(value[key], str):
                return value[key]

        # OpenAI chat format: {"messages": [{"role": "...", "content": "..."}]}
        if "messages" in value and isinstance(value["messages"], list):
            msgs = value["messages"]
            # For inputs: take the last user message
            user_msgs = [m.get("content", "") for m in msgs if m.get("role") == "user"]
            if user_msgs:
                return user_msgs[-1]
            # For outputs: take the last assistant message
            assistant_msgs = [m.get("content", "") for m in msgs if m.get("role") == "assistant"]
            if assistant_msgs:
                return assistant_msgs[-1]
            # Fallback: last message content
            if msgs and "content" in msgs[-1]:
                return msgs[-1]["content"]

        # OpenAI completion format: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in value and isinstance(value["choices"], list):
            choices = value["choices"]
            if choices:
                msg = choices[0].get("message", {})
                if "content" in msg:
                    return msg["content"]
                if "text" in choices[0]:
                    return choices[0]["text"]

        # Fallback: serialize to string
        return json.dumps(value)

    if isinstance(value, list):
        parts = [_extract_text(item) for item in value if item]
        return " ".join(p for p in parts if p)

    return str(value)


def _parse_latency_ms(start, end) -> float | None:
    """Calculate latency in ms from two ISO 8601 timestamp strings."""
    if not start or not end:
        return None
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in str(start) else "%Y-%m-%dT%H:%M:%S"
        t0 = datetime.fromisoformat(str(start).replace("Z", ""))
        t1 = datetime.fromisoformat(str(end).replace("Z", ""))
        return max(0.0, (t1 - t0).total_seconds() * 1000)
    except Exception:
        return None


def _load_json_or_jsonl(path: str) -> list:
    """Load a file that is either a JSON array or newline-delimited JSON."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Try JSON array first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Try JSONL
    records = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ── LangFuse loader ────────────────────────────────────────────────────────────

def load_langfuse(
    path: str,
) -> List[Union[TestCase, AgentTestCase]]:
    """
    Load LangFuse traces exported as JSON and convert them to Rubric test cases.

    How to export from LangFuse:
        Dashboard → Traces → Select traces → Export → JSON

    Each trace becomes a TestCase (simple LLM call) or AgentTestCase (if the
    trace contains tool call observations).

    Args:
        path: Path to the exported JSON or JSONL file.

    Returns:
        List of TestCase or AgentTestCase objects ready for rubric.evaluate().

    Example:
        test_cases = load_langfuse("langfuse_export.json")
        report = rubric.evaluate(test_cases=test_cases, metrics=[
            HallucinationScore(judge_fn=my_llm),
            ToolCallAccuracy(),
        ])
    """
    records = _load_json_or_jsonl(path)
    test_cases = []

    for record in records:
        # A record may be a trace (top-level) or contain observations
        observations = record.get("observations", []) or record.get("spans", []) or []

        # Extract tool calls from observations
        tool_calls = []
        trace_steps = []

        for obs in observations:
            obs_type = obs.get("type", "")
            obs_input = _extract_text(obs.get("input"))
            obs_output = _extract_text(obs.get("output"))
            obs_name = obs.get("name", obs_type)

            # Tool call observations
            if obs_type == "tool":
                tool_calls.append(ToolCall(
                    name=obs_name,
                    arguments=obs.get("input") if isinstance(obs.get("input"), dict) else {},
                    output=obs_output or None,
                    latency_ms=_parse_latency_ms(obs.get("startTime"), obs.get("endTime")),
                ))

            # Nested toolCalls field inside a generation observation
            for tc in obs.get("toolCalls", []):
                tool_calls.append(ToolCall(
                    name=tc.get("name", ""),
                    arguments=tc.get("input", {}),
                    output=_extract_text(tc.get("output")),
                ))

            # Build trace steps
            step_type = {
                "generation": "llm_call",
                "span": "thought",
                "tool": "tool_call",
                "event": "observation",
            }.get(obs_type, obs_type)

            trace_steps.append(TraceStep(
                type=step_type,
                content=obs_output or obs_input,
                latency_ms=_parse_latency_ms(obs.get("startTime"), obs.get("endTime")),
            ))

        # Token usage and cost
        usage = record.get("usage") or {}
        token_usage = None
        if usage.get("input") or usage.get("output"):
            token_usage = {
                "input": usage.get("input", 0),
                "output": usage.get("output", 0),
            }

        cost = record.get("costDetails", {})
        cost_usd = cost.get("total") if cost else None

        input_text = _extract_text(record.get("input"))
        output_text = _extract_text(record.get("output"))
        latency = _parse_latency_ms(
            record.get("startTime") or record.get("timestamp"),
            record.get("endTime"),
        )
        name = record.get("name") or record.get("id", "")[:16]

        if tool_calls:
            test_cases.append(AgentTestCase(
                input=input_text,
                actual_output=output_text,
                tool_calls=tool_calls,
                trace=trace_steps,
                latency_ms=latency,
                token_usage=token_usage,
                cost_usd=cost_usd,
                name=name,
                metadata={"source": "langfuse", "trace_id": record.get("id", "")},
            ))
        else:
            test_cases.append(TestCase(
                input=input_text,
                actual_output=output_text,
                latency_ms=latency,
                token_usage=token_usage,
                cost_usd=cost_usd,
                name=name,
                metadata={"source": "langfuse", "trace_id": record.get("id", "")},
            ))

    return test_cases


# ── LangSmith loader ───────────────────────────────────────────────────────────

def load_langsmith(
    path: str,
) -> List[Union[TestCase, AgentTestCase]]:
    """
    Load LangSmith runs exported as JSON and convert them to Rubric test cases.

    How to export from LangSmith:
        Project → Runs → Filter to root runs → Export as JSON
        Or via REST API: GET /api/v1/runs?is_root=true

    Each root run becomes a TestCase (simple LLM/chain) or AgentTestCase
    (if the run type is "agent" or it has child tool runs).

    Args:
        path: Path to the exported JSON or JSONL file.

    Returns:
        List of TestCase or AgentTestCase objects ready for rubric.evaluate().

    Example:
        test_cases = load_langsmith("langsmith_runs.json")
        report = rubric.evaluate(test_cases=test_cases, metrics=[
            ToolCallAccuracy(),
            LatencyMetric(max_ms=5000),
        ])
    """
    records = _load_json_or_jsonl(path)
    test_cases = []

    for record in records:
        run_type = record.get("run_type", "chain")
        child_runs = record.get("child_runs", []) or []

        # Extract tool calls from child runs with run_type == "tool"
        tool_calls = []
        trace_steps = []

        for child in child_runs:
            child_type = child.get("run_type", "")
            child_input = _extract_text(child.get("inputs"))
            child_output = _extract_text(child.get("outputs"))
            child_name = child.get("name", child_type)

            if child_type == "tool":
                tool_calls.append(ToolCall(
                    name=child_name,
                    arguments=child.get("inputs") if isinstance(child.get("inputs"), dict) else {},
                    output=child_output or None,
                    latency_ms=_parse_latency_ms(
                        child.get("start_time"), child.get("end_time")
                    ),
                    error=child.get("error"),
                ))

            step_type = {
                "llm": "llm_call",
                "chain": "thought",
                "tool": "tool_call",
                "retriever": "observation",
            }.get(child_type, child_type)

            trace_steps.append(TraceStep(
                type=step_type,
                content=child_output or child_input,
                latency_ms=_parse_latency_ms(
                    child.get("start_time"), child.get("end_time")
                ),
            ))

        # Token usage
        total_tokens = record.get("total_tokens")
        prompt_tokens = record.get("prompt_tokens")
        completion_tokens = record.get("completion_tokens")
        token_usage = None
        if prompt_tokens is not None or completion_tokens is not None:
            token_usage = {
                "input": prompt_tokens or 0,
                "output": completion_tokens or 0,
            }

        cost_usd = record.get("total_cost")
        input_text = _extract_text(record.get("inputs"))
        output_text = _extract_text(record.get("outputs"))
        latency = _parse_latency_ms(record.get("start_time"), record.get("end_time"))
        name = record.get("name") or record.get("id", "")[:16]

        is_agent = run_type == "agent" or bool(tool_calls)

        if is_agent:
            test_cases.append(AgentTestCase(
                input=input_text,
                actual_output=output_text,
                tool_calls=tool_calls,
                trace=trace_steps,
                latency_ms=latency,
                token_usage=token_usage,
                cost_usd=cost_usd,
                name=name,
                metadata={
                    "source": "langsmith",
                    "run_id": record.get("id", ""),
                    "run_type": run_type,
                    "tags": record.get("tags", []),
                },
            ))
        else:
            test_cases.append(TestCase(
                input=input_text,
                actual_output=output_text,
                latency_ms=latency,
                token_usage=token_usage,
                cost_usd=cost_usd,
                name=name,
                metadata={
                    "source": "langsmith",
                    "run_id": record.get("id", ""),
                    "run_type": run_type,
                    "tags": record.get("tags", []),
                },
            ))

    return test_cases
