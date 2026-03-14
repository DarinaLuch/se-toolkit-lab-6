"""Regression tests for agent.py CLI."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json() -> None:
    """
    Test that agent.py outputs valid JSON with required fields.
    
    This test runs the agent as a subprocess with a simple question,
    parses the stdout as JSON, and verifies that:
    - 'answer' field exists and is a non-empty string
    - 'tool_calls' field exists and is a list
    
    Note: This test requires .env.agent.secret to be configured with
    valid LLM credentials. Skip if not configured.
    """
    # Path to agent.py in project root
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"
    
    if not agent_path.exists():
        raise FileNotFoundError(f"agent.py not found at {agent_path}")
    
    # Run agent with a simple question
    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2 + 2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with: {result.stderr}"
    
    # Parse stdout as JSON
    output = json.loads(result.stdout)
    
    # Verify required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    
    # Verify field types
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must be non-empty"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
def test_agent_uses_read_file():
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout.strip())
    tools_used = [t["tool"] for t in output["tool_calls"]]
    assert "read_file" in tools_used
    assert "wiki" in output.get("source", "")

def test_agent_uses_list_files():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout.strip())
    tools_used = [t["tool"] for t in output["tool_calls"]]
    assert "list_files" in tools_used