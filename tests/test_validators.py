import unittest

from mcp_transcript_contract_tester.schema import parse_tool_schemas
from mcp_transcript_contract_tester.validators import validate_transcript


class ValidatorTests(unittest.TestCase):
    def test_clean_transcript_has_no_errors(self):
        tools = parse_tool_schemas(
            {
                "tools": [
                    {
                        "name": "search",
                        "inputSchema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {"query": {"type": "string"}},
                        },
                    }
                ]
            }
        )
        messages = [
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "hello"}},
            },
            {
                "jsonrpc": "2.0",
                "id": "1",
                "result": {"content": [], "meta": {"latency_ms": 1, "cost_usd": 0}},
            },
        ]

        report = validate_transcript(messages, tools)

        self.assertEqual(report.summary["errors"], 0)
        self.assertEqual(report.summary["warnings"], 0)

    def test_detects_unknown_tool_missing_required_orphan_and_duplicate(self):
        tools = parse_tool_schemas(
            {
                "search": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                }
            }
        )
        messages = [
            {"id": "dup", "method": "tools/call", "params": {"name": "search", "arguments": {}}},
            {"id": "dup", "method": "tools/call", "params": {"name": "unknown", "arguments": {}}},
            {"id": "orphan", "result": {"content": []}},
        ]

        report = validate_transcript(messages, tools)
        codes = {issue.code for issue in report.issues}

        self.assertIn("jsonrpc.duplicate_request_id", codes)
        self.assertIn("schema.required_missing", codes)
        self.assertIn("tool.unknown", codes)
        self.assertIn("jsonrpc.orphan_result", codes)
        self.assertIn("jsonrpc.missing_response", codes)

    def test_detects_bad_error_format(self):
        report = validate_transcript(
            [
                {"id": "1", "method": "tools/call", "params": {"name": "x", "arguments": {}}},
                {"id": "1", "error": {"code": "BAD", "message": ""}},
            ],
            {},
        )
        codes = {issue.code for issue in report.issues}

        self.assertIn("jsonrpc.error_code", codes)
        self.assertIn("jsonrpc.error_message", codes)

    def test_detects_invalid_metadata_values(self):
        report = validate_transcript(
            [
                {"id": "1", "method": "tools/call", "params": {"name": "x", "arguments": {}}},
                {"id": "1", "result": {"meta": {"latency_ms": -1, "cost_usd": "free"}}},
            ],
            {},
        )
        codes = {issue.code for issue in report.issues}

        self.assertIn("metadata.latency_invalid", codes)
        self.assertIn("metadata.cost_invalid", codes)


if __name__ == "__main__":
    unittest.main()
