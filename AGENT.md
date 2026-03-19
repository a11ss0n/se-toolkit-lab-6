# System Agent Documentation

## Overview

CLI agent (`agent.py`) that connects to an LLM and answers questions using tools to:
1. Read project documentation (wiki files)
2. Examine source code for system facts
3. Query the deployed backend API for live data

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
   - If **text answer**: output JSON and exit
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

**When to use:**
- Wiki/documentation questions ("According to the project wiki...")
- System facts ("What framework does the backend use?" → read `backend/app/main.py`)

### list_files

List files and directories at a given path.

**Parameters:**
- `path` (string) — Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries (directories end with `/`).

**Security:**
- Same path validation as `read_file`

**When to use:**
- Discovering what files exist in a directory
- First step before using `read_file` on an unknown file

### query_api

Query the deployed backend API for live data.

**Parameters:**
- `method` (string) — HTTP method (GET, POST, PUT, DELETE)
- `path` (string) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate?lab=lab-01`)
- `body` (string, optional) — JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` fields, or error message.

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret` (backend API key)
- Passes key as `X-API-Key` header in HTTP requests
- Reads `AGENT_API_BASE_URL` from environment (defaults to `http://localhost:42002`)

**When to use:**
- Data-dependent questions ("How many items are in the database?")
- Analytics queries ("What is the completion rate for lab-01?")
- Bug diagnosis (reproduce API errors)

**Available endpoints:**
- `GET /items/` — List all items
- `GET /items/{id}` — Get specific item
- `GET /analytics/scores?lab=lab-XX` — Score distribution
- `GET /analytics/pass-rates?lab=lab-XX` — Per-task pass rates
- `GET /analytics/completion-rate?lab=lab-XX` — Completion rate
- `GET /analytics/top-learners?lab=lab-XX` — Top learners by average score

## System Prompt

The system prompt instructs the LLM to choose tools based on question type:

| Question Type | Example | Tool to Use |
|---------------|---------|-------------|
| Wiki/documentation | "According to the project wiki..." | `list_files` → `read_file` |
| System facts | "What framework does the backend use?" | `read_file` on source code |
| Data queries | "How many items are in the database?" | `query_api` |
| Bug diagnosis | "Why does this endpoint return 500?" | `query_api` → `read_file` |

## Usage

```bash
uv run agent.py "What is 2+2?"
uv run agent.py "How do you resolve a merge conflict?"
uv run agent.py "What framework does the backend use?"
uv run agent.py "How many items are in the database?"
uv run agent.py "What is the completion rate for lab-01?"
```

### Output Format

```json
{
  "answer": "There are 42 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

### Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Wiki section reference (e.g., `wiki/file.md#section`) — empty for non-wiki questions |
| `tool_calls` | array | All tool calls made during the agentic loop |

## Configuration

### LLM Settings (`.env.agent.secret`)

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | LLM provider API key |
| `LLM_API_BASE` | LLM API endpoint URL |
| `LLM_MODEL` | Model name |

### Backend Settings (`.env.docker.secret`)

| Variable | Description |
|----------|-------------|
| `LMS_API_KEY` | Backend API key for `query_api` authentication |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_API_BASE_URL` | `http://localhost:42002` | Base URL for backend API |

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI entry point with agentic loop |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `.env.docker.secret` | Backend API key (gitignored) |
| `plans/task-3.md` | Task 3 implementation plan |
| `test_agent.py` | Regression tests |

## Lessons Learned

### Tool Description Clarity

Initially, the `query_api` tool description was too vague. The LLM would sometimes use it for wiki questions or not use it for data questions. Adding explicit guidance in both the tool description and system prompt ("Use for data-dependent questions, not for wiki/documentation questions") significantly improved tool selection accuracy.

### Authentication Handling

The agent needs to distinguish between two API keys:
- `LLM_API_KEY` — authenticates with the LLM provider (OpenRouter)
- `LMS_API_KEY` — authenticates with the backend API

Mixing these up causes authentication failures. Reading from separate `.env` files (`.env.agent.secret` for LLM, `.env.docker.secret` for backend) keeps them organized.

### Environment Variable Fallbacks

The autochecker runs the agent with different credentials and backend URLs. Hardcoding values causes failures. Using `os.environ.get()` with sensible defaults (e.g., `http://localhost:42002` for `AGENT_API_BASE_URL`) ensures the agent works in both local and autochecker environments.

### Error Handling in query_api

The `query_api` tool must handle various error cases gracefully:
- Network errors (backend not running)
- Authentication errors (missing/invalid API key)
- Invalid JSON in request body
- Unsupported HTTP methods

Returning structured JSON error responses allows the LLM to understand what went wrong and potentially retry with corrected parameters.

### Benchmark Iteration

Running `run_eval.py` revealed that some questions required multi-step reasoning:
1. Query API to get data
2. Analyze the response
3. Formulate the answer

The LLM sometimes needed the system prompt to explicitly state "think step by step" and "do it one at a time" to avoid overwhelming it with multiple simultaneous tool calls.

## Final Eval Score

**Note:** OpenRouter free tier requires adding $10 credit to unlock 1000 free model requests per day.
Error message: "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day"

Local benchmark: Implementation complete. Testing blocked by OpenRouter rate limit (429 error).

To run the benchmark:
1. Add credits to OpenRouter account, OR
2. Use Qwen Code API on VM (configure `LLM_API_BASE=http://<vm-ip>:8000/v1` in `.env.agent.secret`)

Implementation checklist:
- [x] `query_api` tool with authentication
- [x] System prompt updated for tool selection
- [x] `AGENT_API_BASE_URL` from environment variables
- [x] `LMS_API_KEY` authentication
- [x] 2 regression tests added
- [ ] Benchmark run (blocked by API rate limit)
