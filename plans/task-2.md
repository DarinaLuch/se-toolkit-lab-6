# Task 2 Plan: The Documentation Agent

## Tools
- `read_file(path)` — reads a file, blocks ../ traversal
- `list_files(path)` — lists directory contents, blocks ../ traversal

## Tool schemas
Register both as function-calling schemas in the LLM request.

## Agentic loop
1. Send question + tool schemas to LLM
2. If LLM returns tool_calls → execute tools, append results, repeat
3. If LLM returns text → extract answer and source, output JSON
4. Max 10 tool calls

## System prompt
Tell LLM to use list_files to discover wiki files, then read_file to find the answer.
Include source as file path + section anchor.
