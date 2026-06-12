# Changelog

All notable changes to Rubric will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-06-12

Repositioned around what Rubric does best: **agent behavior testing** —
auto-capture agent runs, evaluate tool calls and traces, catch regressions in CI.

### Added
- **LangGraph / LangChain auto-capture** (`rubriceval.integrations.langgraph`):
  - `run_langgraph(agent, scenarios)` — run scenarios against a compiled graph and get
    fully-populated `AgentTestCase`s (tool calls, arguments, outputs, errors, trace,
    latency, token usage) with zero wiring
  - `from_langgraph(result)` — convert a `graph.invoke()` result in one call
  - `from_messages(messages)` — works with LangChain message objects **and** plain
    OpenAI-format dicts; duck-typed, no langchain dependency required
  - `AgentScenario` — declarative scenario spec with per-scenario expected/forbidden
    tools and metrics
- **Regression diffing** — `rubric compare current.json --baseline baseline.json`:
  - detects pass→fail regressions, score drops on passing tests, fixed tests,
    and new/removed tests, with failing-metric reasons inline
  - `--output-md` renders a PR-comment-ready markdown diff
  - `--fail-on-regression` for CI exit codes
- **GitHub Action** (`Kareem-Rashed/rubric-eval@v0.2.0`) — runs evals on PRs,
  compares against a committed baseline, and posts/updates a regression diff comment
- CI workflow running the test suite on Python 3.9 / 3.11 / 3.13
- Example: `examples/langgraph_eval.py` (runs with zero deps, no API keys)

### Added (previously unreleased on PyPI)
- `HallucinationScore` metric (LLM judge and NLI modes)
- `capture()` context manager and `@track` decorator for zero-friction call recording
- LangFuse / LangSmith trace importers (`load_langfuse`, `load_langsmith`)
- Per-test metrics on `TestCase` and `AgentTestCase`
- Flakiness detection for LLM judge metrics (score variance across repeated runs)

### Changed
- README and package description repositioned from "general LLM eval framework"
  to agent behavior testing

[0.2.0]: https://github.com/Kareem-Rashed/rubric-eval/releases/tag/v0.2.0

## [0.1.0] — 2025-03-25

### Added
- Core evaluation engine (`evaluate()`) with sequential and parallel execution modes
- `TestCase` and `AgentTestCase` data structures for LLM and agent evaluations
- `EvalReport`, `TestResult`, and `MetricResult` result types
- **String matching metrics** (zero dependencies): `ExactMatch`, `Contains`, `NotContains`, `RegexMatch`
- **Semantic metrics**: `SemanticSimilarity` (sentence-transformers), `RougeScore`
- **LLM judge metrics**: `LLMJudge`, `GEval` — works with OpenAI, Anthropic, or any callable
- **Agent metrics**: `ToolCallAccuracy`, `TraceQuality`, `TaskCompletion`, `LatencyMetric`, `CostMetric`
- **Advanced agent metrics**: `ToolCallEfficiency`, `SafetyCompliance`, `ReasoningQuality`, `ContextUtilization`
- Interactive self-contained HTML reports with per-metric breakdown and filter controls
- JSON report export for CI/CD pipelines
- Native pytest integration via `rubric_eval` fixture
- CLI: `rubric run <file>` with CI-friendly exit codes
- Zero required dependencies — optional extras: `[semantic]`, `[rouge]`, `[openai]`, `[anthropic]`, `[all]`
- Professional landing page at `docs/`

[0.1.0]: https://github.com/kareemrashed/rubric-eval/releases/tag/v0.1.0
