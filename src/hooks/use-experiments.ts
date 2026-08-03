"use client"

import { useState, useEffect } from "react"
import type { ExperimentRecord } from "@/lib/types"
import { tatvik } from "@/lib/api"

export function useExperiments() {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    tatvik.experiments.list()
      .then(setExperiments)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  return { experiments, isLoading }
}
