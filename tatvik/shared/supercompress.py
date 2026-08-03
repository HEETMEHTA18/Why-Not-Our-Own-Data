"""SuperCompress — query-aware prompt compression client.

Sits between the app and the local LLM: reduces input tokens before
inference while preserving evidence the model needs to answer correctly.

Two modes:
  * hosted API  — POST /api/v1/compress with an `sc_live_*` key
  * local pip   — if the `supercompress` package is installed, it is used
                  on-device with no key and no network call

Configuration (env, TATVIK_ prefix) is read lazily so the module works
standalone in Tatvik, Governor, Sahapatha, and Hermes:

  TATVIK_SUPERCOMPRESS_ENABLED      (bool, default true)
  TATVIK_SUPERCOMPRESS_API_KEY      (str,  default "")
  TATVIK_SUPERCOMPRESS_HOST         (str,  default https://www.supercompress.dev)
  TATVIK_SUPERCOMPRESS_MIN_TOKENS   (int,  default 100 — skip tiny contexts)
  TATVIK_SUPERCOMPRESS_TIMEOUT      (float, default 10s)

Graceful degradation: disabled / no key / network error / package missing
all return the original context untouched, so the LLM pipeline never breaks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CompressResult:
    compressed_text: str
    original_tokens: int = 0
    kept_tokens: int = 0
    tokens_saved: int = 0
    tokens_saved_pct: float = 0.0
    important_kept_pct: float = 1.0
    compression_risk: str = "none"
    policy_name: str = ""
    mode: str = "passthrough"
    compressed: bool = False
    message: str = ""
    dropped_blocks: list[str] = field(default_factory=list)
    kept_blocks: list[str] = field(default_factory=list)


def _env(name: str, default: Any) -> Any:
    return os.environ.get(f"TATVIK_{name}", default)


def _approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.split()))


class SuperCompressClient:
    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        enabled: bool | None = None,
        min_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key or _env("SUPERCOMPRESS_API_KEY", "") or ""
        self.host = (host or _env("SUPERCOMPRESS_HOST", "") or "https://www.supercompress.dev").rstrip("/")
        self.enabled = self._as_bool(enabled if enabled is not None else _env("SUPERCOMPRESS_ENABLED", True))
        self.min_tokens = int(min_tokens if min_tokens is not None else _env("SUPERCOMPRESS_MIN_TOKENS", 100))
        self.timeout = float(timeout if timeout is not None else _env("SUPERCOMPRESS_TIMEOUT", 10))
        self._local = self._try_local_import()

    @staticmethod
    def _as_bool(v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)

    def _try_local_import(self) -> bool:
        try:
            import supercompress  # noqa: F401
            return True
        except Exception:
            return False

    @property
    def available(self) -> bool:
        """True when compression can actually run (enabled + key or local pkg)."""
        if not self.enabled:
            return False
        return bool(self.api_key) or self._local

    # ---- sync API ----

    def compress(self, context: str, query: str) -> CompressResult:
        """Compress `context` against `query`. Never raises; degrades to passthrough."""
        if not self.enabled:
            return self._passthrough(context, "disabled")
        if not context or not context.strip():
            return self._passthrough(context, "empty context")
        if _approx_tokens(context) < self.min_tokens:
            return self._passthrough(context, f"below min_tokens ({self.min_tokens})")

        if self._local and not self.api_key:
            return self._compress_local(context, query)

        if not self.api_key:
            return self._passthrough(context, "no API key and no local package")

        result = self._compress_hosted(context, query)
        if not result.compressed and self._local:
            return self._compress_local(context, query)
        return result

    def _passthrough(self, context: str, reason: str) -> CompressResult:
        return CompressResult(
            compressed_text=context,
            original_tokens=_approx_tokens(context),
            kept_tokens=_approx_tokens(context),
            compressed=False,
            message=reason,
        )

    def _compress_hosted(self, context: str, query: str) -> CompressResult:
        try:
            import httpx
            resp = httpx.post(
                f"{self.host}/api/v1/compress",
                headers={"X-API-Key": self.api_key},
                json={"context": context, "query": query},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return CompressResult(
                compressed_text=data.get("compressed_text", context),
                original_tokens=int(data.get("original_tokens", 0)),
                kept_tokens=int(data.get("kept_tokens", 0)),
                tokens_saved=int(data.get("tokens_saved", 0)),
                tokens_saved_pct=float(data.get("tokens_saved_pct", 0.0)),
                important_kept_pct=float(data.get("important_kept_pct", 1.0)),
                compression_risk=str(data.get("compression_risk", "")),
                policy_name=str(data.get("policy_name", "")),
                mode=str(data.get("mode", "hosted")),
                compressed=True,
                dropped_blocks=[
                    b.get("type", "") + ":" + " ".join(str(b.get("start_line", "")))
                    for b in (data.get("dropped_blocks") or [])
                ],
                kept_blocks=[
                    b.get("type", "") + ":" + " ".join(str(b.get("start_line", "")))
                    for b in (data.get("kept_blocks") or [])
                ],
            )
        except Exception as e:
            return self._passthrough(context, f"hosted error: {e}")

    def _compress_local(self, context: str, query: str) -> CompressResult:
        try:
            from supercompress import compress_context
            result = compress_context(context, query)
            compressed = getattr(result, "compressed_text", None)
            if not compressed:
                return self._passthrough(context, "local result missing text")
            original = int(getattr(result, "original_tokens", 0) or _approx_tokens(context))
            kept = int(getattr(result, "kept_tokens", 0) or _approx_tokens(compressed))
            kv_pct = getattr(result, "kv_savings_pct", None)
            if kv_pct is None:
                ratio = getattr(result, "compression_ratio", None)
                kv_pct = 0.0 if ratio in (None, 0.0) else (1.0 - 1.0 / ratio) * 100
            return CompressResult(
                compressed_text=compressed,
                original_tokens=original,
                kept_tokens=kept,
                tokens_saved=max(0, original - kept),
                tokens_saved_pct=float(kv_pct or 0.0),
                compression_risk=str(getattr(result, "compression_risk", "") or ""),
                policy_name=str(getattr(result, "policy_name", "") or "supercompress"),
                mode="local",
                compressed=kept < original,
            )
        except Exception as e:
            return self._passthrough(context, f"local error: {e}")

    # ---- async API ----

    async def acompress(self, context: str, query: str) -> CompressResult:
        """Async variant of :meth:`compress` for FastAPI route handlers."""
        if not self.enabled:
            return self._passthrough(context, "disabled")
        if not context or not context.strip():
            return self._passthrough(context, "empty context")
        if _approx_tokens(context) < self.min_tokens:
            return self._passthrough(context, f"below min_tokens ({self.min_tokens})")

        if self._local and not self.api_key:
            return self._compress_local(context, query)

        if not self.api_key:
            return self._passthrough(context, "no API key and no local package")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.host}/api/v1/compress",
                    headers={"X-API-Key": self.api_key},
                    json={"context": context, "query": query},
                )
                resp.raise_for_status()
                data = resp.json()
            return CompressResult(
                compressed_text=data.get("compressed_text", context),
                original_tokens=int(data.get("original_tokens", 0)),
                kept_tokens=int(data.get("kept_tokens", 0)),
                tokens_saved=int(data.get("tokens_saved", 0)),
                tokens_saved_pct=float(data.get("tokens_saved_pct", 0.0)),
                important_kept_pct=float(data.get("important_kept_pct", 1.0)),
                compression_risk=str(data.get("compression_risk", "")),
                policy_name=str(data.get("policy_name", "")),
                mode=str(data.get("mode", "hosted")),
                compressed=True,
            )
        except Exception as e:
            result = self._passthrough(context, f"hosted error: {e}")
            if self._local:
                return self._compress_local(context, query)
            return result


_client: Optional[SuperCompressClient] = None


def get_client() -> SuperCompressClient:
    global _client
    if _client is None:
        _client = SuperCompressClient()
    return _client


def compress_context(context: str, query: str) -> CompressResult:
    """Module-level convenience wrapper (sync)."""
    return get_client().compress(context, query)


async def acompress_context(context: str, query: str) -> CompressResult:
    """Module-level convenience wrapper (async)."""
    return await get_client().acompress(context, query)
