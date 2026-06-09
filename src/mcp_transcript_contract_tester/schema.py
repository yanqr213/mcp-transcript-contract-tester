from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .parser import load_json_file


@dataclass(frozen=True)
class ToolSpec:
    name: str
    schema: Dict[str, Any]
    description: str = ""
    source: str = "schema"


def load_tool_schemas(path: Optional[str]) -> Dict[str, ToolSpec]:
    if not path:
        return {}
    data = load_json_file(path)
    return parse_tool_schemas(data)


def parse_tool_schemas(data: Any) -> Dict[str, ToolSpec]:
    """Parse common MCP-like and agent-tool schema snapshots.

    Supported shapes include:
    - {"tools": [{"name": "...", "inputSchema": {...}}]}
    - mcp-contract-recorder snapshots with {"format": "mcp-contract-recorder.snapshot/v1", "tools": {...}}
    - OpenAPI 3.1 documents exported by mcp-contract-recorder
    - [{"name": "...", "schema": {...}}]
    - {"tool_name": {"type": "object", ...}}
    - {"tool_name": {"inputSchema": {...}}}
    """

    if _is_recorder_snapshot(data):
        return _parse_recorder_snapshot(data)
    if _is_openapi_document(data):
        return _parse_openapi_document(data)

    tools: Dict[str, ToolSpec] = {}
    entries = data.get("tools") if isinstance(data, dict) and isinstance(data.get("tools"), list) else data

    if isinstance(entries, list):
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name") or item.get("tool")
            if not isinstance(name, str) or not name:
                continue
            schema = _schema_from_tool_item(item)
            tools[name] = ToolSpec(name=name, schema=schema, description=str(item.get("description", "")))
        return tools

    if isinstance(entries, dict):
        for name, item in entries.items():
            if not isinstance(name, str):
                continue
            if isinstance(item, Mapping):
                schema = _schema_from_tool_item(item)
                description = str(item.get("description", ""))
            else:
                schema = {}
                description = ""
            tools[name] = ToolSpec(name=name, schema=schema, description=description)
        return tools

    return tools


def _is_recorder_snapshot(data: Any) -> bool:
    return (
        isinstance(data, Mapping)
        and str(data.get("format", "")).startswith("mcp-contract-recorder.snapshot/")
        and isinstance(data.get("tools"), (Mapping, list))
    )


def _parse_recorder_snapshot(data: Mapping[str, Any]) -> Dict[str, ToolSpec]:
    tools: Dict[str, ToolSpec] = {}
    raw_tools = data.get("tools", {})
    if isinstance(raw_tools, Mapping):
        iterable = raw_tools.items()
    else:
        iterable = ((item.get("name", ""), item) for item in raw_tools if isinstance(item, Mapping))

    for fallback_name, item in iterable:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name") or fallback_name
        if not isinstance(name, str) or not name:
            continue
        tools[name] = ToolSpec(
            name=name,
            schema=_schema_from_tool_item(item),
            description=str(item.get("description", "")),
            source="mcp-contract-recorder",
        )
    return tools


def _is_openapi_document(data: Any) -> bool:
    return isinstance(data, Mapping) and str(data.get("openapi", "")).startswith("3.") and isinstance(data.get("paths"), Mapping)


def _parse_openapi_document(data: Mapping[str, Any]) -> Dict[str, ToolSpec]:
    tools: Dict[str, ToolSpec] = {}
    components = data.get("components") if isinstance(data.get("components"), Mapping) else {}
    schemas = components.get("schemas") if isinstance(components.get("schemas"), Mapping) else {}

    for path, path_item in sorted(data.get("paths", {}).items(), key=lambda item: str(item[0])):
        if not isinstance(path_item, Mapping):
            continue
        operation = _first_operation(path_item)
        if not operation:
            continue
        tool_name = _openapi_tool_name(operation, str(path))
        schema = _openapi_request_schema(operation, schemas)
        description = str(operation.get("description") or operation.get("summary") or "")
        tools[tool_name] = ToolSpec(name=tool_name, schema=schema, description=description, source="openapi")
    return tools


def _first_operation(path_item: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    for method in ("post", "put", "patch", "get", "delete"):
        operation = path_item.get(method)
        if isinstance(operation, Mapping):
            return operation
    return None


def _openapi_tool_name(operation: Mapping[str, Any], path: str) -> str:
    extension = operation.get("x-mcp-tool")
    if isinstance(extension, Mapping) and isinstance(extension.get("name"), str) and extension["name"]:
        return extension["name"]
    operation_id = operation.get("operationId")
    if isinstance(operation_id, str) and operation_id:
        return operation_id[5:] if operation_id.startswith("call_") else operation_id
    return path.rstrip("/").split("/")[-1] or path


def _openapi_request_schema(operation: Mapping[str, Any], components: Mapping[str, Any]) -> Dict[str, Any]:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, Mapping):
        return {}
    content = request_body.get("content")
    if not isinstance(content, Mapping):
        return {}
    media = content.get("application/json")
    if not isinstance(media, Mapping):
        media = next((value for value in content.values() if isinstance(value, Mapping)), {})
    schema = media.get("schema") if isinstance(media, Mapping) else None
    if isinstance(schema, Mapping):
        return _resolve_schema(schema, components)
    return {}


def _resolve_schema(schema: Mapping[str, Any], components: Mapping[str, Any]) -> Dict[str, Any]:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        target = components.get(name)
        if isinstance(target, Mapping):
            return dict(target)
    return dict(schema)


def _schema_from_tool_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("inputSchema", "input_schema", "schema", "parameters", "args_schema"):
        value = item.get(key)
        if isinstance(value, dict):
            return value
    if item.get("type") == "object" or "properties" in item or "required" in item:
        return dict(item)
    return {}
