"""Governor-side SuperCompress bridge.

Thin wrapper around the shared client (tatvik/shared/supercompress.py) so
the RAG pipeline can compress retrieved context without importing tatvik
internals directly. Falls back to passthrough if unavailable.
"""

from __future__ import annotations


class _PassthroughResult:
    def __init__(self, context: str) -> None:
        self.compressed_text = context
        self.original_tokens = len(context.split())
        self.kept_tokens = len(context.split())
        self.tokens_saved = 0
        self.tokens_saved_pct = 0.0
        self.important_kept_pct = 1.0
        self.compression_risk = "none"
        self.mode = "passthrough"
        self.message = "supercompress unavailable"
        self.compressed = False


def compress_context(context: str, query: str):
    try:
        from tatvik.shared.supercompress import compress_context as _c
        return _c(context, query)
    except Exception:
        return _PassthroughResult(context)


_Passthrough = _PassthroughResult
