# 📐 Rubric

**The independent LLM & AI agent evaluation framework.**

[![PyPI version](https://badge.fury.io/py/rubric-eval.svg)](https://badge.fury.io/py/rubric-eval)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/kareemrashed/rubric-eval?style=social)](https://github.com/kareemrashed/rubric-eval)

> **Not owned by any AI company. Open source forever.**
>
> Now that Promptfoo has joined OpenAI, the community needs a neutral eval framework.
> Rubric is built by developers, for developers — no conflict of interest.

---

## Why Rubric?

| | Rubric | DeepEval | Promptfoo |
|---|---|---|---|
| Open source | ✅ MIT | ✅ Apache | ✅ MIT (now OpenAI-owned) |
| Agent trace evaluation | ✅ First-class | ❌ Limited | ❌ No |
| Zero required dependencies | ✅ | ❌ Requires LLM API | ❌ Requires Node.js |
| Works with any LLM | ✅ Any callable | ✅ | ✅ |
| pytest integration | ✅ Native fixture | ✅ | ❌ YAML-based |
| Local HTML dashboard | ✅ Built-in | 💰 Paid cloud | ❌ No |
| Owned by AI company | ❌ Independent | ❌ Independent | ✅ OpenAI |

---

## Install

```bash
pip install rubric-eval

# Optional extras (install what you need):
pip install "rubric-eval[semantic]"   # SemanticSimilarity metric
pip install "rubric-eval[openai]"     # LLM judge via OpenAI
pip install "rubric-eval[anthropic]"  # LLM judge via Anthropic
pip install "rubric-eval[all]"        # Everything
```

---

## Quick Start

```python
import rubriceval as rubric

# 1. Define test cases
test_cases = [
    rubric.TestCase(
        input="What is the capital of France?",
        actual_output=my_llm("What is the capital of France?"),
        expected_output="The capital of France is Paris.",
    ),
    rubric.TestCase(
        input="What is 2 + 2?",
        actual_output=my_llm("What is 2 + 2?"),
        expected_output="4",
    ),
]

# 2. Run evaluation
report = rubric.evaluate(
    test_cases=test_cases,
    metrics=[
        rubric.ExactMatch(),
        rubric.Contains("Paris"),
        rubric.SemanticSimilarity(threshold=0.8),
    ],
    output_html="report.html",   # beautiful local dashboard
    output_json="report.json",   # for CI/CD
)

# 3. View results
report.print_summary()
```

**Output:**
```
🔍 Rubric — Running 2 test case(s) with 3 metric(s)...

  [1/2] What is the capital of France?
    ✅ Score: 1.000
        ✓ exact_match: 1.000
        ✓ contains: 1.000
        ✓ semantic_similarity: 0.952

  [2/2] What is 2 + 2?
    ✅ Score: 1.000

============================================================
  RUBRIC EVALUATION REPORT
  Total: 2   ✅ Passed: 2   Pass Rate: 100.0%   Avg Score: 1.000
============================================================
```

---

## Agent Evaluation (Rubric's Superpower)

Unlike other frameworks that only check final output, Rubric evaluates the **entire agent execution** — tool calls, reasoning trace, latency, and task completion.

```python
import rubriceval as rubric

# Your agent returns tool calls and a trace
result = my_agent.run("Book a flight from Cairo to Paris")

test = rubric.AgentTestCase(
    input="Book a flight from Cairo to Paris",
    actual_output=result.output,

    # Which tools MUST be called?
    expected_tools=["search_flights", "book_flight"],

    # Which tools must NOT be called? (safety guardrails)
    forbidden_tools=["send_email", "charge_card"],

    # Pass the actual tool calls your agent made
    tool_calls=result.tool_calls,

    # Pass the full reasoning trace
    trace=result.trace,

    latency_ms=result.latency_ms,
    max_steps=10,  # agent should complete in ≤ 10 steps
)

report = rubric.evaluate(
    test_cases=[test],
    metrics=[
        rubric.ToolCallAccuracy(check_order=True),  # Did it call the right tools?
        rubric.TraceQuality(penalize_loops=True),   # Did it avoid looping?
        rubric.TaskCompletion(),                     # Did it actually finish?
        rubric.LatencyMetric(max_ms=5000),           # Was it fast enough?
        rubric.CostMetric(max_cost_usd=0.05),        # Was it cheap enough?
    ],
)
```

---

## pytest Integration

Rubric integrates natively with pytest — write your evals as regular tests.

```python
# test_my_llm.py
def test_factual_accuracy(rubric_eval):
    rubric_eval.add(
        rubric.TestCase(
            input="What is the capital of Egypt?",
            actual_output=my_llm("What is the capital of Egypt?"),
            expected_output="Cairo",
        ),
        metrics=[rubric.Contains("Cairo"), rubric.SemanticSimilarity(threshold=0.8)],
    )
    # Auto-asserts at end of test — no extra code needed

def test_agent_books_flight(rubric_eval):
    result = agent.run("Book a flight to Paris")
    rubric_eval.add(
        rubric.AgentTestCase(
            input="Book a flight to Paris",
            actual_output=result.output,
            expected_tools=["search_flights", "book_flight"],
            tool_calls=result.tool_calls,
        ),
        metrics=[rubric.ToolCallAccuracy(), rubric.TaskCompletion()],
    )
```

```bash
pytest tests/ -v
```

---

## LLM-as-Judge

Use any LLM to evaluate response quality with custom criteria.
Works with OpenAI, Anthropic, Ollama, or any callable.

```python
from openai import OpenAI
client = OpenAI()

def my_judge(prompt: str) -> str:
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content

report = rubric.evaluate(
    test_cases=test_cases,
    metrics=[
        rubric.LLMJudge(
            criteria="Is the response accurate, concise, and helpful?",
            judge_fn=my_judge,
            threshold=0.7,
        ),
        rubric.GEval(
            name="coherence",
            criteria="The response is logically consistent and well-structured.",
            judge_fn=my_judge,
        ),
    ],
)
```

---

## Available Metrics

### String Matching (no dependencies)
| Metric | Description |
|--------|-------------|
| `ExactMatch()` | Exact string comparison (case-insensitive by default) |
| `Contains(substring)` | Output contains required string(s) |
| `NotContains(forbidden)` | Output does NOT contain forbidden strings |
| `RegexMatch(pattern)` | Output matches a regex pattern |

### Semantic (requires `pip install rubric-eval[semantic]`)
| Metric | Description |
|--------|-------------|
| `SemanticSimilarity(threshold=0.8)` | Cosine similarity via sentence-transformers |
| `RougeScore(rouge_type="rougeL")` | ROUGE overlap score for summarization |

### LLM Judge (requires an LLM API key)
| Metric | Description |
|--------|-------------|
| `LLMJudge(criteria=...)` | Custom LLM-based scoring |
| `GEval(name=..., criteria=...)` | Chain-of-thought LLM evaluation |

### Agent & Performance
| Metric | Description |
|--------|-------------|
| `ToolCallAccuracy()` | Were the right tools called? Were forbidden tools avoided? |
| `TraceQuality()` | Did the agent avoid loops and stay within step budget? |
| `TaskCompletion()` | Did the agent complete the task? |
| `LatencyMetric(max_ms=5000)` | Was the response within latency budget? |
| `CostMetric(max_cost_usd=0.01)` | Was the API cost within budget? |

### Custom Metrics
```python
from rubriceval import BaseMetric, MetricResult

class MyCustomMetric(BaseMetric):
    name = "my_metric"
    threshold = 0.5

    def measure(self, test_case) -> MetricResult:
        score = 1.0 if "good" in test_case.actual_output else 0.0
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            reason="Output contains 'good'." if score else "Output lacks 'good'.",
        )
```

---

## CLI

```bash
# Run an eval file
rubric run my_evals.py

# With HTML and JSON reports
rubric run my_evals.py --output-html report.html --output-json report.json

# Check version
rubric version
```

---

## CI/CD Integration

```yaml
# .github/workflows/eval.yml
name: LLM Evaluation
on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install rubric-eval
      - run: rubric run evals/regression.py --output-json report.json
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - uses: actions/upload-artifact@v4
        with:
          name: rubric-report
          path: report.json
```

Or use `raise_on_failure=True`:
```python
rubric.evaluate(
    test_cases=test_cases,
    metrics=[...],
    raise_on_failure=True,  # exits with code 1 if any test fails
)
```

---

## Roadmap

- [ ] 🌐 Web dashboard (local server with history)
- [ ] 📊 Dataset management (load from CSV/JSONL)
- [ ] 🔄 Regression detection (alert when pass rate drops)
- [ ] 🔗 LangChain / LlamaIndex / CrewAI integrations
- [ ] 📱 Slack/Discord notifications on eval failure
- [ ] 🔴 Real-time production monitoring

---

## Contributing

Rubric is built in the open. Contributions welcome!

```bash
git clone https://github.com/kareemrashed/rubric-eval
cd rubric-eval
pip install -e ".[dev]"
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT © [Kareem Rashed](https://github.com/kareemrashed)

---

<div align="center">
  <b>Built at AUC 🏛️ · Cairo, Egypt 🇪🇬</b>
  <br/>
  <sub>If Rubric saves you time, consider giving it a ⭐</sub>
</div>
