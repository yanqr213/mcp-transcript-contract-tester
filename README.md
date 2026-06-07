# mcp-transcript-contract-tester

`mcp-transcript-contract-tester` 是一个离线 CLI，用来验证已经录制好的 MCP-like / tool-calling / agent tool server transcript，以及对应的 tool schema snapshot。它面向构建 MCP、agent tools、函数调用网关、工具服务器和 CI 回归测试的开发者。

它不是 MCP 官方实现，也不会连接真实服务器。它只读取本地 JSON/JSONL transcript 和 JSON schema snapshot，检查 transcript 是否满足一组稳定、协议中立的合约约束。

## 适合做什么

- 在 CI 中验证录制的 tool transcript 没有回归。
- 检查 request/response `id` 是否配对。
- 检查重复 request id、重复 response id、orphan result、缺失 response。
- 检查调用了 schema snapshot 中不存在的 tool。
- 对 tool arguments 做轻量 JSON Schema 校验，包括 `type`、`required`、`properties`、`enum`、数组和嵌套对象。
- 检查错误响应格式是否一致。
- 检查 result 中是否包含 latency/cost 元数据。
- 与之前的 JSON report 做 baseline diff。
- 输出 Markdown、JSON 或 JUnit，方便本地阅读、机器处理和 CI 展示。

## 不是什么

- 不是 MCP 官方实现。
- 不保证覆盖某个最新 MCP 版本的全部协议细节。
- 不连接 MCP server、LLM API 或真实工具。
- 不做完整 JSON Schema 实现，只做 transcript contract testing 中常见且稳定的粗校验。

## 安装

本地开发安装：

```bash
python -m pip install -e .
```

项目要求 Python 3.9+，运行时无第三方依赖。

## 快速开始

检查一个干净示例：

```bash
mcp-transcript-contract-tester examples/clean.transcript.jsonl \
  --schema examples/tools.schema.json \
  --check error
```

输出 JSON report：

```bash
mcp-transcript-contract-tester examples/broken.transcript.json \
  --schema examples/tools.schema.json \
  --format json \
  --output report.json
```

输出 JUnit：

```bash
mcp-transcript-contract-tester examples/broken.transcript.json \
  --schema examples/tools.schema.json \
  --format junit \
  --output junit.xml
```

与 baseline 比较：

```bash
mcp-transcript-contract-tester examples/broken.transcript.json \
  --schema examples/tools.schema.json \
  --baseline report.json \
  --format markdown
```

## CLI

```text
usage: mcp-transcript-contract-tester [-h] [--schema SCHEMA_PATH]
                                      [--baseline BASELINE]
                                      [--format {markdown,json,junit}]
                                      [--output OUTPUT]
                                      [--check {info,warning,error}]
                                      [--version]
                                      transcript
```

`--check` 会按 severity 控制退出码：

- `--check error`: 只要存在 error，退出码为 1。
- `--check warning`: 存在 warning 或 error，退出码为 1。
- `--check info`: 存在 info、warning 或 error，退出码为 1。
- 不设置 `--check` 时，发现问题也会正常输出报告并返回 0。

解析失败或文件读取失败返回 2。

## Transcript 格式

支持 JSONL，每行一个消息对象：

```json
{"jsonrpc":"2.0","id":"req-1","method":"tools/call","params":{"name":"search_docs","arguments":{"query":"contract"}}}
{"jsonrpc":"2.0","id":"req-1","result":{"content":[],"meta":{"latency_ms":12,"cost_usd":0.0}}}
```

也支持 JSON：

```json
{
  "messages": [
    {"id": "req-1", "method": "tools/call", "params": {"name": "search_docs", "arguments": {"query": "contract"}}},
    {"id": "req-1", "result": {"content": [], "meta": {"latency_ms": 12, "cost_usd": 0.0}}}
  ]
}
```

JSON 根也可以是消息数组，或单个消息对象。工具调用识别尽量兼容常见形状，例如 `method: "tools/call"` 搭配 `params.name` / `params.arguments`，或自定义 method 名与 tool 名相同。

## Tool schema snapshot

支持常见 MCP-like `tools` 数组：

```json
{
  "tools": [
    {
      "name": "search_docs",
      "inputSchema": {
        "type": "object",
        "required": ["query"],
        "properties": {
          "query": {"type": "string"},
          "limit": {"type": "integer"}
        }
      }
    }
  ]
}
```

也支持 name-to-schema map：

```json
{
  "search_docs": {
    "type": "object",
    "required": ["query"],
    "properties": {
      "query": {"type": "string"}
    }
  }
}
```

## Baseline diff

Baseline 使用之前生成的 JSON report。diff 会报告：

- 新增 issue 数量和 fingerprint。
- 已修复 issue 数量和 fingerprint。
- 未变化 issue 数量。
- summary 中 errors、warnings、info、requests、responses、tool_calls 的变化。

## 测试

```bash
python -m unittest discover -s tests
```

## English

`mcp-transcript-contract-tester` is an offline CLI for validating recorded MCP-like, tool-calling, and agent tool server transcripts against a captured tool schema snapshot.

It is not an official MCP implementation. It does not connect to live servers. It validates local JSON/JSONL transcripts using conservative JSON-RPC-like and tool-contract checks that are intended to remain useful across MCP-like and custom agent tool systems.

Key features:

- JSON and JSONL transcript parsing.
- Tool schema snapshot parsing for common `tools` arrays and name-to-schema maps.
- Request/response `id` pairing checks.
- Duplicate id, missing response, and orphan result detection.
- Unknown tool detection.
- Lightweight argument schema validation for `type`, `required`, `properties`, `enum`, arrays, and nested objects.
- Error response consistency checks.
- Latency and cost metadata checks.
- Baseline diff against a previous JSON report.
- Markdown, JSON, and JUnit output.
- `--check` mode for CI severity gates.

Example:

```bash
mcp-transcript-contract-tester examples/clean.transcript.jsonl \
  --schema examples/tools.schema.json \
  --format markdown \
  --check error
```

Use it in CI when you want recorded tool interactions to behave like contract tests: stable, offline, reviewable, and independent from live service availability.

## License

MIT
