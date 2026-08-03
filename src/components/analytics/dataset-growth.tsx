"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Database } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const data = [
  { week: "W1", conversations: 28, corrections: 3 },
  { week: "W2", conversations: 45, corrections: 8 },
  { week: "W3", conversations: 62, corrections: 12 },
  { week: "W4", conversations: 78, corrections: 15 },
  { week: "W5", conversations: 95, corrections: 22 },
  { week: "W6", conversations: 112, corrections: 28 },
]

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
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Database className="w-4 h-4 text-primary" />
          Dataset Growth
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="week" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
              <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} stroke="hsl(var(--border))" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: "12px", color: "hsl(var(--muted-foreground))" }} />
              <Bar dataKey="conversations" fill="hsl(142, 76%, 50%)" radius={[4, 4, 0, 0]} opacity={0.8} />
              <Bar dataKey="corrections" fill="hsl(27, 96%, 61%)" radius={[4, 4, 0, 0]} opacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
