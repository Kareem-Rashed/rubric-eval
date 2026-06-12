<div align="center">
  <img src="docs/logo.svg" alt="Rubric" width="72" height="72"/>
  <h1>Rubric</h1>
  <p><strong>Agent behavior testing for LLM apps.</strong></p>
  <p><em>Test what your agent <strong>did</strong> — tools called, arguments, trace, latency — not just what it said. Catch regressions in CI before they ship.</em></p>
</div>

[![PyPI version](https://badge.fury.io/py/rubric-eval.svg)](https://pypi.org/project/rubric-eval/)
[![CI](https://github.com/Kareem-Rashed/rubric-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/Kareem-Rashed/rubric-eval/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## The problem

Your agent passed every manual check. Then a prompt tweak shipped, and it quietly stopped calling `lookup_order` and started answering from memory. The responses still *look* fine — string-match evals and LLM judges that only see the final output can't catch it.

Rubric tests the **behavior**: which tools were called, with what arguments, in what order, whether forbidden tools were avoided, how clean the reasoning trace was, and how fast it ran. Zero required dependencies, fully local, MIT.

```bash
pip install rubric-eval
```

---

## Test a LangGraph agent in 60 seconds

No callbacks, no wrappers, no manual wiring. Rubric extracts tool calls, arguments, outputs, errors, the full trace, latency, and token usage from the messages your agent already produces.

```python
import rubriceval as rubric
from langgraph.prebuilt import create_react_agent

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
            forbidden_tools=["send_email"],   # must not bypass the ticketing system
        ),
    ]),
    metrics=[
        rubric.ToolCallAccuracy(),            # right tools? no forbidden ones?
        rubric.TraceQuality(),                # no loops, within step budget?
        rubric.LatencyMetric(max_ms=3000),
    ],
    output_html="report.html",
    output_json="report.json",
)
```

```
  [2/2] My account is locked, this is urgent.
    ❌ Score: 0.667
        ✗ tool_call_accuracy: 0.000 — Missing expected tools: ['create_ticket']; Called forbidden tools: ['send_email']
        ✓ trace_quality: 1.000 — Trace looks clean. 3 steps taken.
        ✓ latency: 1.000 — Latency 1840ms is within budget (3000ms).
```

Already have a result from `agent.invoke()`? One call:

```python
case = rubric.from_langgraph(result, expected_tools=["lookup_order"])
```

Not on LangGraph? `rubric.from_messages()` accepts any OpenAI-format message list (`role` / `content` / `tool_calls`), so it works with raw OpenAI tool-calling loops too. LangFuse and LangSmith trace exports load via `load_langfuse()` / `load_langsmith()`, and you can always construct an `AgentTestCase` by hand.

---

## Catch regressions in CI

Rubric ships a GitHub Action that runs your evals on every PR, diffs against a baseline, and posts the result as a comment — like Codecov, but for agent behavior.

```yaml
# .github/workflows/eval.yml
name: Agent Evals
on: [pull_request]

permissions:
  pull-requests: write

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Kareem-Rashed/rubric-eval@v0.2.0
        with:
          eval-file: evals/regression.py
          baseline: evals/baseline.json
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

The PR comment looks like this:

> ## 🧪 Rubric eval — 🔻 1 regression
>
> | | Baseline | Current | Δ |
> |---|---|---|---|
> | Pass rate | 100.0% (12/12) | 91.7% (11/12) | 🔻 -0.08 |
> | Avg score | 0.96 | 0.89 | 🔻 -0.07 |
>
> ### 🔻 Regressions (1)
> - **Urgent — account locked** — pass → **fail** (score 1.00 → 0.67)
>   - `tool_call_accuracy`: 1.00 → 0.00 — Missing expected tools: ['create_ticket']; Called forbidden tools: ['send_email']

The same diff is available locally and in any CI system:

```bash
rubric run evals/regression.py --output-json current.json
rubric compare current.json --baseline evals/baseline.json --fail-on-regression
```

`rubric compare` flags pass→fail regressions, score drops on still-passing tests, fixed tests, and new/removed tests — with the failing metric's reason inline.

---

## Metrics

### Agent behavior (the core)
| Metric | Checks |
|--------|--------|
| `ToolCallAccuracy()` | Expected tools called, forbidden tools avoided, optional order check |
| `TraceQuality()` | No loops, within step budget |
| `TaskCompletion()` | The task was actually finished |
| `ToolCallEfficiency()` | No redundant or wasted tool calls |
| `SafetyCompliance()` | No unsafe actions in the trace |
| `ReasoningQuality()` | Coherent multi-step reasoning |
| `ContextUtilization()` | Provided context was actually used |
| `LatencyMetric(max_ms=...)` | Within latency budget |
| `CostMetric(max_cost_usd=...)` | Within cost budget |

### Output quality
| Metric | Checks |
|--------|--------|
| `LLMJudge(criteria=...)` | Custom LLM-based scoring — works with any callable (OpenAI, Anthropic, Ollama) |
| `GEval(name=..., criteria=...)` | Chain-of-thought LLM evaluation |
| `HallucinationScore()` | Output grounded in the provided context (LLM judge or NLI mode) |
| `SemanticSimilarity(threshold=...)` | Embedding similarity vs expected output (`[semantic]` extra) |
| `RougeScore()` | ROUGE overlap for summarization (`[rouge]` extra) |
| `ExactMatch()` / `Contains()` / `NotContains()` / `RegexMatch()` | String checks, zero dependencies |

LLM-judge metrics support repeated runs with **flakiness detection** — Rubric reports the score variance so you know when your judge, not your agent, is the unstable part.

### Custom metrics

```python
from rubriceval import BaseMetric, MetricResult

class NoApologySpam(BaseMetric):
    name = "no_apology_spam"
    threshold = 1.0

    def measure(self, test_case) -> MetricResult:
        count = test_case.actual_output.lower().count("sorry")
        return MetricResult(
            metric_name=self.name,
            score=1.0 if count <= 1 else 0.0,
            passed=count <= 1,
            reason=f"'sorry' appears {count} time(s).",
        )
```

---

## pytest integration

Evals as regular tests, via the built-in `rubric_eval` fixture:

```python
def test_agent_routes_urgent_requests(rubric_eval):
    result = agent.invoke({"messages": [{"role": "user", "content": "Account locked, urgent!"}]})
    rubric_eval.add(
        rubric.from_langgraph(result,
                              expected_tools=["create_ticket"],
                              forbidden_tools=["send_email"]),
        metrics=[rubric.ToolCallAccuracy()],
    )
    # auto-asserts at end of test
```

---

## CLI

```bash
rubric run evals/regression.py                      # run an eval file
rubric run evals/regression.py --output-html report.html --output-json report.json
rubric run evals/regression.py --quiet --fail-on-error
rubric compare current.json --baseline baseline.json --fail-on-regression
rubric version
```

The HTML report is a single self-contained file with per-test traces, tool calls, and per-metric breakdowns — open it locally, attach it to CI artifacts, no server needed.

---

## Why Rubric

- **Behavior-first.** Most eval frameworks score the final answer. Rubric's core abstraction is the agent run — tools, arguments, trace, latency — because that's where agent bugs actually live.
- **Zero wiring.** `run_langgraph()` / `from_messages()` turn the messages you already have into test cases. No SDK to thread through your app.
- **CI-native.** Baseline diffing, PR comments, and exit codes are built in, not a paid add-on.
- **Zero required dependencies, fully local.** `pip install rubric-eval` pulls in nothing else. Your prompts and traces never leave your machine.
- **Independent and MIT-licensed.** Not owned by an AI company or a platform vendor — no pressure to route your evals through anyone's cloud.

---

## Examples

- [`examples/langgraph_eval.py`](examples/langgraph_eval.py) — agent behavior testing end-to-end (runs with zero deps, no API keys)
- [`examples/eval.py`](examples/eval.py) — a production-realistic suite: FAQ bot + support agent

---

## Roadmap

See [ROADMAP.md](ROADMAP.md). Next up: auto-capture for CrewAI, the OpenAI Agents SDK, and MCP servers; baseline auto-update on merge; dataset loaders.

## Contributing

Contributions are welcome — the [issues](https://github.com/Kareem-Rashed/rubric-eval/issues) tagged `good first issue` are genuinely scoped to a first PR.

```bash
git clone https://github.com/Kareem-Rashed/rubric-eval
cd rubric-eval
pip install -e ".[dev]"
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT © [Kareem Rashed](https://github.com/Kareem-Rashed)
