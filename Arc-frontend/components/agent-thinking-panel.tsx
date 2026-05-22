"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronUp, Brain, Wrench, Eye, Zap, AlertTriangle, CheckCircle2, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ModificationThinkingStep } from "@/types"

interface AgentThinkingPanelProps {
  steps: ModificationThinkingStep[]
  strategyUsed: string
  isProcessing?: boolean
  className?: string
}

const THOUGHT_ICONS: Record<string, React.ReactNode> = {
  reasoning: <Brain className="size-3.5 text-purple-500" />,
  tool_call: <Wrench className="size-3.5 text-blue-500" />,
  observation: <Eye className="size-3.5 text-cyan-500" />,
  decision: <Zap className="size-3.5 text-amber-500" />,
  warning: <AlertTriangle className="size-3.5 text-orange-500" />,
  success: <CheckCircle2 className="size-3.5 text-green-500" />,
  reflection: <MessageCircle className="size-3.5 text-indigo-500" />,
}

const STRATEGY_LABELS: Record<string, { label: string; color: string }> = {
  direct_xml: { label: "Direct XML", color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
  architecture_regeneration: { label: "Full Regen", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" },
  hybrid: { label: "Hybrid", color: "bg-violet-500/10 text-violet-600 border-violet-500/20" },
}

export function AgentThinkingPanel({ steps, strategyUsed, isProcessing, className }: AgentThinkingPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!steps || steps.length === 0) return null

  const strategyInfo = STRATEGY_LABELS[strategyUsed] || STRATEGY_LABELS.hybrid
  const displaySteps = isExpanded ? steps : steps.slice(-3)

  return (
    <div className={cn("rounded-lg border border-border/50 bg-muted/20 overflow-hidden", className)}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <Brain className="size-4 text-purple-500" />
            {isProcessing && (
              <span className="absolute -top-0.5 -right-0.5 size-2 bg-green-500 rounded-full animate-pulse" />
            )}
          </div>
          <span className="text-xs font-semibold text-foreground">Agent Reasoning</span>
          <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0", strategyInfo.color)}>
            {strategyInfo.label}
          </Badge>
          <span className="text-[10px] text-muted-foreground">{steps.length} steps</span>
        </div>
        <div className="size-5 rounded flex items-center justify-center">
          {isExpanded ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </div>
      </button>

      {/* Steps */}
      <div className="px-3 pb-2 space-y-1.5">
        {!isExpanded && steps.length > 3 && (
          <button
            onClick={() => setIsExpanded(true)}
            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          >
            + {steps.length - 3} earlier steps...
          </button>
        )}
        {displaySteps.map((step, idx) => (
          <div
            key={idx}
            className={cn(
              "flex items-start gap-2 px-2 py-1.5 rounded-md text-xs animate-in fade-in-50 duration-200",
              step.type === "warning" ? "bg-orange-500/5" :
              step.type === "success" ? "bg-green-500/5" :
              "bg-background/50"
            )}
          >
            <div className="shrink-0 mt-0.5">
              {THOUGHT_ICONS[step.type] || <MessageCircle className="size-3.5 text-muted-foreground" />}
            </div>
            <p className="text-muted-foreground leading-relaxed flex-1">{step.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
