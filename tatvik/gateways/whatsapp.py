from __future__ import annotations

"""WhatsApp agent gateway — routes incoming WhatsApp messages to the local Tatvik LLM.

Two transport options:
1. Meta Cloud API (official, production): requires WHATSAPP_TOKEN + VERIFY_TOKEN.
   Configure in `gateways/whatsapp/config.py`.
2. whatsapp-web.js (personal number, web scrape): see `tatvik/scripts/whatsapp_bot.py`.

The webhook receives an inbound message, calls Tatvik's chat endpoint, and sends
the reply back through the Meta Graph API.
"""

import httpx
import structlog
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

TATVIK_CHAT_URL = "http://localhost:8000/models/chat"
MODEL_ID = "sahapatha://trained"  # use the fine-tuned model for replies


class WhatsAppMessage(BaseModel):
    from_number: str
    text: str
    message_id: str = ""


class WhatsAppWebhookPayload(BaseModel):
    object: str = "whatsapp_business_account"
    entry: list[dict] = []


def _extract_message(payload: dict) -> WhatsAppMessage | None:
    """Parse a Meta Cloud API webhook payload into a simple message."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for contact in value.get("contacts", []):
                wa_id = contact.get("wa_id")
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        return WhatsAppMessage(
                            from_number=wa_id or "",
                            text=msg.get("text", {}).get("body", ""),
                            message_id=msg.get("id", ""),
                        )
    return None


async def _ask_tatvik(text: str) -> str:
    """Send the message to the local LLM. Uses the trained model if available."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{TATVIK_CHAT_URL}/stream" if "/chat/stream" in TATVIK_CHAT_URL else TATVIK_CHAT_URL,
                json={
                    "model": MODEL_ID,
                    "messages": [{"role": "user", "content": text}],
                    "stream": False,
                },
            )
            if r.status_code != 200:
                return "⚠️ Tatvik is unavailable right now."
            data = r.json()
            return data.get("message", {}).get("content") or data.get("response") or "⚠️ No response."
    except Exception as e:
        logger.error("whatsapp_tatvik_error", error=str(e))
        return "⚠️ Could not reach the local model."


async def _send_whatsapp(to: str, text: str) -> None:
    """Send a reply via Meta Cloud API. Requires env: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID."""
    import os

    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        logger.warning("whatsapp_not_configured", to=to)
        return
    async with httpx.AsyncClient(timeout=20) as client:
        await client.post(
            f"https://graph.facebook.com/v19.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )


@router.get("/webhook")
async def verify_webhook(request: Request) -> dict:
    """Meta verification handshake. Pass ?hub.mode=subscribe&hub.verify_token=TOKEN."""
    import os

    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    if mode == "subscribe" and token == verify_token:
        return {"challenge": params.get("hub.challenge", "")}
    raise HTTPException(403, "Verification failed")


@router.post("/webhook")
async def webhook(request: Request) -> dict:
    """Receive a WhatsApp message, get a Tatvik reply, send it back."""
    payload = await request.json()
    msg = _extract_message(payload)
    if not msg:
        return {"status": "ignored"}

    logger.info("whatsapp_inbound", from_number=msg.from_number, text=msg.text[:80])
    reply = await _ask_tatvik(msg.text)
    await _send_whatsapp(msg.from_number, reply)
    return {"status": "replied"}
