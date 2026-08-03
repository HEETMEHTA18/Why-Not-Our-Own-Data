"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Brain, Cpu, HardDrive, Trash2 } from "lucide-react"
import type { BaseModel } from "@/lib/types"
import { formatBytes } from "@/lib/utils"

interface ModelCardProps {
  model: BaseModel
  onDelete?: (id: string) => void
  busy?: boolean
}

export function ModelCard({ model, onDelete, busy }: ModelCardProps) {
  return (
    <Card className="card-hover">
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-sm">{model.name}</h3>
              <p className="text-xs text-muted-foreground">{model.provider}</p>
            </div>
          </div>
          <Badge variant={model.isLoaded ? "success" : "secondary"}>
            {model.isLoaded ? "Loaded" : "Unloaded"}
          </Badge>
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3" />
            {model.parameterCount}
          </span>
          <span className="flex items-center gap-1">
            <HardDrive className="w-3 h-3" />
            {formatBytes(model.size)}
          </span>
          <span>{model.quantization}</span>
        </div>

        <div className="mt-3 pt-3 border-t border-border flex gap-2">
          <Button variant="secondary" size="sm" className="w-full" disabled={busy} onClick={() => onDelete?.(model.id)} title="Delete model">
            <Trash2 className="w-3 h-3 mr-1.5" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
