from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .parser import load_json_file


@dataclass(frozen=True)
class ToolSpec:
    name: str
    schema: Dict[str, Any]
    description: str = ""


def load_tool_schemas(path: Optional[str]) -> Dict[str, ToolSpec]:
    if not path:
        return {}
    data = load_json_file(path)
    return parse_tool_schemas(data)


def parse_tool_schemas(data: Any) -> Dict[str, ToolSpec]:
    """Parse common MCP-like and agent-tool schema snapshots.

    Supported shapes include:
    - {"tools": [{"name": "...", "inputSchema": {...}}]}
    - [{"name": "...", "schema": {...}}]
    - {"tool_name": {"type": "object", ...}}
    - {"tool_name": {"inputSchema": {...}}}
    """

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


def _schema_from_tool_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("inputSchema", "input_schema", "schema", "parameters", "args_schema"):
        value = item.get(key)
        if isinstance(value, dict):
            return value
    if item.get("type") == "object" or "properties" in item or "required" in item:
        return dict(item)
    return {}
