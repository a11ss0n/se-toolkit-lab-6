# Task 3 Plan: The System Agent

## Overview

Extend the documentation agent from Task 2 with a `query_api` tool to query the deployed backend API. This enables the agent to answer questions about:
- Static system facts (framework, ports, status codes)
- Data-dependent queries (item count, scores, analytics)

## Tool Definition: query_api

Call the deployed backend API with authentication.

**Parameters:**
- `method` (string) — HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string) — API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional) — JSON request body for POST/PUT

**Returns:** JSON string with `status_code` and `body`.

**Authentication:** Use `LMS_API_KEY` from `.env.docker.secret` in the `X-API-Key` header.

**Base URL:** Read from `AGENT_API_BASE_URL` environment variable (default: `http://localhost:42002`).

## Tool Schema (OpenAI Function Calling)

```json
{
  "name": "query_api",
  "description": "Query the deployed backend API. Use for questions about data, analytics, or system status.",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "description": "HTTP method (GET, POST, PUT, DELETE)",
        "enum": ["GET", "POST", "PUT", "DELETE"]
      },
      "path": {
        "type": "string",
        "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
      },
      "body": {
        "type": "string",
        "description": "JSON request body (optional, for POST/PUT)"
      }
    },
    "required": ["method", "path"]
  }
}
```

## Environment Variables

The agent reads configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api (optional) | Environment, default: `http://localhost:42002` |

**Important:** Two distinct keys:
- `LMS_API_KEY` (in `.env.docker.secret`) — protects backend endpoints
- `LLM_API_KEY` (in `.env.agent.secret`) — authenticates with LLM provider

## System Prompt Update

The system prompt will guide the LLM to choose the right tool:

1. **Wiki questions** ("According to the wiki...", "What does REST stand for?") → use `list_files` + `read_file`
2. **System facts** ("What framework does the backend use?", "What port...?") → use `read_file` on source code
3. **Data queries** ("How many items...", "What is the completion rate...") → use `query_api`
4. **Bug diagnosis** → use `query_api` to see error, then `read_file` to find the bug

## Implementation Steps

1. Add `query_api` function to `agent.py`:
   - Read `LMS_API_KEY` from environment
   - Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
   - Make HTTP request with `X-API-Key` header
   - Return JSON response with status_code and body

2. Add `query_api` to tool schemas

3. Update system prompt with tool selection guidance

4. Update `AGENT.md` with:
   - `query_api` documentation
   - Authentication details
   - Tool selection strategy
   - Lessons learned from benchmark (minimum 200 words)

5. Add 2 regression tests:
   - "What framework does the backend use?" → expects `read_file`
   - "How many items are in the database?" → expects `query_api`

6. Run `uv run run_eval.py` and iterate until all 10 questions pass

## Benchmark Iteration Strategy

1. Run `run_eval.py` to see initial score
2. For each failure:
   - Check if wrong tool was called → improve system prompt
   - Check if tool returned error → fix tool implementation
   - Check if answer phrasing doesn't match → adjust answer extraction
3. Re-run until 10/10 pass

## Expected Final Score

Target: 10/10 on local evaluation, pass threshold on autochecker bot (hidden questions + LLM judging).

## Benchmark Results

### Initial Run

```
+ [1/10] According to the project wiki, what steps are needed to protect a branch on GitHub?
+ [2/10] What does the project wiki say about connecting to your VM via SSH?
x [3/10] What Python web framework does this project's backend use?
    Error: Agent timed out (60s)

2/10 passed
```

### Diagnosis

**Problem:** Agent timed out on framework question because:
1. LLM called `list_files` repeatedly in a loop
2. Never read the actual source files
3. OpenRouter API returned 429 rate limit errors

**Root Causes:**
1. System prompt didn't explicitly limit `list_files` usage
2. LLM didn't know the project structure (backend/app/main.py vs backend/main.py)
3. Free model has rate limits

### Iterations

**Iteration 1:** Updated system prompt
- Added "Use list_files ONLY ONCE per directory"
- Added project structure documentation
- Added explicit tool selection guide

**Iteration 2:** Fixed API authentication
- Changed from `X-API-Key` to `Authorization: Bearer <key>`

**Iteration 3:** Added timeout handling
- Agent now handles API errors gracefully

### Current Status

Waiting for OpenRouter rate limit reset to complete full benchmark run.

Tool implementations are complete and tested individually:
- `query_api` correctly authenticates and returns data
- `read_file` correctly reads source files
- `list_files` correctly lists directories

### Next Steps

1. Wait for OpenRouter rate limit reset (~1 hour)
2. Run full benchmark
3. Fix any remaining failures
4. Submit for autochecker evaluation
