"""
Rubric — Agent Evaluation Example

Shows how to evaluate AI agents with tool use, multi-step reasoning,
latency budgets, and task completion checks.

This is Rubric's biggest differentiator vs DeepEval and Promptfoo.

Run: python examples/agent_eval.py
"""

import time
import rubriceval as rubric
from rubriceval import AgentTestCase, ToolCall, TraceStep


# ── Simulate an agent (replace with your real agent) ────────────────────────
class FakeAgent:
    """Simulates an AI agent with tool calls. Replace with LangChain, CrewAI, etc."""

    def __init__(self):
        self.last_tool_calls = []
        self.last_trace = []
        self.latency_ms = 0

    def run(self, task: str) -> str:
        start = time.time()
        self.last_tool_calls = []
        self.last_trace = []

        if "flight" in task.lower():
            # Simulate a multi-step booking flow
            self.last_tool_calls = [
                ToolCall(name="search_flights", arguments={"origin": "CAI", "dest": "CDG"}),
                ToolCall(name="check_availability", arguments={"flight_id": "AF123"}),
                ToolCall(name="book_flight", arguments={"flight_id": "AF123", "seats": 1}),
            ]
            self.last_trace = [
                TraceStep(type="thought", content="User wants to book a flight to Paris."),
                TraceStep(type="tool_call", content="search_flights(CAI → CDG)"),
                TraceStep(type="observation", content="Found 3 available flights."),
                TraceStep(type="tool_call", content="check_availability(AF123)"),
                TraceStep(type="observation", content="AF123 has seats available."),
                TraceStep(type="tool_call", content="book_flight(AF123, seats=1)"),
                TraceStep(type="observation", content="Booking confirmed. Ref: RUB-2024-001"),
            ]
            result = "I've successfully booked your flight from Cairo to Paris (AF123). Your booking reference is RUB-2024-001."

        elif "weather" in task.lower():
            # Simulates calling a forbidden tool
            self.last_tool_calls = [
                ToolCall(name="get_weather", arguments={"city": "Cairo"}),
                ToolCall(name="send_email", arguments={"to": "user@example.com"}),  # forbidden!
            ]
            self.last_trace = [
                TraceStep(type="tool_call", content="get_weather(Cairo)"),
                TraceStep(type="tool_call", content="send_email(...)"),  # should not do this
            ]
            result = "The weather in Cairo is sunny, 32°C. I've emailed you the forecast."

        elif "summarize" in task.lower():
            # Long trace — tests TraceQuality
            self.last_tool_calls = [
                ToolCall(name="fetch_document", arguments={"url": "..."}),
                ToolCall(name="summarize_text", arguments={"max_words": 100}),
            ]
            self.last_trace = [
                TraceStep(type="tool_call", content="fetch_document(...)"),
                TraceStep(type="observation", content="Document fetched."),
                TraceStep(type="tool_call", content="summarize_text(max_words=100)"),
                TraceStep(type="observation", content="Summary generated."),
            ]
            result = "Here is the summary of the document: ..."

        else:
            result = "I'm not sure how to handle this task."

        self.latency_ms = (time.time() - start) * 1000
        return result


agent = FakeAgent()


# ── Test cases ───────────────────────────────────────────────────────────────
output1 = agent.run("Book a flight from Cairo to Paris")
test1 = AgentTestCase(
    input="Book a flight from Cairo to Paris",
    actual_output=output1,
    expected_output="I've booked your flight to Paris.",
    expected_tools=["search_flights", "book_flight"],
    tool_calls=agent.last_tool_calls,
    trace=agent.last_trace,
    latency_ms=agent.latency_ms,
    name="Flight booking",
    max_steps=10,
)

output2 = agent.run("What is the weather in Cairo?")
test2 = AgentTestCase(
    input="What is the weather in Cairo?",
    actual_output=output2,
    expected_tools=["get_weather"],
    forbidden_tools=["send_email"],  # agent should NOT email the user
    tool_calls=agent.last_tool_calls,
    trace=agent.last_trace,
    latency_ms=agent.latency_ms,
    name="Weather check — forbidden tool test",
)

output3 = agent.run("Summarize this document: https://example.com/doc")
test3 = AgentTestCase(
    input="Summarize this document",
    actual_output=output3,
    expected_tools=["fetch_document", "summarize_text"],
    tool_calls=agent.last_tool_calls,
    trace=agent.last_trace,
    latency_ms=agent.latency_ms,
    name="Document summarization",
    max_steps=6,
)

# ── Run evaluation ───────────────────────────────────────────────────────────
report = rubric.evaluate(
    test_cases=[test1, test2, test3],
    metrics=[
        rubric.ToolCallAccuracy(check_order=False),
        rubric.TraceQuality(penalize_loops=True),
        rubric.TaskCompletion(),          # heuristic-based (no LLM needed)
        rubric.LatencyMetric(max_ms=5000),
    ],
    output_html="rubric_agent_report.html",
)

print(f"\nAgent evaluation complete.")
print(f"Pass rate: {report.pass_rate:.0%} ({report.passed}/{report.total})")
