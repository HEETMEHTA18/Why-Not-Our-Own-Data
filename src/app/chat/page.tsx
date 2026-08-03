"use client"

import { AppShell } from "@/components/layout/app-shell"
import { ChatInterface } from "@/components/chat/chat-interface"
import { MessageSquare } from "lucide-react"

export default function ChatPage() {
  return (
    <AppShell>
      <div className="h-full flex flex-col max-w-7xl mx-auto">
        <div className="flex items-center justify-between gap-3 pb-5">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-primary/10 ring-1 ring-primary/20 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-semibold tracking-tight">Chat</h1>
              <p className="text-sm text-muted-foreground truncate">
                Local-first AI assistant · built by Heet Mehta · Autodevs
              </p>
            </div>
          </div>
        </div>
        <ChatInterface />
      </div>
    </AppShell>
  )
}
