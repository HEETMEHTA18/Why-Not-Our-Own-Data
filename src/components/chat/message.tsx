"use client"

import { useState } from "react"
import { ThumbsUp, ThumbsDown, Bot, Copy, Check, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { Message as MessageType } from "@/lib/types"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"

const API = process.env.NEXT_PUBLIC_TATVIK_URL || "http://localhost:8000"

interface MessageProps {
  message: MessageType
  onRate: (id: string, rating: "up" | "down") => void
}

function CodeBlock({ className, children }: any) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || "")
  const lang = match ? match[1] : ""
  const code = String(children).replace(/\n$/, "")

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#1a1a2e] rounded-t-lg border-b border-border/50">
        <span className="text-[11px] text-muted-foreground font-mono uppercase">{lang || "code"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={lang || "text"}
        PreTag="div"
        customStyle={{ margin: 0, borderRadius: "0 0 0.5rem 0.5rem", fontSize: "13px" }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

export function Message({ message, onRate }: MessageProps) {
  const isUser = message.role === "user"
  const [learned, setLearned] = useState(false)

  const handleLearn = async () => {
    try {
      const res = await fetch(`${API}/sahapatha/learn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: message.content,
          response: message.content,
          metadata: { source: "chat-ui" },
        }),
      })
      if (res.ok) setLearned(true)
    } catch {}
  }

  return (
    <div className={cn("flex gap-3 group w-full", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shrink-0 shadow-md shadow-emerald-500/20">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={cn("flex flex-col", isUser ? "items-end" : "items-start max-w-[min(85%,52rem)]")}>
        <div className={cn(
          "text-sm leading-relaxed overflow-hidden",
          isUser
            ? "rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-primary-foreground shadow-sm shadow-primary/10"
            : "px-1 py-1"
        )}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-code:bg-[#1a1a2e] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-pre:p-0 prose-pre:border-0 prose-pre:bg-transparent">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const isInline = !className
                    if (isInline) {
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    }
                    return <CodeBlock className={className}>{children}</CodeBlock>
                  },
                }}
              >
                {message.content || "..."}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.content && (
          <div className="flex items-center gap-1 pt-1.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="w-6 h-6"
              onClick={() => onRate(message.id, "up")}
              title="Good response"
            >
              <ThumbsUp className={cn("w-3.5 h-3.5", message.rating === "up" ? "text-primary" : "text-muted-foreground")} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="w-6 h-6"
              onClick={() => onRate(message.id, "down")}
              title="Bad response"
            >
              <ThumbsDown className={cn("w-3.5 h-3.5", message.rating === "down" ? "text-red-400" : "text-muted-foreground")} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="w-6 h-6"
              onClick={handleLearn}
              title="Save to training data"
            >
              <BookOpen className={cn("w-3.5 h-3.5", learned ? "text-amber-400" : "text-muted-foreground")} />
            </Button>
            {message.latency && (
              <span className="text-[10px] text-muted-foreground ml-2">{message.latency}ms</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
