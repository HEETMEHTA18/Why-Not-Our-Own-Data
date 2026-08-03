"use client"

import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { timeAgo } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface ExperimentRow {
  id: string
  name: string
  status: "running" | "completed" | "failed" | "queued"
  progress: number
  startedAt: string
  completedAt?: string
  modelVersion: string
  datasetSize: number
  metrics: {
    loss: number
    accuracy: number
    evalScore: number
  }
}

interface ExperimentTableProps {
  experiments: ExperimentRow[]
  isLoading?: boolean
}

export function ExperimentTable({ experiments, isLoading }: ExperimentTableProps) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">All Experiments</h2>
      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Name</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Status</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Accuracy</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Loss</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Eval Score</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Dataset</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground text-xs uppercase">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {experiments.length === 0 && !isLoading && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">No experiments yet</td></tr>
            )}
            {experiments.map((exp) => (
              <tr key={exp.id} className="hover:bg-secondary/30 transition-colors">
                <td className="px-4 py-3 font-medium">{exp.name}</td>
                <td className="px-4 py-3">
                  {exp.status === "running" ? (
                    <div className="flex items-center gap-2">
                      <Badge variant="warning" className="animate-pulse">Running</Badge>
                      <Progress value={exp.progress} className="w-16 h-1" />
                    </div>
                  ) : (
                    <Badge variant={exp.status === "completed" ? "success" : "destructive"}>
                      {exp.status}
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-3 font-mono">
                  {exp.metrics.accuracy > 0 ? `${exp.metrics.accuracy}%` : "-"}
                </td>
                <td className="px-4 py-3 font-mono">{exp.metrics.loss.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono">
                  {exp.metrics.evalScore > 0 ? `${exp.metrics.evalScore}%` : "-"}
                </td>
                <td className="px-4 py-3">{exp.datasetSize} samples</td>
                <td className="px-4 py-3 text-muted-foreground text-xs">{timeAgo(exp.startedAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
