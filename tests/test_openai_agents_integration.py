"""Tests for the dependency-free OpenAI Agents SDK result adapter."""

from rubriceval import AgentTestCase, from_agents_sdk


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_from_agents_sdk_extracts_tool_call_output_and_trace():
    result = Obj(
        input="Where is order ORD-9821?",
        new_items=[
            Obj(
                type="tool_call_item",
                raw_item=Obj(
                    name="lookup_order",
                    arguments='{"order_id": "ORD-9821"}',
                    call_id="call_1",
                ),
            ),
            Obj(
                type="tool_call_output_item",
                raw_item=Obj(call_id="call_1"),
                output={"status": "shipped", "eta": "Friday"},
            ),
            Obj(
                type="message_output_item",
                raw_item=Obj(content=[Obj(type="output_text", text="It arrives Friday.")]),
            ),
        ],
        final_output="It arrives Friday.",
    )

    case = from_agents_sdk(result, expected_tools=["lookup_order"])

    assert isinstance(case, AgentTestCase)
    assert case.input == "Where is order ORD-9821?"
    assert case.actual_output == "It arrives Friday."
    assert case.tool_names_called == ["lookup_order"]
    assert case.tool_calls[0].arguments == {"order_id": "ORD-9821"}
    assert case.tool_calls[0].output == {"status": "shipped", "eta": "Friday"}
    assert [step.type for step in case.trace] == ["llm_call", "tool_call", "llm_call"]
    assert case.metadata == {"source": "openai_agents"}


def test_from_agents_sdk_accepts_mapping_items_and_structured_final_output():
    result = Obj(
        input=[
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": [{"type": "input_text", "text": "Run check"}]},
        ],
        new_items=[
            {
                "type": "tool_call_item",
                "raw_item": {"name": "check", "arguments": "not-json", "id": "c1"},
            },
            {
                "type": "tool_call_output_item",
                "raw_item": {"call_id": "c1"},
                "output": ["ok", 1],
            },
            {
                "type": "reasoning_item",
                "raw_item": {"summary": [{"text": "Validated the result."}]},
            },
        ],
        final_output={"status": "complete"},
    )

    case = from_agents_sdk(result, metadata={"run_id": "r1"})

    assert case.input == "Run check"
    assert case.actual_output == '{"status": "complete"}'
    assert case.tool_calls[0].arguments == {"_raw": "not-json"}
    assert case.tool_calls[0].output == ["ok", 1]
    assert case.trace[-1].type == "thought"
    assert case.metadata == {"source": "openai_agents", "run_id": "r1"}


def test_from_agents_sdk_captures_hosted_tool_payload_and_inline_results():
    result = Obj(
        input="Search the policy files",
        new_items=[
            {
                "type": "tool_call_item",
                "raw_item": {
                    "type": "file_search_call",
                    "id": "fs_1",
                    "queries": ["agent safety policy"],
                    "results": [{"file_id": "policy.md", "score": 0.91}],
                    "status": "completed",
                },
            }
        ],
        final_output="Found the policy.",
    )

    case = from_agents_sdk(result)

    assert case.tool_names_called == ["file_search"]
    assert case.tool_calls[0].arguments == {"queries": ["agent safety policy"]}
    assert case.tool_calls[0].output == [{"file_id": "policy.md", "score": 0.91}]
    assert case.trace[0].metadata == {"tool_calls": ["file_search"]}


def test_from_agents_sdk_captures_tool_search_items():
    result = Obj(
        input="Find the account lookup tool",
        new_items=[
            Obj(
                type="tool_search_call_item",
                raw_item=Obj(
                    type="tool_search_call",
                    call_id="call_search_1",
                    arguments={"query": "account balance"},
                    execution="server",
                    status="completed",
                ),
            ),
            Obj(
                type="tool_search_output_item",
                raw_item=Obj(
                    type="tool_search_output",
                    call_id="call_search_1",
                    tools=[{"name": "lookup_balance"}],
                    execution="server",
                    status="completed",
                ),
            ),
        ],
        final_output="Found it.",
    )

    case = from_agents_sdk(result)

    assert case.tool_names_called == ["tool_search"]
    assert case.tool_calls[0].arguments == {"query": "account balance"}
    assert case.tool_calls[0].output == [{"name": "lookup_balance"}]
    assert [step.type for step in case.trace] == ["llm_call", "tool_call"]


def test_from_agents_sdk_requires_new_items_shape():
    try:
        from_agents_sdk(Obj(final_output="done"))
        assert False, "expected ValueError"
    except ValueError as error:
        assert "new_items" in str(error)
