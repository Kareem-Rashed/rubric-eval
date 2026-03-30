"""
Rubric — Evaluation Example

This is how you'd use Rubric in a real project.

Scenario: a customer support AI system with two components:
  1. An FAQ bot — simple LLM responses to common questions
  2. A support agent — multi-step reasoning with tools for complex requests

Both are evaluated before shipping.

Swap the stub functions for your real LLM/agent calls. Everything else stays.

Run: python examples/eval.py
"""

import time
import rubriceval as rubric
from rubriceval import AgentTestCase, ToolCall, TraceStep


# ─────────────────────────────────────────────────────────────────────────────
# PART 1: FAQ BOT
# Simple LLM responses to common questions.
# ─────────────────────────────────────────────────────────────────────────────

# Replace with your real LLM call:
#   return openai.chat.completions.create(...).choices[0].message.content
#   return anthropic.messages.create(...).content[0].text

def faq_bot(question: str) -> str:
    responses = {
        "What are the pricing plans?":
            "We offer three plans: Starter ($29/mo, up to 5 users), "
            "Growth ($99/mo, up to 25 users), and Enterprise (custom pricing). "
            "All plans include a 14-day free trial.",

        "How do I cancel my subscription?":
            "Go to Settings → Billing → Cancel Subscription. "
            "Your access continues until the end of the current billing period "
            "and you can export your data at any time.",

        "What happens to my data if I cancel?":
            "Your data is retained for 30 days after cancellation. "
            "After 30 days it is permanently deleted. You can export it any time before then.",

        "Do you support SSO?":
            "SSO is available on Growth and Enterprise plans. "
            "We support SAML 2.0 with Okta, Azure AD, and Google Workspace.",

        # Intentionally vague — will fail the specificity check:
        "Is my payment information secure?":
            "Yes, we take security very seriously.",
    }
    return responses.get(question, "I'm not sure, please contact support.")


faq_tests = [
    rubric.TestCase(
        name="Pricing inquiry",
        input="What are the pricing plans?",
        actual_output=faq_bot("What are the pricing plans?"),
    ),
    rubric.TestCase(
        name="Cancellation flow",
        input="How do I cancel my subscription?",
        actual_output=faq_bot("How do I cancel my subscription?"),
    ),
    rubric.TestCase(
        name="Data retention after cancel",
        input="What happens to my data if I cancel?",
        actual_output=faq_bot("What happens to my data if I cancel?"),
    ),
    rubric.TestCase(
        name="SSO support",
        input="Do you support SSO?",
        actual_output=faq_bot("Do you support SSO?"),
    ),
    rubric.TestCase(
        name="Payment security",
        input="Is my payment information secure?",
        actual_output=faq_bot("Is my payment information secure?"),
    ),
]

# Safety check — applies to all FAQ responses
rubric.evaluate(
    test_cases=faq_tests,
    metrics=[rubric.NotContains(["I don't know", "I'm not sure", "contact support"])],
    run_name="FAQ Bot — Safety",
    verbose=False,
)

# Per-question content checks — each question requires specific information
content_checks = [
    (faq_tests[0], ["$29", "$99", "trial"]),
    (faq_tests[1], ["Settings", "Billing", "export"]),
    (faq_tests[2], ["30 days", "deleted"]),
    (faq_tests[3], ["Growth", "Enterprise", "SAML"]),
    (faq_tests[4], ["PCI", "encrypt"]),   # vague answer — will fail
]

print("=" * 60)
print("FAQ BOT — Content checks")
print("=" * 60)
for tc, required in content_checks:
    rubric.evaluate(
        test_cases=[tc],
        metrics=[rubric.Contains(required)],
        verbose=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PART 2: SUPPORT AGENT
# Handles complex requests with tools: order lookup, knowledge base search,
# ticket creation. Evaluated on whether it calls the right tools, stays
# within its boundaries, and completes tasks correctly.
# ─────────────────────────────────────────────────────────────────────────────

# Replace with your real agent. The key is capturing what it actually did:
# tool_calls, trace, and latency. Most agent frameworks expose these natively
# (LangChain callbacks, CrewAI event hooks, OpenAI function call logs, etc.).

class SupportAgent:
    """Stub agent — replace with your real one."""

    def __init__(self):
        self.tool_calls: list[ToolCall] = []
        self.trace: list[TraceStep] = []
        self.latency_ms: float = 0.0

    def run(self, user_message: str) -> str:
        self.tool_calls = []
        self.trace = []
        start = time.monotonic()

        if "order" in user_message.lower():
            self.trace.append(TraceStep(type="thought",
                content="User is asking about an order. I'll look it up first."))
            self.tool_calls.append(ToolCall(
                name="lookup_order",
                arguments={"order_id": "ORD-9821"},
                output='{"status": "in_transit", "eta": "2 days"}',
                latency_ms=210,
            ))
            self.trace.append(TraceStep(type="tool_call", content="lookup_order(ORD-9821)", latency_ms=210))
            self.trace.append(TraceStep(type="observation", content="Order in transit, ETA 2 days."))
            self.tool_calls.append(ToolCall(
                name="create_ticket",
                arguments={"type": "delivery_inquiry", "order_id": "ORD-9821"},
                output='{"ticket_id": "TKT-4421", "priority": "normal"}',
                latency_ms=185,
            ))
            self.trace.append(TraceStep(type="tool_call", content="create_ticket(delivery_inquiry)", latency_ms=185))
            self.trace.append(TraceStep(type="observation", content="Ticket TKT-4421 created."))
            result = ("Your order ORD-9821 is in transit and should arrive within 2 days. "
                      "I've created a ticket (TKT-4421) so our team can monitor it for you.")

        elif "return" in user_message.lower():
            self.trace.append(TraceStep(type="thought",
                content="User wants to return an item. Let me check the return policy."))
            self.tool_calls.append(ToolCall(
                name="search_knowledge_base",
                arguments={"query": "return policy"},
                output='{"answer": "30-day return window, item must be unused, free return label provided."}',
                latency_ms=175,
            ))
            self.trace.append(TraceStep(type="tool_call", content="search_knowledge_base(return policy)", latency_ms=175))
            self.trace.append(TraceStep(type="observation", content="Return policy retrieved."))
            result = ("You can return any unused item within 30 days for a full refund. "
                      "I've successfully generated a prepaid return label — just drop it off at any post office.")

        elif "locked" in user_message.lower() or "urgent" in user_message.lower():
            # Agent should create a ticket and escalate — but must NOT email the user directly.
            # send_email is a forbidden tool (agents shouldn't bypass the ticketing system).
            self.trace.append(TraceStep(type="thought",
                content="Account locked — high priority. I'll escalate via ticket immediately."))
            self.tool_calls.append(ToolCall(
                name="create_ticket",
                arguments={"type": "account_locked", "priority": "urgent"},
                output='{"ticket_id": "TKT-9901", "priority": "urgent", "eta_minutes": 15}',
                latency_ms=195,
            ))
            self.trace.append(TraceStep(type="tool_call", content="create_ticket(account_locked, urgent)", latency_ms=195))
            self.trace.append(TraceStep(type="observation", content="Urgent ticket TKT-9901 created. ETA: 15 min."))
            # Correctly does NOT call send_email
            result = ("I've successfully created an urgent ticket (TKT-9901) for your locked account. "
                      "Our team will reach out within 15 minutes.")

        else:
            result = "I'm not able to help with that. Please contact support."

        self.latency_ms = (time.monotonic() - start) * 1000
        return result


agent = SupportAgent()


def make_agent_test(name, message, expected_tools, forbidden_tools=None) -> AgentTestCase:
    output = agent.run(message)
    return AgentTestCase(
        name=name,
        input=message,
        actual_output=output,
        expected_tools=expected_tools,
        forbidden_tools=forbidden_tools or [],
        tool_calls=agent.tool_calls,
        trace=agent.trace,
        latency_ms=agent.latency_ms,
        max_steps=8,
    )


agent_tests = [
    make_agent_test(
        name="Order inquiry",
        message="Where is my order #ORD-9821?",
        expected_tools=["lookup_order", "create_ticket"],
    ),
    make_agent_test(
        name="Return request",
        message="I want to return an item I bought last week.",
        expected_tools=["search_knowledge_base"],
    ),
    make_agent_test(
        name="Urgent — account locked",
        message="My account is locked and I can't log in, this is urgent.",
        expected_tools=["create_ticket"],
        forbidden_tools=["send_email"],  # must escalate via ticket, not email directly
    ),
]

print("\n" + "=" * 60)
print("SUPPORT AGENT — Evaluation")
print("=" * 60)
rubric.evaluate(
    test_cases=agent_tests,
    metrics=[
        rubric.ToolCallAccuracy(check_order=False),
        rubric.TraceQuality(penalize_loops=True),
        rubric.TaskCompletion(),
        rubric.LatencyMetric(max_ms=3000),
    ],
    output_html="report.html",
    run_name="Support Agent — Pre-ship Eval",
)
