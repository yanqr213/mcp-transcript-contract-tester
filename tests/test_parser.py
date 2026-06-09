import json
import tempfile
import unittest
from pathlib import Path

from mcp_transcript_contract_tester.parser import ParseError, load_transcript


class ParserTests(unittest.TestCase):
    def test_loads_jsonl_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.jsonl"
            path.write_text('{"id":"1","method":"tool"}\n{"id":"1","result":{}}\n', encoding="utf-8")

            messages = load_transcript(str(path))

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["method"], "tool")

    def test_loads_json_messages_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.json"
            path.write_text(json.dumps({"messages": [{"id": "1", "method": "tool"}]}), encoding="utf-8")

            messages = load_transcript(str(path))

        self.assertEqual(messages, [{"id": "1", "method": "tool"}])

    def test_loads_json_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.json"
            path.write_text('\ufeff{"messages":[{"id":"1","method":"tool"}]}', encoding="utf-8")

            messages = load_transcript(str(path))

        self.assertEqual(messages, [{"id": "1", "method": "tool"}])

    def test_rejects_non_object_jsonl_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.jsonl"
            path.write_text("[1,2]\n", encoding="utf-8")

            with self.assertRaises(ParseError):
                load_transcript(str(path))


if __name__ == "__main__":
    unittest.main()
