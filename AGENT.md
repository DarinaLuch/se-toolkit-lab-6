# Agent Architecture

## Overview

This project implements an LLM-powered CLI agent that answers questions by calling a remote LLM API. The agent is built in phases:

- **Task 1** (this document): Basic LLM integration — parse input, call LLM, output JSON
- **Task 2**: Add tool definitions and tool calling
- **Task 3**: Full agentic loop with tool execution

## LLM Provider

**Provider**: Qwen Code API  
**Model**: `qwen3-coder-plus`

### Why Qwen Code?

- 1000 free requests per day
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API (easy integration)
- Strong tool calling support (needed for Tasks 2-3)

### Alternative

OpenRouter API can be used as a fallback with models like `meta-llama/llama-3.3-70b-instruct:free`.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  CLI Input  │ ──→ │  Environment │ ──→ │  LLM Client │ ──→ │  JSON Output │
│  (argparse) │     │  (dotenv)    │     │  (httpx)    │     │  (stdout)    │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  .env.agent  │
                    │  .secret     │
                    └──────────────┘
```

## Components

### `agent.py`

The main CLI entry point with the following responsibilities:

| Function | Purpose |
|----------|---------|
| `load_env()` | Load and validate `.env.agent.secret` |
| `call_llm()` | Make HTTP request to LLM API |
| `main()` | Parse CLI args, orchestrate flow, output JSON |

### Data Flow

1. **Input**: User provides question as command-line argument
2. **Environment**: Load API credentials from `.env.agent.secret`
3. **Request**: Build OpenAI-compatible chat completions request
4. **API Call**: POST to `{LLM_API_BASE}/v1/chat/completions`
5. **Response**: Extract answer from LLM response
6. **Output**: Print JSON `{"answer": "...", "tool_calls": []}` to stdout

## Configuration

### Environment Variables

Create `.env.agent.secret` (copy from `.env.agent.example`):

```bash
# LLM API key (from Qwen Code or OpenRouter)
LLM_API_KEY=your-api-key-here

# API base URL
LLM_API_BASE=http://<vm-ip>:<port>/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

- `answer` (string): The LLM's response
- `tool_calls` (array): Empty in Task 1, populated in Task 2+

All debug/progress output goes to **stderr**.

## Usage

```bash
# Run with uv
uv run agent.py "What does REST stand for?"

# Example output
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing `.env.agent.secret` | Print error to stderr, exit 1 |
| Missing env vars | Print error to stderr, exit 1 |
| HTTP error | Print status to stderr, exit 1 |
| Timeout (>60s) | Print timeout to stderr, exit 1 |
| Success | Exit 0 |

## Testing

Run the regression test:

```bash
pytest backend/tests/unit/test_agent.py
```

The test verifies:
1. `agent.py` runs successfully
2. Output is valid JSON
3. `answer` field exists and is non-empty
4. `tool_calls` field exists and is a list

## Files

```
project-root/
├── agent.py              # Main CLI agent
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example configuration
├── AGENT.md              # This documentation
└── plans/
    └── task-1.md         # Implementation plan
```

## Future Work (Tasks 2-3)

- **Task 2**: Define tools (e.g., `query_api`, `read_file`) and enable tool calling
- **Task 3**: Implement agentic loop — parse tool calls, execute tools, return results
