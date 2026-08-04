"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, RefreshCw } from "lucide-react"
import { useServiceHealth } from "@/hooks/use-service-health"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function ServiceHealth() {
  const { services, refresh } = useServiceHealth()
  const online = services.filter((s) => s.ok).length

  return (
    <Card>
      <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Service Health
        </CardTitle>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={refresh} title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2">
          <Badge variant={online === services.length ? "success" : online > 0 ? "warning" : "destructive"}>
            {online}/{services.length} online
          </Badge>
        </div>
        <div className="space-y-2">
          {services.map((s) => (
            <div key={s.name} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-2">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    s.ok ? "bg-emerald-500 animate-pulse-slow" : "bg-destructive/70"
                  )}
                />
                {s.name}
              </span>
              <span className={cn("font-mono text-xs", s.ok ? "text-emerald-400" : "text-destructive/80")}>
                {s.ok ? (s.latencyMs !== null ? `${s.latencyMs}ms` : "ok") : (s.detail || "down")}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
