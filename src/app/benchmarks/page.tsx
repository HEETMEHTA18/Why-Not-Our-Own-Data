"use client"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Gauge, Play, Loader2 } from "lucide-react"
import { useState, useCallback } from "react"
import { useBenchmarks } from "@/hooks/use-benchmarks"
import { tatvik } from "@/lib/api"

const SUITE_TASKS = ["mmlu", "gsm8k", "hellaswag", "arc_easy", "boolq"]
const DEFAULT_MODEL = "qwen2.5-coder-3b-instruct"

export default function BenchmarksPage() {
  const { benchmarks, isLoading, refetch } = useBenchmarks()
  const [running, setRunning] = useState<string | null>(null)
  const [runningAll, setRunningAll] = useState(false)
  const [notice, setNotice] = useState("")

  const items = benchmarks.length > 0
    ? benchmarks.map((b) => ({
        id: b.id,
        name: b.task,
        category: b.task,
        currentScore: b.score,
        previousScore: 0,
        maxScore: 100,
      }))
    : []

  const runTask = useCallback(async (task: string) => {
    setRunning(task)
    setNotice("")
    try {
      await tatvik.evaluation.run(DEFAULT_MODEL, undefined, { tasks: [task] })
      setNotice(`Queued ${task}`)
      setTimeout(() => { refetch(); setNotice("") }, 1500)
    } catch (err) {
      setNotice(`Failed to queue ${task}: ${err instanceof Error ? err.message : "error"}`)
    } finally {
      setRunning(null)
    }
  }, [refetch])

  const runAll = useCallback(async () => {
    setRunningAll(true)
    setNotice("")
    try {
      await tatvik.evaluation.run(DEFAULT_MODEL, undefined, { tasks: SUITE_TASKS })
      setNotice("Queued full suite")
      setTimeout(() => { refetch(); setNotice("") }, 1500)
    } catch (err) {
      setNotice(`Failed to queue suite: ${err instanceof Error ? err.message : "error"}`)
    } finally {
      setRunningAll(false)
    }
  }, [refetch])

  return (
    <AppShell>
      <div className="space-y-8 max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
              <Gauge className="w-5 h-5 text-primary" />
              Benchmarks
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Evaluate model performance</p>
          </div>
          <Button className="gap-2" onClick={runAll} disabled={runningAll}>
            {runningAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {runningAll ? "Queuing…" : "Run All"}
          </Button>
        </div>

        {notice && <p className={`text-sm ${notice.startsWith("Failed") ? "text-red-500" : "text-emerald-500"}`}>{notice}</p>}

        {items.length === 0 && !isLoading && (
          <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">No benchmarks run yet.</CardContent></Card>
        )}

        <div className="grid grid-cols-1 gap-3">
          {items.map((bm) => {
            const pct = (bm.currentScore / Math.max(bm.maxScore, 1)) * 100
            return (
              <Card key={bm.id} className="card-hover">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
                        <span className="text-lg font-bold font-mono text-primary">{bm.currentScore.toFixed(1)}</span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{bm.name}</h3>
                          <Badge variant="secondary" className="text-[10px]">{bm.category}</Badge>
                        </div>
                        <div className="mt-2">
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span>Score: {bm.currentScore.toFixed(1)}</span>
                          </div>
                          <div className="mt-2 w-full bg-secondary rounded-full h-1.5">
                            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => runTask(bm.name)}
                      disabled={running === bm.name}
                    >
                      {running === bm.name ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1" />}
                      {running === bm.name ? "Queuing…" : "Run"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </AppShell>
  )
}
