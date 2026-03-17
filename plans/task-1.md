# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

Provider: OpenRouter
Model: nvidia/nemotron-3-super-120b-a12b:free

Reasons:
- Free model with no credit card required
- OpenAI-compatible API
- Works from Russia
- Good performance for basic Q&A

## Configuration

LLM credentials stored in .env.agent.secret:
- LLM_API_KEY - OpenRouter API key
- LLM_API_BASE - https://openrouter.ai/api/v1
- LLM_MODEL - nvidia/nemotron-3-super-120b-a12b:free

## Agent Architecture

CLI Input (question) -> agent.py (parse, call, format) -> LLM API (HTTP POST /chat/completions) -> JSON Output {answer, tool_calls}

## Implementation Structure

1. Environment Loading - pydantic-settings
2. LLM Client - httpx, POST /chat/completions
3. Response Parsing - response.choices[0].message.content
4. Output Formatting - JSON to stdout, logs to stderr
5. Error Handling - 60s timeout

## Testing Strategy

Regression test: run agent.py, parse JSON, assert answer and tool_calls
