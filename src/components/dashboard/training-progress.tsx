"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { FlaskConical, Loader2, Clock, ListOrdered } from "lucide-react"
import type { TrainingStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

interface TrainingProgressProps {
  training: TrainingStatus
}

export function TrainingProgress({ training }: TrainingProgressProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-primary" />
          Training Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-3 h-3 rounded-full",
            training.isTraining ? "bg-amber-400 animate-pulse" : "bg-emerald-500"
          )} />
          <span className="text-sm font-medium">
            {training.isTraining ? "Training in progress" : "Idle"}
          </span>
        </div>

        {training.isTraining && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-mono text-sm">{training.progress}%</span>
            </div>
            <Progress value={training.progress} className="h-1.5" />
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              ETA: {training.eta ?? "Calculating..."}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-sm pt-1 border-t border-border">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <ListOrdered className="w-3.5 h-3.5" />
            Queue
          </span>
          <span className="font-mono text-sm font-medium">
            {training.queueLength} jobs
          </span>
        </div>

        {training.currentJob && (
          <div className="text-xs text-muted-foreground">
            Current: {training.currentJob}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
