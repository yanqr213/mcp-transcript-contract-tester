import unittest

from mcp_transcript_contract_tester.schema import parse_tool_schemas


class SchemaTests(unittest.TestCase):
    def test_parse_recorder_snapshot_tool_map(self):
        tools = parse_tool_schemas(
            {
                "format": "mcp-contract-recorder.snapshot/v1",
                "recorderVersion": "0.3.0",
                "tools": {
                    "search_docs": {
                        "name": "search_docs",
                        "inputSchema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {"query": {"type": "string"}},
                        },
                        "compatibility": {"inputSchemaHash": "abc"},
                    }
                },
            }
        )

        self.assertEqual(set(tools), {"search_docs"})
        self.assertEqual(tools["search_docs"].source, "mcp-contract-recorder")
        self.assertEqual(tools["search_docs"].schema["properties"]["query"]["type"], "string")

    def test_parse_openapi_export_with_mcp_extension(self):
        tools = parse_tool_schemas(
            {
                "openapi": "3.1.0",
                "info": {"title": "Contracts", "version": "1"},
                "paths": {
                    "/tools/search-docs": {
                        "post": {
                            "operationId": "call_search_docs",
                            "x-mcp-tool": {"name": "search_docs"},
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SearchDocsInput"}
                                    }
                                }
                            },
                        }
                    }
                },
                "components": {
                    "schemas": {
                        "SearchDocsInput": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {"query": {"type": "string"}},
                        }
                    }
                },
            }
        )

        self.assertEqual(set(tools), {"search_docs"})
        self.assertEqual(tools["search_docs"].source, "openapi")
        self.assertEqual(tools["search_docs"].schema["required"], ["query"])

    def test_parse_openapi_falls_back_to_operation_id(self):
        tools = parse_tool_schemas(
            {
                "openapi": "3.1.0",
                "paths": {
                    "/tools/echo": {
                        "post": {
                            "operationId": "call_echo",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"text": {"type": "string"}},
                                        }
                                    }
                                }
                            },
                        }
                    }
                },
            }
        )

        self.assertEqual(set(tools), {"echo"})
        self.assertEqual(tools["echo"].schema["properties"]["text"]["type"], "string")


if __name__ == "__main__":
    unittest.main()
