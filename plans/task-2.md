# Task 2 Plan: The Documentation Agent

## Overview

Extend the agent from Task 1 with tools (read_file, list_files) and an agentic loop to answer questions about the project documentation.

## Tool Definitions

### read_file
Read a file from the project repository.

**Parameters:**
- `path` (string) — relative path from project root

**Returns:** File contents as a string, or error message if file doesn't exist.

**Security:** Must not read files outside the project directory (no `../` traversal).

### list_files
List files and directories at a given path.

**Parameters:**
- `path` (string) — relative directory path from project root

**Returns:** Newline-separated listing of entries.

**Security:** Must not list directories outside the project directory.

## Tool Schemas (OpenAI Function Calling)

```json
{
  "name": "read_file",
  "description": "Read a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

```json
{
  "name": "list_files",
  "description": "List files and directories at a given path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

## Agentic Loop

```
1. Send user question + tool schemas to LLM
2. Parse response:
   - If tool_calls: execute each tool, append results as tool messages, go to step 1
   - If text answer: extract answer + source, output JSON and exit
3. Maximum 10 tool calls per question
```

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files
2. Use `read_file` to read relevant documentation
3. Include source reference (file path + section anchor) in the answer
4. Call tools step by step, not all at once

## Path Security

- Resolve all paths relative to project root
- Reject paths containing `..` (directory traversal)
- Reject absolute paths
- Use `os.path.realpath` to verify final path is within project root

## Output Format

```json
{
  "answer": "string",
  "source": "wiki/file.md#section",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/file.md"}, "result": "..."}
  ]
}
```

## Testing Strategy

2 regression tests:
1. "How do you resolve a merge conflict?" → expects read_file in tool_calls, wiki/git-workflow.md in source
2. "What files are in the wiki?" → expects list_files in tool_calls
