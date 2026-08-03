"use client"

import { useState } from "react"
import type { LogEntry } from "@/lib/types"

export function useLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([])

  // Logs are system-generated; store them via the notification/event system
  // For now, they're sourced from backend calls
  const addLog = (entry: LogEntry) => setLogs((prev) => [entry, ...prev])

  return { logs, addLog }
}
