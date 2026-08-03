"use client"

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts"

interface ForecastData {
  dates: string[]
  actual_close: number[]
  predicted_open: number[]
  predicted_high: number[]
  predicted_low: number[]
  predicted_close: number[]
}

export function ForecastChart({ data }: { data: ForecastData }) {
  const chartData = data.dates.map((date, i) => ({
    date,
    actual: data.actual_close?.[i] ?? null,
    predicted: data.predicted_close?.[i] ?? null,
    predictedHigh: data.predicted_high?.[i] ?? null,
    predictedLow: data.predicted_low?.[i] ?? null,
  }))

  const hasActual = chartData.some((d) => d.actual !== null)

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="date"
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          tickLine={false}
        />
        <YAxis
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          tickLine={false}
          domain={["auto", "auto"]}
          tickFormatter={(v: number) => v.toFixed(0)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            fontSize: "13px",
          }}
          formatter={(value: number) => value?.toFixed(2) ?? "—"}
        />
        <Legend />
        {hasActual && (
          <Line
            type="monotone"
            dataKey="actual"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            name="Actual Close"
            connectNulls={false}
          />
        )}
        <Line
          type="monotone"
          dataKey="predicted"
          stroke="hsl(var(--chart-2, #22c55e))"
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          name="Predicted Close"
        />
        <Line
          type="monotone"
          dataKey="predictedHigh"
          stroke="hsl(var(--chart-3, #f59e0b))"
          strokeWidth={1}
          strokeDasharray="3 3"
          dot={false}
          name="Predicted High"
        />
        <Line
          type="monotone"
          dataKey="predictedLow"
          stroke="hsl(var(--chart-4, #ef4444))"
          strokeWidth={1}
          strokeDasharray="3 3"
          dot={false}
          name="Predicted Low"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
