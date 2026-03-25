.PHONY: test lint build publish clean

# Run all tests
test:
	pytest tests/ -v

# Lint and format check
lint:
	ruff check rubriceval/ tests/
	ruff format --check rubriceval/ tests/

# Auto-fix lint issues
fmt:
	ruff check --fix rubriceval/ tests/
	ruff format rubriceval/ tests/

# Build the distribution packages (wheel + sdist)
build: clean
	python -m build

# Upload to PyPI (run 'make build' first)
# Requires: pip install twine  OR  pip install rubric-eval[dev]
# You'll be prompted for your PyPI API token.
publish: build
	twine upload dist/*

# Upload to TestPyPI first (safe to test before real PyPI)
publish-test: build
	twine upload --repository testpypi dist/*

# Remove build artifacts
clean:
	rm -rf dist/ build/ *.egg-info rubriceval.egg-info
