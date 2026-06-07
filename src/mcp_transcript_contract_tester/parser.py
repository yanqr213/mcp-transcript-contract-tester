from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class ParseError(ValueError):
    """Raised when a transcript or schema file cannot be parsed."""


def load_json_file(path: str) -> Any:
    file_path = Path(path)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ParseError(f"{file_path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def load_transcript(path: str) -> List[Dict[str, Any]]:
    """Load a JSON or JSONL transcript into a flat message list.

    Accepted JSON shapes:
    - [message, ...]
    - {"messages": [message, ...]}
    - {"transcript": [message, ...]}
    - one message object

    JSONL files are expected to contain one message object per non-empty line.
    """

    file_path = Path(path)
    if file_path.suffix.lower() == ".jsonl":
        return _load_jsonl(file_path)

    data = load_json_file(path)
    messages = _extract_messages(data)
    return _ensure_message_objects(messages, str(file_path))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ParseError(f"{path}: cannot read file: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"{path}:{line_number}: invalid JSON at column {exc.colno}: {exc.msg}"
            ) from exc
        if not isinstance(item, dict):
            raise ParseError(f"{path}:{line_number}: JSONL entries must be objects")
        messages.append(item)
    return messages


def _extract_messages(data: Any) -> List[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("messages", "transcript", "events"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    raise ParseError("transcript root must be an object, an array, or JSONL objects")


def _ensure_message_objects(messages: List[Any], source: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for index, item in enumerate(messages):
        if not isinstance(item, dict):
            raise ParseError(f"{source}: message #{index} must be an object")
        result.append(item)
    return result
