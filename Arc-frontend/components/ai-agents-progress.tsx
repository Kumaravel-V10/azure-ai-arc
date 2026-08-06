"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { getApiUrl, API_CONFIG, UI_CONFIG } from "@/lib/config"
import { AgentInteractionDialog } from "@/components/agent-interaction-dialog"
import { AgentThinkingLive } from "@/components/agent-thinking-live"
import {
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Clock,
  Zap,
  Shield,
  Gauge,
  Building2,
  Link2,
  ClipboardCheck,
  Layers,
  MessageSquare,
  Brain,
  Activity,
} from "lucide-react"

type AgentStatus = "pending" | "running" | "complete" | "error"

interface AgentOutputSummary {
  duration?: number
  message?: string  // Progress message from backend
  // Agentic AI - Thinking summary
  thought_type?: string  // For individual thinking updates
  thought?: string
  emoji?: string
  agent_persona?: string
  agent_emoji?: string
  thinking_summary?: {
    agent?: string
    persona?: { role?: string; emoji?: string; expertise?: string[] }
    thoughts?: Array<{ type: string; content: string; timestamp: string; emoji: string }>
    tool_calls?: Array<{ tool: string; duration_ms: number }>
    messages_sent?: number
    messages_received?: number
  }
  // ComponentExtraction
  apis_found?: number
  nfrs_found?: number
  tech_requirements?: number
  tech_stack?: number
  integration_points?: number
  complexity?: string
  recommended_pattern?: string
  // AzureReference
  matched_architectures?: number
  recommended_services?: number
  design_decisions?: number
  local_docs_matched?: number
  top_references?: string[]
  // Security
  security_services?: string[]
  compliance_score?: number
  critical_issues?: number
  // Performance
  performance_services?: string[]
  performance_score?: number
  optimization_opportunities?: number
  // Architecture
  services_designed?: number
  connections_created?: number
  containers_defined?: number
  architecture_pattern?: string
  architecture_score?: number
  service_names?: string[]
  // Connection
  total_connections?: number
  services_connected?: number
  orphan_services?: number
  has_primary_chain?: boolean
  // Validation
  validation_score?: number
  validation_status?: string
  requirements_coverage?: { coverage_percentage?: number; implemented?: number; total_requirements?: number }
  missing_components?: number
  recommendations?: number
  // Common
  quick_wins?: number
  context_used?: string[]
  data_passed_to_next?: string[]
  interaction?: boolean
}

interface AgentLog {
  agent: string
  status: string
  percentage: number
  timestamp: string
  output_summary: AgentOutputSummary
}

interface Agent {
  id: string
  name: string
  agentKey: string
  icon: React.ElementType
  status: AgentStatus
  outputSummary?: AgentOutputSummary
}

interface AIAgentsProgressProps {
  onComplete: (data: any) => void
  requirements?: string
}

const AGENT_NAME_MAP: Record<string, string> = {
  ComponentExtractionAgent: "components",
  AzureArchitectureReferenceAgent: "references",
  SecurityAgent: "security",
  PerformanceAgent: "performance",
  ArchitectureAgent: "architecture",
  ConnectionExpertAgent: "connection",
  RequirementsValidationAgent: "validation",
}

const POLL_INTERVAL = UI_CONFIG.PROGRESS.POLL_INTERVAL_MS

export function AIAgentsProgress({
  onComplete,
  requirements = "Generate architecture",
}: AIAgentsProgressProps) {
  const [agents, setAgents] = useState<Agent[]>([
    { id: "components", name: "Component Extractor", agentKey: "ComponentExtractionAgent", icon: Layers, status: "pending" },
    { id: "references", name: "Azure Reference Mapper", agentKey: "AzureArchitectureReferenceAgent", icon: Building2, status: "pending" },
    { id: "security", name: "Security Expert", agentKey: "SecurityAgent", icon: Shield, status: "pending" },
    { id: "performance", name: "Performance Expert", agentKey: "PerformanceAgent", icon: Gauge, status: "pending" },
    { id: "architecture", name: "Architecture Expert", agentKey: "ArchitectureAgent", icon: Zap, status: "pending" },
    { id: "connection", name: "Connection Expert", agentKey: "ConnectionExpertAgent", icon: Link2, status: "pending" },
    { id: "validation", name: "Requirements Validator", agentKey: "RequirementsValidationAgent", icon: ClipboardCheck, status: "pending" },
  ])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progressPct, setProgressPct] = useState(0)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [pendingInteraction, setPendingInteraction] = useState<any | null>(null)
  const [liveThoughts, setLiveThoughts] = useState<Array<{type: string; content: string; timestamp: string; emoji: string; agent?: string; duration_ms?: number}>>([])
  const [currentAgentThought, setCurrentAgentThought] = useState<{agent_name: string; agent_emoji: string; agent_role: string; current_thought: string; thought_type: string; thoughts_count: number; tools_used: number; messages_sent: number; elapsed_ms: number} | null>(null)
  const startTimeRef = useRef<number>(Date.now())
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hasCompletedRef = useRef(false)

  // ── Start the workflow ──────────────────────────────────────────
  useEffect(() => {
    let cancelled = false

    const startWorkflow = async () => {
      try {
        startTimeRef.current = Date.now()
        const response = await fetch(getApiUrl("GENERATE_STREAM"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requirements,
            project_name: "AI Agents Architecture",
            environment: "production",
            include_terraform: true,
            include_mermaid: true,
            use_professional_style: true,
          }),
        })

        if (!response.ok) {
          const errBody = await response.text()
          throw new Error(errBody || `HTTP ${response.status}`)
        }

        const data = await response.json()
        if (!cancelled) {
          setSessionId(data.session_id)
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error("Failed to start workflow:", err)
          setError(err.message || "Failed to start workflow")
        }
      }
    }

    startWorkflow()
    return () => { cancelled = true }
  }, [requirements])

  // ── Elapsed time ticker ─────────────────────────────────────────
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [])

  // ── Process a progress response ─────────────────────────────────
  const processProgress = useCallback(
    (progress: any) => {
      if (!progress) return

      const currentAgent = progress.current_agent
      const logs: AgentLog[] = progress.agent_logs || []
      const pct = progress.progress_percentage || 0
      setProgressPct(pct)

      // Handle live thoughts from backend (real-time agent thinking stream)
      if (progress.live_thoughts && progress.live_thoughts.length > 0) {
        setLiveThoughts(progress.live_thoughts.map((t: any) => ({
          type: t.type || "reasoning",
          content: t.content || "",
          timestamp: t.timestamp || "",
          emoji: t.emoji || "🧠",
          agent: t.agent?.replace("Agent", "") || undefined,
        })))
      }

      // Handle human-in-the-loop interaction
      if (progress.interaction && (progress.status === "waiting_for_input" || progress.status === "waiting")) {
        setPendingInteraction(progress.interaction)
      } else {
        setPendingInteraction(null)
      }

      // Collect live thoughts from all agent logs for the thinking panel
      const allThoughts: Array<{type: string; content: string; timestamp: string; emoji: string; agent?: string; duration_ms?: number}> = []
      for (const log of logs) {
        const summary = log.output_summary
        // Collect individual thinking updates
        if (summary?.thought_type && summary?.thought) {
          allThoughts.push({
            type: summary.thought_type,
            content: summary.thought,
            timestamp: log.timestamp,
            emoji: summary.emoji || "🧠",
            agent: log.agent.replace("Agent", ""),
          })
        }
        // Collect from thinking_summary
        if (summary?.thinking_summary?.thoughts) {
          for (const t of summary.thinking_summary.thoughts) {
            allThoughts.push({
              type: t.type,
              content: t.content,
              timestamp: t.timestamp,
              emoji: t.emoji,
              agent: summary.thinking_summary.agent?.replace("Agent", ""),
            })
          }
        }
      }
      if (allThoughts.length > 0) {
        setLiveThoughts(allThoughts)
      }

      // Update current agent thought state
      if (currentAgent) {
        const runningLog = logs.find(l => l.agent === currentAgent && l.status === "running")
        if (runningLog?.output_summary) {
          const s = runningLog.output_summary
          setCurrentAgentThought({
            agent_name: currentAgent,
            agent_emoji: s.agent_emoji || "🤖",
            agent_role: s.agent_persona || currentAgent.replace("Agent", ""),
            current_thought: s.thought || s.message || "Processing...",
            thought_type: s.thought_type || "reasoning",
            thoughts_count: s.thinking_summary?.thoughts?.length || 0,
            tools_used: s.thinking_summary?.tool_calls?.length || 0,
            messages_sent: s.thinking_summary?.messages_sent || 0,
            elapsed_ms: (s.duration || 0) * 1000,
          })
        }
      }

      // Build maps of completed and running agents from logs
      const completedMap = new Map<string, AgentOutputSummary>()
      const runningMap = new Map<string, AgentOutputSummary>()
      
      for (const log of logs) {
        const localId = AGENT_NAME_MAP[log.agent]
        if (localId) {
          if (log.status === "completed") {
            completedMap.set(localId, log.output_summary)
          } else if (log.status === "running") {
            runningMap.set(localId, log.output_summary)
          }
        }
      }

      setAgents((prev) =>
        prev.map((agent) => {
          if (completedMap.has(agent.id)) {
            return { ...agent, status: "complete", outputSummary: completedMap.get(agent.id) }
          }
          if (currentAgent && agent.agentKey === currentAgent) {
            // Get running message if available
            const runningSummary = runningMap.get(agent.id)
            return { ...agent, status: "running", outputSummary: runningSummary || agent.outputSummary }
          }
          // If this agent's key partially matches the current_agent string
          if (
            currentAgent &&
            currentAgent.toLowerCase().includes(agent.id.toLowerCase())
          ) {
            const runningSummary = runningMap.get(agent.id)
            return { ...agent, status: "running", outputSummary: runningSummary || agent.outputSummary }
          }
          return agent
        }),
      )

      // Handle completion
      if (progress.status === "completed" && progress.result && !hasCompletedRef.current) {
        hasCompletedRef.current = true
        // Mark all agents complete
        setAgents((prev) =>
          prev.map((a) => ({
            ...a,
            status: "complete",
            outputSummary: completedMap.get(a.id) || a.outputSummary,
          })),
        )
        setProgressPct(100)
        if (timerRef.current) clearInterval(timerRef.current)

        // Call onComplete with the full workflow result
        setTimeout(() => onComplete(progress.result), 600)
      }

      if (progress.status === "error") {
        setError(progress.error || "Workflow failed")
        if (timerRef.current) clearInterval(timerRef.current)
      }
    },
    [onComplete],
  )

  // ── Poll for progress ───────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) return

    const poll = async () => {
      try {
        const res = await fetch(getApiUrl("PROGRESS", sessionId))
        if (!res.ok) return
        const data = await res.json()
        processProgress(data)

        // Stop polling when done
        if (data.status === "completed" || data.status === "error") {
          if (pollingRef.current) clearInterval(pollingRef.current)
        }
      } catch {
        // Silently retry on network blip
      }
    }

    poll() // Immediately poll once
    pollingRef.current = setInterval(poll, POLL_INTERVAL)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [sessionId, processProgress])

  // ── Format elapsed time ─────────────────────────────────────────
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return m > 0 ? `${m}m ${s}s` : `${s}s`
  }

  // ── Render output summary for each agent ────────────────────────
  const renderOutputSummary = (agent: Agent) => {
    const s = agent.outputSummary
    if (!s) return null

    const items: { label: string; value: string | number }[] = []

    switch (agent.id) {
      case "components":
        if (s.apis_found != null) items.push({ label: "APIs Found", value: s.apis_found })
        if (s.nfrs_found != null) items.push({ label: "NFRs Found", value: s.nfrs_found })
        if (s.tech_requirements != null) items.push({ label: "Tech Requirements", value: s.tech_requirements })
        if (s.tech_stack != null) items.push({ label: "Tech Stack Items", value: s.tech_stack })
        if (s.integration_points != null) items.push({ label: "Integration Points", value: s.integration_points })
        if (s.complexity) items.push({ label: "Complexity", value: s.complexity })
        if (s.recommended_pattern) items.push({ label: "Recommended Pattern", value: s.recommended_pattern })
        break
      case "references":
        if (s.matched_architectures != null) items.push({ label: "Reference Architectures Matched", value: s.matched_architectures })
        if (s.recommended_services != null) items.push({ label: "Recommended Services", value: s.recommended_services })
        if (s.design_decisions != null) items.push({ label: "Design Decisions", value: s.design_decisions })
        if (s.local_docs_matched != null) items.push({ label: "Local Docs Matched", value: s.local_docs_matched })
        if (s.recommended_pattern) items.push({ label: "Pattern", value: s.recommended_pattern })
        if (s.top_references?.length) items.push({ label: "Top References", value: s.top_references.join(", ") })
        break
      case "security":
        if (s.compliance_score != null) items.push({ label: "Compliance Score", value: `${s.compliance_score}/100` })
        if (s.security_services?.length) items.push({ label: "Security Services", value: s.security_services.join(", ") })
        if (s.critical_issues != null) items.push({ label: "Critical Issues", value: s.critical_issues })
        if (s.quick_wins != null) items.push({ label: "Quick Wins", value: s.quick_wins })
        break
      case "performance":
        if (s.performance_score != null) items.push({ label: "Performance Score", value: `${s.performance_score}/100` })
        if (s.performance_services?.length) items.push({ label: "Performance Services", value: s.performance_services.join(", ") })
        if (s.optimization_opportunities != null) items.push({ label: "Optimizations", value: s.optimization_opportunities })
        if (s.quick_wins != null) items.push({ label: "Quick Wins", value: s.quick_wins })
        break
      case "architecture":
        if (s.architecture_pattern) items.push({ label: "Pattern", value: s.architecture_pattern })
        if (s.architecture_score != null) items.push({ label: "Architecture Score", value: `${s.architecture_score}/100` })
        if (s.services_designed != null) items.push({ label: "Services Designed", value: s.services_designed })
        if (s.connections_created != null) items.push({ label: "Connections", value: s.connections_created })
        if (s.containers_defined != null) items.push({ label: "Containers", value: s.containers_defined })
        if (s.service_names?.length) items.push({ label: "Services", value: s.service_names.join(", ") })
        break
      case "connection":
        if (s.total_connections != null) items.push({ label: "Total Connections", value: s.total_connections })
        if (s.services_connected != null) items.push({ label: "Services Connected", value: s.services_connected })
        if (s.orphan_services != null) items.push({ label: "Orphan Services Fixed", value: s.orphan_services })
        if (s.has_primary_chain != null) items.push({ label: "Has Primary Chain", value: s.has_primary_chain ? "Yes" : "No" })
        break
      case "validation":
        if (s.validation_score != null) items.push({ label: "Validation Score", value: `${s.validation_score}/100` })
        if (s.validation_status) items.push({ label: "Status", value: s.validation_status })
        if (s.requirements_coverage?.coverage_percentage != null)
          items.push({
            label: "Coverage",
            value: `${s.requirements_coverage.coverage_percentage}% (${s.requirements_coverage.implemented ?? 0}/${s.requirements_coverage.total_requirements ?? 0})`,
          })
        if (s.missing_components != null) items.push({ label: "Missing Components", value: s.missing_components })
        if (s.recommendations != null) items.push({ label: "Recommendations", value: s.recommendations })
        break
    }

    return (
      <div className="mt-3 space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
        {/* Key output metrics */}
        <div className="grid grid-cols-2 gap-2">
          {items.map((item) => (
            <div key={item.label} className="rounded-md bg-muted/50 px-3 py-1.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                {item.label}
              </p>
              <p className="text-xs font-semibold text-foreground truncate" title={String(item.value)}>
                {item.value}
              </p>
            </div>
          ))}
        </div>

        {/* Duration */}
        {s.duration != null && (
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <Clock className="size-3" />
            <span>Completed in {s.duration.toFixed(1)}s</span>
          </div>
        )}

        {/* Data flow indicators */}
        {s.context_used?.length ? (
          <div className="flex flex-wrap items-center gap-1 text-[10px]">
            <span className="text-muted-foreground">Received from:</span>
            {s.context_used.map((ctx) => (
              <Badge key={ctx} variant="outline" className="text-[10px] px-1.5 py-0">
                {ctx.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        ) : null}

        {s.data_passed_to_next?.length ? (
          <div className="flex flex-wrap items-center gap-1 text-[10px]">
            <span className="text-muted-foreground">Passed to next:</span>
            {s.data_passed_to_next.map((d) => (
              <Badge key={d} variant="secondary" className="text-[10px] px-1.5 py-0">
                {d.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        ) : null}

        {/* Agentic AI - Thinking Trail (Enhanced) */}
        {s.thinking_summary?.thoughts?.length ? (
          <div className="mt-3 border-t border-border/50 pt-3">
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20">
                  <Brain className="size-3 text-purple-400" />
                  <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Agent Reasoning</span>
                </div>
                {s.thinking_summary.persona?.emoji && (
                  <span title={s.thinking_summary.persona.role} className="text-sm">
                    {s.thinking_summary.persona.emoji}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                {s.thinking_summary.tool_calls?.length ? (
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 text-blue-400 border-blue-400/30 bg-blue-500/5">
                    🔧 {s.thinking_summary.tool_calls.length} tools
                  </Badge>
                ) : null}
                {s.thinking_summary.messages_sent ? (
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 text-pink-400 border-pink-400/30 bg-pink-500/5">
                    💬 {s.thinking_summary.messages_sent} sent
                  </Badge>
                ) : null}
                <Badge variant="outline" className="text-[9px] px-1.5 py-0 text-purple-400 border-purple-400/30 bg-purple-500/5">
                  {s.thinking_summary.thoughts.length} steps
                </Badge>
              </div>
            </div>
            {s.thinking_summary.persona?.role && (
              <p className="text-[10px] text-muted-foreground/60 mb-2 italic">
                &ldquo;{s.thinking_summary.persona.role}&rdquo; {s.thinking_summary.persona.expertise?.length ? `• Expertise: ${s.thinking_summary.persona.expertise.slice(0, 3).join(", ")}` : ""}
              </p>
            )}
            <div className="space-y-1 max-h-[200px] overflow-y-auto scrollbar-thin pr-1">
              {s.thinking_summary.thoughts.slice(-8).map((thought, idx) => {
                const typeColor = thought.type === "warning" ? "text-orange-400" 
                  : thought.type === "success" ? "text-emerald-400"
                  : thought.type === "decision" ? "text-amber-400"
                  : thought.type === "tool_call" ? "text-blue-400"
                  : thought.type === "reflection" ? "text-indigo-400"
                  : thought.type === "communication" ? "text-pink-400"
                  : "text-muted-foreground/70"
                const typeBg = thought.type === "warning" ? "bg-orange-500/5 border-orange-500/10" 
                  : thought.type === "success" ? "bg-emerald-500/5 border-emerald-500/10"
                  : thought.type === "decision" ? "bg-amber-500/5 border-amber-500/10"
                  : "bg-background/30 border-transparent"
                return (
                  <div
                    key={idx}
                    className={`flex items-start gap-2 px-2 py-1.5 rounded-md border text-[10px] ${typeBg} animate-in fade-in slide-in-from-left-1`}
                    style={{ animationDelay: `${idx * 40}ms` }}
                  >
                    <span className="shrink-0 mt-px">{thought.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <span className={`font-medium uppercase tracking-wider text-[8px] ${typeColor}`}>{thought.type}</span>
                      <p className="text-muted-foreground/80 leading-relaxed mt-0.5">{thought.content}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  // ── Handle interaction response ──────────────────────────────────
  const handleInteractionRespond = useCallback(async (decision: string, feedback?: string) => {
    if (!sessionId) return
    
    try {
      const res = await fetch(getApiUrl("INTERACTION_RESPOND", sessionId, "respond"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, feedback }),
      })
      
      if (res.ok) {
        setPendingInteraction(null)
      }
    } catch (err) {
      console.error("Failed to send interaction response:", err)
    }
  }, [sessionId])

  // ── Error state ─────────────────────────────────────────────────
  if (error) {
    return (
      <Card className="bg-card/60 backdrop-blur-xl p-6 border-border/30 animate-scale-in">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <AlertCircle className="size-6 text-red-500" />
              <span className="absolute -top-0.5 -right-0.5 flex size-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-red-500" />
              </span>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-red-400">Workflow Error</h3>
              <p className="mt-1 text-sm text-red-400/80">{error}</p>
            </div>
          </div>
        </div>
      </Card>
    )
  }

  // ── Main render ─────────────────────────────────────────────────
  const completedCount = agents.filter((a) => a.status === "complete").length
  const isRunning = agents.some((a) => a.status === "running")

  return (
    <Card className="bg-card/60 backdrop-blur-xl p-6 border-border/30 shadow-2xl shadow-black/10 animate-scale-in">
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <div className="relative flex size-2.5">
                {isRunning && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />}
                <span className={`relative inline-flex size-2.5 rounded-full ${completedCount === agents.length ? 'bg-emerald-500' : isRunning ? 'bg-primary' : 'bg-muted-foreground/50'}`} />
              </div>
              AI Multi-Agent Pipeline
            </h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {pendingInteraction
                ? "⏸ Waiting for your review and approval..."
                : completedCount === agents.length
                ? "All agents completed successfully ✓"
                : isRunning
                  ? "Processing your architecture requirements..."
                  : sessionId
                    ? "Agents queued..."
                    : "Initializing workflow..."}
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 text-sm font-mono text-muted-foreground bg-muted/30 px-3 py-1 rounded-lg">
              <Clock className="size-3.5 text-primary" />
              <span>{formatTime(elapsedTime)}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {completedCount}/{agents.length} agents
            </p>
          </div>
        </div>

        {/* Overall progress bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Overall Progress</span>
            <span className="font-mono">{progressPct}%</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-secondary/50 backdrop-blur-sm">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary via-primary/90 to-accent transition-all duration-700 ease-out relative overflow-hidden"
              style={{ width: `${progressPct}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
            </div>
          </div>
        </div>

        {/* Human-in-the-loop interaction dialog */}
        {pendingInteraction && (
          <AgentInteractionDialog
            interaction={pendingInteraction}
            onRespond={handleInteractionRespond}
          />
        )}

        {/* Live Agent Thinking Panel - shows real-time agent reasoning */}
        {isRunning && (
          <AgentThinkingLive
            thoughts={liveThoughts}
            currentAgent={currentAgentThought}
            isProcessing={isRunning}
          />
        )}

        {/* Agent pipeline list */}
        <div className="space-y-1">
          {agents.map((agent, index) => {
            const Icon = agent.icon
            const isExpanded = expandedAgent === agent.id
            const hasDetails = agent.status === "complete" && agent.outputSummary
            const showConnector = index < agents.length - 1

            return (
              <div key={agent.id} className="animate-slide-up" style={{ animationDelay: `${index * 80}ms` }}>
                <div
                  className={`
                    flex items-center gap-3 rounded-xl border p-3.5 transition-all duration-500 cursor-pointer group
                    ${agent.status === "running"
                      ? "border-primary/40 bg-gradient-to-r from-primary/10 to-primary/5 shadow-lg shadow-primary/10"
                      : agent.status === "complete"
                        ? "border-emerald-500/30 bg-gradient-to-r from-emerald-500/5 to-transparent hover:from-emerald-500/10"
                        : "border-border/30 bg-muted/10 hover:bg-muted/20"
                    }
                  `}
                  onClick={() => hasDetails && setExpandedAgent(isExpanded ? null : agent.id)}
                >
                  {/* Status icon with ring animation */}
                  <div className="flex-shrink-0 relative">
                    {agent.status === "pending" && <Circle className="size-5 text-muted-foreground/30" />}
                    {agent.status === "running" && agent.outputSummary?.interaction && (
                      <MessageSquare className="size-5 text-amber-400 animate-pulse" />
                    )}
                    {agent.status === "running" && !agent.outputSummary?.interaction && (
                      <>
                        <span className="absolute inset-0 animate-ping rounded-full bg-primary/20" style={{ animationDuration: '2s' }} />
                        <Loader2 className="relative size-5 animate-spin text-primary" />
                      </>
                    )}
                    {agent.status === "complete" && <CheckCircle2 className="size-5 text-emerald-500 animate-scale-in" />}
                    {agent.status === "error" && <AlertCircle className="size-5 text-red-500" />}
                  </div>

                  {/* Agent icon */}
                  <div
                    className={`flex size-9 items-center justify-center rounded-lg transition-all duration-500 ${
                      agent.status === "complete"
                        ? "bg-emerald-500/10 text-emerald-400 shadow-sm shadow-emerald-500/10"
                        : agent.status === "running"
                          ? "bg-primary/10 text-primary shadow-sm shadow-primary/10 animate-pulse"
                          : "bg-muted/50 text-muted-foreground/40"
                    }`}
                  >
                    <Icon className="size-4" />
                  </div>

                  {/* Agent info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className={`text-sm font-medium transition-colors duration-300 ${agent.status === 'pending' ? 'text-muted-foreground/60' : 'text-foreground'}`}>{agent.name}</p>
                      {agent.status === "complete" && agent.outputSummary?.duration != null && (
                        <span className="text-[10px] text-muted-foreground font-mono bg-muted/30 px-1.5 py-0.5 rounded">
                          {agent.outputSummary.duration.toFixed(1)}s
                        </span>
                      )}
                      {agent.status === "running" && agent.outputSummary?.agent_emoji && (
                        <span className="text-xs animate-bounce" title={agent.outputSummary?.agent_persona}>
                          {agent.outputSummary.agent_emoji}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate" title={agent.outputSummary?.message || agent.outputSummary?.thought}>
                      {agent.status === "running"
                        ? (agent.outputSummary?.thought 
                            ? `${agent.outputSummary?.emoji || '🧠'} ${agent.outputSummary.thought.substring(0, 80)}`
                            : agent.outputSummary?.message?.replace(/^[📝🏢🔐⚡🏗️🔗✅🔍📊\s]+/, '') || "Analyzing...")
                        : agent.status === "complete"
                          ? getCompletionSummaryLine(agent)
                          : `Agent ${index + 1} of ${agents.length}`}
                    </p>
                  </div>

                  {/* Running progress indicator */}
                  {agent.status === "running" && (
                    <div className="typing-indicator flex gap-1 text-primary">
                      <span /><span /><span />
                    </div>
                  )}

                  {/* Expand/collapse for completed agents */}
                  {hasDetails && (
                    <button className="text-muted-foreground/50 group-hover:text-foreground transition-all duration-300">
                      {isExpanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                    </button>
                  )}
                </div>

                {/* Expanded agent output details */}
                {isExpanded && hasDetails && (
                  <div className="ml-8 mr-2 mt-1 mb-1 rounded-xl border border-border/20 bg-card/40 backdrop-blur-sm p-3 animate-slide-up">
                    {renderOutputSummary(agent)}
                  </div>
                )}

                {/* Pipeline connector */}
                {showConnector && (
                  <div className="flex justify-center py-0.5">
                    <div className={`w-px h-4 transition-all duration-500 ${
                      agent.status === "complete" 
                        ? "bg-gradient-to-b from-emerald-500/50 to-emerald-500/10" 
                        : "bg-border/20"
                    }`} />
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        {sessionId && (
          <div className="flex items-center justify-between border-t border-border/20 pt-3 text-[10px] text-muted-foreground">
            <span className="font-mono opacity-60">Session: {sessionId.slice(0, 16)}...</span>
            <span className="flex items-center gap-1">
              {completedCount === agents.length ? (
                <><CheckCircle2 className="size-3 text-emerald-500" /> Ready</>
              ) : (
                <><span className="relative flex size-1.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" /><span className="relative inline-flex size-1.5 rounded-full bg-primary" /></span> Live updates</>
              )}
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}

/** One-liner summary for completed agents shown inline */
function getCompletionSummaryLine(agent: Agent): string {
  const s = agent.outputSummary
  if (!s) return "Completed"

  // Use message from backend if available (strips emoji prefix)
  if (s.message) {
    return s.message.replace(/^[✅🔐⚡🏗️🔗📝🏢🔍📊\s]+/, '')
  }

  switch (agent.id) {
    case "components":
      return `${s.apis_found ?? 0} APIs, ${s.nfrs_found ?? 0} NFRs, ${s.tech_stack ?? 0} tech stack → ${s.complexity ?? "?"} complexity`
    case "references":
      return `${s.matched_architectures ?? 0} ref architectures, ${s.recommended_services ?? 0} services recommended`
    case "security":
      return `Score ${s.compliance_score ?? 0}/100, ${s.security_services?.length ?? 0} services, ${s.critical_issues ?? 0} issues`
    case "performance":
      return `Score ${s.performance_score ?? 0}/100, ${s.performance_services?.length ?? 0} services`
    case "architecture":
      return `${s.services_designed ?? 0} services, ${s.connections_created ?? 0} connections — ${s.architecture_pattern ?? "N/A"}`
    case "connection":
      return `${s.total_connections ?? 0} connections, ${s.services_connected ?? 0} services connected`
    case "validation":
      return `Score ${s.validation_score ?? 0}/100 — ${s.validation_status ?? "N/A"}`
    default:
      return "Completed"
  }
}
