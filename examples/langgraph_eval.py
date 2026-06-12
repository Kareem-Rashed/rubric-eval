"""
Rubric — LangGraph Agent Evaluation Example

Evaluate a LangGraph agent's *behavior* — which tools it called, with what
arguments, whether it avoided forbidden tools, and how clean its trace was —
with zero manual wiring. Rubric extracts everything from the messages your
agent already produces.

With a real LangGraph agent it looks like this:

    from langgraph.prebuilt import create_react_agent
    import rubriceval as rubric

    agent = create_react_agent(model, tools=[lookup_order, create_ticket, send_email])

    report = rubric.evaluate(
        test_cases=rubric.run_langgraph(agent, scenarios=[
            rubric.AgentScenario(
                input="Where is my order #ORD-9821?",
                expected_tools=["lookup_order"],
            ),
            rubric.AgentScenario(
                input="My account is locked, this is urgent.",
                expected_tools=["create_ticket"],
                forbidden_tools=["send_email"],   # must not bypass ticketing
            ),
        ]),
        metrics=[rubric.ToolCallAccuracy(), rubric.TraceQuality(), rubric.LatencyMetric(max_ms=3000)],
        output_html="report.html",
    )

This file runs the exact same pipeline against a tiny simulated agent so you
can try it with zero dependencies and no API keys:

    python examples/langgraph_eval.py
"""

import rubriceval as rubric


# ─────────────────────────────────────────────────────────────────────────────
# A simulated customer-support agent.
# It mimics what create_react_agent returns: a state dict with "messages"
# containing AI tool calls and tool results. Swap this for your real agent.
# ─────────────────────────────────────────────────────────────────────────────

class SimulatedSupportAgent:
    def invoke(self, payload, config=None):
        question = payload["messages"][0]["content"]

        if "order" in question.lower():
            return {"messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": "", "tool_calls": [
                    {"id": "c1", "name": "lookup_order", "args": {"order_id": "ORD-9821"}},
                ]},
                {"role": "tool", "tool_call_id": "c1",
                 "content": '{"status": "shipped", "eta": "June 14"}'},
                {"role": "assistant",
                 "content": "Your order ORD-9821 shipped and arrives June 14."},
            ]}

        # Buggy behavior on urgent requests: emails the user directly
        # instead of opening a ticket. Rubric should catch this.
        return {"messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c2", "name": "send_email", "args": {"to": "user@example.com"}},
            ]},
            {"role": "tool", "tool_call_id": "c2", "content": "email sent"},
            {"role": "assistant", "content": "I've emailed you about your locked account."},
        ]}


agent = SimulatedSupportAgent()

report = rubric.evaluate(
    test_cases=rubric.run_langgraph(agent, scenarios=[
        rubric.AgentScenario(
            name="Order inquiry",
            input="Where is my order #ORD-9821?",
            expected_tools=["lookup_order"],
        ),
        rubric.AgentScenario(
            name="Urgent — account locked",
            input="My account is locked, this is urgent.",
            expected_tools=["create_ticket"],
            forbidden_tools=["send_email"],
        ),
    ]),
    metrics=[
        rubric.ToolCallAccuracy(),
        rubric.TraceQuality(penalize_loops=True),
        rubric.LatencyMetric(max_ms=3000),
    ],
)

# Expected outcome: "Order inquiry" passes; "Urgent — account locked" fails
# because the agent called send_email (forbidden) and never called create_ticket.
