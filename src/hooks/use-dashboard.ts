"use client"

import { useState, useEffect, useCallback } from "react"
import type { DashboardData, TrainingStatus, AdapterRecord, BenchmarkResult, ExperimentRecord, GovernorDecision } from "@/lib/types"
import { tatvik, governor } from "@/lib/api"

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [recommendation, setRecommendation] = useState<GovernorDecision | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const [gpuRaw, trainingStatus, adapters, benchmarks, experiments, models] = await Promise.all([
        tatvik.system.gpu().catch(() => null),
        tatvik.training.status().catch(() => null),
        tatvik.training.adapters().catch(() => []),
        tatvik.evaluation.list().catch(() => []),
        tatvik.experiments.list(5).catch(() => []),
        tatvik.models.list().catch(() => []),
      ])
      const t = trainingStatus?.[0] as Record<string, unknown> | undefined
      const training: TrainingStatus = {
        is_training: Boolean(t?.is_training), current_job: (t?.current_job as string) || null,
        queue_length: Number(t?.queue_length || 0), progress: Number(t?.progress || 0), eta: (t?.eta as string) || null,
        isTraining: Boolean(t?.is_training), currentJob: (t?.current_job as string) || null, queueLength: Number(t?.queue_length || 0),
      }
      const raw = (gpuRaw as unknown as Record<string, unknown>) || {}
      const gpus = (raw.gpus as Array<Record<string, unknown>>) || []
      const g0 = gpus[0] || {}
      const utilization = Number(raw.avg_utilization_pct ?? g0.utilization_pct ?? 0)
      const memUsed = Number(raw.avg_memory_mb ?? g0.used_memory_mb ?? 0)
      const memTotal = Number(raw.total_memory_mb ?? g0.total_memory_mb ?? 0)
      const temperature = Number(g0.temperature_c ?? 0)
      const gpu = {
        utilization, memory_used: memUsed, memory_total: memTotal,
        memoryUsed: memUsed, memoryTotal: memTotal, temperature,
      }
      setData({ gpu, training, models, adapters, recent_benchmarks: benchmarks, recent_experiments: experiments })
    } catch {
      // backend unreachable
    }
    setIsLoading(false)
  }, [])

  const checkRecommendation = useCallback(async () => {
    try {
      const rec = await governor.recommend()
      setRecommendation(rec)
    } catch {
      setRecommendation(null)
    }
  }, [])

  useEffect(() => { fetch() }, [fetch])

  return { data, recommendation, isLoading, checkRecommendation, refetch: fetch }
}
