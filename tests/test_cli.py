import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from mcp_transcript_contract_tester.cli import main


class CliTests(unittest.TestCase):
    def test_cli_check_error_exits_zero_for_clean_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema = Path(tmp) / "schema.json"
            transcript = Path(tmp) / "transcript.jsonl"
            schema.write_text(
                json.dumps(
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
                ),
                encoding="utf-8",
            )
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "1",
                                "method": "tools/call",
                                "params": {"name": "search", "arguments": {"query": "x"}},
                            }
                        ),
                        json.dumps(
                            {
                                "id": "1",
                                "result": {"content": [], "meta": {"latency_ms": 1, "cost_usd": 0}},
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                exit_code = main([str(transcript), "--schema", str(schema), "--format", "json", "--check", "error"])

        self.assertEqual(exit_code, 0)

    def test_cli_accepts_recorder_snapshot_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema = Path(tmp) / "snapshot.json"
            transcript = Path(tmp) / "transcript.jsonl"
            schema.write_text(
                json.dumps(
                    {
                        "format": "mcp-contract-recorder.snapshot/v1",
                        "tools": {
                            "search": {
                                "name": "search",
                                "inputSchema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {"query": {"type": "string"}},
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "1", "method": "tools/call", "params": {"name": "search", "arguments": {"query": "x"}}}),
                        json.dumps({"id": "1", "result": {"meta": {"latency_ms": 1, "cost_usd": 0}}}),
                    ]
                ),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                exit_code = main([str(transcript), "--schema", str(schema), "--format", "json", "--check", "error"])

        self.assertEqual(exit_code, 0)

    def test_cli_accepts_openapi_schema_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema = Path(tmp) / "contract.openapi.json"
            transcript = Path(tmp) / "transcript.jsonl"
            schema.write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "paths": {
                            "/tools/search": {
                                "post": {
                                    "operationId": "call_search",
                                    "x-mcp-tool": {"name": "search"},
                                    "requestBody": {
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "required": ["query"],
                                                    "properties": {"query": {"type": "string"}},
                                                }
                                            }
                                        }
                                    },
                                }
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "1", "method": "tools/call", "params": {"name": "search", "arguments": {"query": "x"}}}),
                        json.dumps({"id": "1", "result": {"meta": {"latency_ms": 1, "cost_usd": 0}}}),
                    ]
                ),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                exit_code = main([str(transcript), "--schema", str(schema), "--format", "json", "--check", "error"])

        self.assertEqual(exit_code, 0)

    def test_cli_check_error_exits_one_for_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "transcript.json"
            out = Path(tmp) / "reports" / "report.json"
            transcript.write_text(json.dumps([{"id": "1", "method": "tools/call"}]), encoding="utf-8")

            exit_code = main([str(transcript), "--format", "json", "--output", str(out), "--check", "error"])

        self.assertEqual(exit_code, 1)

    def test_cli_writes_baseline_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "transcript.json"
            baseline = Path(tmp) / "baseline.json"
            out = Path(tmp) / "report.json"
            transcript.write_text(json.dumps([{"id": "1", "method": "tools/call"}]), encoding="utf-8")
            baseline.write_text(json.dumps({"summary": {}, "issues": []}), encoding="utf-8")

            exit_code = main(
                [str(transcript), "--baseline", str(baseline), "--format", "json", "--output", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("baseline_diff", data)

    def test_cli_writes_sarif_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "transcript.json"
            out = Path(tmp) / "report.sarif"
            transcript.write_text(json.dumps([{"id": "1", "method": "tools/call"}]), encoding="utf-8")

            exit_code = main([str(transcript), "--format", "sarif", "--output", str(out)])
            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["runs"][0]["tool"]["driver"]["name"], "mcp-transcript-contract-tester")

    def test_cli_version_does_not_require_transcript(self):
        with redirect_stdout(StringIO()) as stdout:
            exit_code = main(["--version"])

        self.assertEqual(exit_code, 0)
        self.assertRegex(stdout.getvalue(), r"\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
