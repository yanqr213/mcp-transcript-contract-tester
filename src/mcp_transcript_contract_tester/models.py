from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    location: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        parts = [
            self.code,
            self.severity,
            self.location,
            self.message,
        ]
        return "|".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.location:
            data["location"] = self.location
        if self.details:
            data["details"] = self.details
        return data


@dataclass
class Report:
    transcript_path: str
    schema_path: Optional[str]
    total_messages: int
    issues: List[Issue]
    summary: Dict[str, Any]
    baseline_diff: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "transcript_path": self.transcript_path,
            "schema_path": self.schema_path,
            "total_messages": self.total_messages,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
        }
        if self.baseline_diff is not None:
            data["baseline_diff"] = self.baseline_diff
        return data


def severity_at_least(actual: str, threshold: str) -> bool:
    return SEVERITY_ORDER[actual] >= SEVERITY_ORDER[threshold]
