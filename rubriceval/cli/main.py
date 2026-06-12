"""
Rubric CLI — command-line interface for running evaluations.

Usage:
    rubric run examples/basic_eval.py
    rubric run examples/basic_eval.py --output-html report.html
    rubric run examples/basic_eval.py --output-json report.json
    rubric compare report.json --baseline evals/baseline.json
    rubric version
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        prog="rubric",
        description=" Rubric — Agent behavior testing for LLM apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rubric run my_evals.py
  rubric run my_evals.py --output-html report.html
  rubric run my_evals.py --output-json report.json --verbose
  rubric compare report.json --baseline evals/baseline.json --fail-on-regression

Docs: https://github.com/kareem-rashed/rubric-eval
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # rubric run
    run_parser = subparsers.add_parser("run", help="Run an evaluation file")
    run_parser.add_argument("file", help="Python file containing evaluate() calls")
    run_parser.add_argument(
        "--output-html", metavar="PATH", help="Write HTML report to this path"
    )
    run_parser.add_argument(
        "--output-json", metavar="PATH", help="Write JSON report to this path"
    )
    run_parser.add_argument(
        "--quiet", "-q", action="store_true", default=False, help="Suppress per-test output, show only final summary"
    )
    run_parser.add_argument(
        "--fail-on-error", action="store_true", help="Exit with code 1 if any test fails"
    )

    # rubric compare
    compare_parser = subparsers.add_parser(
        "compare", help="Diff a current report against a baseline (regression detection)"
    )
    compare_parser.add_argument(
        "current", help="Path to the current JSON report (from rubric run --output-json)"
    )
    compare_parser.add_argument(
        "--baseline", metavar="PATH",
        help="Path to the baseline JSON report (e.g. committed from main)",
    )
    compare_parser.add_argument(
        "--output-md", metavar="PATH",
        help="Write a PR-comment-ready markdown diff to this path",
    )
    compare_parser.add_argument(
        "--score-drop-threshold", type=float, default=0.1, metavar="FLOAT",
        help="Flag passing tests whose score dropped more than this (default: 0.1)",
    )
    compare_parser.add_argument(
        "--fail-on-regression", action="store_true",
        help="Exit with code 1 if any baseline-passing test now fails",
    )
    compare_parser.add_argument(
        "--quiet", "-q", action="store_true", default=False,
        help="Suppress terminal output (markdown is still written)",
    )

    # rubric version
    subparsers.add_parser("version", help="Show Rubric version")

    args = parser.parse_args()

    if args.command == "version":
        from rubriceval import __version__
        print(f"Rubric v{__version__}")
        return

    if args.command == "run":
        _run_file(args)
        return

    if args.command == "compare":
        from rubriceval.cli.compare import run_compare
        sys.exit(run_compare(args))

    parser.print_help()


def _run_file(args):
    """Load and execute a Python eval file."""
    filepath = os.path.abspath(args.file)

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    # Inject CLI args into environment so evaluate() picks them up transparently
    os.environ["RUBRIC_OUTPUT_HTML"] = args.output_html or ""
    os.environ["RUBRIC_OUTPUT_JSON"] = args.output_json or ""
    if args.fail_on_error:
        os.environ["RUBRIC_RAISE_ON_FAILURE"] = "1"
    if args.quiet:
        os.environ["RUBRIC_QUIET"] = "1"

    # Load and execute the file
    spec = importlib.util.spec_from_file_location("rubric_eval_file", filepath)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"\n❌ Error running {filepath}:\n{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
