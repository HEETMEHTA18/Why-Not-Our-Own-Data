"use client"

import { useState, useEffect, useCallback } from "react"

export interface ServiceState {
  name: string
  url: string
  ok: boolean
  latencyMs: number | null
  detail?: string
}

export interface CompressionState {
  enabled: boolean
  mode: "hosted" | "local" | "passthrough" | "unknown"
  apiKeySet: boolean
  minTokens: number
  contextWindow: number
}

const SERVICES: { name: string; url: string; port: number }[] = [
  { name: "Tatvik API", url: "http://localhost:8000/system/health", port: 8000 },
  { name: "Governor", url: "http://localhost:8100/health", port: 8100 },
  { name: "Hermes", url: "http://localhost:8101/health", port: 8101 },
  { name: "llama-server", url: "http://localhost:11434/health", port: 11434 },
]

async function probe(url: string): Promise<{ ok: boolean; latencyMs: number | null; detail?: string }> {
  const started = performance.now()
  try {
    const res = await fetch(url, { cache: "no-store" })
    const latencyMs = Math.round(performance.now() - started)
    return { ok: res.ok, latencyMs }
  } catch {
    return { ok: false, latencyMs: null, detail: "unreachable" }
  }
}

export function useServiceHealth() {
  const [services, setServices] = useState<ServiceState[]>(SERVICES.map(s => ({
    name: s.name, url: s.url, ok: false, latencyMs: null,
  })))
  const [compression, setCompression] = useState<CompressionState>({
    enabled: false, mode: "unknown", apiKeySet: false, minTokens: 100, contextWindow: 4096,
  })

  const refresh = useCallback(async () => {
    const results = await Promise.all(
      SERVICES.map(async (s) => {
        const probeResult = await probe(s.url)
        return { name: s.name, url: s.url, port: s.port, ...probeResult }
      })
    )
    setServices(results)

    try {
      const res = await fetch("http://localhost:8000/system/health", { cache: "no-store" })
      const data = await res.json()
      setCompression({
        enabled: Boolean(data.supercompress?.enabled ?? false),
        mode: (data.supercompress?.mode as CompressionState["mode"]) || "unknown",
        apiKeySet: Boolean(data.supercompress?.api_key_set ?? false),
        minTokens: Number(data.supercompress?.min_tokens ?? 100),
        contextWindow: Number(data.supercompress?.context_window ?? 4096),
      })
    } catch {
      // backend down — keep last known state
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 15000)
    return () => clearInterval(interval)
  }, [refresh])

  return { services, compression, refresh }
}
