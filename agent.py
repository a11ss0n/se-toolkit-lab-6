#!/usr/bin/env python3
import json
import sys
from typing import Any

import httpx
from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.agent.secret", env_file_encoding="utf-8")
    
    llm_api_key: str
    llm_api_base: str
    llm_model: str = "qwen3-coder-plus"


def log_debug(message: str) -> None:
    print(message, file=sys.stderr)


def call_llm(question: str, settings: Settings) -> dict[str, Any]:
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": question}],
    }
    log_debug(f"Calling LLM at {url}")
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    tool_calls = data["choices"][0]["message"].get("tool_calls", [])
    return {"answer": content, "tool_calls": tool_calls if tool_calls else []}


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "<question>"', file=sys.stderr)
        return 1
    question = sys.argv[1]
    try:
        settings = Settings()
    except Exception as e:
        log_debug(f"Error loading settings: {e}")
        return 1
    try:
        result = call_llm(question, settings)
        print(json.dumps(result))
        return 0
    except Exception as e:
        log_debug(f"Error calling LLM: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
