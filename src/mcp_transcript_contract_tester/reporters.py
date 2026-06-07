from __future__ import annotations

import json
from xml.etree import ElementTree

from .models import Issue, Report


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"


def render_markdown(report: Report) -> str:
    summary = report.summary
    lines = [
        "# Transcript Contract Report",
        "",
        f"- Transcript: `{report.transcript_path}`",
        f"- Schema: `{report.schema_path or 'none'}`",
        f"- Messages: {report.total_messages}",
        f"- Requests: {summary.get('requests', 0)}",
        f"- Responses: {summary.get('responses', 0)}",
        f"- Tool calls: {summary.get('tool_calls', 0)}",
        f"- Issues: {summary.get('errors', 0)} error, {summary.get('warnings', 0)} warning, {summary.get('info', 0)} info",
        "",
    ]

    if report.baseline_diff:
        diff = report.baseline_diff
        lines.extend(
            [
                "## Baseline Diff",
                "",
                f"- New issues: {diff['new_issues']}",
                f"- Resolved issues: {diff['resolved_issues']}",
                f"- Unchanged issues: {diff['unchanged_issues']}",
                "",
            ]
        )

    lines.extend(["## Issues", ""])
    if not report.issues:
        lines.append("No issues found.")
    else:
        lines.extend(["| Severity | Code | Location | Message |", "| --- | --- | --- | --- |"])
        for issue in report.issues:
            lines.append(
                f"| {issue.severity} | `{issue.code}` | `{issue.location}` | {issue.message} |"
            )
    return "\n".join(lines) + "\n"


def render_junit(report: Report) -> str:
    suite = ElementTree.Element(
        "testsuite",
        {
            "name": "mcp-transcript-contract-tester",
            "tests": str(max(len(report.issues), 1)),
            "failures": str(sum(1 for issue in report.issues if issue.severity == "error")),
            "errors": "0",
        },
    )

    if not report.issues:
        ElementTree.SubElement(suite, "testcase", {"classname": "transcript", "name": "contract"})
    else:
        for issue in report.issues:
            case = ElementTree.SubElement(
                suite,
                "testcase",
                {"classname": issue.severity, "name": f"{issue.code} {issue.location}".strip()},
            )
            if issue.severity == "error":
                failure = ElementTree.SubElement(
                    case,
                    "failure",
                    {"type": issue.code, "message": issue.message},
                )
                failure.text = _issue_text(issue)
            elif issue.severity == "warning":
                skipped = ElementTree.SubElement(case, "skipped", {"message": issue.message})
                skipped.text = _issue_text(issue)
            else:
                system_out = ElementTree.SubElement(case, "system-out")
                system_out.text = _issue_text(issue)

    return _xml_to_string(suite)


def render_report(report: Report, output_format: str) -> str:
    renderers = {
        "json": render_json,
        "markdown": render_markdown,
        "junit": render_junit,
    }
    return renderers[output_format](report)


def _issue_text(issue: Issue) -> str:
    return "\n".join(
        [
            f"severity: {issue.severity}",
            f"code: {issue.code}",
            f"location: {issue.location}",
            f"message: {issue.message}",
        ]
    )


def _xml_to_string(element: ElementTree.Element) -> str:
    raw = ElementTree.tostring(element, encoding="unicode")
    # ElementTree already escapes text/attributes; html.unescape is not used.
    return '<?xml version="1.0" encoding="utf-8"?>\n' + raw + "\n"
