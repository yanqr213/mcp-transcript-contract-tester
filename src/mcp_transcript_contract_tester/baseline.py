from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from .models import Issue, Report


def load_baseline(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def diff_against_baseline(report: Report, baseline: Dict[str, Any]) -> Dict[str, Any]:
    baseline_issues = baseline.get("issues", [])
    old = _fingerprints_from_dicts(baseline_issues)
    new = {issue.fingerprint() for issue in report.issues}

    added = sorted(new - old)
    resolved = sorted(old - new)
    unchanged = sorted(new & old)

    current_summary = report.summary
    baseline_summary = baseline.get("summary", {})
    summary_delta = {}
    for key in ("errors", "warnings", "info", "requests", "responses", "tool_calls"):
        before = baseline_summary.get(key, 0)
        after = current_summary.get(key, 0)
        if before != after:
            summary_delta[key] = {"before": before, "after": after, "delta": after - before}

    return {
        "new_issues": len(added),
        "resolved_issues": len(resolved),
        "unchanged_issues": len(unchanged),
        "new_issue_fingerprints": added,
        "resolved_issue_fingerprints": resolved,
        "summary_delta": summary_delta,
    }


def _fingerprints_from_dicts(items: Iterable[Dict[str, Any]]) -> Set[str]:
    fingerprints: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        issue = Issue(
            code=str(item.get("code", "")),
            severity=str(item.get("severity", "")),
            message=str(item.get("message", "")),
            location=str(item.get("location", "")),
        )
        fingerprints.add(issue.fingerprint())
    return fingerprints
