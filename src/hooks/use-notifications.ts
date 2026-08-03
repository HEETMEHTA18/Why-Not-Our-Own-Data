"use client"

import { useState, useCallback, useEffect } from "react"
import type { Notification, GovernorDecision } from "@/lib/types"
import { governor } from "@/lib/api"

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    governor.recommend()
      .then((rec: GovernorDecision) => {
        if (rec.recommend) {
          setNotifications([{
            id: "training-ready",
            type: "info",
            title: "Training Ready",
            message: rec.reason,
            timestamp: new Date().toISOString(),
            read: false,
          }])
        }
      })
      .catch(() => {})
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  const markRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }, [])

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }, [])

  const addNotification = useCallback((notif: Notification) => {
    setNotifications((prev) => [notif, ...prev])
  }, [])

  return { notifications, unreadCount, markRead, markAllRead, addNotification }
}
