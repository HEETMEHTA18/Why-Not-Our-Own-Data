"use client"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { BarChart3, TrendingUp, Database, Target, Brain, FlaskConical } from "lucide-react"
import { StatsCard } from "@/components/dashboard/stats-card"
import dynamic from "next/dynamic"
import { useState, useEffect } from "react"

const BenchmarkChart = dynamic(() => import("@/components/analytics/benchmark-chart").then((m) => m.BenchmarkChart), { ssr: false })
const DatasetGrowth = dynamic(() => import("@/components/analytics/dataset-growth").then((m) => m.DatasetGrowth), { ssr: false })

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"

export default function AnalyticsPage() {
  const [stats, setStats] = useState<any>({})

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [sahapathaRes, modelsRes] = await Promise.all([
          fetch(`${API}/sahapatha/status`).then(r => r.json()).catch(() => ({})),
          fetch(`${API}/models`).then(r => r.json()).catch(() => []),
        ])
        setStats({ sahapatha: sahapathaRes, models: modelsRes })
      } catch {}
    }
    loadStats()
  }, [])

  const s = stats.sahapatha || {}
  const bestLoss = s.last_train_metrics?.best_loss
  const versions = s.total_versions || 0
  const bufferSize = s.buffer_size || 0

  return (
    <AppShell>
      <div className="space-y-8 max-w-6xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            Analytics
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Training performance over time</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatsCard
            title="Best Loss"
            value={bestLoss ? bestLoss.toFixed(4) : "—"}
            subtitle={`Across ${versions} version(s)`}
            icon={Target}
            trend={bestLoss ? { value: 0, positive: true } : null}
          />
          <StatsCard
            title="Adapter Versions"
            value={String(versions)}
            subtitle={`${bufferSize} samples in buffer`}
            icon={TrendingUp}
            trend={null}
          />
          <StatsCard
            title="Base Model"
            value={(stats.models?.[0]?.name || "—").slice(0, 20)}
            subtitle={stats.models?.[0]?.details?.quantization_level
              ? `Quant: ${String(stats.models[0].details.quantization_level)}`
              : "No model loaded"}
            icon={Brain}
            trend={null}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <BenchmarkChart />
          <DatasetGrowth />
        </div>
      </div>
    </AppShell>
  )
}