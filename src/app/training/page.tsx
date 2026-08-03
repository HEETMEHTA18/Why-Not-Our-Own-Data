"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Cpu, Loader2 } from "lucide-react"
import { tatvik } from "@/lib/api"
import type { AdapterRecord } from "@/lib/types"
import { timeAgo } from "@/lib/utils"

interface TrainingJob {
  id: string
  type: string
  status: string
  progress: number
  error?: string
  created_at: string
}

const statusVariant = (s: string) =>
  s === "completed" ? "success" : s === "failed" ? "destructive" : s === "running" ? "warning" : "secondary"

export default function TrainingPage() {
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [adapters, setAdapters] = useState<AdapterRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      tatvik.training.status().catch(() => []),
      tatvik.training.adapters().catch(() => []),
    ])
      .then(([j, a]) => { setJobs(j as TrainingJob[]); setAdapters(a) })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  return (
    <AppShell>
      <div className="space-y-8 max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary" />
            Training
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Active jobs and completed adapter versions</p>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading training state...
          </div>
        ) : (
          <>
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Jobs</h2>
              {jobs.length === 0 ? (
                <Card><CardContent className="p-6 text-center text-sm text-muted-foreground">No training jobs yet.</CardContent></Card>
              ) : (
                jobs.map((j) => (
                  <Card key={j.id} className="card-hover">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm">{j.id.slice(0, 8)}…</span>
                          <Badge variant={statusVariant(j.status)}>{j.status}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {j.progress > 0 ? `${j.progress}%` : timeAgo(j.created_at)}
                        </div>
                      </div>
                      {j.error && <p className="text-xs text-destructive mt-2">{j.error}</p>}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>

            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Adapters</h2>
              {adapters.length === 0 ? (
                <Card><CardContent className="p-6 text-center text-sm text-muted-foreground">No adapters trained yet.</CardContent></Card>
              ) : (
                adapters.map((a) => (
                  <Card key={a.id} className="card-hover">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm font-medium">
                            {a.base_model_id.slice(0, 6)}… · v{a.version}
                          </span>
                          <Badge variant={statusVariant(a.status)}>{a.status}</Badge>
                          <span className="text-xs text-muted-foreground">{a.dataset_id || a.notes || "—"}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {a.metrics?.eval_score
                            ? `eval ${((a.metrics.eval_score as number) * 100).toFixed(1)}%`
                            : timeAgo(a.created_at)}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
