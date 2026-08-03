"""Tatvik Platform MCP bridge — expose the local LLM stack to opencode.

A stdio MCP server that bridges opencode to:
  * Tatvik API   (:8000)  — chat, generate, models, registry, training, eval
  * Governor API (:8100)  — knowledge base search, RAG retrieval, stats
  * Hermes API   (:8101)  — agent orchestration
  * SuperCompress        — query-aware prompt compression (hosted or local)

Run directly:
    python mcp_bridge/server.py
Or via opencode config:
    mcp: { "tatvik": { "type": "local", "command": ["python", "<repo>/mcp_bridge/server.py"] } }
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)
from mcp.server.models import InitializationOptions

TATVIK_URL = os.environ.get("TATVIK_API_URL", "http://localhost:8000")
GOVERNOR_URL = os.environ.get("GOVERNOR_API_URL", "http://localhost:8100")
HERMES_URL = os.environ.get("HERMES_API_URL", "http://localhost:8101")

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_ROOT)


def _http(method: str, url: str, json_body: dict | None = None, timeout: float = 30.0) -> Any:
    import httpx
    resp = httpx.request(method, url, json=json_body, timeout=timeout)
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


def _s_compress(context: str, query: str) -> dict:
    """Compress context against a query using the shared SuperCompress client."""
    from tatvik.shared.supercompress import compress_context
    r = compress_context(context, query)
    return {
        "compressed_text": r.compressed_text,
        "original_tokens": r.original_tokens,
        "kept_tokens": r.kept_tokens,
        "tokens_saved_pct": round(r.tokens_saved_pct, 2),
        "important_kept_pct": round(r.important_kept_pct, 2),
        "compression_risk": r.compression_risk,
        "mode": r.mode,
        "compressed": r.compressed,
        "message": r.message,
    }


TOOLS: list[Tool] = []


def _tool(name: str, description: str, props: dict, required: list[str] | None = None) -> Tool:
    return Tool(
        name=name,
        description=description,
        input_schema={"type": "object", "properties": props, "required": required or []},
    )


def _result(obj: Any) -> CallToolResult:
    if isinstance(obj, str):
        text = obj
    else:
        text = json.dumps(obj, indent=2, default=str)
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _error(msg: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=f"ERROR: {msg}")], is_error=True)


# --------------------------------------------------------------------------
# Tool definitions
# --------------------------------------------------------------------------

TOOLS = [
    # ---- Inference / chat bridge ----
    _tool(
        "tatvik_chat",
        "Chat with the local LLM through Tatvik. messages is an array of {role, content} (roles: system/user/assistant). Optional model override. Context compression is applied automatically before inference.",
        {"messages": {"type": "array", "items": {"type": "object"}}, "model": {"type": "string"}},
        ["messages"],
    ),
    _tool(
        "tatvik_generate",
        "Free-form text generation against the local model. prompt is the input; optional system prompt.",
        {"prompt": {"type": "string"}, "system": {"type": "string"}},
        ["prompt"],
    ),
    # ---- Platform control ----
    _tool("tatvik_list_models", "List all models loaded/available in the local runtime.", {}),
    _tool(
        "tatvik_pull_model",
        "Pull a model into the local runtime (e.g. 'qwen2.5-coder:0.5b').",
        {"name": {"type": "string"}},
        ["name"],
    ),
    _tool("tatvik_delete_model", "Delete a model from the local runtime.", {"name": {"type": "string"}}, ["name"]),
    _tool("tatvik_runtime_stats", "Runtime stats: GPU utilization, memory, active jobs.", {}),
    _tool("tatvik_list_adapters", "List trained LoRA adapters in the registry.", {}),
    _tool("tatvik_list_models_registry", "List registry models.", {}),
    _tool(
        "tatvik_run_evaluation",
        "Run a benchmark evaluation. base_model required; optional adapter_path.",
        {"base_model": {"type": "string"}, "adapter_path": {"type": "string"}},
        ["base_model"],
    ),
    # ---- Sahapatha (continuous learning) ----
    _tool(
        "sahapatha_learn",
        "Record a prompt/response interaction into the Sahapatha learning buffer. Enables continuous QLoRA fine-tuning.",
        {"prompt": {"type": "string"}, "response": {"type": "string"}},
        ["prompt", "response"],
    ),
    _tool("sahapatha_status", "Sahapatha training buffer + adapter status.", {}),
    _tool("sahapatha_train", "Trigger a training cycle (requires buffered samples).", {}),
    # ---- Governor ----
    _tool(
        "governor_kb_search",
        "Search the Governor knowledge base. query required; k optional (default 5).",
        {"query": {"type": "string"}, "k": {"type": "integer"}},
        ["query"],
    ),
    _tool(
        "governor_rag",
        "RAG retrieval from Governor. query required; k optional; compress (default true) applies SuperCompress to the retrieved context before it reaches the model.",
        {"query": {"type": "string"}, "k": {"type": "integer"}, "compress": {"type": "boolean"}, "knowledge_type": {"type": "string"}},
        ["query"],
    ),
    _tool("governor_stats", "Governor system stats (datasets, knowledge base size).", {}),
    # ---- Hermes orchestrator ----
    _tool("hermes_status", "Hermes orchestrator status.", {}),
    _tool("hermes_list_agents", "List Hermes agents.", {}),
    _tool("hermes_run_agent", "Run a Hermes agent. agent_id required.", {"agent_id": {"type": "string"}}, ["agent_id"]),
    # ---- SuperCompress ----
    _tool(
        "compress_context",
        "Compress a prompt/context against a query before sending to an LLM. Returns compressed text plus savings stats. Query-aware: keeps evidence relevant to the question.",
        {"context": {"type": "string"}, "query": {"type": "string"}},
        ["context", "query"],
    ),
]


# --------------------------------------------------------------------------
# Tool handlers
# --------------------------------------------------------------------------

async def _handle_tool(name: str, args: dict) -> CallToolResult:
    try:
        if name == "tatvik_chat":
            messages = args.get("messages") or []
            body = {"model": args.get("model", ""), "messages": messages, "stream": False}
            return _result(_http("POST", f"{TATVIK_URL}/models/chat", body))

        if name == "tatvik_generate":
            body = {"model": args.get("model", ""), "prompt": args["prompt"], "stream": False}
            if args.get("system"):
                body["system"] = args["system"]
            return _result(_http("POST", f"{TATVIK_URL}/models/generate", body))

        if name == "tatvik_list_models":
            return _result(_http("GET", f"{TATVIK_URL}/models"))

        if name == "tatvik_pull_model":
            return _result(_http("POST", f"{TATVIK_URL}/models/pull?name={args['name']}"))

        if name == "tatvik_delete_model":
            return _result(_http("DELETE", f"{TATVIK_URL}/models/{args['name']}"))

        if name == "tatvik_runtime_stats":
            return _result(_http("GET", f"{TATVIK_URL}/models/runtime/stats"))

        if name == "tatvik_list_adapters":
            return _result(_http("GET", f"{TATVIK_URL}/registry/adapters"))

        if name == "tatvik_list_models_registry":
            return _result(_http("GET", f"{TATVIK_URL}/registry/models"))

        if name == "tatvik_run_evaluation":
            params = {"base_model": args["base_model"]}
            if args.get("adapter_path"):
                params["adapter_path"] = args["adapter_path"]
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            return _result(_http("POST", f"{TATVIK_URL}/evaluation/run?{qs}"))

        if name == "sahapatha_learn":
            body = {"prompt": args["prompt"], "response": args["response"]}
            return _result(_http("POST", f"{TATVIK_URL}/sahapatha/learn", body))

        if name == "sahapatha_status":
            return _result(_http("GET", f"{TATVIK_URL}/sahapatha/status"))

        if name == "sahapatha_train":
            return _result(_http("POST", f"{TATVIK_URL}/sahapatha/train"))

        if name == "governor_kb_search":
            return _result(_http("GET", f"{GOVERNOR_URL}/memory/kb/search?query={args['query']}&k={args.get('k', 5)}"))

        if name == "governor_rag":
            body = {
                "query": args["query"],
                "k": args.get("k", 5),
                "compress": bool(args.get("compress", True)),
                "knowledge_type": args.get("knowledge_type", ""),
            }
            return _result(_http("POST", f"{GOVERNOR_URL}/rag/retrieve", body))

        if name == "governor_stats":
            return _result(_http("GET", f"{GOVERNOR_URL}/memory/stats"))

        if name == "hermes_status":
            return _result(_http("GET", f"{HERMES_URL}/status"))

        if name == "hermes_list_agents":
            return _result(_http("GET", f"{HERMES_URL}/agents"))

        if name == "hermes_run_agent":
            return _result(_http("POST", f"{HERMES_URL}/agents/run", {"agent_id": args["agent_id"]}))

        if name == "compress_context":
            return _result(_s_compress(args["context"], args["query"]))

        return _error(f"unknown tool: {name}")
    except Exception as e:
        return _error(f"{name}: {type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------

async def _list_tools(ctx, params=None) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def _call_tool(ctx, req: CallToolRequestParams) -> CallToolResult:
    args = dict(req.arguments or {})
    return await _handle_tool(req.name, args)


def _build_server() -> Server:
    return Server(
        "tatvik-platform",
        version="0.1.0",
        instructions=(
            "Bridge to the Tatvik local LLM platform: chat/generate against the local model, "
            "manage models/adapters/training, query Governor's knowledge base + RAG, orchestrate "
            "Hermes agents, and compress prompt context with SuperCompress."
        ),
        on_list_tools=_list_tools,
        on_call_tool=_call_tool,
    )


async def main() -> None:
    server = _build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import anyio
    anyio.run(main)
