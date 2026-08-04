"use client"

import { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { tatvik } from "@/lib/api"
import type { BenchmarkResult } from "@/lib/types"

const LINE_COLORS = [
  "hsl(142, 76%, 50%)",
  "hsl(217, 91%, 60%)",
  "hsl(27, 96%, 61%)",
  "hsl(280, 70%, 60%)",
  "hsl(0, 72%, 55%)",
]

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 shadow-lg text-sm">
        <p className="font-medium mb-1">{label}</p>
        {payload.map((p: any) => (
          <div key={p.name} className="flex items-center gap-2 text-xs" style={{ color: p.color }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            {p.name}: {p.value}%
          </div>
        ))}
      </div>
    )
  }
  return null
}

interface Point {
  label: string
  [task: string]: string | number
}

export function BenchmarkChart() {
  const [data, setData] = useState<Point[]>([])
  const [tasks, setTasks] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    tatvik.evaluation.list()
      .then((results: BenchmarkResult[]) => {
        const taskNames = Array.from(new Set(results.map((r) => r.task)))
        const points = results
          .map((r) => ({
            ts: r.created_at,
            task: r.task,
            score: Math.round(r.score * 1000) / 10,
          }))
          .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())

        const labels = Array.from(new Set(points.map((p) => p.ts)))
        const rows = labels.map((ts) => {
          const row: Point = { label: new Date(ts).toLocaleDateString() }
          for (const t of taskNames) {
            const hit = points.find((p) => p.ts === ts && p.task === t)
            if (hit) row[t] = hit.score
          }
          return row
        })
        setData(rows)
        setTasks(taskNames)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          Benchmark Progression
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">Loading benchmarks…</div>
        ) : data.length === 0 ? (
          <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">
            No benchmark results yet. Run a benchmark to populate this chart.
          </div>
        ) : (
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
                <YAxis domain={[0, 100]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: "12px", color: "hsl(var(--muted-foreground))" }} />
                {tasks.map((t, i) => (
                  <Line
                    key={t}
                    type="monotone"
                    dataKey={t}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4, fill: LINE_COLORS[i % LINE_COLORS.length] }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
