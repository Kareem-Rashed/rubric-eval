"""
LangGraph / LangChain agent auto-capture.

Turn an agent run into a fully-populated AgentTestCase with one call — tool
calls, arguments, outputs, errors, reasoning trace, latency, and token usage
are all extracted from the messages your agent already produces. No callbacks,
no wrappers, no manual wiring.

Works with:
- LangGraph (`create_react_agent`, any StateGraph with a "messages" key)
- LangChain message objects (AIMessage / ToolMessage / HumanMessage)
- Plain OpenAI-format message dicts ({"role": ..., "content": ..., "tool_calls": [...]})

Zero dependencies — extraction is duck-typed, so nothing from langchain or
langgraph is imported.

Usage:

    import rubriceval as rubric
    from rubriceval.integrations.langgraph import run_langgraph, AgentScenario

    agent = create_react_agent(model, tools=[lookup_order, create_ticket])

    report = rubric.evaluate(
        test_cases=run_langgraph(agent, scenarios=[
            AgentScenario(
                input="Where is my order #ORD-9821?",
                expected_tools=["lookup_order"],
            ),
            AgentScenario(
                input="My account is locked, this is urgent.",
                expected_tools=["create_ticket"],
                forbidden_tools=["send_email"],
            ),
        ]),
        metrics=[rubric.ToolCallAccuracy(), rubric.TraceQuality()],
    )

Or, if you already have a result from graph.invoke():

    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    case = from_langgraph(result, expected_tools=["lookup_order"])
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from rubriceval.core.test_case import AgentTestCase, ToolCall, TraceStep


# ── Message field extraction (duck-typed) ──────────────────────────────────────

def _role(msg: Any) -> str:
    """Normalized role: 'assistant', 'user', 'tool', 'system', or ''."""
    if isinstance(msg, dict):
        raw = msg.get("role") or msg.get("type") or ""
    else:
        raw = getattr(msg, "type", None) or getattr(msg, "role", None) or ""
    raw = str(raw).lower()
    return {
        "ai": "assistant",
        "aimessagechunk": "assistant",
        "human": "user",
    }.get(raw, raw)


def _content_text(msg: Any) -> str:
    """Extract plain text from a message's content (string or content blocks)."""
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in (None, "text") and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            elif isinstance(getattr(block, "text", None), str):
                parts.append(block.text)
        return "".join(parts)
    return str(content)


def _normalize_tool_call(tc: Any) -> tuple[Optional[str], str, dict]:
    """Return (id, name, args) from a LangChain or OpenAI-format tool call."""
    if isinstance(tc, dict):
        if "function" in tc:  # OpenAI format: arguments is a JSON string
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except (ValueError, TypeError):
                    args = {"_raw": args}
            return tc.get("id"), fn.get("name", ""), args or {}
        return tc.get("id"), tc.get("name", ""), tc.get("args") or {}
    args = getattr(tc, "args", None) or {}
    return getattr(tc, "id", None), getattr(tc, "name", ""), args


def _tool_calls_of(msg: Any) -> list:
    if isinstance(msg, dict):
        return msg.get("tool_calls") or []
    return getattr(msg, "tool_calls", None) or []


def _attr(msg: Any, key: str) -> Any:
    if isinstance(msg, dict):
        return msg.get(key)
    return getattr(msg, key, None)


# ── Core extraction ────────────────────────────────────────────────────────────

def from_messages(
    messages: List[Any],
    *,
    input: Optional[str] = None,
    name: Optional[str] = None,
    expected_output: Optional[str] = None,
    expected_tools: Optional[List[str]] = None,
    forbidden_tools: Optional[List[str]] = None,
    max_steps: Optional[int] = None,
    metrics: Optional[list] = None,
    latency_ms: Optional[float] = None,
    context: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AgentTestCase:
    """
    Build an AgentTestCase from a list of chat messages.

    Accepts LangChain message objects, OpenAI-format dicts, or a mix. Tool
    calls are matched to their results by tool_call_id; the final assistant
    message becomes actual_output; token usage is summed across AI messages.

    Args:
        messages: The full message history of the agent run.
        input: The user input. Defaults to the first user message.
        Other args are passed through to AgentTestCase.
    """
    tool_calls: list[ToolCall] = []
    by_id: dict[str, ToolCall] = {}
    trace: list[TraceStep] = []
    first_user: Optional[str] = None
    last_answer = ""
    tokens_in = 0
    tokens_out = 0
    saw_usage = False

    for msg in messages:
        role = _role(msg)
        text = _content_text(msg)

        if role == "user":
            if first_user is None:
                first_user = text
            else:
                trace.append(TraceStep(type="observation", content=text))

        elif role == "assistant":
            calls = _tool_calls_of(msg)
            for tc in calls:
                tc_id, tc_name, tc_args = _normalize_tool_call(tc)
                call = ToolCall(name=tc_name, arguments=tc_args)
                tool_calls.append(call)
                if tc_id:
                    by_id[tc_id] = call
            if text:
                last_answer = text
            usage = _attr(msg, "usage_metadata")
            if isinstance(usage, dict):
                tokens_in += usage.get("input_tokens", 0) or 0
                tokens_out += usage.get("output_tokens", 0) or 0
                saw_usage = True
            step_content = text or f"[tool calls: {[ _normalize_tool_call(tc)[1] for tc in calls ]}]"
            trace.append(TraceStep(
                type="llm_call",
                content=step_content,
                metadata={"tool_calls": [_normalize_tool_call(tc)[1] for tc in calls]} if calls else {},
            ))

        elif role == "tool":
            tc_id = _attr(msg, "tool_call_id")
            tool_name = _attr(msg, "name") or ""
            status = _attr(msg, "status")
            is_error = str(status).lower() == "error" if status else False

            call = by_id.get(tc_id) if tc_id else None
            if call is None:
                # No id match — attach to the first unanswered call with the
                # same name, or record a standalone call.
                for c in tool_calls:
                    if c.output is None and c.error is None and (not tool_name or c.name == tool_name):
                        call = c
                        break
            if call is None:
                call = ToolCall(name=tool_name)
                tool_calls.append(call)
            if is_error:
                call.error = text or "tool error"
            else:
                call.output = text
            trace.append(TraceStep(
                type="tool_call",
                content=text,
                metadata={"tool": call.name, "error": is_error},
            ))

    meta = {"source": "langgraph"}
    if metadata:
        meta.update(metadata)

    return AgentTestCase(
        input=input if input is not None else (first_user or ""),
        actual_output=last_answer,
        expected_output=expected_output,
        expected_tools=expected_tools,
        forbidden_tools=forbidden_tools,
        tool_calls=tool_calls,
        trace=trace,
        latency_ms=latency_ms,
        token_usage={"input": tokens_in, "output": tokens_out} if saw_usage else None,
        name=name,
        max_steps=max_steps,
        metrics=metrics or [],
        context=context,
        metadata=meta,
    )


def from_langgraph(result: Any, **kwargs) -> AgentTestCase:
    """
    Build an AgentTestCase from the result of graph.invoke() / agent.invoke().

    Accepts the state dict LangGraph returns (anything with a "messages" key)
    or a plain list of messages. All keyword args are forwarded to
    from_messages() — see it for the full list.

    Example:
        result = agent.invoke({"messages": [{"role": "user", "content": q}]})
        case = from_langgraph(result, expected_tools=["lookup_order"])
    """
    if isinstance(result, list):
        messages = result
    else:
        messages = None
        if isinstance(result, dict):
            messages = result.get("messages")
        if messages is None:
            messages = getattr(result, "messages", None)
        if messages is None:
            raise ValueError(
                "from_langgraph() expected a LangGraph result with a 'messages' key "
                f"or a list of messages, got {type(result).__name__}. "
                "If your graph state uses a different key, pass result[<your_key>] directly."
            )
    return from_messages(messages, **kwargs)


# ── Scenario runner ────────────────────────────────────────────────────────────

@dataclass
class AgentScenario:
    """
    One test scenario for run_langgraph(): the input to send and the behavior
    you expect back.

    Example:
        AgentScenario(
            input="My account is locked, this is urgent.",
            expected_tools=["create_ticket"],
            forbidden_tools=["send_email"],
            metrics=[rubric.Contains("ticket")],  # optional per-scenario metrics
        )
    """

    input: str
    name: Optional[str] = None
    expected_output: Optional[str] = None
    expected_tools: Optional[List[str]] = None
    forbidden_tools: Optional[List[str]] = None
    max_steps: Optional[int] = None
    metrics: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def run_langgraph(
    graph: Any,
    scenarios: List[AgentScenario],
    *,
    config: Optional[dict] = None,
    input_key: str = "messages",
) -> List[AgentTestCase]:
    """
    Run a compiled LangGraph agent on each scenario and return ready-to-evaluate
    AgentTestCases with tool calls, trace, and latency captured automatically.

    Args:
        graph: A compiled graph / agent with .invoke() (e.g. from create_react_agent).
        scenarios: What to send and what behavior to expect.
        config: Optional LangGraph config forwarded to invoke (e.g. thread_id).
        input_key: State key holding the message list (default "messages").

    Returns:
        List of AgentTestCase — pass straight to rubric.evaluate().

    Example:
        report = rubric.evaluate(
            test_cases=run_langgraph(agent, scenarios),
            metrics=[rubric.ToolCallAccuracy(), rubric.TraceQuality()],
        )
    """
    cases = []
    for scenario in scenarios:
        payload = {input_key: [{"role": "user", "content": scenario.input}]}
        start = time.perf_counter()
        if config is not None:
            result = graph.invoke(payload, config=config)
        else:
            result = graph.invoke(payload)
        latency_ms = (time.perf_counter() - start) * 1000

        cases.append(from_langgraph(
            result,
            input=scenario.input,
            name=scenario.name,
            expected_output=scenario.expected_output,
            expected_tools=scenario.expected_tools,
            forbidden_tools=scenario.forbidden_tools,
            max_steps=scenario.max_steps,
            metrics=scenario.metrics,
            latency_ms=latency_ms,
            metadata=scenario.metadata,
        ))
    return cases
