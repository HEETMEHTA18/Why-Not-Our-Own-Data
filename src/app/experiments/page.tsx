"use client"

import { AppShell } from "@/components/layout/app-shell"
import { ExperimentTable } from "@/components/experiments/experiment-table"
import { ComparisonView } from "@/components/experiments/comparison-view"
import { FlaskConical } from "lucide-react"
import { useExperiments } from "@/hooks/use-experiments"
import { useModels } from "@/hooks/use-models"

export default function ExperimentsPage() {
  const { experiments, isLoading } = useExperiments()
  const { adapters } = useModels()

  const rows = experiments.length > 0
    ? experiments.map((e) => ({
        id: e.id,
        name: e.experiment_type,
        status: e.status as "running" | "completed" | "failed" | "queued",
        progress: e.status === "completed" ? 100 : e.status === "running" ? 50 : 0,
        startedAt: e.created_at,
        completedAt: e.completed_at,
        modelVersion: e.base_model_id,
        datasetSize: 0,
        metrics: {
          loss: (e.metrics?.loss as number) ?? 0,
          accuracy: (e.metrics?.accuracy as number) ?? 0,
          evalScore: (e.metrics?.eval_score as number) ?? 0,
        },
      }))
    : []

  const comparisonData: Record<string, any> = {}
  adapters.forEach((a, i) => {
    const m = a.metrics || {}
    comparisonData[`v${a.version}`] = {
      accuracy: (m.accuracy as number) || (m.eval_score as number) || 0,
      latency: (m.latency as number) || 0,
      evalScore: (m.eval_score as number) || (m.accuracy as number) || 0,
      loss: (m.final_loss as number) || (m.best_loss as number) || 0,
      datasetSize: (m.samples as number) || (m.epochs as number) || 0,
    }
  })

  return (
    <AppShell>
      <div className="space-y-8 max-w-6xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-primary" />
            Experiments
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Track and compare training experiments</p>
        </div>

        {adapters.length > 0 && <ComparisonView data={comparisonData} />}
        <ExperimentTable experiments={rows} isLoading={isLoading} />
      </div>
    </AppShell>
  )
}