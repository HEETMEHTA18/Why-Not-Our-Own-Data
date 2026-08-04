"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Gauge, Thermometer, Cpu, Activity } from "lucide-react"
import type { GPUInfo } from "@/lib/types"
import { cn } from "@/lib/utils"

interface GPUMonitorProps {
  gpu: GPUInfo
}

export function GPUMonitor({ gpu }: GPUMonitorProps) {
  const memPercent = (gpu.memoryUsed / gpu.memoryTotal) * 100

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Cpu className="w-4 h-4 text-primary" />
          GPU Monitor
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              Utilization
            </span>
            <span className={cn(
              "font-mono text-sm font-medium",
              gpu.utilization > 80 ? "text-red-400" : gpu.utilization > 50 ? "text-amber-400" : "text-emerald-400"
            )}>
              {gpu.utilization}%
            </span>
          </div>
          <Progress value={gpu.utilization} className="h-1.5" />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Memory</span>
            <span className="font-mono text-sm font-medium">
              {(gpu.memoryUsed / 1024).toFixed(1)}GB / {(gpu.memoryTotal / 1024).toFixed(1)}GB
            </span>
          </div>
          <Progress value={memPercent} className="h-1.5" />
        </div>

        <div className="flex items-center justify-between text-sm pt-1 border-t border-border">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <Thermometer className="w-3.5 h-3.5" />
            Temperature
          </span>
          <span className={cn(
            "font-mono text-sm font-medium",
            gpu.temperature > 80 ? "text-red-400" : gpu.temperature > 70 ? "text-amber-400" : "text-emerald-400"
          )}>
            {gpu.temperature}°C
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
