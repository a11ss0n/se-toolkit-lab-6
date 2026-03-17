# Agent Documentation

## Overview

CLI agent (agent.py) that connects to an LLM and answers questions using tools to read project documentation.

## Architecture

```
User Question → agent.py → LLM API → tool call? → execute tool → back to LLM
                                                      │
                                                      no
                                                      │
                                                      ▼
                                              JSON output with answer
```

### Agentic Loop

1. Send user question + tool schemas to LLM
2. Parse response:
   - If **tool_calls**: execute each tool, append results as tool messages, go to step 1
   - If **text answer**: extract answer + source, output JSON and exit
3. Maximum 10 tool calls per question

## LLM Provider

**Provider:** OpenRouter  
**Model:** nvidia/nemotron-3-super-120b-a12b:free

OpenRouter provides free models with OpenAI-compatible API. No credit card required.

## Tools

### read_file

Read a file from the project repository.

**Parameters:**
- `path` (string) — Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message.

**Security:**
- Rejects paths containing `..` (directory traversal)
- Rejects absolute paths
- Verifies final path is within project root

### list_files

List files and directories at a given path.

**Parameters:**
- `path` (string) — Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries (directories end with `/`).

**Security:**
- Same path validation as `read_file`

## System Prompt

The system prompt instructs the LLM to:
1. Use `list_files` to discover wiki files
2. Use `read_file` to read relevant documentation
3. Include source reference (file path + section anchor) in the answer
4. Call tools step by step, not all at once

## Usage

```bash
uv run agent.py "What is 2+2?"
uv run agent.py "How do you resolve a merge conflict?"
uv run agent.py "What files are in the wiki?"
```

### Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

### Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Wiki section reference (e.g., `wiki/file.md#section`) |
| `tool_calls` | array | All tool calls made during the agentic loop |

## Configuration

Edit `.env.agent.secret`:
- `LLM_API_KEY` — Your OpenRouter API key
- `LLM_API_BASE` — `https://openrouter.ai/api/v1`
- `LLM_MODEL` — `nvidia/nemotron-3-super-120b-a12b:free`

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI entry point with agentic loop |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `test_agent.py` | Regression tests |
