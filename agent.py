#!/usr/bin/env python3
"""
System Agent with tool calling capabilities.

Tools:
- read_file: Read a file from the project repository
- list_files: List files and directories at a given path
- query_api: Query the deployed backend API
"""
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import SettingsConfigDict, BaseSettings


# Maximum tool calls per question
MAX_TOOL_CALLS = 12

# System prompt for the system agent
SYSTEM_PROMPT = """You are a system assistant with access to tools for reading files, listing directories, and querying the backend API.

When answering questions, choose the appropriate tool based on the question type:

1. **Wiki/documentation questions** (e.g., "According to the project wiki...", "What does the documentation say about..."):
   - Use list_files ONCE to discover wiki files
   - Use read_file to read the most relevant file (e.g., wiki/github.md for GitHub questions, wiki/ssh.md for SSH questions)
   - ALWAYS include a source reference at the END of your answer in format: Source: wiki/filename.md#section-anchor

2. **System facts** (e.g., "What framework does the backend use?", "What port does the API run on?"):
   - Use read_file to examine backend/app/main.py directly (don't list files first)
   - Look for imports like "from fastapi import FastAPI" or "import flask"

3. **Data-dependent queries** (e.g., "How many items are in the database?", "What is the completion rate for lab-01?"):
   - Use query_api with GET method
   - GET /items/ to count items
   - GET /analytics/{endpoint}?lab=lab-XX for analytics

4. **Bug diagnosis** (e.g., "Why does this endpoint return an error?"):
   - Use query_api to reproduce the error
   - Use read_file to examine the relevant source code

Be efficient: minimize tool calls. For wiki questions, list files once then read the most relevant file.
For system facts, read backend/app/main.py directly.
Always end wiki answers with: Source: wiki/filename.md#section-anchor
"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.agent.secret", env_file_encoding="utf-8", extra="ignore")

    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b:free"

    def __init__(self, **kwargs):
        # Read from environment variables first, then from file
        super().__init__(
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            llm_api_base=os.environ.get("LLM_API_BASE", ""),
            llm_model=os.environ.get("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"),
            **kwargs
        )


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.docker.secret", env_file_encoding="utf-8", extra="ignore")

    lms_api_key: str = ""


def log_debug(message: str) -> None:
    print(message, file=sys.stderr)


# =============================================================================
# Tools
# =============================================================================

def get_project_root() -> Path:
    """Get the project root directory (where agent.py is located)."""
    return Path(__file__).parent.resolve()


def is_safe_path(path: str) -> tuple[bool, str]:
    """
    Check if a path is safe (within project root, no directory traversal).
    Returns (is_safe, resolved_path_or_error).
    """
    # Reject paths with directory traversal
    if ".." in path:
        return False, "Error: Directory traversal not allowed"
    
    # Reject absolute paths
    if os.path.isabs(path):
        return False, "Error: Absolute paths not allowed"
    
    project_root = get_project_root()
    try:
        # Resolve the full path
        full_path = (project_root / path).resolve()
        # Check if it's within project root
        if not str(full_path).startswith(str(project_root)):
            return False, "Error: Path outside project directory"
        return True, str(full_path)
    except Exception as e:
        return False, f"Error: Invalid path - {e}"


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    
    Args:
        path: Relative path from project root
        
    Returns:
        File contents as string, or error message
    """
    is_safe, result = is_safe_path(path)
    if not is_safe:
        return result
    
    try:
        with open(result, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root

    Returns:
        Newline-separated listing of entries, or error message
    """
    is_safe, result = is_safe_path(path)
    if not is_safe:
        return result

    try:
        dir_path = Path(result)
        if not dir_path.exists():
            return f"Error: Directory not found: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = []
        for entry in sorted(dir_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return "\n".join(entries)
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


def get_agent_api_base_url() -> str:
    """Get the backend API base URL from environment variable."""
    return os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")


def get_lms_api_key() -> str:
    """Get the LMS API key from environment variable."""
    return os.environ.get("LMS_API_KEY", "")


def query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the deployed backend API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API endpoint path (e.g., /items/, /analytics/completion-rate)
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and body, or error message
    """
    base_url = get_agent_api_base_url()
    api_key = get_lms_api_key()

    # Build full URL
    url = f"{base_url.rstrip('/')}{path}"

    # Prepare headers
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                headers["Content-Type"] = "application/json"
                response = client.post(url, headers=headers, json=json.loads(body) if body else {})
            elif method.upper() == "PUT":
                headers["Content-Type"] = "application/json"
                response = client.put(url, headers=headers, json=json.loads(body) if body else {})
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return json.dumps({"error": f"Unsupported method: {method}"})

            result = {
                "status_code": response.status_code,
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
            return json.dumps(result)
    except httpx.HTTPError as e:
        return json.dumps({"error": str(e), "status_code": getattr(e.response, "status_code", 0) if hasattr(e, "response") else 0})
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON in request body: {e}"})
    except Exception as e:
        return json.dumps({"error": f"API request failed: {e}"})


# Tool registry
TOOLS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


# =============================================================================
# Tool Schemas for OpenAI Function Calling
# =============================================================================

def get_tool_schemas() -> list[dict[str, Any]]:
    """Return tool schemas for OpenAI-compatible function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the deployed backend API for live data (item counts, scores, analytics). Use for data-dependent questions, not for wiki/documentation questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE). Use GET for reading data."
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate?lab=lab-01')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests (e.g., '{\"key\": \"value\"}')"
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


# =============================================================================
# LLM Client
# =============================================================================

def call_llm(messages: list[dict[str, Any]], settings: Settings, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Call the LLM API with messages and optional tools.
    
    Args:
        messages: List of message dicts with role and content
        settings: LLM settings
        tools: Optional list of tool schemas
        
    Returns:
        Response data from LLM
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
    }
    
    if tools:
        payload["tools"] = tools
    
    log_debug(f"Calling LLM at {url}")
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


# =============================================================================
# Agentic Loop
# =============================================================================

def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        args: Tool arguments
        
    Returns:
        Tool result as string
    """
    if tool_name not in TOOLS:
        return f"Error: Unknown tool '{tool_name}'"
    
    try:
        return TOOLS[tool_name](**args)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def run_agent_loop(question: str, settings: Settings) -> dict[str, Any]:
    """
    Run the agentic loop: call LLM, execute tools, repeat until answer.
    
    Args:
        question: User's question
        settings: LLM settings
        
    Returns:
        Result dict with answer, source, and tool_calls
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_schemas = get_tool_schemas()
    tool_calls_log: list[dict[str, Any]] = []
    
    for iteration in range(MAX_TOOL_CALLS):
        log_debug(f"Iteration {iteration + 1}/{MAX_TOOL_CALLS}")
        
        # Call LLM
        response = call_llm(messages, settings, tools=tool_schemas)
        message = response["choices"][0]["message"]
        
        # Check for tool calls
        tool_calls = message.get("tool_calls", [])
        
        if not tool_calls:
            # No tool calls - LLM provided final answer
            log_debug("LLM provided final answer")
            answer = message.get("content", "")
            
            # Try to extract source from the answer
            source = extract_source(answer)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
        
        # Execute tool calls
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "unknown")
            
            # Parse arguments
            try:
                args = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            
            log_debug(f"Executing tool: {tool_name} with args: {args}")
            
            # Execute the tool
            result = execute_tool(tool_name, args)
            
            # Log the tool call
            tool_calls_log.append({
                "tool": tool_name,
                "args": args,
                "result": result
            })
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result,
                "name": tool_name
            })
        
        # Continue loop - LLM will process tool results
        messages.append({
            "role": "assistant",
            "content": message.get("content", ""),
            "tool_calls": tool_calls
        })
    
    # Max iterations reached
    log_debug("Max tool calls reached")
    return {
        "answer": "Maximum tool calls reached. Partial answer may be incomplete.",
        "source": "",
        "tool_calls": tool_calls_log
    }


def extract_source(answer: str) -> str:
    """
    Try to extract a source reference from the answer.
    Looks for patterns like wiki/file.md or wiki/file.md#section
    """
    import re
    
    # Pattern to match wiki/file.md or wiki/file.md#anchor
    pattern = r'(wiki/[\w\-/]+\.md(?:#[\w\-]+)?)'
    match = re.search(pattern, answer)
    
    if match:
        return match.group(1)
    
    return ""


# =============================================================================
# Main Entry Point
# =============================================================================

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

    # Check if LLM credentials are set
    if not settings.llm_api_key:
        log_debug("Error: LLM_API_KEY is not set. Set it in .env.agent.secret or environment variable.")
        return 1

    if not settings.llm_api_base:
        log_debug("Error: LLM_API_BASE is not set. Set it in .env.agent.secret or environment variable.")
        return 1

    try:
        result = run_agent_loop(question, settings)
        print(json.dumps(result))
        return 0
    except Exception as e:
        log_debug(f"Error running agent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
