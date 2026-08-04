"use client"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Zap, Database } from "lucide-react"
import { useServiceHealth } from "@/hooks/use-service-health"

export function ContextWindow() {
  const { compression } = useServiceHealth()
  const window = compression.contextWindow || 4096

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          Context &amp; Compression
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Context window</span>
          <span className="font-mono text-sm font-medium">{window.toLocaleString()} tokens</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" />
            Compressor
          </span>
          <Badge
            variant={compression.enabled ? "success" : "outline"}
            className={compression.enabled ? undefined : "text-muted-foreground"}
          >
            {compression.enabled
              ? compression.mode === "hosted"
                ? "hosted policy"
                : compression.mode === "local"
                  ? "local policy"
                  : "enabled"
              : "off"}
          </Badge>
        </div>

        {compression.apiKeySet && (
          <p className="text-[11px] text-muted-foreground">
            API key configured · min {compression.minTokens} tokens to compress
          </p>
        )}
      </CardContent>
    </Card>
  )
}
