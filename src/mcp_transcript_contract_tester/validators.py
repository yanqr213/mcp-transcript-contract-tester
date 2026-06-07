from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .jsonschema_lite import validate_arguments
from .models import Issue, Report
from .schema import ToolSpec


def validate_transcript(
    messages: List[Dict[str, Any]],
    tools: Dict[str, ToolSpec],
    transcript_path: str = "",
    schema_path: Optional[str] = None,
) -> Report:
    issues: List[Issue] = []
    requests: Dict[Any, Tuple[int, Dict[str, Any]]] = {}
    responses: Dict[Any, Tuple[int, Dict[str, Any]]] = {}
    method_counts: Counter[str] = Counter()
    tool_call_count = 0

    for index, message in enumerate(messages):
        location = f"messages[{index}]"
        issues.extend(_validate_message_shape(message, location))

        method = message.get("method")
        if isinstance(method, str):
            method_counts[method] += 1

        if _is_request(message):
            request_id = message["id"]
            if request_id in requests:
                issues.append(
                    Issue(
                        code="jsonrpc.duplicate_request_id",
                        severity="error",
                        message=f"Request id {request_id!r} is used more than once.",
                        location=location,
                    )
                )
            else:
                requests[request_id] = (index, message)

            tool_name, arguments = extract_tool_call(message, tools)
            if tool_name:
                tool_call_count += 1
                if tools and tool_name not in tools:
                    issues.append(
                        Issue(
                            code="tool.unknown",
                            severity="error",
                            message=f"Tool '{tool_name}' is not present in the schema snapshot.",
                            location=location,
                        )
                    )
                elif tool_name in tools:
                    issues.extend(validate_arguments(tools[tool_name].schema, arguments, f"{location}.arguments"))

        if _is_response(message):
            response_id = message.get("id")
            if response_id in responses:
                issues.append(
                    Issue(
                        code="jsonrpc.duplicate_response_id",
                        severity="warning",
                        message=f"Response id {response_id!r} appears more than once.",
                        location=location,
                    )
                )
            else:
                responses[response_id] = (index, message)
            issues.extend(_validate_response(message, location))
            issues.extend(_validate_result_metadata(message, location))

    request_ids = set(requests)
    response_ids = set(responses)
    for request_id in sorted(request_ids - response_ids, key=str):
        index, _ = requests[request_id]
        issues.append(
            Issue(
                code="jsonrpc.missing_response",
                severity="error",
                message=f"Request id {request_id!r} has no matching response.",
                location=f"messages[{index}]",
            )
        )
    for response_id in sorted(response_ids - request_ids, key=str):
        index, _ = responses[response_id]
        issues.append(
            Issue(
                code="jsonrpc.orphan_result",
                severity="error",
                message=f"Response id {response_id!r} does not match any request.",
                location=f"messages[{index}]",
            )
        )

    summary = {
        "errors": sum(1 for issue in issues if issue.severity == "error"),
        "warnings": sum(1 for issue in issues if issue.severity == "warning"),
        "info": sum(1 for issue in issues if issue.severity == "info"),
        "requests": len(requests),
        "responses": len(responses),
        "tool_calls": tool_call_count,
        "known_tools": len(tools),
        "methods": dict(sorted(method_counts.items())),
    }
    return Report(
        transcript_path=transcript_path,
        schema_path=schema_path,
        total_messages=len(messages),
        issues=issues,
        summary=summary,
    )


def extract_tool_call(message: Dict[str, Any], tools: Dict[str, ToolSpec]) -> Tuple[Optional[str], Any]:
    params = message.get("params")
    if not isinstance(params, dict):
        params = {}

    for key in ("name", "tool", "toolName", "tool_name"):
        value = params.get(key)
        if isinstance(value, str) and value:
            return value, _extract_arguments(params)

    for key in ("name", "tool", "toolName", "tool_name"):
        value = message.get(key)
        if isinstance(value, str) and value:
            return value, _extract_arguments(params or message)

    method = message.get("method")
    if isinstance(method, str):
        if method in tools:
            return method, _extract_arguments(params)
        if method in {"tools/call", "tool.call", "call_tool", "tools.call"}:
            name = params.get("name") or params.get("tool") or params.get("toolName")
            if isinstance(name, str):
                return name, _extract_arguments(params)

    return None, {}


def _extract_arguments(container: Dict[str, Any]) -> Any:
    for key in ("arguments", "args", "input", "parameters"):
        if key in container:
            return container[key]
    return {}


def _is_request(message: Dict[str, Any]) -> bool:
    return "id" in message and isinstance(message.get("method"), str) and "result" not in message and "error" not in message


def _is_response(message: Dict[str, Any]) -> bool:
    return "id" in message and ("result" in message or "error" in message)


def _validate_message_shape(message: Dict[str, Any], location: str) -> Iterable[Issue]:
    if message.get("jsonrpc") is not None and message.get("jsonrpc") != "2.0":
        yield Issue(
            code="jsonrpc.version",
            severity="warning",
            message="jsonrpc field is present but is not '2.0'.",
            location=location,
        )
    if "id" in message and isinstance(message.get("id"), (dict, list, bool)):
        yield Issue(
            code="jsonrpc.id_type",
            severity="error",
            message="id should be a string, number, or null.",
            location=f"{location}.id",
        )
    if "method" in message and not isinstance(message.get("method"), str):
        yield Issue(
            code="jsonrpc.method_type",
            severity="error",
            message="method must be a string when present.",
            location=f"{location}.method",
        )
    if "id" in message and "method" not in message and "result" not in message and "error" not in message:
        yield Issue(
            code="jsonrpc.incomplete_message",
            severity="error",
            message="Message with id has neither method nor result/error.",
            location=location,
        )


def _validate_response(message: Dict[str, Any], location: str) -> Iterable[Issue]:
    has_result = "result" in message
    has_error = "error" in message
    if has_result and has_error:
        yield Issue(
            code="jsonrpc.response_ambiguous",
            severity="error",
            message="Response must not contain both result and error.",
            location=location,
        )
    if has_error:
        error = message.get("error")
        if not isinstance(error, dict):
            yield Issue(
                code="jsonrpc.error_format",
                severity="error",
                message="error must be an object.",
                location=f"{location}.error",
            )
            return
        if not isinstance(error.get("code"), int) or isinstance(error.get("code"), bool):
            yield Issue(
                code="jsonrpc.error_code",
                severity="error",
                message="error.code must be an integer.",
                location=f"{location}.error.code",
            )
        if not isinstance(error.get("message"), str) or not error.get("message"):
            yield Issue(
                code="jsonrpc.error_message",
                severity="error",
                message="error.message must be a non-empty string.",
                location=f"{location}.error.message",
            )


def _validate_result_metadata(message: Dict[str, Any], location: str) -> Iterable[Issue]:
    if "result" not in message:
        return
    result = message.get("result")
    meta = {}
    if isinstance(result, dict):
        candidate = result.get("meta") or result.get("_meta") or result.get("metadata")
        if isinstance(candidate, dict):
            meta = candidate
        else:
            meta = result
    latency_key = _first_present(meta, ("latency_ms", "duration_ms", "elapsed_ms"))
    cost_key = _first_present(meta, ("cost_usd", "cost", "total_cost_usd"))
    has_latency = latency_key is not None
    has_cost = cost_key is not None
    if not has_latency:
        yield Issue(
            code="metadata.latency_missing",
            severity="warning",
            message="Result does not expose latency metadata such as latency_ms or duration_ms.",
            location=location,
        )
    elif not _is_number(meta[latency_key]) or meta[latency_key] < 0:
        yield Issue(
            code="metadata.latency_invalid",
            severity="warning",
            message="Latency metadata should be a non-negative number.",
            location=f"{location}.{latency_key}",
        )
    if not has_cost:
        yield Issue(
            code="metadata.cost_missing",
            severity="info",
            message="Result does not expose cost metadata such as cost_usd or cost.",
            location=location,
        )
    elif not _is_number(meta[cost_key]) or meta[cost_key] < 0:
        yield Issue(
            code="metadata.cost_invalid",
            severity="warning",
            message="Cost metadata should be a non-negative number.",
            location=f"{location}.{cost_key}",
        )


def _first_present(container: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    for key in keys:
        if key in container:
            return key
    return None


def _is_number(value: Any) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
