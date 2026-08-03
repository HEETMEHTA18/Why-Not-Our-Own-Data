"use client"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { StatsCard } from "@/components/dashboard/stats-card"
import { Button } from "@/components/ui/button"
import { TrendingUp, Target, BarChart3, LineChart } from "lucide-react"
import dynamic from "next/dynamic"
import { useState, useEffect, useCallback } from "react"

const ForecastChart = dynamic(() => import("@/components/forecast/forecast-chart").then((m) => m.ForecastChart), { ssr: false })

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"

const TICKERS = [
  "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
  "HINDUNILVR.NS", "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS",
  "KOTAKBANK.NS", "LT.NS", "WIPRO.NS", "AXISBANK.NS", "TITAN.NS",
  "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NTPC.NS",
  "M&M.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TRENT.NS", "BAJAJFINSV.NS",
  "HCLTECH.NS", "ADANIPORTS.NS", "TATASTEEL.NS", "TATAMOTORS.NS", "COALINDIA.NS",
  "NESTLEIND.NS", "ONGC.NS", "DMART.NS", "SBILIFE.NS", "EICHERMOT.NS",
  "GODREJCP.NS", "BRITANNIA.NS", "HDFCLIFE.NS", "DIVISLAB.NS", "CIPLA.NS",
  "SHRIRAMFIN.NS", "DRREDDY.NS", "GRASIM.NS", "HAL.NS", "ADANIENT.NS",
  "HEROMOTOCO.NS", "BPCL.NS", "BAJAJ-AUTO.NS", "TECHM.NS", "INDUSINDBK.NS",
]

export default function ForecastPage() {
  const [ticker, setTicker] = useState("RELIANCE.NS")
  const [predLen, setPredLen] = useState(10)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const runForecast = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/forecast/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, pred_len: predLen }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text.slice(0, 200))
      }
      const json = await res.json()
      setData(json)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [ticker, predLen])

  return (
    <AppShell>
      <div className="space-y-8 max-w-7xl mx-auto">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Kronos Forecast
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            NSE stock price forecasting with the fine-tuned Kronos financial time-series model (24.7M params)
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Ticker</label>
            <select
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              {TICKERS.map((t) => (
                <option key={t} value={t}>{t.replace(".NS", "")}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Steps Ahead</label>
            <select
              value={predLen}
              onChange={(e) => setPredLen(Number(e.target.value))}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              {[5, 10, 15, 20].map((n) => (
                <option key={n} value={n}>{n} weeks</option>
              ))}
            </select>
          </div>
          <Button onClick={runForecast} disabled={loading} className="gap-2">
            <BarChart3 className="w-4 h-4" />
            {loading ? "Forecasting..." : "Run Forecast"}
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="py-4">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {data && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatsCard
                title="MAPE"
                value={data.mape ? `${data.mape.toFixed(1)}%` : "—"}
                subtitle="Mean Absolute Percentage Error"
                icon={Target}
                trend={data.mape < 10 ? { value: 0, positive: true } : { value: 0, positive: false }}
              />
              <StatsCard
                title="Last Actual Close"
                value={data.last_actual_close?.toFixed(2) ?? "—"}
                subtitle={data.dates?.[data.dates.length - 1] ?? ""}
                icon={LineChart}
                trend={null}
              />
              <StatsCard
                title="Predicted Close"
                value={data.last_predicted_close?.toFixed(2) ?? "—"}
                subtitle={`At ${data.dates?.[data.dates.length - 1] ?? ""}`}
                icon={TrendingUp}
                trend={data.last_actual_close && data.last_predicted_close
                  ? {
                      value: ((data.last_predicted_close / data.last_actual_close) - 1) * 100,
                      positive: data.last_predicted_close >= data.last_actual_close,
                    }
                  : null}
              />
              <StatsCard
                title="Ticker"
                value={data.ticker?.replace(".NS", "") ?? "—"}
                subtitle={`${data.predicted_close?.length ?? 0} week forecast`}
                icon={BarChart3}
                trend={null}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <LineChart className="w-4 h-4 text-primary" />
                  Price Forecast
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ForecastChart data={data} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Prediction Table</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 px-3 font-medium text-muted-foreground">Date</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">Actual Close</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">Predicted Open</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">Predicted High</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">Predicted Low</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">Predicted Close</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.dates.map((date: string, i: number) => (
                        <tr key={i} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="py-2 px-3 font-medium">{date}</td>
                          <td className="text-right py-2 px-3 font-mono">
                            {data.actual_close?.[i]?.toFixed(2) ?? "—"}
                          </td>
                          <td className="text-right py-2 px-3 font-mono">
                            {data.predicted_open?.[i]?.toFixed(2) ?? "—"}
                          </td>
                          <td className="text-right py-2 px-3 font-mono">
                            {data.predicted_high?.[i]?.toFixed(2) ?? "—"}
                          </td>
                          <td className="text-right py-2 px-3 font-mono">
                            {data.predicted_low?.[i]?.toFixed(2) ?? "—"}
                          </td>
                          <td className="text-right py-2 px-3 font-mono font-semibold">
                            {data.predicted_close?.[i]?.toFixed(2) ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {!data && !error && (
          <Card>
            <CardContent className="py-12 flex flex-col items-center gap-3 text-muted-foreground">
              <TrendingUp className="w-10 h-10 opacity-30" />
              <p className="text-sm">Select a ticker and click Run Forecast to see predictions</p>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
