"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Undo2, Rocket, Loader2 } from "lucide-react"
import type { Adapter } from "@/lib/types"
import { timeAgo, formatBytes } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { tatvik } from "@/lib/api"

interface AdapterListProps {
  adapters: Adapter[]
  baseModel: string
  onChanged?: () => void
}

export function AdapterList({ adapters, baseModel, onChanged }: AdapterListProps) {
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState("")

  if (adapters.length === 0) return null

  const act = async (adapterId: string, action: "deploy" | "rollback") => {
    setBusy(adapterId)
    setNotice("")
    try {
      if (action === "deploy") {
        await tatvik.deployment.deploy(adapterId)
        setNotice(`Deployed ${adapterId}`)
      } else {
        await tatvik.deployment.rollback(adapterId)
        setNotice(`Rolled back ${adapterId}`)
      }
      setTimeout(() => { setNotice(""); onChanged?.() }, 1500)
    } catch (err) {
      setNotice(`Action failed: ${err instanceof Error ? err.message : "error"}`)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-2 bg-secondary/50 border-b border-border text-xs text-muted-foreground font-medium">
        {baseModel}
      </div>
      {notice && <div className={`px-4 py-2 text-xs ${notice.startsWith("Action") ? "text-red-500" : "text-emerald-500"}`}>{notice}</div>}
      <div className="divide-y divide-border">
        {adapters.map((adapter) => (
          <div key={adapter.id} className="flex items-center justify-between px-4 py-3 hover:bg-secondary/30 transition-colors">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-2 h-2 rounded-full",
                adapter.status === "active" ? "bg-emerald-500" : "bg-muted-foreground/30"
              )} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{adapter.version}</span>
                  <Badge variant={adapter.status === "active" ? "success" : "secondary"}>
                    {adapter.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                  <span>{timeAgo(adapter.createdAt)}</span>
                  <span>{formatBytes(adapter.size)}</span>
                  {adapter.metrics && (
                    <>
                      <span>Acc: {adapter.metrics.accuracy}%</span>
                      <span>Score: {adapter.metrics.evalScore}%</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {adapter.status === "active" ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground"
                  disabled={busy === adapter.id}
                  onClick={() => act(adapter.id, "rollback")}
                  title="Roll back this adapter"
                >
                  {busy === adapter.id ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Undo2 className="w-3.5 h-3.5 mr-1" />}
                  Rollback
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground"
                  disabled={busy === adapter.id}
                  onClick={() => act(adapter.id, "deploy")}
                  title="Deploy this adapter"
                >
                  {busy === adapter.id ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Rocket className="w-3.5 h-3.5 mr-1" />}
                  Deploy
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
