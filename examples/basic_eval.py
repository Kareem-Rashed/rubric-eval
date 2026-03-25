"""
Rubric — Basic Example

This shows the simplest possible usage of Rubric.
No LLM API key required for ExactMatch / Contains metrics.

Run: python examples/basic_eval.py

Key patterns demonstrated:
  - Contains vs ExactMatch: LLMs return prose, not verbatim strings.
    Use Contains("Cairo") not ExactMatch when expected_output="Cairo"
    but the actual output is "The capital of Egypt is Cairo."
  - Per-test-case metrics: metrics apply to ALL test cases in one evaluate()
    call. Use separate evaluate() calls to scope a metric to a single test.
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


# ── Test cases ────────────────────────────────────────────────────────────────
france = rubric.TestCase(
    input="What is the capital of France?",
    actual_output=my_llm("What is the capital of France?"),
    expected_output="Paris",
    name="Capital of France",
)
math = rubric.TestCase(
    input="What is 2 + 2?",
    actual_output=my_llm("What is 2 + 2?"),
    expected_output="4",
    name="Basic math",
)
shakespeare = rubric.TestCase(
    input="Who wrote Hamlet?",
    actual_output=my_llm("Who wrote Hamlet?"),
    expected_output="Shakespeare",
    name="Shakespeare authorship",
)
egypt = rubric.TestCase(
    input="What is the capital of Egypt?",
    actual_output=my_llm("What is the capital of Egypt?"),
    expected_output="Cairo",
    name="Capital of Egypt",
)
planet = rubric.TestCase(
    input="What is the largest planet?",
    actual_output=my_llm("What is the largest planet?"),
    expected_output="Jupiter",
    name="Largest planet — should fail",
)

# ── Run 1: shared safety check across all tests ───────────────────────────────
# NotContains applies the same rule to every test — a good fit for shared checks.
rubric.evaluate(
    test_cases=[france, math, shakespeare, egypt, planet],
    metrics=[rubric.NotContains(["I don't know", "I'm not sure"])],
    verbose=False,
)

# ── Run 2: Contains — right metric for LLM prose output ──────────────────────
# LLMs return "The capital of Egypt is Cairo." not just "Cairo".
# Contains("Cairo") passes; ExactMatch(expected="Cairo") would wrongly fail.
# Metrics here apply to all 4 tests, so we use expected_output-based Contains
# by running each test separately.
for test in [france, math, shakespeare, egypt]:
    rubric.evaluate(
        test_cases=[test],
        metrics=[rubric.Contains(test.expected_output)],
        verbose=False,
    )

# ── Run 3: France-specific check — scoped metric via separate evaluate() call ─
# This is the pattern for per-test-case metrics: one evaluate() per test.
rubric.evaluate(
    test_cases=[france],
    metrics=[rubric.Contains("Paris")],  # only checked against the France test
    verbose=False,
)

# ── Run 4: Planet — intentional failure (answer is Saturn, not Jupiter) ───────
# Also writes the HTML/JSON report.
report = rubric.evaluate(
    test_cases=[planet],
    metrics=[rubric.Contains("Jupiter")],
    output_html="rubric_report.html",
    output_json="rubric_report.json",
)

print(f"\nPass rate (planet test): {report.pass_rate:.0%}  ← expected failure")
print(
    "\nTip: Use Contains or SemanticSimilarity for LLM output."
    " Reserve ExactMatch for structured data, code, or exact single-word answers."
)
