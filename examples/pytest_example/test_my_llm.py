"""
Rubric — pytest Integration Example

Write LLM evaluations as normal pytest tests.
The `rubric_eval` fixture is auto-registered via pyproject.toml entry points.

Run: pytest examples/pytest_example/ -v
"""

import rubriceval as rubric


# ── Fake LLM (replace with your real one) ───────────────────────────────────
def my_llm(prompt: str) -> str:
    responses = {
        "What is the capital of Egypt?": "Cairo is the capital of Egypt.",
        "Is the sky blue?": "Yes, the sky appears blue due to Rayleigh scattering.",
        "What is 10 / 2?": "10 divided by 2 equals 5.",
    }
    return responses.get(prompt, "I don't know.")


# ── Tests using rubric_eval fixture ─────────────────────────────────────────

def test_geography(rubric_eval):
    """LLM should correctly identify Egypt's capital."""
    rubric_eval.add(
        rubric.TestCase(
            input="What is the capital of Egypt?",
            actual_output=my_llm("What is the capital of Egypt?"),
            expected_output="Cairo",
        ),
        metrics=[
            rubric.Contains("Cairo"),
            rubric.NotContains(["I don't know", "I'm not sure"]),
        ],
    )


def test_science(rubric_eval):
    """LLM should explain the sky's color scientifically."""
    rubric_eval.add(
        rubric.TestCase(
            input="Is the sky blue?",
            actual_output=my_llm("Is the sky blue?"),
            expected_output="Yes, the sky is blue because of Rayleigh scattering.",
        ),
        metrics=[
            rubric.Contains(["blue", "Rayleigh", "scattering"], require_all=False),
        ],
    )


def test_math(rubric_eval):
    """LLM should compute basic arithmetic correctly."""
    rubric_eval.add(
        rubric.TestCase(
            input="What is 10 / 2?",
            actual_output=my_llm("What is 10 / 2?"),
            expected_output="5",
        ),
        metrics=[
            rubric.Contains("5"),
            rubric.RegexMatch(r"\b5\b"),
        ],
    )


def test_multiple_cases(rubric_eval):
    """You can add multiple test cases in one test function."""
    questions = [
        ("What is the capital of Egypt?", "Cairo"),
        ("What is 10 / 2?", "5"),
    ]

    for question, expected in questions:
        rubric_eval.add(
            rubric.TestCase(
                input=question,
                actual_output=my_llm(question),
                expected_output=expected,
                name=question,
            ),
            metrics=[rubric.Contains(expected)],
        )
