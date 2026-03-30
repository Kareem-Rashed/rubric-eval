"""
Rubric — LangChain Example

Shows how to evaluate a LangChain LCEL pipeline with Rubric.

Install extras:
    pip install langchain langchain-openai rubric-eval

Run:
    OPENAI_API_KEY=sk-... python examples/langchain_example.py

If LangChain is not installed the script falls back to a plain callable
so you can see the Rubric API without any extra dependencies.
"""

import rubriceval as rubric

# ── Build the chain (or a plain fallback) ─────────────────────────────────────

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a concise factual assistant. Answer in one sentence."),
            ("human", "{question}"),
        ]
    )
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    chain = prompt | llm | StrOutputParser()

    def run_chain(question: str) -> str:
        return chain.invoke({"question": question})

    print("Using real LangChain LCEL chain (gpt-3.5-turbo)\n")

except ImportError:
    # ── Fallback: simulate responses so the example still runs ────────────────
    _RESPONSES = {
        "What is the capital of France?": "The capital of France is Paris.",
        "What is the boiling point of water in Celsius?": "Water boils at 100 degrees Celsius.",
        "Who wrote Romeo and Juliet?": "Romeo and Juliet was written by William Shakespeare.",
        "What is the speed of light?": "The speed of light is approximately 299,792 kilometres per second.",
        # Intentionally wrong to demonstrate a failing test:
        "What is the largest ocean on Earth?": "The largest ocean on Earth is the Atlantic Ocean.",
    }

    def run_chain(question: str) -> str:  # type: ignore[misc]
        return _RESPONSES.get(question, "I don't know.")

    print("LangChain not installed — using simulated responses.\n")
    print("Install with: pip install langchain langchain-openai\n")

# ── Define test cases ─────────────────────────────────────────────────────────

test_cases = [
    rubric.TestCase(
        name="Capital of France",
        input="What is the capital of France?",
        actual_output=run_chain("What is the capital of France?"),
        expected_output="Paris",
    ),
    rubric.TestCase(
        name="Boiling point of water",
        input="What is the boiling point of water in Celsius?",
        actual_output=run_chain("What is the boiling point of water in Celsius?"),
        expected_output="100",
    ),
    rubric.TestCase(
        name="Romeo and Juliet author",
        input="Who wrote Romeo and Juliet?",
        actual_output=run_chain("Who wrote Romeo and Juliet?"),
        expected_output="Shakespeare",
    ),
    rubric.TestCase(
        name="Speed of light",
        input="What is the speed of light?",
        actual_output=run_chain("What is the speed of light?"),
        expected_output="299,792 kilometres per second",
    ),
    rubric.TestCase(
        name="Largest ocean — should fail",
        input="What is the largest ocean on Earth?",
        actual_output=run_chain("What is the largest ocean on Earth?"),
        expected_output="Pacific",
    ),
]

# ── Evaluate with Contains ────────────────────────────────────────────────────
# Contains is the right choice for LLM/chain output: models return prose, not
# bare keywords, so ExactMatch would wrongly fail on "Paris" vs "… is Paris."

print("=== Run 1: Contains (keyword check) ===")
for tc in test_cases:
    rubric.evaluate(
        test_cases=[tc],
        metrics=[rubric.Contains(tc.expected_output)],
        verbose=True,
    )

# ── Evaluate with SemanticSimilarity ─────────────────────────────────────────
# SemanticSimilarity catches paraphrases that Contains misses.
# Requires: pip install rubric-eval[semantic]

print("\n=== Run 2: SemanticSimilarity ===")
try:
    rubric.evaluate(
        test_cases=test_cases,
        metrics=[rubric.SemanticSimilarity(threshold=0.7)],
        verbose=True,
    )
except Exception as exc:
    print(f"SemanticSimilarity skipped ({exc})")
    print("Install with: pip install rubric-eval[semantic]\n")

# ── Evaluate with LLMJudge ────────────────────────────────────────────────────
# LLMJudge uses an LLM to assess quality beyond surface matching.
# Requires: pip install rubric-eval[openai] and OPENAI_API_KEY set.

print("\n=== Run 3: LLMJudge ===")
try:
    rubric.evaluate(
        test_cases=test_cases,
        metrics=[rubric.LLMJudge(criteria="Is the answer factually correct and concise?")],
        verbose=True,
    )
except Exception as exc:
    print(f"LLMJudge skipped ({exc})")
    print("Install with: pip install rubric-eval[openai] and set OPENAI_API_KEY.\n")

# ── Final report with HTML output ────────────────────────────────────────────
# Use NotContains as a shared safety check across all test cases, then write
# the HTML report.  Per-test expected_output checks were already done in Run 1.

print("\n=== Run 4: Full report (shared safety check + HTML) ===")
report = rubric.evaluate(
    test_cases=test_cases,
    metrics=[rubric.NotContains(["I don't know", "I'm not sure", "Error"])],
    output_html="rubric_langchain_report.html",
    run_name="LangChain LCEL Evaluation",
)

print(f"\nPass rate: {report.pass_rate:.0%}")
print("HTML report written to rubric_langchain_report.html")
