#!/usr/bin/env python3
"""
LLM Agent CLI - Task 3: System Agent

Usage:
    uv run agent.py "How many items are in the database?"

Output:
    {"answer": "...", "source": "...", "tool_calls": [...]}
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
    for env_file in [".env.agent.secret", ".env.docker.secret"]:
        env_path = PROJECT_ROOT / env_file
        if env_path.exists():
            load_dotenv(env_path)

    required = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env = {}
    for var in required:
        value = os.getenv(var)
        if not value:
            print(f"Error: {var} not set", file=sys.stderr)
            sys.exit(1)
        env[var] = value

    env["LMS_API_KEY"] = os.getenv("LMS_API_KEY", "")
    env["AGENT_API_BASE_URL"] = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    return env


# ── Tools ─────────────────────────────────────────────────────────────────────

def read_file(path: str) -> str:
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT.resolve())):
        return "Error: access outside project directory is not allowed"
    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"
    return target.read_text(encoding="utf-8")


def list_files(path: str) -> str:
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT.resolve())):
        return "Error: access outside project directory is not allowed"
    if not target.exists():
        return f"Error: directory not found: {path}"
    if not target.is_dir():
        return f"Error: not a directory: {path}"
    entries = sorted(target.iterdir())
    return "\n".join(e.name for e in entries)


def query_api(method: str, path: str, body: str, env: dict, no_auth: bool = False) -> str:
    base_url = env["AGENT_API_BASE_URL"].rstrip("/")
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if env["LMS_API_KEY"] and not no_auth:
        headers["Authorization"] = f"Bearer {env['LMS_API_KEY']}"
    

    try:
        with httpx.Client(timeout=60.0) as client:
            req_body = json.loads(body) if body else None
            resp = client.request(method.upper(), url, headers=headers, json=req_body)
            return json.dumps({"status_code": resp.status_code, "body": resp.text})
    except Exception as e:
        return json.dumps({"status_code": 0, "body": f"Error: {e}"})


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository. Use for source code and wiki documentation.",
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
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": (
                "Call the deployed backend API to get live data. "
                "Use for questions about counts, scores, users, items, or any live system state. "
                "Example paths: /items/, /learners/, /analytics/completion-rate"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method: GET, POST, etc."},
                    "path": {"type": "string", "description": "API path, e.g. /items/"},
                    "body": {"type": "string", "description": "Optional JSON request body as string"},
                    "no_auth": {"type": "boolean", "description": "Set to true to make the request without authentication headers, to test what unauthenticated users see"}
                },
                "required": ["method", "path"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an assistant for a software project called Learning Management Service.

Project structure:
- wiki/ — documentation files
- backend/app/routers/ — API router modules
- backend/app/models/ — data models
- backend/app/ — main application code

Known lab identifiers in the system: lab-01, lab-02, lab-03, lab-04, lab-05, lab-06

You have three tools:
- list_files(path): list files in the project directory
- read_file(path): read a file (wiki docs or source code)
- query_api(method, path): call the live backend API

Rules:
- For questions about HTTP request journey → read ONLY: docker-compose.yml, caddy/Caddyfile, Dockerfile, backend/app/main.py. After reading these 4 files give the final answer immediately. Do NOT read any models, routers, or other files.
- For questions about HTTP request journey, system architecture, or docker → read ONLY these exact files: docker-compose.yml, Dockerfile. Then answer immediately without reading any other files. Do not read routers, models, or other source files.
- For questions about crashes or bugs in endpoints → first query_api the endpoint directly with a real lab name (e.g. lab-01), then immediately read_file the relevant router source code. Do not explore directories first.
- For questions about what happens without authentication → use query_api with no_auth=true
- For questions about authentication behavior → make the request WITHOUT the Authorization header to see the actual status code
- For wiki questions → list_files("wiki"), then read_file on relevant files
- For router/API structure questions → list_files("backend/app/routers"), then read EVERY .py file in that directory
- For framework/architecture questions → read_file on backend/app/main.py or source code directly
- For live data questions (counts, scores, users) → use query_api
- When asked to list ALL modules → read ALL files, not just some of them
- Never give a partial answer mid-reading — finish reading all files first

Always include a source at the end:
- Wiki: SOURCE: wiki/filename.md#section
- API: SOURCE: api:<path>
- Code: SOURCE: backend/app/routers/<file>
"""


def execute_tool(name: str, args: dict, env: dict) -> str:
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    elif name == "query_api":
        return query_api(args.get("method", "GET"), args.get("path", "/"), args.get("body", ""), env, args.get("no_auth", False))
    return f"Error: unknown tool: {name}"


# ── Agentic loop ──────────────────────────────────────────────────────────────

def run_agent(question: str, env: dict) -> dict:
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

    with httpx.Client(timeout=120.0) as client:
        for iteration in range(MAX_TOOL_CALLS + 1):
            print(f"LLM call #{iteration + 1}...", file=sys.stderr)

            payload = {
                "model": env["LLM_MODEL"],
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
                "max_tokens": 4096,
            }

            try:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException:
                print("Error: LLM timed out", file=sys.stderr)
                return {"answer": "Error: LLM timed out", "source": "", "tool_calls": []}
            except httpx.HTTPStatusError as e:
                print(f"Error: HTTP {e.response.status_code}: {e.response.text}", file=sys.stderr)
                return {"answer": f"Error calling LLM: HTTP {e.response.status_code}", "source": "", "tool_calls": []}
            except httpx.HTTPStatusError as e:
                print(f"Error: HTTP {e.response.status_code}: {e.response.text}", file=sys.stderr)
                return {"answer": f"Error calling LLM: HTTP {e.response.status_code}", "source": "", "tool_calls": []}
            choice = data["choices"][0]
            msg = choice["message"]
            messages.append(msg)

            if not msg.get("tool_calls"):
                answer = (msg.get("content") or "")
                
                if any(phrase in answer.lower() for phrase in ["i need to", "continue reading", "let me read", "i'll read", "now i'll", "i will read", "next i'll", "i'll check", "i'll now"]):
                    messages.append({"role": "user", "content": "Continue — read the remaining files and give the full answer."})
                    continue
                for line in answer.splitlines():
                    if line.startswith("SOURCE:"):
                        source = line.replace("SOURCE:", "").strip()
                        answer = answer.replace(line, "").strip()
                        break
                break

            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                print(f"Tool: {name}({args})", file=sys.stderr)
                result = execute_tool(name, args, env)
                tool_calls_log.append({"tool": name, "args": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            if len(tool_calls_log) >= MAX_TOOL_CALLS:
                print("Max tool calls reached", file=sys.stderr)
                break

    return {"answer": answer, "source": source, "tool_calls": tool_calls_log}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="System Agent")
    parser.add_argument("question", type=str)
    args = parser.parse_args()

    env = load_env()
    print(f"Using model: {env['LLM_MODEL']}", file=sys.stderr)

    result = run_agent(args.question, env)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()