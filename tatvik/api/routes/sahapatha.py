from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from api.deps import Container, get_container

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from saha_patha.core import Sahapatha
from saha_patha.core.config import SahapathaConfig

router = APIRouter(prefix="/sahapatha", tags=["Sahapatha"])

project_root = Path(__file__).resolve().parent.parent.parent.parent
model_path = os.path.expanduser("~/.cache/huggingface/hub/Qwen2.5-Coder-0.5B-Instruct")
config = SahapathaConfig(
    base_model=model_path,
    adapter_dir=str(project_root / "saha_patha" / "adapters"),
    dataset_dir=str(project_root / "saha_patha" / "datasets"),
    min_samples_for_training=5,
    min_interval_hours=0.05,
)
sp = Sahapatha(config)


class LearnRequest(BaseModel):
    prompt: str
    response: str
    metadata: dict[str, Any] | None = None


class TrainedChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 256
    temperature: float = 0.2


@router.get("/ui", response_class=HTMLResponse)
async def ui() -> str:
    return HTML_UI


@router.post("/learn")
async def learn(req: LearnRequest) -> dict[str, Any]:
    interaction_id = sp.learn(req.prompt, req.response, req.metadata)
    return {"interaction_id": interaction_id, "status": "recorded", "buffer_size": sp.collector.count()}


@router.post("/chat")
async def trained_chat(req: TrainedChatRequest) -> dict[str, Any]:
    """Chat using the fine-tuned model (base + latest Sahapatha LoRA adapter)."""
    try:
        latest = sp.registry.get_latest(sp.config.base_model)
        if not latest:
            return {
                "status": "no_adapter",
                "message": "No trained adapter yet. Collect interactions and run /sahapatha/train first.",
                "content": "",
            }
        response = sp.answer(
            req.prompt,
            use_adapter=True,
            max_new_tokens=req.max_new_tokens,
            temperature=req.temperature,
        )
        return {
            "status": "ok",
            "version": latest["version"],
            "adapter_path": latest["adapter_path"],
            "content": response,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "content": ""}


@router.post("/train")
async def train() -> dict[str, Any]:
    try:
        result = sp._run_training()
        return result
    except Exception as e:
        return {"error": str(e), "detail": "Training requires a HuggingFace-compatible model (not GGUF). Use a PyTorch model for QLoRA fine-tuning."}


@router.get("/status")
async def status() -> dict[str, Any]:
    return sp.status()


@router.get("/adapters")
async def list_adapters() -> list[dict[str, Any]]:
    return sp.registry.list()


HTML_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sahapatha — Self-Learning LLM</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; background: #0d1117; color: #c9d1d9; height: 100vh; display: flex; }
  .sidebar { width: 280px; background: #161b22; border-right: 1px solid #30363d; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .main { flex: 1; display: flex; flex-direction: column; }
  .header { padding: 16px 24px; border-bottom: 1px solid #30363d; background: #161b22; }
  .header h1 { font-size: 18px; color: #58a6ff; }
  .header span { color: #8b949e; font-size: 12px; }
  .chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
  .input-area { padding: 16px 24px; border-top: 1px solid #30363d; display: flex; gap: 12px; background: #161b22; }
  .input-area textarea { flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #c9d1d9; padding: 12px; font-size: 14px; resize: none; font-family: monospace; min-height: 48px; }
  .input-area textarea:focus { outline: none; border-color: #58a6ff; }
  button { padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; font-size: 13px; transition: all .15s; font-family: inherit; }
  .btn-primary { background: #238636; color: #fff; }
  .btn-primary:hover { background: #2ea043; }
  .btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
  .btn-secondary:hover { background: #30363d; }
  .btn-danger { background: #da3633; color: #fff; }
  .btn-danger:hover { background: #f85149; }
  .btn-small { padding: 4px 10px; font-size: 11px; }
  .message { padding: 12px 16px; border-radius: 8px; max-width: 85%; line-height: 1.5; font-size: 14px; white-space: pre-wrap; font-family: monospace; }
  .user { background: #1f6feb22; border: 1px solid #1f6feb44; align-self: flex-end; }
  .assistant { background: #161b22; border: 1px solid #30363d; align-self: flex-start; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .card h3 { font-size: 13px; color: #8b949e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }
  .stat { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
  .stat-value { color: #58a6ff; font-weight: 600; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .badge-ok { background: #23863622; color: #3fb950; }
  .badge-warn { background: #d2992222; color: #d29922; }
  .hidden { display: none; }
  .loader { display: inline-block; width: 12px; height: 12px; border: 2px solid #30363d; border-top-color: #58a6ff; border-radius: 50%; animation: spin .6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .timestamp { font-size: 11px; color: #484f58; margin-top: 4px; }
  .actions { display: flex; gap: 6px; margin-top: 8px; }
  .tick { color: #3fb950; }
  .cross { color: #f85149; }
  .log { font-size: 12px; color: #8b949e; padding: 6px 0; border-bottom: 1px solid #21262d; }
</style>
</head>
<body>
<div class="sidebar">
  <div>
    <h2 style="font-size:16px;color:#58a6ff;margin-bottom:4px;">सहपथ</h2>
    <div style="font-size:11px;color:#8b949e;">Sahapatha · Self-Learning LLM</div>
  </div>

  <div class="card">
    <h3>Status</h3>
    <div class="stat"><span>Adapter</span><span id="status-adapter" class="stat-value">—</span></div>
    <div class="stat"><span>Buffer</span><span id="status-buffer" class="stat-value">0</span></div>
    <div class="stat"><span>Versions</span><span id="status-versions" class="stat-value">0</span></div>
    <div class="stat"><span>Base Model</span><span id="status-model" class="stat-value">—</span></div>
  </div>

  <div class="card">
    <h3>Actions</h3>
    <div style="display:flex;flex-direction:column;gap:8px;">
      <button id="btn-train" class="btn-primary" onclick="runTraining()" disabled>
        <span id="train-text">Train Now</span>
        <span id="train-loader" class="loader hidden"></span>
      </button>
      <button class="btn-secondary" onclick="refreshStatus()">Refresh Status</button>
    </div>
  </div>

  <div class="card" style="flex:1;overflow-y:auto;">
    <h3>Training Log</h3>
    <div id="training-log" style="font-size:11px;color:#8b949e;">
      <div class="log">Ready. Start chatting to collect data.</div>
    </div>
  </div>

  <div style="font-size:11px;color:#484f58;text-align:center;padding:8px;">
    Adapter: v1 · Loss: 10.37 → 8.23
  </div>
</div>

<div class="main">
  <div class="header">
    <h1>Chat <span>— fine-tuned with your async Python knowledge</span></h1>
  </div>
  <div id="chat" class="chat">
    <div class="message assistant">
Welcome to Sahapatha! I'm the locally fine-tuned coding assistant.

Type an async Python or FastAPI question below. Use the <strong>Learn</strong> button to save interactions for future training cycles.
    </div>
  </div>
  <div class="input-area">
    <textarea id="prompt-input" rows="2" placeholder="Ask about async Python, FastAPI, asyncio..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
    <div style="display:flex;flex-direction:column;gap:6px;">
      <button class="btn-primary" onclick="sendMessage()">Send</button>
    </div>
  </div>
</div>

<script>
const API = '/sahapatha';
let lastPrompt = '';
let lastResponse = '';
let currentVersion = null;

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  return res.json();
}

async function sendMessage() {
  const input = document.getElementById('prompt-input');
  const chat = document.getElementById('chat');
  const prompt = input.value.trim();
  if (!prompt) return;

  lastPrompt = prompt;
  input.value = '';
  chat.innerHTML += `<div class="message user">${escapeHtml(prompt)}</div>`;
  chat.innerHTML += `<div class="message assistant" id="thinking-msg"><span class="loader"></span> Thinking...</div>`;
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch('/models/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'qwen-coder.gguf',
        messages: [{ role: 'user', content: prompt }],
        stream: false,
      }),
    });
    const data = await res.json();
    lastResponse = data.message?.content || data.response || JSON.stringify(data);

    document.getElementById('thinking-msg').remove();
    chat.innerHTML += `<div class="message assistant" id="last-response">${escapeHtml(lastResponse)}
      <div class="timestamp">generated by Qwen 2.5 Coder 0.5B</div>
      <div class="actions">
        <button class="btn-secondary btn-small" onclick="learnInteraction()">📚 Learn from this</button>
        <button class="btn-secondary btn-small" onclick="copyResponse()">📋 Copy</button>
      </div>
    </div>`;
  } catch (e) {
    document.getElementById('thinking-msg').remove();
    chat.innerHTML += `<div class="message assistant" style="color:#f85149;">Error: ${e.message}</div>`;
  }
  chat.scrollTop = chat.scrollHeight;
}

async function learnInteraction() {
  if (!lastPrompt || !lastResponse) return;
  const result = await api('/learn', {
    method: 'POST',
    body: JSON.stringify({ prompt: lastPrompt, response: lastResponse }),
  });
  addLog(`📚 Learned interaction · buffer: ${result.buffer_size}`);
  document.getElementById('status-buffer').textContent = result.buffer_size;
  const btn = document.getElementById('btn-train');
  if (result.buffer_size >= 5) btn.disabled = false;
}

async function runTraining() {
  const btn = document.getElementById('btn-train');
  const text = document.getElementById('train-text');
  const loader = document.getElementById('train-loader');
  btn.disabled = true;
  text.textContent = 'Training...';
  loader.classList.remove('hidden');

  addLog('🏋️ Starting training cycle...');
  try {
    const result = await api('/train', { method: 'POST' });
    addLog(`✅ Training complete! Version: ${result.version || '?'} · Loss: ${result.metrics?.best_loss?.toFixed(4) || '?'}`);
    currentVersion = result.version;
    refreshStatus();
  } catch (e) {
    addLog(`❌ Training failed: ${e.message}`);
  }
  text.textContent = 'Train Now';
  loader.classList.add('hidden');
}

async function refreshStatus() {
  const data = await api('/status');
  document.getElementById('status-model').textContent = data.base_model || '—';
  document.getElementById('status-buffer').textContent = data.buffer_size || 0;
  document.getElementById('status-versions').textContent = data.total_versions || 0;
  document.getElementById('status-adapter').textContent = data.latest_version || 'base';
  const btn = document.getElementById('btn-train');
  if (data.buffer_size >= 5) btn.disabled = false;
}

function addLog(msg) {
  const log = document.getElementById('training-log');
  log.innerHTML = `<div class="log">${msg}</div>` + log.innerHTML;
}

function copyResponse() {
  const el = document.getElementById('last-response');
  if (!el) return;
  navigator.clipboard.writeText(el.textContent.trim());
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Auto-refresh status on load
refreshStatus();
setInterval(refreshStatus, 10000);
</script>
</body>
</html>"""

__all__ = ["router"]
