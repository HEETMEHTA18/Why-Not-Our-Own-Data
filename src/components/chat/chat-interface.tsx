"use client"

import { useState, useRef, useEffect } from "react"
import { useChat } from "@/hooks/use-chat"
import { Message } from "./message"
import { InputBar } from "./input-bar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Trash2, Brain, RefreshCw, Code2, Bug, GitBranch, Sparkles, X, FlaskConical, Plus, History, MessageSquare } from "lucide-react"
import type { SahapathaStatus } from "@/lib/types"
import { SUGGESTIONS } from "@/lib/system-prompt"
import { cn } from "@/lib/utils"

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"

const SUGGESTION_ICONS: Record<string, React.ReactNode> = {
  Code2: <Code2 className="w-4 h-4" />,
  Bug: <Bug className="w-4 h-4" />,
  GitBranch: <GitBranch className="w-4 h-4" />,
  Sparkles: <Sparkles className="w-4 h-4" />,
}

export function ChatInterface() {
  const { messages, isLoading, sendMessage, rateMessage, clearMessages, conversations, activeConversationId, startNewConversation, openConversation, deleteConversation, stopGenerating } = useChat()
  const [models, setModels] = useState<{ id: string; name: string }[]>([])
  const [selectedModel, setSelectedModel] = useState("")
  const [sahapatha, setSahapatha] = useState<SahapathaStatus | null>(null)
  const [bufferCount, setBufferCount] = useState(0)
  const [showSidebar, setShowSidebar] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchModels = async () => {
    try {
      const [modelsRes, sahRes] = await Promise.all([
        fetch(`${API}/models`),
        fetch(`${API}/sahapatha/status`).then(r => r.json()).catch(() => ({} as SahapathaStatus)),
      ])
      const data = await modelsRes.json()
      const list = data.map((m: any) => {
        const raw = m.name || m.model || ""
        const name = raw.split("/").pop()!.replace(/\.gguf$/i, "").replace(/-instruct-q4_k_m$/i, "").replace(/-/g, " ")
        return { id: raw, name }
      })
      if (sahRes.latest_version && sahRes.total_versions > 0) {
        list.unshift({
          id: "sahapatha://trained",
          name: `Trained v${sahRes.latest_version} (Sahapatha)`,
        })
      }
      setModels(list)
      if (list.length > 0 && !selectedModel) setSelectedModel(list[0].id)
    } catch {}
  }

  const fetchSahapatha = async () => {
    try {
      const statusRes = await fetch(`${API}/sahapatha/status`)
      const data = await statusRes.json()
      setSahapatha(data)
      setBufferCount(data.buffer_size || 0)
    } catch {}
  }

  useEffect(() => {
    fetchModels()
    fetchSahapatha()
    const interval = setInterval(fetchSahapatha, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full min-h-0 gap-4">
      {showHistory && (
        <div className="w-64 shrink-0 flex flex-col rounded-lg border border-border bg-background/60 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
            <div className="flex items-center gap-2 text-sm font-medium">
              <History className="w-4 h-4 text-muted-foreground" />
              Conversations
            </div>
            <Button variant="ghost" size="icon" className="w-6 h-6" onClick={() => setShowHistory(false)}>
              <X className="w-3.5 h-3.5" />
            </Button>
          </div>
          <ScrollArea className="flex-1 min-h-0">
            <div className="p-2 space-y-0.5">
              {conversations.length === 0 && (
                <p className="text-xs text-muted-foreground px-3 py-6 text-center">
                  No conversations yet. Start chatting to save them here.
                </p>
              )}
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={cn(
                    "group flex items-start gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors",
                    c.id === activeConversationId
                      ? "bg-secondary/70 text-foreground"
                      : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
                  )}
                  onClick={() => openConversation(c.id, c.model)}
                >
                  <MessageSquare className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate">{c.title}</p>
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                      {new Date(c.updatedAt).toLocaleDateString()} {new Date(c.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteConversation(c.id) }}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-opacity shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-background/60 overflow-hidden relative">
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-border/60">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="max-w-full rounded-md border border-border/60 bg-background/70 px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          <div className="flex items-center gap-1.5">
            <Button variant="ghost" size="sm" onClick={startNewConversation} className="text-muted-foreground">
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              New
            </Button>
            {bufferCount > 0 && (
              <span className="text-xs font-medium text-amber-200 bg-amber-500/10 ring-1 ring-amber-500/20 px-2.5 py-1 rounded-full">
                {bufferCount} in buffer
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => { fetchModels(); fetchSahapatha(); }} className="text-muted-foreground">
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowHistory(v => !v)} className={cn("text-muted-foreground", showHistory && "text-foreground bg-secondary/50")}>
              <History className="w-3.5 h-3.5 mr-1.5" />
              History
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSidebar(v => !v)}
              className={cn("text-muted-foreground", showSidebar && "text-foreground bg-secondary/50")}
            >
              <FlaskConical className="w-3.5 h-3.5 mr-1.5" />
              Training
            </Button>
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearMessages} className="text-muted-foreground">
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                Clear
              </Button>
            )}
          </div>
        </div>

        <ScrollArea ref={scrollRef} className="flex-1 min-h-0">
          <div className="px-4 md:px-8 py-4 space-y-6 min-h-full">
            {isEmpty && (
              <div className="flex flex-col items-center justify-center h-full min-h-[420px] py-16 text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center mb-6 shadow-lg shadow-emerald-500/20">
                  <Brain className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-2xl md:text-3xl font-semibold tracking-tight mb-2">How can I help you today?</h2>
                <p className="text-sm text-muted-foreground mb-10 max-w-md">
                  Tatvik runs locally on your hardware — your code and conversations never leave your machine.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s.title}
                      onClick={() => sendMessage(s.prompt, selectedModel)}
                      className="group text-left rounded-xl border border-border/60 bg-secondary/30 hover:bg-secondary/60 hover:border-border px-4 py-3.5 transition-all duration-200 card-hover"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center text-primary shrink-0">
                          {SUGGESTION_ICONS[s.icon] || <Sparkles className="w-4 h-4" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground/90">{s.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{s.prompt}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <Message key={msg.id} message={msg} onRate={rateMessage} />
            ))}

            {isLoading && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                  <Brain className="w-4 h-4 text-muted-foreground animate-pulse" />
                </div>
                <div className="flex flex-col gap-2 py-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span className="text-xs text-muted-foreground">Thinking...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <InputBar onSend={(msg) => sendMessage(msg, selectedModel)} isLoading={isLoading} onStop={stopGenerating} />
      </div>

      {showSidebar && (
        <div className="w-64 shrink-0 flex flex-col gap-3 overflow-y-auto">
          <Card className="p-4 space-y-4 bg-card/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <FlaskConical className="w-3.5 h-3.5 text-primary" />
                <span className="font-medium text-foreground">Sahapatha Training</span>
              </div>
              <Button variant="ghost" size="icon" className="w-6 h-6" onClick={() => setShowSidebar(false)}>
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-md bg-secondary/50 px-3 py-2 text-xs">
                <span className="text-muted-foreground">Buffer</span>
                <div className="flex items-center gap-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${bufferCount > 0 ? 'bg-amber-400' : 'bg-muted-foreground/30'}`} />
                  <span className="font-mono font-medium">{bufferCount}</span>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-md bg-secondary/50 px-3 py-2 text-xs">
                <span className="text-muted-foreground">Versions</span>
                <span className="font-mono font-medium">{sahapatha?.total_versions || 0}</span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-secondary/50 px-3 py-2 text-xs">
                <span className="text-muted-foreground">Latest</span>
                <span className="font-mono font-medium text-primary">v{sahapatha?.latest_version || "—"}</span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-secondary/50 px-3 py-2 text-xs">
                <span className="text-muted-foreground">Status</span>
                <span className={`text-xs font-medium ${sahapatha?.ready_to_train ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                  {sahapatha?.ready_to_train ? "Ready" : "Collecting"}
                </span>
              </div>
            </div>

            {sahapatha?.last_train_metrics && (
              <div className="pt-2 border-t border-border space-y-1.5">
                <span className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">Last Training</span>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Loss</span>
                  <span className="font-mono font-medium text-emerald-400">
                    {(sahapatha.last_train_metrics as any).best_loss?.toFixed(4) || "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Epochs</span>
                  <span className="font-mono font-medium">{(sahapatha.last_train_metrics as any).epochs || "—"}</span>
                </div>
              </div>
            )}

            {sahapatha?.last_train_time && (
              <div className="pt-2 border-t border-border">
                <span className="text-[10px] text-muted-foreground">
                  Last trained {Math.round((Date.now() - sahapatha.last_train_time * 1000) / 60000)}m ago
                </span>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
