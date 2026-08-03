"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, TrendingUp, FlaskConical } from "lucide-react"
import type { Benchmark, Experiment } from "@/lib/types"
import { timeAgo } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface RecentActivityProps {
  benchmarks: Benchmark[]
  experiments: Experiment[]
}

export function RecentActivity({ benchmarks, experiments }: RecentActivityProps) {
  const recent = [
    ...benchmarks.map((b) => ({ type: "benchmark" as const, data: b })),
    ...experiments.map((e) => ({ type: "experiment" as const, data: e })),
  ]
    .sort((a, b) => {
      const ta = a.type === "benchmark" ? a.data.date : (a.data as Experiment).startedAt
      const tb = b.type === "benchmark" ? b.data.date : (b.data as Experiment).startedAt
      return new Date(tb).getTime() - new Date(ta).getTime()
    })
    .slice(0, 5)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Recent Activity
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {recent.map((item) => {
          if (item.type === "benchmark") {
            const b = item.data as Benchmark
            return (
              <div key={b.id} className="flex items-center justify-between text-sm py-1.5">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                  <span>{b.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "font-mono text-xs",
                    b.previousScore && b.score > b.previousScore ? "text-emerald-400" : "text-muted-foreground"
                  )}>
                    {b.score}%
                  </span>
                  {b.previousScore && (
                    <span className={cn(
                      "text-xs",
                      b.score >= b.previousScore ? "text-emerald-400" : "text-red-400"
                    )}>
                      {b.score >= b.previousScore ? "+" : ""}{(b.score - b.previousScore).toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            )
          }
          const e = item.data as Experiment
          return (
            <div key={e.id} className="flex items-center justify-between text-sm py-1.5">
              <div className="flex items-center gap-2">
                <FlaskConical className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="truncate max-w-[160px]">{e.name}</span>
              </div>
              <Badge variant={e.status === "completed" ? "success" : e.status === "running" ? "warning" : "default"}>
                {e.status}
              </Badge>
            </div>
          )
        })}
        {recent.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">No activity yet</p>
        )}
      </CardContent>
    </Card>
  )
}
