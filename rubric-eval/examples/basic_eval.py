"""
Rubric — Basic Example

This shows the simplest possible usage of Rubric.
No LLM API key required for ExactMatch / Contains metrics.

Run: python examples/basic_eval.py
"""

import rubriceval as rubric


# ── Simulate an LLM (replace with your real LLM call) ──────────────────────
def my_llm(prompt: str) -> str:
    """Fake LLM for demo. Replace with real calls."""
    responses = {
        "What is the capital of France?": "The capital of France is Paris.",
        "What is 2 + 2?": "2 + 2 = 4",
        "Who wrote Hamlet?": "Hamlet was written by William Shakespeare.",
        "What is the capital of Egypt?": "The capital of Egypt is Cairo.",
        # Intentionally bad response to show a failure:
        "What is the largest planet?": "I believe it might be Saturn.",
    }
    return responses.get(prompt, "I don't know.")


# ── Define test cases ────────────────────────────────────────────────────────
test_cases = [
    rubric.TestCase(
        input="What is the capital of France?",
        actual_output=my_llm("What is the capital of France?"),
        expected_output="The capital of France is Paris.",
        name="Capital of France",
    ),
    rubric.TestCase(
        input="What is 2 + 2?",
        actual_output=my_llm("What is 2 + 2?"),
        expected_output="4",
        name="Basic math",
    ),
    rubric.TestCase(
        input="Who wrote Hamlet?",
        actual_output=my_llm("Who wrote Hamlet?"),
        expected_output="William Shakespeare",
        name="Shakespeare authorship",
    ),
    rubric.TestCase(
        input="What is the capital of Egypt?",
        actual_output=my_llm("What is the capital of Egypt?"),
        expected_output="Cairo",
        name="Capital of Egypt",
    ),
    rubric.TestCase(
        input="What is the largest planet?",
        actual_output=my_llm("What is the largest planet?"),
        expected_output="Jupiter",
        name="Largest planet — should fail",
    ),
]

# ── Run evaluation ───────────────────────────────────────────────────────────
report = rubric.evaluate(
    test_cases=test_cases,
    metrics=[
        rubric.ExactMatch(case_sensitive=False),
        rubric.Contains("Paris", require_all=False),  # only for France test
        rubric.NotContains(["I don't know", "I'm not sure"]),
    ],
    output_html="rubric_report.html",
    output_json="rubric_report.json",
)

# The summary is already printed by evaluate(), but you can also:
print(f"Pass rate: {report.pass_rate:.0%}")
print(f"Average score: {report.avg_score:.3f}")
