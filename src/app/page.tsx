"use client"

import { AppShell } from "@/components/layout/app-shell"
import { StatsCard } from "@/components/dashboard/stats-card"
import { GPUMonitor } from "@/components/dashboard/gpu-monitor"
import { TrainingProgress } from "@/components/dashboard/training-progress"
import { RecentActivity } from "@/components/dashboard/recent-activity"
import { TrainingApprovalDialog } from "@/components/notifications/training-approval-dialog"
import { useDashboard } from "@/hooks/use-dashboard"
import { MessageSquare, Brain, Database, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useEffect } from "react"

export default function DashboardPage() {
  const { data, recommendation, isLoading } = useDashboard()
  const [showApproval, setShowApproval] = useState(false)

  useEffect(() => {
    if (recommendation?.recommend) {
      const timer = setTimeout(() => setShowApproval(true), 1500)
      return () => clearTimeout(timer)
    }
  }, [recommendation])

  const gpu = data?.gpu ?? { utilization: 0, memory_used: 0, memory_total: 0, memoryUsed: 0, memoryTotal: 0, temperature: 0, processes: 0 }
  const training = data?.training ?? { is_training: false, current_job: null, queue_length: 0, progress: 0, eta: null, isTraining: false, currentJob: null, queueLength: 0 }
  const benchmarks = data?.recent_benchmarks ?? []
  const experiments = data?.recent_experiments ?? []

  return (
    <AppShell>
      <div className="space-y-8 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Overview of your AI learning platform
            </p>
          </div>
          {recommendation?.recommend && (
            <Button onClick={() => setShowApproval(true)} className="gap-2">
              <TrendingUp className="w-4 h-4" />
              Training Ready
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Active Model"
            value={data?.models?.[0]?.name ?? "None"}
            subtitle={data?.models?.[0]?.details?.quantization as string}
            icon={Brain}
            trend={null}
          />
          <StatsCard
            title="Active Adapter"
            value={data?.adapters?.find(a => a.status === "completed")?.version ? `v${data.adapters.find(a => a.status === "completed")!.version}` : "Base"}
            subtitle={`Score: ${data?.adapters?.find(a => a.status === "completed")?.metrics?.eval_score ?? "-"}`}
            icon={Database}
            trend={null}
          />
          <StatsCard
            title="Total Benchmarks"
            value={String(benchmarks.length)}
            subtitle={`${experiments.length} experiments`}
            icon={MessageSquare}
            trend={null}
          />
          <StatsCard
            title="GPU Utilization"
            value={`${gpu.utilization}%`}
            subtitle={`${gpu.temperature}°C`}
            icon={Database}
            trend={null}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <GPUMonitor gpu={{ utilization: gpu.utilization, memory_used: gpu.memory_used, memory_total: gpu.memory_total, memoryUsed: gpu.memory_used, memoryTotal: gpu.memory_total, temperature: gpu.temperature, processes: gpu.processes }} />
          <TrainingProgress training={{ is_training: training.is_training, current_job: training.current_job, queue_length: training.queue_length, progress: training.progress, eta: training.eta, isTraining: training.is_training, currentJob: training.current_job, queueLength: training.queue_length }} />
          <RecentActivity benchmarks={benchmarks.map(b => ({ id: b.id, name: b.task, score: b.score, previousScore: undefined, date: b.created_at, modelVersion: b.base_model_id }))} experiments={experiments.map(e => ({ id: e.id, name: e.experiment_type, status: e.status as "running" | "completed" | "failed" | "queued", progress: e.status === "completed" ? 100 : 0, startedAt: e.created_at, completedAt: e.completed_at, modelVersion: e.base_model_id, datasetSize: 0, metrics: { loss: (e.metrics?.loss as number) ?? 0, accuracy: (e.metrics?.accuracy as number) ?? 0, evalScore: (e.metrics?.eval_score as number) ?? 0 } }))} />
        </div>
      </div>

      {recommendation && (
        <TrainingApprovalDialog
          open={showApproval}
          onOpenChange={setShowApproval}
          recommendation={recommendation}
        />
      )}
    </AppShell>
  )
}
