"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const data = [
  { version: "Base", mmlu: 62.1, gsm8k: 65.2, humaneval: 52.0 },
  { version: "v1", mmlu: 64.3, gsm8k: 67.8, humaneval: 53.5 },
  { version: "v2", mmlu: 66.0, gsm8k: 69.5, humaneval: 55.8 },
  { version: "v3", mmlu: 68.2, gsm8k: 72.5, humaneval: 58.0 },
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

export function BenchmarkChart() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          Benchmark Progression
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="version" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
              <YAxis domain={[45, 80]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: "12px", color: "hsl(var(--muted-foreground))" }} />
              <Line type="monotone" dataKey="mmlu" stroke="hsl(142, 76%, 50%)" strokeWidth={2} dot={{ r: 4, fill: "hsl(142, 76%, 50%)" }} />
              <Line type="monotone" dataKey="gsm8k" stroke="hsl(217, 91%, 60%)" strokeWidth={2} dot={{ r: 4, fill: "hsl(217, 91%, 60%)" }} />
              <Line type="monotone" dataKey="humaneval" stroke="hsl(27, 96%, 61%)" strokeWidth={2} dot={{ r: 4, fill: "hsl(27, 96%, 61%)" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
