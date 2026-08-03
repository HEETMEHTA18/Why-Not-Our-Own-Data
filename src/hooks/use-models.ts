"use client"

import { useState, useEffect, useCallback } from "react"
import type { ModelInfo, AdapterRecord } from "@/lib/types"
import { tatvik } from "@/lib/api"

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [adapters, setAdapters] = useState<AdapterRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const refetch = useCallback(() => {
    Promise.all([
      tatvik.models.list().catch(() => []),
      tatvik.training.adapters().catch(() => []),
    ])
      .then(([m, a]) => { setModels(m); setAdapters(a) })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => { refetch() }, [refetch])

  return { models, adapters, isLoading, refetch }
}
