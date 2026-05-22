"use client"

import { useState, useEffect, useRef } from "react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  Brain,
  Wrench,
  Eye,
  Zap,
  AlertTriangle,
  CheckCircle2,
  MessageCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Network,
  Search,
  Code,
  Shield,
  Timer,
  ArrowRight,
  Activity,
} from "lucide-react"

interface ThinkingStep {
  type: string
  content: string
  timestamp: string
  emoji: string
  agent?: string
  duration_ms?: number
}

interface AgentLiveThought {
  agent_name: string
  agent_emoji: string
  agent_role: string
  current_thought: string
  thought_type: string
  thoughts_count: number
  tools_used: number
  messages_sent: number
  elapsed_ms: number
}

interface AgentThinkingLiveProps {
  thoughts: ThinkingStep[]
  currentAgent?: AgentLiveThought | null
  isProcessing?: boolean
  className?: string
}

const THOUGHT_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; bgColor: string; label: string }> = {
  reasoning: {
    icon: <Brain className="size-3" />,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10 border-purple-500/20",
    label: "Reasoning"
  },
  tool_call: {
    icon: <Wrench className="size-3" />,
    color: "text-blue-400",
    bgColor: "bg-blue-500/10 border-blue-500/20",
    label: "Tool Call"
  },
  observation: {
    icon: <Eye className="size-3" />,
    color: "text-cyan-400",
    bgColor: "bg-cyan-500/10 border-cyan-500/20",
    label: "Observation"
  },
  decision: {
    icon: <Zap className="size-3" />,
    color: "text-amber-400",
    bgColor: "bg-amber-500/10 border-amber-500/20",
    label: "Decision"
  },
  warning: {
    icon: <AlertTriangle className="size-3" />,
    color: "text-orange-400",
    bgColor: "bg-orange-500/10 border-orange-500/20",
    label: "Warning"
  },
  success: {
    icon: <CheckCircle2 className="size-3" />,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10 border-emerald-500/20",
    label: "Complete"
  },
  reflection: {
    icon: <Sparkles className="size-3" />,
    color: "text-indigo-400",
    bgColor: "bg-indigo-500/10 border-indigo-500/20",
    label: "Reflection"
  },
  communication: {
    icon: <MessageCircle className="size-3" />,
    color: "text-pink-400",
    bgColor: "bg-pink-500/10 border-pink-500/20",
    label: "Communication"
  },
}

export function AgentThinkingLive({ thoughts, currentAgent, isProcessing, className }: AgentThinkingLiveProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [visibleThoughts, setVisibleThoughts] = useState<ThinkingStep[]>([])

  // Auto-scroll to latest thought
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thoughts, isExpanded])

  // Animate thoughts appearing
  useEffect(() => {
    setVisibleThoughts(thoughts.slice(-12))
  }, [thoughts])

  if (!thoughts || thoughts.length === 0) {
    if (!isProcessing) return null
    return (
      <div className={cn("rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-accent/5 overflow-hidden", className)}>
        <div className="px-4 py-3 flex items-center gap-3">
          <div className="relative">
            <Brain className="size-4 text-primary" />
            <span className="absolute -top-0.5 -right-0.5 size-2 bg-primary rounded-full animate-pulse" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-foreground">Agent is thinking...</p>
            <div className="flex items-center gap-1.5 mt-1">
              <div className="typing-indicator flex gap-0.5">
                <span className="size-1 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="size-1 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="size-1 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-[10px] text-muted-foreground">Initializing analysis pipeline...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const displayThoughts = isExpanded ? visibleThoughts : visibleThoughts.slice(-3)

  return (
    <div className={cn(
      "rounded-xl border overflow-hidden transition-all duration-300",
      isProcessing 
        ? "border-primary/30 bg-gradient-to-br from-card/80 to-primary/5 shadow-lg shadow-primary/5" 
        : "border-border/30 bg-card/60",
      className
    )}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-muted/20 transition-all duration-200"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Brain className={cn("size-4", isProcessing ? "text-primary" : "text-muted-foreground")} />
            {isProcessing && (
              <span className="absolute -top-0.5 -right-0.5 size-2 bg-primary rounded-full animate-pulse" />
            )}
          </div>
          <span className="text-xs font-bold text-foreground">Live Agent Thoughts</span>
          
          {/* Current agent badge */}
          {currentAgent && (
            <Badge 
              variant="outline" 
              className="text-[10px] px-2 py-0 bg-primary/5 border-primary/20 text-primary gap-1 animate-in fade-in"
            >
              <span>{currentAgent.agent_emoji}</span>
              <span>{currentAgent.agent_role}</span>
            </Badge>
          )}
          
          {/* Stats */}
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-0.5">
              <Activity className="size-2.5" />
              {thoughts.length} steps
            </span>
            {currentAgent && currentAgent.tools_used > 0 && (
              <span className="flex items-center gap-0.5">
                <Wrench className="size-2.5" />
                {currentAgent.tools_used} tools
              </span>
            )}
            {currentAgent && currentAgent.messages_sent > 0 && (
              <span className="flex items-center gap-0.5">
                <MessageCircle className="size-2.5" />
                {currentAgent.messages_sent} msgs
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isProcessing && (
            <div className="flex items-center gap-1 text-[10px] text-primary">
              <div className="size-1.5 rounded-full bg-primary animate-pulse" />
              <span>Live</span>
            </div>
          )}
          {isExpanded ? <ChevronUp className="size-3.5 text-muted-foreground" /> : <ChevronDown className="size-3.5 text-muted-foreground" />}
        </div>
      </button>

      {/* Live thought stream */}
      <div 
        ref={scrollRef}
        className={cn(
          "transition-all duration-300 overflow-hidden",
          isExpanded ? "max-h-[400px] overflow-y-auto" : "max-h-[120px]"
        )}
      >
        <div className="px-3 pb-3 space-y-1">
          {!isExpanded && thoughts.length > 3 && (
            <button
              onClick={(e) => { e.stopPropagation(); setIsExpanded(true) }}
              className="text-[10px] text-primary/70 hover:text-primary transition-colors pl-2 py-0.5"
            >
              ↑ {thoughts.length - 3} earlier thoughts...
            </button>
          )}
          
          {displayThoughts.map((step, idx) => {
            const config = THOUGHT_TYPE_CONFIG[step.type] || THOUGHT_TYPE_CONFIG.reasoning
            const isLatest = idx === displayThoughts.length - 1 && isProcessing
            
            return (
              <div
                key={`${step.timestamp}-${idx}`}
                className={cn(
                  "flex items-start gap-2 px-2.5 py-2 rounded-lg border text-xs transition-all duration-300",
                  config.bgColor,
                  isLatest && "ring-1 ring-primary/20 shadow-sm",
                  "animate-in fade-in slide-in-from-left-2"
                )}
                style={{ animationDelay: `${idx * 30}ms`, animationDuration: "200ms" }}
              >
                {/* Type indicator */}
                <div className={cn("shrink-0 mt-0.5 flex items-center justify-center size-5 rounded-md bg-background/50", config.color)}>
                  {config.icon}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={cn("text-[9px] font-bold uppercase tracking-wider", config.color)}>
                      {config.label}
                    </span>
                    {step.agent && (
                      <span className="text-[9px] text-muted-foreground">
                        • {step.agent}
                      </span>
                    )}
                    {step.duration_ms && (
                      <span className="text-[9px] text-muted-foreground flex items-center gap-0.5">
                        <Timer className="size-2" />
                        {step.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <p className={cn(
                    "text-[11px] leading-relaxed",
                    isLatest ? "text-foreground font-medium" : "text-muted-foreground"
                  )}>
                    {step.content}
                  </p>
                </div>
                
                {/* Live indicator for latest */}
                {isLatest && (
                  <div className="shrink-0 mt-1">
                    <div className="size-1.5 rounded-full bg-primary animate-pulse" />
                  </div>
                )}
              </div>
            )
          })}
          
          {/* Typing indicator when processing */}
          {isProcessing && (
            <div className="flex items-center gap-2 px-2.5 py-2 text-[11px] text-muted-foreground">
              <div className="flex gap-0.5">
                <span className="size-1 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="size-1 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="size-1 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="italic">Thinking...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
