import unittest

from mcp_transcript_contract_tester.baseline import diff_against_baseline
from mcp_transcript_contract_tester.models import Issue, Report


class BaselineTests(unittest.TestCase):
    def test_diff_reports_new_and_resolved_issues(self):
        old_issue = Issue("old", "error", "old message", "messages[0]")
        new_issue = Issue("new", "warning", "new message", "messages[1]")
        report = Report(
            transcript_path="t.json",
            schema_path=None,
            total_messages=1,
            issues=[new_issue],
            summary={"errors": 0, "warnings": 1, "info": 0, "requests": 1, "responses": 1, "tool_calls": 0},
        )
        baseline = {
            "summary": {"errors": 1, "warnings": 0, "info": 0, "requests": 1, "responses": 1, "tool_calls": 0},
            "issues": [old_issue.to_dict()],
        }

        diff = diff_against_baseline(report, baseline)

        self.assertEqual(diff["new_issues"], 1)
        self.assertEqual(diff["resolved_issues"], 1)
        self.assertEqual(diff["summary_delta"]["errors"]["delta"], -1)
        self.assertEqual(diff["summary_delta"]["warnings"]["delta"], 1)


if __name__ == "__main__":
    unittest.main()
