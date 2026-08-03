"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Brain, TrendingUp, Clock, Database, Gauge, Sparkles } from "lucide-react"
import type { GovernorDecision } from "@/lib/types"
import { governor } from "@/lib/api"
import { useState } from "react"

interface TrainingApprovalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  recommendation: GovernorDecision
}

export function TrainingApprovalDialog({ open, onOpenChange, recommendation }: TrainingApprovalDialogProps) {
  const [approved, setApproved] = useState<boolean | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleApprove = async () => {
    setSubmitting(true)
    try {
      if (recommendation.recommendation_id) {
        await governor.approve(recommendation.recommendation_id, true)
      }
      setApproved(true)
    } catch {
      setApproved(true)
    }
    setSubmitting(false)
  }

  const handleReject = async () => {
    setSubmitting(true)
    try {
      if (recommendation.recommendation_id) {
        await governor.approve(recommendation.recommendation_id, false)
      }
      setApproved(false)
    } catch {
      setApproved(false)
    }
    setSubmitting(false)
  }

  const details = recommendation.details as Record<string, unknown> | undefined
  const conditionDetails = details?.recommendation as Record<string, unknown> | undefined

  if (approved !== null) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {approved ? (
                <>
                  <Sparkles className="w-5 h-5 text-primary" />
                  Training Started
                </>
              ) : (
                <>
                  <Database className="w-5 h-5 text-muted-foreground" />
                  Training Declined
                </>
              )}
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 text-center">
            {approved ? (
              <div className="space-y-3">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                  <Brain className="w-8 h-8 text-primary" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Training has been queued. You'll be notified when it completes.
                </p>
                <Progress value={0} className="h-1.5 animate-pulse-slow" />
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  More data will be collected before the next recommendation.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => { setApproved(null); onOpenChange(false) }} className="w-full">
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Training Recommended
          </DialogTitle>
          <DialogDescription>
            The governance engine recommends a training run. Review the details below.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-xl bg-secondary/50 border border-border p-4 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" />
                Example Count
              </span>
              <span className="font-semibold text-lg">{String(conditionDetails?.example_count ?? "—")}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5" />
                Avg Quality
              </span>
              <Badge variant="success">{conditionDetails?.avg_quality ? `${(Number(conditionDetails.avg_quality) * 100).toFixed(0)}%` : "—"}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                Estimated Improvement
              </span>
              <span className="font-semibold text-emerald-400">+{String(conditionDetails?.estimated_improvement ?? "—")}%</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Duration
              </span>
              <span className="font-mono text-sm">{String(conditionDetails?.estimated_duration_min ?? "—")} min</span>
            </div>
          </div>

          <p className="text-xs text-muted-foreground text-center">{recommendation.reason}</p>
        </div>

        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={handleReject}
            className="flex-1"
            disabled={submitting}
          >
            Not Now
          </Button>
          <Button
            variant="default"
            onClick={handleApprove}
            className="flex-1 gap-2"
            disabled={submitting}
          >
            <Brain className="w-4 h-4" />
            {submitting ? "Submitting..." : "Start Training"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
