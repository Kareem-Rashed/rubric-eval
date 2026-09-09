"""OpenAI Agents SDK run auto-capture.

This module intentionally does not import ``openai-agents``.  The SDK result
and run-item objects are inspected by shape so Rubric keeps its zero required
dependencies while still accepting real ``RunResult`` instances.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from rubriceval.core.test_case import AgentTestCase, ToolCall, TraceStep

_MISSING = object()
_TOOL_METADATA_FIELDS = {
    "call_id",
    "created_by",
    "id",
    "name",
    "output",
    "outputs",
    "result",
    "results",
    "status",
    "type",
}


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _text(value: Any) -> str:
    """Convert SDK text/content values to stable plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for block in value:
            text = _field(block, "text")
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    if isinstance(value, Mapping) or isinstance(value, (tuple, set)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            pass
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return json.dumps(model_dump(), ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            pass
    return str(value)


def _arguments(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value) if value.strip() else {}
        except (TypeError, ValueError):
            return {"_raw": value}
        return parsed if isinstance(parsed, dict) else {"_raw": value}
    return {"_raw": value}


def _tool_name(item: Any, raw: Any) -> str:
    name = _field(item, "tool_name") or _field(raw, "name")
    if name:
        return str(name)
    raw_type = str(_field(raw, "type", ""))
    return raw_type.removesuffix("_call")


def _tool_arguments(raw: Any) -> dict[str, Any]:
    explicit = _field(raw, "arguments", _MISSING)
    if explicit is not _MISSING:
        return _arguments(explicit)

    if isinstance(raw, Mapping):
        payload = dict(raw)
    else:
        model_dump = getattr(raw, "model_dump", None)
        if callable(model_dump):
            try:
                payload = model_dump(exclude_none=True)
            except TypeError:
                payload = model_dump()
        else:
            payload = vars(raw) if hasattr(raw, "__dict__") else {}

    if not isinstance(payload, Mapping):
        return {}
    return {
        str(key): value
        for key, value in payload.items()
        if key not in _TOOL_METADATA_FIELDS and not str(key).startswith("_") and value is not None
    }


def _inline_tool_output(raw: Any) -> Any:
    for name in ("output", "outputs", "result", "results", "tools"):
        value = _field(raw, name, _MISSING)
        if value is not _MISSING and value is not None:
            return value
    return None


def _message_text(item: Any) -> str:
    raw = _field(item, "raw_item", item)
    return _text(_field(raw, "content", ""))


def _input_text(run_input: Any) -> str:
    if isinstance(run_input, str):
        return run_input
    if isinstance(run_input, list):
        for item in run_input:
            if str(_field(item, "role", "")).lower() == "user":
                return _text(_field(item, "content", ""))
    return _text(run_input)


def from_agents_sdk(result: Any, **kwargs: Any) -> AgentTestCase:
    """Build an :class:`AgentTestCase` from an OpenAI Agents SDK result.

    ``result`` may be a real ``RunResult`` or a stand-in exposing ``input``,
    ``new_items``, and ``final_output``.  Function tool calls and outputs are
    matched by ``call_id``; message items and tool activity become trace steps.
    Additional keyword arguments are forwarded to ``AgentTestCase``.
    """
    new_items = _field(result, "new_items", _MISSING)
    if new_items is _MISSING:
        raise ValueError(
            "from_agents_sdk() expected an OpenAI Agents SDK result with "
            f"a 'new_items' attribute, got {type(result).__name__}."
        )

    tool_calls: list[ToolCall] = []
    by_id: dict[str, ToolCall] = {}
    trace: list[TraceStep] = []

    for item in new_items or []:
        item_type = _field(item, "type", "")
        raw = _field(item, "raw_item", item)

        if item_type in {"tool_call_item", "tool_search_call_item", "handoff_call_item"}:
            name = _tool_name(item, raw)
            call_id = _field(item, "call_id") or _field(raw, "call_id") or _field(raw, "id")
            call = ToolCall(
                name=name,
                arguments=_tool_arguments(raw),
                output=_inline_tool_output(raw),
            )
            tool_calls.append(call)
            if call_id is not None:
                by_id[str(call_id)] = call
            trace.append(
                TraceStep(
                    type="llm_call",
                    content=f"[tool call: {name}]",
                    metadata={"tool_calls": [name]},
                )
            )

        elif item_type in {
            "tool_call_output_item",
            "tool_search_output_item",
            "handoff_output_item",
        }:
            call_id = _field(item, "call_id") or _field(raw, "call_id") or _field(raw, "id")
            matched_call = by_id.get(str(call_id)) if call_id is not None else None
            if matched_call is None:
                matched_call = next(
                    (candidate for candidate in tool_calls if candidate.output is None),
                    None,
                )
            if matched_call is None:
                matched_call = ToolCall(name="")
                tool_calls.append(matched_call)
            matched_call.output = _field(item, "output", _inline_tool_output(raw))
            trace.append(
                TraceStep(
                    type="tool_call",
                    content=matched_call.output,
                    metadata={"tool": matched_call.name},
                )
            )

        elif item_type == "message_output_item":
            message = _message_text(item)
            if message:
                trace.append(TraceStep(type="llm_call", content=message))

        elif item_type == "reasoning_item":
            summary = _text(_field(raw, "summary", ""))
            if summary:
                trace.append(TraceStep(type="thought", content=summary))

    metadata = {"source": "openai_agents"}
    metadata.update(kwargs.pop("metadata", None) or {})
    input_value = kwargs.pop("input", None)
    if input_value is None:
        input_value = _input_text(_field(result, "input", ""))

    return AgentTestCase(
        input=input_value,
        actual_output=_text(_field(result, "final_output", "")),
        tool_calls=tool_calls,
        trace=trace,
        metadata=metadata,
        **kwargs,
    )
