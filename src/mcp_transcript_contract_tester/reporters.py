from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List
from xml.etree import ElementTree

from .models import Issue, Report
from . import __version__


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


def render_sarif(report: Report) -> str:
    rules = _sarif_rules(report.issues)
    results = [_sarif_result(report, issue) for issue in report.issues]
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "mcp-transcript-contract-tester",
                        "semanticVersion": __version__,
                        "informationUri": "https://github.com/yanqr213/mcp-transcript-contract-tester",
                        "rules": rules,
                    }
                },
                "automationDetails": {"id": report.transcript_path or "transcript-contract"},
                "results": results,
                "properties": _run_properties(report),
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_report(report: Report, output_format: str) -> str:
    renderers = {
        "json": render_json,
        "markdown": render_markdown,
        "junit": render_junit,
        "sarif": render_sarif,
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


def _sarif_rules(issues: List[Issue]) -> List[Dict[str, Any]]:
    severities: Dict[str, str] = {}
    messages: Dict[str, str] = {}
    for issue in issues:
        if _severity_rank(issue.severity) > _severity_rank(severities.get(issue.code, "info")):
            severities[issue.code] = issue.severity
        messages.setdefault(issue.code, issue.message)
    return [
        {
            "id": code,
            "name": code.replace(".", " ").replace("_", " ").title(),
            "shortDescription": {"text": messages[code]},
            "fullDescription": {"text": _rule_help(code)},
            "defaultConfiguration": {"level": _sarif_level(severities[code])},
            "help": {"text": _rule_help(code), "markdown": _rule_help(code)},
            "properties": {"precision": "medium", "tags": ["mcp", "transcript", "agent-tools", "contract-testing"]},
        }
        for code in sorted(severities)
    ]


def _sarif_result(report: Report, issue: Issue) -> Dict[str, Any]:
    fingerprint_source = "|".join([report.transcript_path, report.schema_path or "", issue.fingerprint()])
    return {
        "ruleId": issue.code,
        "level": _sarif_level(issue.severity),
        "message": {"text": issue.message},
        "locations": [_sarif_location(report, issue)],
        "partialFingerprints": {
            "mcpTranscriptContractTester/v1": hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:32]
        },
        "properties": {
            "severity": issue.severity,
            "code": issue.code,
            "location": issue.location,
            "details": issue.details,
        },
    }


def _run_properties(report: Report) -> Dict[str, Any]:
    properties: Dict[str, Any] = {
        "summary": report.summary,
        "totalMessages": report.total_messages,
    }
    if report.schema_path:
        properties["schemaPath"] = report.schema_path
    if report.baseline_diff is not None:
        properties["baselineDiff"] = report.baseline_diff
    return properties


def _sarif_location(report: Report, issue: Issue) -> Dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": _artifact_uri(report.transcript_path)},
            "region": {"startLine": _location_line(issue.location)},
        },
        "logicalLocations": [
            {
                "name": issue.location or issue.code,
                "fullyQualifiedName": ".".join(part for part in [report.transcript_path, issue.location] if part),
                "kind": "function",
            }
        ],
    }


def _artifact_uri(path: str) -> str:
    return path.replace("\\", "/") if path else "transcript.json"


def _location_line(location: str) -> int:
    match = re.search(r"messages\[(\d+)\]", location or "")
    if match:
        return int(match.group(1)) + 1
    return 1


def _sarif_level(severity: str) -> str:
    if severity == "error":
        return "error"
    if severity == "warning":
        return "warning"
    return "note"


def _severity_rank(severity: str) -> int:
    return {"info": 0, "warning": 1, "error": 2}.get(severity, 0)


def _rule_help(code: str) -> str:
    if code.startswith("jsonrpc."):
        return "Review JSON-RPC request/response pairing, ids, response shape, and error object consistency in the recorded transcript."
    if code.startswith("schema."):
        return "The tool call arguments do not satisfy the provided tool schema snapshot. Update the transcript, schema, or tool wrapper validation."
    if code.startswith("tool."):
        return "The transcript references a tool that is not present in the schema snapshot."
    if code.startswith("metadata."):
        return "Add stable latency and cost metadata to tool results so CI can track agent runtime behavior."
    if code.startswith("baseline."):
        return "Compare this finding with the previous JSON baseline to decide whether the transcript contract changed intentionally."
    return "Review this transcript contract finding and update the recorded transcript, schema snapshot, or agent tool behavior."
