"""Standalone WhatsApp bot using whatsapp-web.js (personal number, no Meta API).

Usage:
    pip install whatsapp-web.js  # or via npm in a Node wrapper — see notes below
    python -m tatvik.scripts.whatsapp_bot

NOTES:
- whatsapp-web.js is a Node library. The cleanest integration is to run this
  logic as a small Node process (index.js) that imports whatsapp-web.js and
  POSTs each inbound message to Tatvik at /models/chat, then replies.
- This Python module provides the Tatvik-side handler used by that Node bridge.
"""

from __future__ import annotations

import httpx

TATVIK_CHAT_URL = "http://localhost:8000/models/chat"
MODEL_ID = "/home/heet18/Documents/Why-Not-Our-Own-Data/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"

SYSTEM = (
    "You are Tatvik, a privacy-first local AI assistant built by Heet Mehta at Autodevs. "
    "Answer the WhatsApp message concisely. Use code blocks for code."
)


async def handle_inbound_message(text: str) -> str:
    """Core handler — call from the Node bridge for every inbound WhatsApp message."""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            TATVIK_CHAT_URL,
            json={
                "model": MODEL_ID,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": text},
                ],
                "stream": False,
            },
        )
        if r.status_code != 200:
            return "⚠️ Tatvik is unavailable right now."
        data = r.json()
        return data.get("message", {}).get("content") or "⚠️ No response."


# Minimal Node bridge (save as whatsapp-bridge/index.js):
NODE_BRIDGE = r"""
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({ authStrategy: new LocalAuth() });

client.on('qr', (qr) => qrcode.generate(qr, { small: true }));
client.on('ready', () => console.log('WhatsApp bot connected!'));

client.on('message', async (msg) => {
  if (msg.fromMe) return;
  try {
    const res = await fetch('http://localhost:8000/models/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: '<MODEL_PATH>',
        messages: [
          { role: 'system', content: 'You are Tatvik, built by Heet Mehta at Autodevs. Be concise.' },
          { role: 'user', content: msg.body },
        ],
        stream: false,
      }),
    });
    const data = await res.json();
    const reply = data.message?.content || '⚠️ No response.';
    await msg.reply(reply);
  } catch (e) {
    await msg.reply('⚠️ Tatvik is offline.');
  }
});

client.initialize();
"""
