import json
import unittest
from xml.etree import ElementTree

from mcp_transcript_contract_tester.models import Issue, Report
from mcp_transcript_contract_tester.reporters import render_junit, render_json, render_markdown, render_sarif


class ReporterTests(unittest.TestCase):
    def test_junit_marks_errors_as_failures(self):
        report = Report(
            transcript_path="t.json",
            schema_path="s.json",
            total_messages=1,
            issues=[Issue("schema.required_missing", "error", "Missing query", "messages[0].query")],
            summary={"errors": 1, "warnings": 0, "info": 0},
        )

        xml = render_junit(report)
        root = ElementTree.fromstring(xml)

        self.assertEqual(root.attrib["failures"], "1")
        self.assertEqual(root.find("testcase/failure").attrib["type"], "schema.required_missing")

    def test_json_and_markdown_render(self):
        report = Report(
            transcript_path="t.json",
            schema_path=None,
            total_messages=0,
            issues=[],
            summary={"errors": 0, "warnings": 0, "info": 0, "requests": 0, "responses": 0, "tool_calls": 0},
        )

        self.assertIn('"issues": []', render_json(report))
        self.assertIn("No issues found.", render_markdown(report))

    def test_sarif_renders_issue_results(self):
        report = Report(
            transcript_path="examples/broken.transcript.json",
            schema_path="examples/tools.schema.json",
            total_messages=2,
            issues=[Issue("jsonrpc.missing_response", "error", "Request has no response", "messages[1]")],
            summary={"errors": 1, "warnings": 0, "info": 0},
        )

        data = json.loads(render_sarif(report))
        run = data["runs"][0]

        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(run["tool"]["driver"]["name"], "mcp-transcript-contract-tester")
        self.assertEqual(run["results"][0]["ruleId"], "jsonrpc.missing_response")
        self.assertEqual(run["results"][0]["level"], "error")
        self.assertEqual(
            run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "examples/broken.transcript.json",
        )
        self.assertEqual(run["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"], 2)


if __name__ == "__main__":
    unittest.main()
