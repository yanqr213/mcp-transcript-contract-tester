from __future__ import annotations

from typing import Any, Dict, List

from .models import Issue


def validate_arguments(schema: Dict[str, Any], value: Any, location: str) -> List[Issue]:
    """A deliberately small JSON Schema checker.

    It covers the parts that catch most transcript contract regressions without
    pretending to be a full JSON Schema implementation: type, required,
    properties, enum, arrays, and nested objects.
    """

    issues: List[Issue] = []
    _validate(schema or {}, value, location, issues)
    return issues


def _validate(schema: Dict[str, Any], value: Any, location: str, issues: List[Issue]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        issues.append(
            Issue(
                code="schema.type_mismatch",
                severity="error",
                message=f"Expected {expected_type}, got {_json_type(value)}.",
                location=location,
            )
        )
        return

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        issues.append(
            Issue(
                code="schema.enum_mismatch",
                severity="error",
                message="Value is not one of the allowed enum values.",
                location=location,
                details={"allowed": enum},
            )
        )

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for name in required:
                if isinstance(name, str) and name not in value:
                    issues.append(
                        Issue(
                            code="schema.required_missing",
                            severity="error",
                            message=f"Missing required argument '{name}'.",
                            location=f"{location}.{name}",
                        )
                    )

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for name, child_schema in properties.items():
                if name in value and isinstance(child_schema, dict):
                    _validate(child_schema, value[name], f"{location}.{name}", issues)

    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                _validate(items, item, f"{location}[{index}]", issues)


def _matches_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__
