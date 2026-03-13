# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice

**Provider**: Qwen Code API
**Model**: `qwen3-coder-plus`

**Rationale**:
- 1000 free requests per day (sufficient for development and testing)
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API (easy integration with standard libraries)
- Strong tool calling support (needed for Task 2-3)

## Architecture

The agent will follow a simple pipeline:

```
CLI argument → Load env → Build request → Call LLM API → Parse response → Output JSON
```

### Components

1. **Environment Loading**
   - Read `.env.agent.secret` using `python-dotenv`
   - Extract: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Validate all required variables are present

2. **CLI Interface**
   - Accept question as first positional argument via `argparse`
   - Show help with `-h`/`--help`
   - Exit with error if no question provided

3. **LLM Client**
   - Use `httpx` (async HTTP client) for API calls
   - OpenAI-compatible `/v1/chat/completions` endpoint
   - POST request with:
     - `model`: from env
     - `messages`: system + user message
     - `temperature`: 0.7 for balanced responses
   - Timeout: 60 seconds

4. **Response Parsing**
   - Extract `content` from LLM response
   - Build output JSON: `{"answer": "...", "tool_calls": []}`
   - Handle API errors gracefully

5. **Output Handling**
   - **stdout**: Only the final JSON (single line)
   - **stderr**: All debug/progress messages, errors
   - Exit code 0 on success, non-zero on failure

## Error Handling

| Error Type | Handling |
|------------|----------|
| Missing env vars | Print error to stderr, exit 1 |
| Missing CLI argument | Print usage to stderr, exit 1 |
| HTTP error | Print status to stderr, exit 1 |
| JSON parse error | Print error to stderr, exit 1 |
| Timeout | Print timeout message to stderr, exit 1 |

## Dependencies

- `httpx` - already in pyproject.toml (for HTTP requests)
- `python-dotenv` - need to add for loading `.env.agent.secret`
- `argparse` - standard library (CLI parsing)
- `json` - standard library (JSON handling)

## Testing Strategy

One regression test that:
1. Runs `uv run agent.py "Test question"` as subprocess
2. Parses stdout as JSON
3. Asserts `answer` field exists and is non-empty string
4. Asserts `tool_calls` field exists and is a list

## File Structure

```
c:\Users\Darina\git\se-toolkit-lab-6\
├── agent.py              # Main CLI agent
├── .env.agent.secret     # LLM credentials (gitignored)
├── AGENT.md              # Architecture documentation
└── plans/
    └── task-1.md         # This plan
```

## Implementation Steps

1. Copy `.env.agent.example` to `.env.agent.secret` and configure
2. Add `python-dotenv` to dependencies
3. Create `agent.py` with CLI, env loading, and LLM call
4. Test manually with a sample question
5. Write regression test
6. Create `AGENT.md` documentation
