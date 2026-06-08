from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .baseline import diff_against_baseline, load_baseline
from .models import severity_at_least
from .parser import ParseError, load_transcript
from .reporters import render_report
from .schema import load_tool_schemas
from .validators import validate_transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-transcript-contract-tester",
        description="Offline contract tester for MCP-like and custom agent tool transcripts.",
    )
    parser.add_argument("transcript", nargs="?", help="JSON or JSONL transcript file.")
    parser.add_argument(
        "--schema",
        dest="schema_path",
        help="Tool schema snapshot JSON. Supports MCP-like tools arrays and name-to-schema maps.",
    )
    parser.add_argument("--baseline", help="Previous JSON report to diff against.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "junit", "sarif"),
        default="markdown",
        help="Report format.",
    )
    parser.add_argument("--output", "-o", help="Write report to a file instead of stdout.")
    parser.add_argument(
        "--check",
        choices=("info", "warning", "error"),
        help="Exit non-zero when any issue is at least this severity.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from . import __version__

        print(__version__)
        return 0
    if not args.transcript:
        parser.error("the following arguments are required: transcript")

    try:
        messages = load_transcript(args.transcript)
        tools = load_tool_schemas(args.schema_path)
        report = validate_transcript(messages, tools, args.transcript, args.schema_path)
        if args.baseline:
            report.baseline_diff = diff_against_baseline(report, load_baseline(args.baseline))
        rendered = render_report(report, args.format)
    except (OSError, ParseError, ValueError) as exc:
        print(f"mcp-transcript-contract-tester: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if args.check and any(severity_at_least(issue.severity, args.check) for issue in report.issues):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
