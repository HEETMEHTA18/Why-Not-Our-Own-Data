"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  MessageSquare,
  Brain,
  FlaskConical,
  BarChart3,
  ScrollText,
  Settings,
  Gauge,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Zap,
  Network,
  Bot,
  ShieldCheck,
  Sparkles,
  Boxes,
  Cpu,
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/models", label: "Models", icon: Brain },
  { href: "/registry", label: "Registry", icon: Boxes },
  { href: "/training", label: "Training", icon: Cpu },
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/agents", label: "Agents", icon: Zap },
  { href: "/hermes", label: "Hermes", icon: Bot },
  { href: "/approval", label: "Approval", icon: ShieldCheck },
  { href: "/intelligence", label: "Intelligence", icon: Sparkles },
  { href: "/knowledge", label: "Knowledge", icon: Network },
  { href: "/benchmarks", label: "Benchmarks", icon: Gauge },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "relative flex flex-col h-screen border-r border-sidebar-border bg-sidebar/95 shadow-2xl shadow-black/20 transition-all duration-300 ease-in-out",
          collapsed ? "w-[64px]" : "w-[248px]"
        )}
      >
        <div className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border">
          {!collapsed && (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/15">
                <Brain className="w-4 h-4 text-primary-foreground" />
              </div>
              <div>
                <span className="block font-semibold text-sm tracking-tight">Tatvik</span>
                <span className="block text-[11px] text-sidebar-foreground/60">Model ops</span>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="w-full flex justify-center">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/15">
                <Brain className="w-4 h-4 text-primary-foreground" />
              </div>
            </div>
          )}
        </div>

        <nav className="flex-1 py-4 px-2.5 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center justify-center h-10 w-full rounded-lg transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-sidebar-foreground hover:bg-sidebar-muted hover:text-foreground"
                      )}
                    >
                      <Icon className="w-5 h-5" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="ml-2">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 h-10 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-sidebar-foreground hover:bg-sidebar-muted hover:text-foreground"
                )}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="p-2.5 border-t border-sidebar-border">
          {collapsed ? (
            <Button
              variant="ghost"
              size="icon"
              className="w-full h-10"
              onClick={() => setCollapsed(false)}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-3 text-sidebar-foreground"
              onClick={() => setCollapsed(true)}
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Collapse</span>
            </Button>
          )}
        </div>
      </aside>
    </TooltipProvider>
  )
}
