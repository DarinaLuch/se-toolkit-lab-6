#!/usr/bin/env python3
"""
LLM Agent CLI - Task 2: Documentation Agent

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    {"answer": "...", "source": "wiki/git-workflow.md#section", "tool_calls": [...]}
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
MAX_TOOL_CALLS = 10


def load_env() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env.agent.secret"
    if env_path.exists():
        load_dotenv(env_path)
    required_vars = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"Error: {var} not set", file=sys.stderr)
            sys.exit(1)
        env[var] = value
    return env


# ── Tools ────────────────────────────────────────────────────────────────────

def read_file(path: str) -> str:
    """Read a file from the project directory."""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT.resolve())):
        return "Error: access outside project directory is not allowed"
    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"
    return target.read_text(encoding="utf-8")


def list_files(path: str) -> str:
    """List files in a directory."""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT.resolve())):
        return "Error: access outside project directory is not allowed"
    if not target.exists():
        return f"Error: directory not found: {path}"
    if not target.is_dir():
        return f"Error: not a directory: {path}"
    entries = sorted(target.iterdir())
    return "\n".join(e.name for e in entries)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path from project root"}
                },
                "required": ["path"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a documentation assistant for a software project.
To answer questions, use the available tools to explore the project wiki:
1. Use list_files to discover what files exist (start with "wiki" directory)
2. Use read_file to read relevant files
3. Once you have enough information, give a concise answer

Always include a source reference in this exact format at the end of your answer:
SOURCE: wiki/filename.md#section-name

Use the actual filename and the most relevant section heading (lowercase, spaces replaced with hyphens).
"""


def execute_tool(name: str, args: dict) -> str:
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    else:
        return f"Error: unknown tool: {name}"


# ── Agentic loop ─────────────────────────────────────────────────────────────

def run_agent(question: str, env: dict[str, str]) -> dict:
    api_base = env["LLM_API_BASE"].rstrip("/")
    if not api_base.endswith("/v1"):
        api_base += "/v1"
    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {env['LLM_API_KEY']}",
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    answer = ""
    source = ""

    with httpx.Client(timeout=60.0) as client:
        for iteration in range(MAX_TOOL_CALLS + 1):
            print(f"LLM call #{iteration + 1}...", file=sys.stderr)

            payload = {
                "model": env["LLM_MODEL"],
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
                "max_tokens": 1024,
            }

            try:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException:
                print("Error: LLM timed out", file=sys.stderr)
                sys.exit(1)
            except httpx.HTTPStatusError as e:
                print(f"Error: HTTP {e.response.status_code}: {e.response.text}", file=sys.stderr)
                sys.exit(1)

            choice = data["choices"][0]
            msg = choice["message"]
            messages.append(msg)

            # No tool calls → final answer
            if not msg.get("tool_calls"):
                answer = msg.get("content", "")
                # Extract source from answer
                for line in answer.splitlines():
                    if line.startswith("SOURCE:"):
                        source = line.replace("SOURCE:", "").strip()
                        answer = answer.replace(line, "").strip()
                        break
                break

            # Execute tool calls
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                print(f"Tool call: {name}({args})", file=sys.stderr)
                result = execute_tool(name, args)
                tool_calls_log.append({"tool": name, "args": args, "result": result})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            if len(tool_calls_log) >= MAX_TOOL_CALLS:
                print("Max tool calls reached", file=sys.stderr)
                break

    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Documentation Agent")
    parser.add_argument("question", type=str)
    args = parser.parse_args()

    env = load_env()
    print(f"Using model: {env['LLM_MODEL']}", file=sys.stderr)

    result = run_agent(args.question, env)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()