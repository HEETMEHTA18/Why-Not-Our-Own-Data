"use client"

import { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Database } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { governor } from "@/lib/api"

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 shadow-lg text-sm">
        <p className="font-medium mb-1">{label}</p>
        {payload.map((p: any) => (
          <div key={p.name} className="flex items-center gap-2 text-xs" style={{ color: p.color }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            {p.name}: {p.value}
          </div>
        ))}
      </div>
    )
  }
  return null
}

export function DatasetGrowth() {
  const [data, setData] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      governor.collector.stats().catch(() => null),
      governor.dataset.stats().catch(() => null),
    ])
      .then(([collector, dataset]) => {
        const rows: Record<string, unknown>[] = []
        if (collector && typeof collector === "object") {
          rows.push({
            name: "Conversations",
            total: Number((collector as any).total ?? 0),
            withCorrections: Number((collector as any).with_corrections ?? 0),
          })
        }
        if (dataset && typeof dataset === "object") {
          rows.push({
            name: "Dataset examples",
            valid: Number((dataset as any).valid_examples ?? 0),
            invalid: Number((dataset as any).invalid_examples ?? 0),
          })
        }
        setData(rows)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const hasData = data.some((r) => Object.values(r).some((v) => Number(v) > 0))

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Database className="w-4 h-4 text-primary" />
          Dataset Growth
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">Loading dataset stats…</div>
        ) : !hasData ? (
          <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">
            No conversation or dataset stats recorded yet.
          </div>
        ) : (
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: "12px", color: "hsl(var(--muted-foreground))" }} />
                <Bar dataKey="total" name="Total" fill="hsl(142, 76%, 50%)" radius={[4, 4, 0, 0]} opacity={0.8} />
                <Bar dataKey="withCorrections" name="With corrections" fill="hsl(27, 96%, 61%)" radius={[4, 4, 0, 0]} opacity={0.8} />
                <Bar dataKey="valid" name="Valid examples" fill="hsl(142, 76%, 50%)" radius={[4, 4, 0, 0]} opacity={0.8} />
                <Bar dataKey="invalid" name="Invalid examples" fill="hsl(0, 72%, 55%)" radius={[4, 4, 0, 0]} opacity={0.8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
