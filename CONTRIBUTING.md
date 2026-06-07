# Contributing

Thanks for improving `mcp-transcript-contract-tester`.

## Development

This project targets Python 3.9+ and intentionally prefers the standard library.

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## Design principles

- Keep the tester offline. It should validate recorded transcripts and schema snapshots without contacting real MCP servers, model APIs, or tool servers.
- Keep protocol assumptions conservative. The project validates JSON-RPC-like structure and tool-call contracts without claiming to implement any official MCP version.
- Prefer small, dependency-free checks. Add third-party dependencies only when they clearly improve correctness or maintainability.
- Make CI output useful. Report formats should help developers spot regressions quickly.

## Pull request checklist

- Add or update focused unit tests.
- Update `README.md` when CLI behavior changes.
- Update `CHANGELOG.md` for user-visible changes.
- Include examples when adding a new transcript or schema shape.
