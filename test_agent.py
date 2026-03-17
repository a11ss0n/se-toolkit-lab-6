"""Regression tests for agent.py CLI."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with required fields."""
    project_root = Path(__file__).parent
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

    assert "answer" in output, "Output should have 'answer' field"
    assert isinstance(output["answer"], str), "'answer' should be a string"

    assert "tool_calls" in output, "Output should have 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' should be a list"

    assert "source" in output, "Output should have 'source' field"


def test_agent_list_files_tool():
    """Test that agent uses list_files tool for wiki exploration."""
    project_root = Path(__file__).parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What files are in the wiki directory?"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=120,
    )

    stdout = result.stdout.strip()
    assert stdout, "stdout should not be empty"

    output = json.loads(stdout)

    # Check required fields
    assert "answer" in output, "Output should have 'answer' field"
    assert "tool_calls" in output, "Output should have 'tool_calls' field"
    assert "source" in output, "Output should have 'source' field"

    # Check that list_files was called
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Should have at least one tool call"
    
    tool_names = [call.get("tool") for call in tool_calls]
    assert "list_files" in tool_names, f"Should use list_files tool, got: {tool_names}"


def test_agent_read_file_tool():
    """Test that agent uses read_file tool for documentation questions."""
    project_root = Path(__file__).parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "How do you resolve a merge conflict in git?"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=120,
    )

    stdout = result.stdout.strip()
    assert stdout, "stdout should not be empty"

    output = json.loads(stdout)

    # Check required fields
    assert "answer" in output, "Output should have 'answer' field"
    assert "tool_calls" in output, "Output should have 'tool_calls' field"

    # Check that read_file was called
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Should have at least one tool call"
    
    tool_names = [call.get("tool") for call in tool_calls]
    assert "read_file" in tool_names, f"Should use read_file tool, got: {tool_names}"
