"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import type { Message, Conversation } from "@/lib/types"
import { SYSTEM_PROMPT } from "@/lib/system-prompt"

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"
const STORAGE_KEY = "tatvik.conversations.v1"
const MAX_CONTEXT_MESSAGES = 8

interface ConversationMeta {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  model: string
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<ConversationMeta[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const TRAINED_MODEL_ID = "sahapatha://trained"

  const isTrainedModel = (id: string) => id === TRAINED_MODEL_ID

  const loadConversations = useCallback(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const list = JSON.parse(raw) as ConversationMeta[]
        setConversations(list.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)))
      }
    } catch {}
  }, [])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const persistConversations = useCallback((list: ConversationMeta[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
    } catch {}
  }, [])

  const startNewConversation = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setMessages([])
    setActiveConversationId(null)
  }, [])

  const openConversation = useCallback((id: string, modelId: string) => {
    if (abortRef.current) abortRef.current.abort()
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const list = JSON.parse(raw) as ConversationMeta[]
      const conv = list.find((c) => c.id === id)
      if (!conv) return
      const convRaw = localStorage.getItem(`tatvik.conv.${id}`)
      if (convRaw) {
        const saved = JSON.parse(convRaw) as Message[]
        setMessages(saved)
      } else {
        setMessages([])
      }
      setActiveConversationId(id)
    } catch {}
  }, [])

  const deleteConversation = useCallback((id: string) => {
    try {
      localStorage.removeItem(`tatvik.conv.${id}`)
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id)
        persistConversations(next)
        return next
      })
      if (activeConversationId === id) {
        setMessages([])
        setActiveConversationId(null)
      }
    } catch {}
  }, [activeConversationId, persistConversations])

  const sendMessage = useCallback(async (content: string, modelId: string) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsLoading(true)

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      model: modelId,
    }
    const assistantMsg: Message = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      model: modelId,
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])

    const history = messages
      .slice(-MAX_CONTEXT_MESSAGES)
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }))

    let contextBlock = ""
    try {
      const ctxRes = await fetch(`${API}/models/context`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: content, max_results: 3 }),
        signal: controller.signal,
      })
      if (ctxRes.ok) {
        const ctxData = await ctxRes.json()
        const snippets = ctxData.snippets || []
        if (snippets.length > 0) {
          const parts = snippets.map(
            (s: { path: string; line: number; content: string }) =>
              `### ${s.path}:${s.line}\n\`\`\`\n${s.content}\n\`\`\``
          )
          contextBlock = `\n\nRelevant project context (from codebase search):\n${parts.join("\n\n")}`
        }
      }
    } catch {}

    let webBlock = ""
    try {
      const webRes = await fetch(`${API}/models/websearch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: content, max_results: 3, fetch_content: true }),
        signal: controller.signal,
      })
      if (webRes.ok) {
        const webData = await webRes.json()
        const results = webData.results || []
        if (results.length > 0) {
          const parts = results.map(
            (r: { title: string; url: string; snippet: string; content: string }) =>
              `### ${r.title}\nURL: ${r.url}\n${(r.content || r.snippet || "").slice(0, 1500)}`
          )
          webBlock = `\n\nLive web search results (from DuckDuckGo):\n${parts.join("\n\n")}`
        }
      }
    } catch {}

    const enrichedPrompt = `${content}${contextBlock}${webBlock}`

    try {
      let responseText = ""
      if (isTrainedModel(modelId)) {
        const res = await fetch(`${API}/sahapatha/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: enrichedPrompt,
            max_new_tokens: 512,
            temperature: 0.3,
          }),
          signal: controller.signal,
        })
        if (!res.ok) {
          const err = await res.text()
          throw new Error(err.slice(0, 200))
        }
        const data = await res.json()
        if (data.status === "no_adapter") {
          throw new Error("No trained adapter yet. Use the base model or run /sahapatha/train first.")
        }
        if (data.status === "error") throw new Error(data.detail)
        responseText = data.content || ""
      } else {
        const res = await fetch(`${API}/models/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: modelId,
            messages: [
              { role: "system", content: SYSTEM_PROMPT },
              ...history,
              { role: "user", content: enrichedPrompt },
            ],
            stream: true,
          }),
          signal: controller.signal,
        })
        if (!res.ok || !res.body) {
          const err = await res.text()
          throw new Error(err.slice(0, 200))
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        const append = (text: string) => {
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = { ...last, content: last.content + text }
            }
            return updated
          })
        }

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n\n")
          buffer = lines.pop() || ""
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue
            const payload = line.slice(6)
            if (payload === "[DONE]") continue
            try {
              const data = JSON.parse(payload)
              if (data.content) append(data.content)
            } catch {}
          }
        }
      }

      if (isTrainedModel(modelId) && responseText) {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: responseText }
          }
          return updated
        })
      }
    } catch (e: unknown) {
      const name = (e as Error)?.name
      if (name !== "AbortError") {
        const msg = e instanceof Error ? e.message : "Request failed"
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: `⚠️ ${msg}` }
          }
          return updated
        })
      }
    } finally {
      setIsLoading(false)
    }

    const finalMessages = messages.concat(userMsg)
    const title = content.length > 48 ? `${content.slice(0, 48)}…` : content
    const now = new Date().toISOString()

    setConversations((prev) => {
      const existing = prev.find((c) => c.id === activeConversationId)
      const meta: ConversationMeta = {
        id: activeConversationId || `conv-${Date.now()}`,
        title: existing?.title || title,
        createdAt: existing?.createdAt || now,
        updatedAt: now,
        model: modelId,
      }
      const list = existing
        ? prev.map((c) => (c.id === meta.id ? meta : c))
        : [meta, ...prev]
      persistConversations(list)
      try {
        localStorage.setItem(`tatvik.conv.${meta.id}`, JSON.stringify(finalMessages))
      } catch {}
      return list
    })
    setActiveConversationId((prev) => prev || `conv-${Date.now()}`)
  }, [messages, activeConversationId, persistConversations])

  const rateMessage = useCallback((messageId: string, rating: "up" | "down") => {
    setMessages((prev) => {
      const updated = prev.map((m) => (m.id === messageId ? { ...m, rating } : m))
      return updated
    })
  }, [])

  const clearMessages = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setMessages([])
  }, [])

  const stopGenerating = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
  }, [])

  return {
    messages,
    isLoading,
    conversations,
    activeConversationId,
    sendMessage,
    rateMessage,
    clearMessages,
    stopGenerating,
    startNewConversation,
    openConversation,
    deleteConversation,
  }
}
