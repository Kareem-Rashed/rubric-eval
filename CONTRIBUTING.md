# Contributing to Rubric

First off — thanks for being here. Rubric is built by developers for developers,
and every contribution matters, no matter how small.

## Ways to Contribute

- 🐛 **Bug reports** — open an issue with a minimal reproducible example
- 💡 **Feature requests** — open an issue with your use case
- 📝 **Documentation** — improve the README, add examples
- 🔧 **Code** — fix bugs, add metrics, improve performance
- ⭐ **Star** — helps others find the project

## Development Setup

```bash
git clone https://github.com/kareemrashed/rubric-eval
cd rubric-eval
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## Adding a New Metric

1. Create a file in `rubriceval/metrics/` (or add to an existing file)
2. Subclass `BaseMetric` and implement `measure()`
3. Export it from `rubriceval/__init__.py`
4. Add tests in `tests/test_metrics.py`
5. Document it in `README.md`

Example:
```python
from rubriceval.metrics.base import BaseMetric
from rubriceval.core.results import MetricResult

class MyNewMetric(BaseMetric):
    name = "my_new_metric"
    threshold = 0.5

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def measure(self, test_case) -> MetricResult:
        # Your scoring logic here
        score = 1.0  # 0.0 to 1.0
        passed = score >= self.threshold
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            reason="Explanation of the score",
        )
```

## Code Style

- Follow existing patterns
- Use type hints
- Write docstrings with examples
- Keep zero required dependencies as the default

## Commit Messages

Use conventional commits:
- `feat: add RougeScore metric`
- `fix: handle empty trace in TraceQuality`
- `docs: add LangChain integration example`
- `test: add ToolCallAccuracy edge cases`

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-metric`)
3. Make your changes
4. Run `pytest tests/` — all tests must pass
5. Open a PR with a clear description

## Code of Conduct

Be kind, be constructive, be helpful. That's it.
