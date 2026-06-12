"""
Unit tests for the LangGraph / LangChain auto-capture integration.

Extraction is duck-typed, so these tests use lightweight stand-ins that mimic
LangChain message objects (.type/.content/.tool_calls/...) and OpenAI-format
dicts — no langchain install required.
Run: pytest tests/
"""

import rubriceval as rubric
from rubriceval import AgentTestCase
from rubriceval.integrations.langgraph import (
    AgentScenario,
    from_langgraph,
    from_messages,
    run_langgraph,
)


class Msg:
    """Mimics a LangChain message (AIMessage / ToolMessage / HumanMessage)."""

    def __init__(self, type, content="", tool_calls=None, tool_call_id=None,
                 name=None, status=None, usage_metadata=None):
        self.type = type
        self.content = content
        if tool_calls is not None:
            self.tool_calls = tool_calls
        if tool_call_id is not None:
            self.tool_call_id = tool_call_id
        if name is not None:
            self.name = name
        if status is not None:
            self.status = status
        if usage_metadata is not None:
            self.usage_metadata = usage_metadata


def react_run():
    """A typical create_react_agent message history: ask → tool call → answer."""
    return [
        Msg("human", "Where is my order #ORD-9821?"),
        Msg("ai", "", tool_calls=[
            {"name": "lookup_order", "args": {"order_id": "ORD-9821"}, "id": "call_1"},
        ], usage_metadata={"input_tokens": 120, "output_tokens": 15}),
        Msg("tool", '{"status": "shipped", "eta": "June 14"}',
            tool_call_id="call_1", name="lookup_order"),
        Msg("ai", "Your order shipped and arrives June 14.",
            usage_metadata={"input_tokens": 160, "output_tokens": 22}),
    ]


# ── from_messages: LangChain-style objects ───────────────────────────────────

def test_extracts_tool_calls_with_outputs():
    case = from_messages(react_run())
    assert isinstance(case, AgentTestCase)
    assert case.tool_names_called == ["lookup_order"]
    assert case.tool_calls[0].arguments == {"order_id": "ORD-9821"}
    assert "shipped" in case.tool_calls[0].output
    assert case.tool_calls[0].error is None


def test_extracts_input_and_final_output():
    case = from_messages(react_run())
    assert case.input == "Where is my order #ORD-9821?"
    assert case.actual_output == "Your order shipped and arrives June 14."


def test_builds_trace_steps():
    case = from_messages(react_run())
    assert [s.type for s in case.trace] == ["llm_call", "tool_call", "llm_call"]


def test_aggregates_token_usage():
    case = from_messages(react_run())
    assert case.token_usage == {"input": 280, "output": 37}


def test_tool_error_status_sets_error():
    messages = [
        Msg("human", "Cancel order #1"),
        Msg("ai", "", tool_calls=[{"name": "cancel_order", "args": {}, "id": "c1"}]),
        Msg("tool", "Order not found", tool_call_id="c1", name="cancel_order", status="error"),
        Msg("ai", "I couldn't find that order."),
    ]
    case = from_messages(messages)
    assert case.tool_calls[0].error == "Order not found"
    assert case.tool_calls[0].output is None


def test_content_blocks_are_flattened():
    messages = [
        Msg("human", "hi"),
        Msg("ai", [{"type": "text", "text": "Hello "}, {"type": "text", "text": "there"}]),
    ]
    case = from_messages(messages)
    assert case.actual_output == "Hello there"


def test_tool_result_without_id_matches_by_name():
    messages = [
        Msg("human", "q"),
        Msg("ai", "", tool_calls=[{"name": "search", "args": {"q": "x"}}]),
        Msg("tool", "results...", name="search"),
        Msg("ai", "done"),
    ]
    case = from_messages(messages)
    assert case.tool_calls[0].output == "results..."


# ── from_messages: OpenAI-format dicts ───────────────────────────────────────

def test_openai_dict_messages():
    messages = [
        {"role": "user", "content": "Book a flight to Paris"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_a", "type": "function",
             "function": {"name": "search_flights", "arguments": '{"dest": "CDG"}'}},
        ]},
        {"role": "tool", "tool_call_id": "call_a", "content": "3 flights found"},
        {"role": "assistant", "content": "I found 3 flights to Paris."},
    ]
    case = from_messages(messages)
    assert case.tool_names_called == ["search_flights"]
    assert case.tool_calls[0].arguments == {"dest": "CDG"}
    assert case.tool_calls[0].output == "3 flights found"
    assert case.actual_output == "I found 3 flights to Paris."


def test_openai_malformed_arguments_kept_raw():
    messages = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "tool_calls": [
            {"id": "c", "function": {"name": "t", "arguments": "not json"}},
        ]},
    ]
    case = from_messages(messages)
    assert case.tool_calls[0].arguments == {"_raw": "not json"}


# ── from_langgraph ───────────────────────────────────────────────────────────

def test_from_langgraph_accepts_state_dict():
    case = from_langgraph({"messages": react_run()}, expected_tools=["lookup_order"])
    assert case.expected_tools == ["lookup_order"]
    assert case.tool_names_called == ["lookup_order"]


def test_from_langgraph_accepts_message_list():
    case = from_langgraph(react_run())
    assert case.tool_names_called == ["lookup_order"]


def test_from_langgraph_rejects_unknown_shape():
    try:
        from_langgraph(42)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "messages" in str(e)


# ── run_langgraph ────────────────────────────────────────────────────────────

class FakeGraph:
    """Mimics a compiled LangGraph agent: invoke(state) -> state with messages."""

    def __init__(self):
        self.payloads = []

    def invoke(self, payload, config=None):
        self.payloads.append((payload, config))
        question = payload["messages"][0]["content"]
        return {"messages": [Msg("human", question)] + react_run()[1:]}


def test_run_langgraph_builds_cases_with_latency():
    graph = FakeGraph()
    scenarios = [
        AgentScenario(input="Where is my order #ORD-9821?",
                      expected_tools=["lookup_order"], forbidden_tools=["send_email"]),
        AgentScenario(input="Track #ORD-5555", name="tracking"),
    ]
    cases = run_langgraph(graph, scenarios)
    assert len(cases) == 2
    assert all(c.latency_ms is not None and c.latency_ms >= 0 for c in cases)
    assert cases[0].expected_tools == ["lookup_order"]
    assert cases[0].forbidden_tools == ["send_email"]
    assert cases[1].name == "tracking"
    # the scenario input was sent to the graph as a user message
    assert graph.payloads[0][0] == {"messages": [
        {"role": "user", "content": "Where is my order #ORD-9821?"}]}


def test_run_langgraph_forwards_config():
    graph = FakeGraph()
    run_langgraph(graph, [AgentScenario(input="q")],
                  config={"configurable": {"thread_id": "t1"}})
    assert graph.payloads[0][1] == {"configurable": {"thread_id": "t1"}}


# ── End-to-end with metrics ──────────────────────────────────────────────────

def test_extracted_case_works_with_tool_call_accuracy():
    case = from_messages(react_run(), expected_tools=["lookup_order", "create_ticket"])
    result = rubric.ToolCallAccuracy().measure(case)
    assert not result.passed  # create_ticket was never called
    assert "create_ticket" in result.reason


def test_extracted_case_passes_evaluate():
    case = from_messages(react_run(), expected_tools=["lookup_order"])
    report = rubric.evaluate(
        test_cases=[case],
        metrics=[rubric.ToolCallAccuracy()],
        verbose=False,
        show_summary=False,
    )
    assert report.passed == 1
