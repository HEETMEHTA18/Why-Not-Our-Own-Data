"use client"

import { useState, useRef, KeyboardEvent } from "react"
import { Send, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface InputBarProps {
  onSend: (message: string) => void
  isLoading: boolean
  onStop?: () => void
}

export function InputBar({ onSend, isLoading, onStop }: InputBarProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (!input.trim() || isLoading) return
    onSend(input.trim())
    setInput("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = "auto"
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`
    }
  }

  return (
    <div className="px-4 md:px-8 py-4 bg-gradient-to-t from-background via-background/80 to-transparent">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-end gap-1.5 rounded-2xl border border-border/70 bg-secondary/30 px-2 py-2 shadow-xl shadow-black/20 transition-all duration-200 focus-within:border-border focus-within:bg-secondary/50 focus-within:shadow-emerald-500/5">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="Message Tatvik..."
            rows={1}
            className={cn(
              "flex-1 resize-none rounded-xl bg-transparent",
              "px-3 py-2 text-sm placeholder:text-muted-foreground/55",
              "focus:outline-none focus:ring-0",
              "transition-all duration-200"
            )}
            disabled={isLoading}
          />
          <Button
            onClick={isLoading ? onStop : handleSend}
            disabled={!isLoading && (!input.trim())}
            size="icon"
            className="shrink-0 h-9 w-9 rounded-xl"
          >
            {isLoading ? (
              <Square className="w-4 h-4" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <p className="text-center text-[11px] text-muted-foreground/50 mt-2">
          Tatvik runs 100% locally — built by Heet Mehta · Autodevs. Press Enter to send, Shift+Enter for new line.
        </p>
      </div>
    </div>
  )
}
