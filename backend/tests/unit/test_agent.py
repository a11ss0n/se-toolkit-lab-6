"""Regression tests for agent.py CLI."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with required fields."""
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    
    stdout = result.stdout.strip()
    assert stdout, "stdout should not be empty"
    
    output = json.loads(stdout)
    
    assert "answer" in output
    assert isinstance(output["answer"], str)
    
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
