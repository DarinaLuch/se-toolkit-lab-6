#!/usr/bin/env python3
"""
LLM Agent CLI - Task 1

A simple CLI agent that takes a question, sends it to an LLM,
and returns a structured JSON answer.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    {"answer": "...", "tool_calls": []}
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def load_env() -> dict[str, str]:
    env_path = Path(__file__).parent / ".env.agent.secret"
    
    if env_path.exists():
        load_dotenv(env_path)  # загружай только если файл есть
    
    required_vars = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"Error: {var} not set", file=sys.stderr)
            sys.exit(1)
        env[var] = value
    
    return env


def call_lllm(question: str, env: dict[str, str]) -> str:
    """
    Call the LLM API with the given question.
    
    Args:
        question: The user's question
        env: Environment dict with API credentials
        
    Returns:
        The LLM's answer as a string
        
    Raises:
        SystemExit: If the API call fails
    """
    api_base = env["LLM_API_BASE"]
    api_key = env["LLM_API_KEY"]
    model = env["LLM_MODEL"]
    
    # Ensure API base ends with /v1
    if not api_base.rstrip("/").endswith("/v1"):
        api_base = api_base.rstrip("/") + "/v1"
    
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely and accurately."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
    print(f"Calling LLM at {url}...", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract the answer from the response
            if "choices" not in data or len(data["choices"]) == 0:
                print("Error: No choices in LLM response", file=sys.stderr)
                sys.exit(1)
            
            answer = data["choices"][0]["message"]["content"]
            return answer
            
    except httpx.TimeoutException:
        print("Error: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code} from LLM API", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Failed to connect to LLM API: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Agent - Ask questions and get JSON answers"
    )
    parser.add_argument(
        "question",
        type=str,
        help="The question to ask the LLM"
    )
    
    args = parser.parse_args()
    
    # Load environment
    env = load_env()
    print(f"Using model: {env['LLM_MODEL']}", file=sys.stderr)
    
    # Call LLM
    answer = call_lllm(args.question, env)
    
    # Build output
    output = {
        "answer": answer,
        "tool_calls": []
    }
    
    # Output JSON to stdout (single line, no extra whitespace)
    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()
