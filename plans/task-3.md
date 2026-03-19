# Task 3 Plan: The System Agent

## Overview

Extend the Documentation Agent from Task 2 with a new `query_api` tool that allows the agent to query the deployed backend API. This enables the agent to answer two new kinds of questions:

1. **Static system facts** — framework, ports, status codes (via `read_file` on source code)
2. **Data-dependent queries** — item count, scores, analytics (via `query_api` tool)

## Tool Schema: query_api

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `method` | string | Yes | HTTP method (GET, POST, PUT, DELETE, etc.) |
| `path` | string | Yes | API endpoint path (e.g., `/items/`, `/analytics/completion-rate`) |
| `body` | string | No | JSON request body for POST/PUT requests |

### Returns

JSON string with structure:
```json
{
  "status_code": 200,
  "body": { ... }
}
```

### Authentication

- Use `LMS_API_KEY` from `.env.docker.secret` (backend API key, NOT the LLM key)
- Pass as `X-API-Key` header in the HTTP request
- Read from environment variable at runtime

### Implementation

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the deployed backend API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path (e.g., /items/)
        body: Optional JSON request body
        
    Returns:
        JSON string with status_code and body
    """
    # Read LMS_API_KEY from environment
    # Build URL from AGENT_API_BASE_URL env var (default: http://localhost:42002)
    # Send HTTP request with X-API-Key header
    # Return JSON response
```

## Environment Variables

The agent must read all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

**Important:** The autochecker runs the agent with different credentials. Never hardcode values.

## System Prompt Update

Update the system prompt to guide the LLM on when to use each tool:

- **wiki questions** ("According to the project wiki...") → use `list_files` and `read_file` on `wiki/` directory
- **system facts** ("What framework does the backend use?") → use `read_file` on source code (`backend/app/main.py`, etc.)
- **data queries** ("How many items are in the database?") → use `query_api` with appropriate endpoint
- **bug diagnosis** → use `query_api` to reproduce the error, then `read_file` to find the bug

Example prompt addition:
```
For data-dependent questions (item counts, scores, analytics):
1. Use query_api to fetch data from the backend
2. Use GET /items/ to count items
3. Use GET /analytics/{endpoint}?lab=lab-XX for analytics

For system facts (framework, ports, status codes):
1. Use read_file to examine source code
2. Check backend/app/main.py for framework info
3. Check .env.docker.secret for port configurations
```

## Backend API Endpoints

Available endpoints for `query_api`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/items/` | GET | List all items |
| `/items/{id}` | GET | Get specific item |
| `/analytics/scores?lab=lab-XX` | GET | Score distribution |
| `/analytics/pass-rates?lab=lab-XX` | GET | Per-task pass rates |
| `/analytics/timeline?lab=lab-XX` | GET | Submissions per day |
| `/analytics/groups?lab=lab-XX` | GET | Per-group performance |
| `/analytics/completion-rate?lab=lab-XX` | GET | Completion rate |
| `/analytics/top-learners?lab=lab-XX` | GET | Top learners |

## Testing Strategy

Add 2 regression tests:

1. **System fact question**: "What framework does the backend use?"
   - Expected: `read_file` in tool_calls (reads `backend/app/main.py`)
   - Answer should contain "FastAPI"

2. **Data query question**: "How many items are in the database?"
   - Expected: `query_api` in tool_calls (calls `GET /items/`)
   - Answer should contain a number

## Benchmark Iteration Strategy

1. Run `uv run run_eval.py` to test against 10 local questions
2. For each failure:
   - Read the feedback hint
   - Identify which tool should have been used
   - Improve tool description or system prompt
   - Re-run until passing
3. Target: 10/10 passing locally before autochecker evaluation

## Initial Benchmark Score

**Note:** OpenRouter free tier requires adding $10 credit to unlock 1000 free model requests per day.
Error message: "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day"

To run the benchmark:
1. Add credits to OpenRouter account, OR
2. Use Qwen Code API on VM (configure `LLM_API_BASE=http://<vm-ip>:8000/v1`)

After running `run_eval.py`, update this section with the score.

## Iteration Log

### Issue: Rate Limit 429
- **Problem:** OpenRouter free tier has daily rate limit
- **Solution:** Add $10 credit to OpenRouter account or use alternative LLM provider

### Issue: Source field missing for wiki questions
- **Problem:** Agent didn't include source reference in answer
- **Solution:** Updated system prompt to explicitly require "Source: wiki/filename.md#section-anchor" at end of wiki answers

### Issue: Max tool calls reached for system facts
- **Problem:** Agent used too many iterations for simple questions
- **Solution:** Updated system prompt to be more efficient: "read backend/app/main.py directly" for system facts

## Lessons Learned

Will be added after completing the benchmark and documenting in `AGENT.md`.
