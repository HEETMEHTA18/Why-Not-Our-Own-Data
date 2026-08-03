"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Undo2, Check, Archive } from "lucide-react"
import type { Adapter } from "@/lib/types"
import { timeAgo, formatBytes } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface AdapterListProps {
  adapters: Adapter[]
  baseModel: string
}

export function AdapterList({ adapters, baseModel }: AdapterListProps) {
  if (adapters.length === 0) return null

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-2 bg-secondary/50 border-b border-border text-xs text-muted-foreground font-medium">
        {baseModel}
      </div>
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
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  <Archive className="w-3.5 h-3.5 mr-1" />
                  Archive
                </Button>
              ) : (
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  <Undo2 className="w-3.5 h-3.5 mr-1" />
                  Rollback
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
