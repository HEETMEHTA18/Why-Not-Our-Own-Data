"use client"

import { useState, useEffect, useCallback } from "react"
import type { BenchmarkResult } from "@/lib/types"
import { tatvik } from "@/lib/api"

export function useBenchmarks() {
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetch = useCallback(() => {
    tatvik.evaluation.list()
      .then(setBenchmarks)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => { fetch() }, [fetch])

  return { benchmarks, isLoading, refetch: fetch }
}
