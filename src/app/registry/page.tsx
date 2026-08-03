"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Boxes, Loader2 } from "lucide-react"
import { tatvik } from "@/lib/api"
import { timeAgo } from "@/lib/utils"

interface RegistryModel {
  id: string
  name: string
  tag: string
  size_bytes: number
  is_available: boolean
  metadata: Record<string, unknown>
  created_at: string
}

function fmtSize(bytes: number): string {
  if (!bytes) return "-"
  const mb = bytes / 1024 / 1024
  if (mb < 1024) return `${mb.toFixed(0)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

export default function RegistryPage() {
  const [models, setModels] = useState<RegistryModel[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    tatvik.registry.models().catch(() => []).then((m) => {
      setModels(m as RegistryModel[])
      setIsLoading(false)
    })
  }, [])

  return (
    <AppShell>
      <div className="space-y-8 max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Boxes className="w-5 h-5 text-primary" />
            Model Registry
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Registered base models and their versions</p>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading registry...
          </div>
        ) : models.length === 0 ? (
          <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No base models registered yet.</CardContent></Card>
        ) : (
          <div className="space-y-3">
            {models.map((m) => (
              <Card key={m.id} className="card-hover">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
                        <Boxes className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium font-mono text-sm">{m.name}</h3>
                          <Badge variant={m.is_available ? "success" : "secondary"}>
                            {m.is_available ? "available" : "unavailable"}
                          </Badge>
                          <Badge variant="secondary" className="text-[10px]">:{m.tag}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {fmtSize(m.size_bytes)}
                          {m.metadata?.params ? ` · ${m.metadata.params}` : ""}
                          {m.metadata?.family ? ` · ${m.metadata.family}` : ""}
                          {m.metadata?.quantization ? ` · ${m.metadata.quantization}` : ""}
                          {" · "}registered {timeAgo(m.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground font-mono">{m.id.slice(0, 8)}…</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}
