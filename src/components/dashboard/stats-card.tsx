"use client"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react"

interface StatsCardProps {
  title: string
  value: string
  subtitle: string
  icon: LucideIcon
  trend: { value: number; positive: boolean } | null
}

export function StatsCard({ title, value, subtitle, icon: Icon, trend }: StatsCardProps) {
  return (
    <Card className="card-hover">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {title}
            </p>
            <p className="text-2xl font-semibold tracking-tight">{value}</p>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
            {trend && (
              <div className="flex items-center gap-1 pt-1">
                {trend.positive ? (
                  <TrendingUp className="w-3 h-3 text-emerald-400" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-red-400" />
                )}
                <span className={cn(
                  "text-xs font-medium",
                  trend.positive ? "text-emerald-400" : "text-red-400"
                )}>
                  {trend.positive ? "+" : ""}{trend.value}%
                </span>
              </div>
            )}
          </div>
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
