# Changelog

All notable changes to Rubric will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
