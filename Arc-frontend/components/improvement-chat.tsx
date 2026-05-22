"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import {
  Send, Check, Loader2, ChevronDown, ChevronUp,
  Sparkles, AlertCircle, Lightbulb, User, Bot,
  ArrowRight, Code2, RefreshCw, Blend, History
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getApiUrl } from "@/lib/config"
import { AgentThinkingPanel } from "@/components/agent-thinking-panel"
import { ModificationDiffView } from "@/components/modification-diff-view"
import { ModificationValidationPanel } from "@/components/modification-validation-panel"
import type {
  ModificationThinkingStep, ModificationDiff,
  ModificationValidation, ModificationHistoryEntry
} from "@/types"

interface ChatMessage {
  id: string
  type: "user" | "ai"
  content: string
  timestamp: Date
  status?: "sending" | "processing" | "complete" | "error"
  changes?: string[]
  error?: string
  thinkingSteps?: ModificationThinkingStep[]
  diffSummary?: ModificationDiff
  validationResults?: ModificationValidation
  strategyUsed?: string
}

interface ImprovementChatProps {
  architecture: any
  onArchitectureUpdate: (newArchitecture: any, newDiagramXml: string, mermaid?: string, terraform?: string) => void
  sessionId: string
  currentXml?: string
  originalRequirements?: string
  className?: string
}

type Strategy = "hybrid" | "direct_xml" | "architecture_regeneration"

const STRATEGIES: { value: Strategy; label: string; icon: React.ReactNode; desc: string }[] = [
  { value: "hybrid", label: "Hybrid", icon: <Blend className="size-3.5" />, desc: "Auto-selects best approach" },
  { value: "direct_xml", label: "Direct XML", icon: <Code2 className="size-3.5" />, desc: "Preserves layout" },
  { value: "architecture_regeneration", label: "Full Regen", icon: <RefreshCw className="size-3.5" />, desc: "Rebuilds entire diagram" },
]

const EXAMPLE_IMPROVEMENTS = [
  { text: "Add Redis cache", icon: "⚡" },
  { text: "Connect to Key Vault", icon: "🔐" },
  { text: "Add monitoring", icon: "📊" },
  { text: "Add CDN layer", icon: "🌐" }
]

export function ImprovementChat({
  architecture,
  onArchitectureUpdate,
  sessionId,
  currentXml,
  originalRequirements,
  className
}: ImprovementChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [strategy, setStrategy] = useState<Strategy>("hybrid")
  const [history, setHistory] = useState<ModificationHistoryEntry[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [activeResultId, setActiveResultId] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 80)}px`
    }
  }, [input])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        setTimeout(() => {
          scrollContainer.scrollTop = scrollContainer.scrollHeight
        }, 100)
      }
    }
  }, [messages])

  const applyModification = async (prompt: string) => {
    if (!prompt.trim() || isProcessing || !architecture) return

    const userMsgId = `user-${Date.now()}`
    const aiMsgId = `ai-${Date.now()}`

    const userMessage: ChatMessage = {
      id: userMsgId,
      type: "user",
      content: prompt.trim(),
      timestamp: new Date(),
      status: "complete"
    }

    const aiMessage: ChatMessage = {
      id: aiMsgId,
      type: "ai",
      content: "Modification agent analyzing your request...",
      timestamp: new Date(),
      status: "processing"
    }

    setMessages(prev => [...prev, userMessage, aiMessage])
    setInput("")
    setIsProcessing(true)
    setActiveResultId(aiMsgId)

    try {
      const response = await fetch(getApiUrl("DIAGRAM_MODIFY"), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          modification_prompt: prompt.trim(),
          current_architecture: architecture,
          current_xml: currentXml || "",
          strategy: strategy,
          original_requirements: originalRequirements || ""
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      const changesText = result.changes_applied?.length > 0
        ? result.changes_applied.join(" | ")
        : "Architecture updated successfully"

      setMessages(prev => prev.map(msg =>
        msg.id === aiMsgId
          ? {
              ...msg,
              content: changesText,
              status: "complete" as const,
              changes: result.changes_applied || [],
              thinkingSteps: result.thinking_process || [],
              diffSummary: result.diff_summary || null,
              validationResults: result.validation_results || null,
              strategyUsed: result.strategy_used || strategy,
            }
          : msg
      ))

      // Add to history
      setHistory(prev => [...prev, {
        id: aiMsgId,
        prompt: prompt.trim(),
        strategy: result.strategy_used || strategy,
        changes: result.changes_applied || [],
        timestamp: new Date(),
        diff: result.diff_summary,
        validation: result.validation_results,
      }])

      // Update the diagram
      if (result.architecture && result.diagram_xml) {
        onArchitectureUpdate(
          result.architecture,
          result.diagram_xml,
          result.mermaid,
          result.terraform
        )
      }

    } catch (error) {
      console.error('Modification error:', error)
      setMessages(prev => prev.map(msg =>
        msg.id === aiMsgId
          ? {
              ...msg,
              content: error instanceof Error ? error.message : "Failed to apply modification",
              status: "error" as const,
              error: error instanceof Error ? error.message : "Unknown error"
            }
          : msg
      ))
    } finally {
      setIsProcessing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      applyModification(input)
    }
  }

  const clearChat = () => {
    setMessages([])
    setActiveResultId(null)
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!architecture || !architecture.services?.length) {
    return null
  }

  const hasMessages = messages.length > 0
  const activeMsg = messages.find(m => m.id === activeResultId)

  return (
    <div className={cn(
      "border-t border-border/30 bg-gradient-to-b from-background/95 to-muted/30 backdrop-blur-sm transition-all duration-300",
      isCollapsed ? "h-14" : "h-auto",
      className
    )}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-muted/20 transition-all duration-200 group"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="size-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Sparkles className="size-4 text-white" />
            </div>
            {isProcessing && (
              <span className="absolute -top-0.5 -right-0.5 size-2.5 bg-green-500 rounded-full animate-pulse" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-sm text-foreground">Modify Architecture</h3>
            <p className="text-xs text-muted-foreground">AI agent with validation pipeline</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {history.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => { e.stopPropagation(); setShowHistory(!showHistory); }}
            >
              <History className="size-3" />
              {history.length}
            </Button>
          )}
          {hasMessages && (
            <Badge variant="secondary" className="bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20">
              {messages.filter(m => m.type === "user").length} changes
            </Badge>
          )}
          {hasMessages && !isCollapsed && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => { e.stopPropagation(); clearChat(); }}
            >
              Clear
            </Button>
          )}
          <div className="size-6 rounded-full bg-muted/50 flex items-center justify-center">
            {isCollapsed ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </div>
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="px-4 pb-4 space-y-3">
          {/* Strategy Selector */}
          <div className="flex items-center gap-1.5">
            {STRATEGIES.map((s) => (
              <button
                key={s.value}
                onClick={() => setStrategy(s.value)}
                disabled={isProcessing}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border",
                  strategy === s.value
                    ? "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/30 shadow-sm"
                    : "bg-background/50 text-muted-foreground border-transparent hover:bg-muted/50 hover:border-border/50"
                )}
                title={s.desc}
              >
                {s.icon}
                {s.label}
              </button>
            ))}
          </div>

          {/* History Panel (collapsible) */}
          {showHistory && history.length > 0 && (
            <div className="rounded-lg border border-border/50 bg-muted/20 p-2 space-y-1.5 max-h-[120px] overflow-y-auto">
              <p className="text-[10px] font-semibold text-muted-foreground px-1">Modification History</p>
              {history.map((entry, idx) => (
                <div
                  key={entry.id}
                  className={cn(
                    "flex items-center gap-2 px-2 py-1 rounded-md text-xs cursor-pointer hover:bg-muted/50 transition-colors",
                    activeResultId === entry.id && "bg-violet-500/10 border border-violet-500/20"
                  )}
                  onClick={() => setActiveResultId(entry.id)}
                >
                  <span className="text-muted-foreground w-4">{idx + 1}.</span>
                  <span className="flex-1 truncate">{entry.prompt}</span>
                  <Badge variant="outline" className="text-[8px] px-1 py-0">{entry.strategy === "direct_xml" ? "XML" : entry.strategy === "architecture_regeneration" ? "Regen" : "Hybrid"}</Badge>
                  <span className="text-[10px] text-muted-foreground">{formatTime(entry.timestamp)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Chat Messages */}
          {hasMessages ? (
            <ScrollArea ref={scrollRef} className="max-h-[160px] pr-2">
              <div className="space-y-3">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-2.5 animate-in fade-in-50 slide-in-from-bottom-2 duration-300",
                      msg.type === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    {/* Avatar */}
                    <div className={cn(
                      "size-7 rounded-full flex items-center justify-center shrink-0 shadow-sm",
                      msg.type === "user"
                        ? "bg-gradient-to-br from-blue-500 to-cyan-500"
                        : "bg-gradient-to-br from-violet-500 to-purple-600"
                    )}>
                      {msg.type === "user"
                        ? <User className="size-3.5 text-white" />
                        : <Bot className="size-3.5 text-white" />
                      }
                    </div>

                    {/* Message Bubble */}
                    <div className={cn(
                      "max-w-[85%] rounded-2xl px-3.5 py-2 shadow-sm",
                      msg.type === "user"
                        ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-tr-md"
                        : msg.status === "error"
                          ? "bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-tl-md"
                          : msg.status === "processing"
                            ? "bg-muted/80 border border-border/50 rounded-tl-md"
                            : "bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/20 rounded-tl-md"
                    )}>
                      <div className="flex items-start gap-2">
                        {msg.status === "processing" && (
                          <Loader2 className="size-4 animate-spin shrink-0 mt-0.5 text-violet-500" />
                        )}
                        {msg.status === "complete" && msg.type === "ai" && (
                          <Check className="size-4 shrink-0 mt-0.5 text-green-500" />
                        )}
                        {msg.status === "error" && (
                          <AlertCircle className="size-4 shrink-0 mt-0.5" />
                        )}
                        <p className={cn(
                          "text-sm leading-relaxed",
                          msg.type === "ai" && msg.status !== "error" && "text-foreground"
                        )}>
                          {msg.content}
                        </p>
                      </div>
                      {msg.strategyUsed && msg.status === "complete" && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 mt-1">
                          {msg.strategyUsed === "direct_xml" ? "Direct XML" : msg.strategyUsed === "architecture_regeneration" ? "Full Regen" : "Hybrid"}
                        </Badge>
                      )}
                      <p className={cn(
                        "text-[10px] mt-1 opacity-60",
                        msg.type === "user" ? "text-white/70" : "text-muted-foreground"
                      )}>
                        {formatTime(msg.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          ) : (
            /* Example Prompts */
            <div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2.5">
                <Lightbulb className="size-3.5 text-amber-500" />
                <span className="font-medium">Quick modifications</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {EXAMPLE_IMPROVEMENTS.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(example.text)}
                    className="group flex items-center gap-2 px-3 py-2 rounded-xl bg-muted/50 hover:bg-muted border border-transparent hover:border-border/50 text-left transition-all duration-200 hover:scale-[1.02] hover:shadow-sm"
                  >
                    <span className="text-base">{example.icon}</span>
                    <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors truncate">
                      {example.text}
                    </span>
                    <ArrowRight className="size-3 ml-auto text-muted-foreground/50 group-hover:text-foreground/50 group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Agent Results Panels (shown for active result) */}
          {activeMsg && activeMsg.status === "complete" && activeMsg.type === "ai" && (
            <div className="space-y-2">
              {/* Thinking Panel */}
              {activeMsg.thinkingSteps && activeMsg.thinkingSteps.length > 0 && (
                <AgentThinkingPanel
                  steps={activeMsg.thinkingSteps}
                  strategyUsed={activeMsg.strategyUsed || strategy}
                />
              )}

              {/* Diff View */}
              {(activeMsg.diffSummary || activeMsg.changes) && (
                <ModificationDiffView
                  diff={activeMsg.diffSummary!}
                  changesApplied={activeMsg.changes || []}
                />
              )}

              {/* Validation Panel */}
              {activeMsg.validationResults && (
                <ModificationValidationPanel
                  validation={activeMsg.validationResults}
                />
              )}
            </div>
          )}

          {/* Input */}
          <div className="flex gap-2 items-end">
            <div className="flex-1 relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe a modification..."
                className="min-h-[44px] max-h-[80px] resize-none text-sm bg-background/80 border-border/50 rounded-xl pl-4 pr-4 py-3 focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all"
                disabled={isProcessing}
              />
            </div>
            <Button
              onClick={() => applyModification(input)}
              disabled={!input.trim() || isProcessing}
              size="icon"
              className={cn(
                "shrink-0 size-11 rounded-xl shadow-lg transition-all duration-200",
                input.trim() && !isProcessing
                  ? "bg-gradient-to-br from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 shadow-violet-500/25 hover:shadow-violet-500/40 hover:scale-105"
                  : "bg-muted"
              )}
            >
              {isProcessing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
