"use client"

import { Bell, Brain, Gauge } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useNotifications } from "@/hooks/use-notifications"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { useState, useEffect } from "react"

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"

export function Topbar() {
  const { unreadCount } = useNotifications()
  const [modelName, setModelName] = useState("...")
  const [adapterVersion, setAdapterVersion] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const [modelsRes, sahapathaRes] = await Promise.all([
          window.fetch(`${API}/models`).then(r => r.json()).catch(() => []),
          window.fetch(`${API}/sahapatha/status`).then(r => r.json()).catch(() => ({}))
        ])
        if (modelsRes.length > 0) {
          const name = modelsRes[0].name || modelsRes[0].model || "—"
          const friendly = name.split("/").pop()!.replace(/\.gguf$/i, "").replace(/-instruct-q4_k_m$/i, "").replace(/-/g, " ")
          setModelName(friendly.includes("qwen") ? "Qwen 2.5 Coder 3B" : friendly)
        }
        if (sahapathaRes.latest_version) setAdapterVersion(`v${sahapathaRes.latest_version}`)
      } catch {}
    }
    fetch()
    const interval = setInterval(fetch, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="flex items-center justify-between h-16 px-4 md:px-6 border-b border-border bg-background/75 backdrop-blur-xl">
      <div className="flex items-center gap-4 min-w-0">
        <div className="flex items-center gap-2 text-sm text-muted-foreground min-w-0">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-slow" />
            <span className="hidden sm:inline">llama-server</span>
          </div>
          <span className="text-border hidden sm:inline">/</span>
          <div className="flex items-center gap-1.5 min-w-0">
            <Brain className="w-3.5 h-3.5" />
            <span className="truncate">{modelName}</span>
          </div>
          {adapterVersion && (
            <>
              <span className="text-border hidden sm:inline">/</span>
              <div className="flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5" />
                <span className={cn(
                  "text-xs font-semibold px-2 py-1 rounded-full",
                  "text-emerald-300 bg-emerald-500/10 ring-1 ring-emerald-500/20"
                )}>
                  {adapterVersion} active
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Link href="/logs">
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-[10px] font-bold flex items-center justify-center text-primary-foreground">
                {unreadCount}
              </span>
            )}
          </Button>
        </Link>
      </div>
    </header>
  )
}
