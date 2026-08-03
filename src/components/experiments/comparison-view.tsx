"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowUp, ArrowDown, Minus } from "lucide-react"
import { cn } from "@/lib/utils"

interface ComparisonData {
  [version: string]: {
    accuracy: number
    latency: number
    evalScore: number
    loss: number
    datasetSize: number
  }
}

interface ComparisonViewProps {
  data: ComparisonData
}

export function ComparisonView({ data }: ComparisonViewProps) {
  const versions = Object.entries(data)
  const baseScores = versions.find(([v]) => v === "base")?.[1]

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Version Comparison</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {versions.map(([version, metrics]) => {
          const isBase = version === "base"
          const accuracyDiff = baseScores && !isBase ? metrics.accuracy - baseScores.accuracy : null

          return (
            <Card key={version} className={cn(
              !isBase && "card-hover",
              metrics.accuracy > 90 && "border-primary/20"
            )}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className={cn(
                    "text-sm font-mono font-bold",
                    isBase ? "text-muted-foreground" : "text-primary"
                  )}>
                    {isBase ? "Base" : version}
                  </span>
                  {accuracyDiff !== null && (
                    <Badge variant={accuracyDiff > 0 ? "success" : "destructive"} className="text-[10px]">
                      {accuracyDiff > 0 ? "+" : ""}{accuracyDiff.toFixed(1)}%
                    </Badge>
                  )}
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Accuracy</span>
                    <span className="font-mono font-medium">{metrics.accuracy}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Eval Score</span>
                    <span className="font-mono">{metrics.evalScore}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Latency</span>
                    <span className="font-mono">{metrics.latency}ms</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Loss</span>
                    <span className="font-mono">{metrics.loss.toFixed(2)}</span>
                  </div>
                  {metrics.datasetSize > 0 && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Dataset</span>
                      <span className="font-mono">{metrics.datasetSize}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
