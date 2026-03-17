# Agent Documentation

## Overview

CLI agent (agent.py) that connects to an LLM and answers questions.

## Architecture

User Question -> agent.py -> LLM API -> JSON Response

## LLM Provider

Provider: OpenRouter
Model: nvidia/nemotron-3-super-120b-a12b:free

OpenRouter provides free models with OpenAI-compatible API. No credit card required.

## Usage

```bash
uv run agent.py "What is 2+2?"
```

Output:
```json
{"answer": "4", "tool_calls": []}
```

## Configuration

Edit `.env.agent.secret`:
- `LLM_API_KEY` - Your OpenRouter API key
- `LLM_API_BASE` - https://openrouter.ai/api/v1
- `LLM_MODEL` - nvidia/nemotron-3-super-120b-a12b:free

## Files

- agent.py - Main CLI entry point
- .env.agent.secret - LLM credentials (gitignored)
- plans/task-1.md - Implementation plan
- test_agent.py - Regression tests
