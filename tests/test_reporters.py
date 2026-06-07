import unittest
from xml.etree import ElementTree

from mcp_transcript_contract_tester.models import Issue, Report
from mcp_transcript_contract_tester.reporters import render_junit, render_json, render_markdown


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


if __name__ == "__main__":
    unittest.main()
