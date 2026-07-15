"use client"

import { useEffect, useMemo, useState } from "react"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AgentThinkingLive } from "@/components/agent-thinking-live"
import DiagramEmbed from "@/components/DiagramEmbed"
import { AlertTriangle, Brain, ClipboardList, ExternalLink, GitCompareArrows, Layers3, ShieldAlert, Sparkles } from "lucide-react"
import { getApiUrl, UI_CONFIG } from "@/lib/config"
import { toast } from "@/hooks/use-toast"

type DiagramReference = {
  type: string
  title: string
  path?: string
  status?: string
}

type ImpactConnection = {
  source: string
  target: string
  label?: string
}

type ImpactComponent = {
  id: string
  name: string
  layer: string
  purpose: string
  status: string
  changeStatus?: string
  impactSummary?: string
  changeDescription?: string
  resourceType?: string
  repoFolder?: string
  featureMapping?: string
  deliveredFeatures?: string[]
  matchedDeliveredFeatures?: string[]
  impactReason?: string
  discussionRequired?: boolean
  humanDiscussionRequired?: boolean
  humanDiscussionReason?: string
  diagramReferences?: DiagramReference[]
}

type DetailedImpactRow = {
  component: string
  layer: string
  currentRole: string
  impact: string
  changeNeeded: string
  risk: string
  discussionRequired: string
}

type AnalyzerResult = {
  application: { name: string; environment: string; viewMode: string }
  feature: {
    name: string
    description: string
    changeType: string
    priority: string
    targetRelease?: string
    businessCapability?: string
  }
  existingArchitecture: { components: ImpactComponent[]; connections?: ImpactConnection[] }
  proposedArchitecture: { components: ImpactComponent[]; connections?: ImpactConnection[] }
  systemsSummary?: { impactedSystems?: string[]; newSystems?: string[] }
  applicationReference?: {
    found: boolean
    application_name?: string
    diagram_path?: string
    diagram_title?: string
  }
  architectureDiagramXml?: string | null
  proposedArchitectureDiagramPath?: string
  proposedArchitectureDiagramXml?: string | null
  architectureDiff: { added: string[]; modified: string[]; unchanged: string[]; removed: string[] }
  impactSummary: {
    impactLevel: string
    impactedComponentCount: number
    newComponentCount: number
    apiChangeRequired: boolean
    dataChangeRequired: boolean
    securityReviewRequired: boolean
    discussionRequired: boolean
  }
  detailedImpactTable: DetailedImpactRow[]
  newComponentRecommendations: Array<{
    componentName: string
    componentType: string
    purpose: string
    reasonNeeded: string
    ownerNeeded: string
    deploymentRequired: string
    discussionRequired: string
  }>
  decisionPanel: Array<{
    decision: string
    question: string
    participants: string[]
    priority: string
  }>
  minimalExplanation: {
    whyImpacted: string
    whatChanges: string
    discussionRequired: string
  }
  aiConfidence: {
    confidence: string
    assumptions: string[]
    missingInformation: string[]
    sourceUsed: string[]
  }
  discussionItems: Array<{
    topic: string
    reason: string
    requiredParticipants: string[]
    priority: string
  }>
  legend: Record<string, string>
}

type LiveThought = {
  type: string
  content: string
  timestamp: string
  emoji: string
  agent?: string
  duration_ms?: number
}

type CurrentAgentThought = {
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

type ProgressLog = {
  agent: string
  status: string
  percentage: number
  timestamp: string
  output_summary?: {
    message?: string
    thought?: string
    thought_type?: string
    emoji?: string
    agent_emoji?: string
    agent_persona?: string
    thinking_summary?: {
      thoughts?: Array<{ type: string; content: string; timestamp: string; emoji: string }>
      tool_calls?: Array<{ tool: string; duration_ms: number }>
      messages_sent?: number
    }
  }
}

function statusBadge(changeStatus?: string) {
  if (changeStatus === "New") return "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
  if (changeStatus === "Impacted") return "bg-amber-500/15 text-amber-400 border-amber-500/20"
  if (changeStatus === "Removed") return "bg-rose-500/15 text-rose-400 border-rose-500/20"
  return "bg-muted text-muted-foreground"
}

function riskBadge(risk: string) {
  if (risk === "High") return "destructive"
  if (risk === "Medium") return "secondary"
  return "outline"
}

function toDisplayText(value: unknown): string {
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean") return String(value)
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>
    const named = record.name ?? record.component ?? record.title
    if (typeof named === "string") return named
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return ""
}

function listKey(prefix: string, value: unknown, index: number): string {
  return `${prefix}-${index}-${toDisplayText(value)}`
}

const LAYER_ORDER = ["UI", "API", "Service", "Data", "Integration", "Observability", "Security"]

function layerOrder(layer: string) {
  const index = LAYER_ORDER.indexOf(layer)
  return index === -1 ? LAYER_ORDER.length : index
}

function ArchitectureDiagram({
  title,
  architecture,
}: {
  title: string
  architecture: { components: ImpactComponent[]; connections?: ImpactConnection[] }
}) {
  const grouped = architecture.components.reduce<Record<string, ImpactComponent[]>>((acc, component) => {
    if (!acc[component.layer]) acc[component.layer] = []
    acc[component.layer].push(component)
    return acc
  }, {})

  const componentsById = architecture.components.reduce<Record<string, ImpactComponent>>((acc, c) => {
    acc[c.id] = c
    return acc
  }, {})

  const layers = Object.keys(grouped).sort((a, b) => layerOrder(a) - layerOrder(b))

  return (
    <Card className="p-4">
      <h4 className="font-semibold mb-3">{title}</h4>

      <div className="space-y-3">
        {layers.map((layer, layerIdx) => (
          <div key={`layer-${layerIdx}-${layer}`} className="rounded-lg border border-border/40 bg-card/30 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">{layer} Layer</p>
            <div className="grid md:grid-cols-2 gap-2">
              {grouped[layer].map((component, componentIdx) => (
                <Card key={`component-${layer}-${component.id || component.name}-${componentIdx}`} className="p-3 bg-card/60 border-border/50">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-sm">{component.name}</p>
                      <p className="text-xs text-muted-foreground mt-1">{component.impactSummary || component.purpose}</p>
                      {(component.changeStatus === "Impacted" || component.changeStatus === "New") && (component.changeDescription || component.impactSummary) && (
                        <p className="text-xs mt-2 text-primary/90">
                          Change: {component.changeDescription || component.impactSummary}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge className={statusBadge(component.changeStatus)}>{component.changeStatus || "Existing"}</Badge>
                      {component.humanDiscussionRequired && (
                        <Badge variant="destructive" className="gap-1">
                          <AlertTriangle className="size-3" />
                          Human Discussion
                        </Badge>
                      )}
                    </div>
                  </div>

                  {component.humanDiscussionRequired && component.humanDiscussionReason && (
                    <p className="text-xs text-rose-300 mt-2">{component.humanDiscussionReason}</p>
                  )}

                  {component.diagramReferences && component.diagramReferences.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-[11px] font-medium text-muted-foreground">Next-level references</p>
                      <div className="flex flex-wrap gap-1.5">
                        {component.diagramReferences.map((reference, idx) => (
                          reference.path ? (
                            <a
                              key={`ref-link-${component.id || component.name}-${reference.type}-${reference.path || ""}-${idx}`}
                              href={reference.path}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-border/50 px-2 py-1 text-[10px] text-foreground hover:bg-muted/40"
                            >
                              <ExternalLink className="size-3" />
                              {reference.type}
                            </a>
                          ) : (
                            <span key={`ref-label-${component.id || component.name}-${reference.type}-${idx}`} className="inline-flex items-center rounded-md border border-border/50 px-2 py-1 text-[10px] text-muted-foreground">
                              {reference.type}
                            </span>
                          )
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>

      {(architecture.connections || []).length > 0 && (
        <div className="mt-4 rounded-lg border border-border/40 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">Integration / Data Flow Connections</p>
          <div className="space-y-1">
            {(architecture.connections || []).map((connection, idx) => {
              const source = componentsById[connection.source]?.name || connection.source
              const target = componentsById[connection.target]?.name || connection.target
              return (
                <p key={`${connection.source}-${connection.target}-${idx}`} className="text-xs text-muted-foreground">
                  {source} → {target}{connection.label ? ` (${connection.label})` : ""}
                </p>
              )
            })}
          </div>
        </div>
      )}
    </Card>
  )
}

export function FeatureImpactTab() {
  const [applicationName, setApplicationName] = useState("AgentAssist")
  const [featureName, setFeatureName] = useState("")
  const [featureDescription, setFeatureDescription] = useState("")
  const [businessCapability, setBusinessCapability] = useState("General")
  const [changeType, setChangeType] = useState("New Feature")
  const [priority, setPriority] = useState("Medium")
  const [targetRelease, setTargetRelease] = useState("")

  const [architectureLayer, setArchitectureLayer] = useState("API+Data+Integration")
  const [impactType, setImpactType] = useState("Functional+Security")
  const [environment, setEnvironment] = useState("Prod")
  const [viewMode, setViewMode] = useState("Technical View")
  const [confidenceThreshold, setConfidenceThreshold] = useState("All")

  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeResultTab, setActiveResultTab] = useState("existing")
  const [result, setResult] = useState<AnalyzerResult | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [workflowStatus, setWorkflowStatus] = useState<string>("idle")
  const [progressPct, setProgressPct] = useState(0)
  const [currentAgent, setCurrentAgent] = useState<string | null>(null)
  const [agentLogs, setAgentLogs] = useState<ProgressLog[]>([])
  const [liveThoughts, setLiveThoughts] = useState<LiveThought[]>([])
  const [currentAgentThought, setCurrentAgentThought] = useState<CurrentAgentThought | null>(null)
  const [applicationDiagramXml, setApplicationDiagramXml] = useState<string | null>(null)
  const [applicationDiagramTitle, setApplicationDiagramTitle] = useState<string | null>(null)
  const [applicationDiagramMatched, setApplicationDiagramMatched] = useState(false)
  const [proposedDiagramXmlPreview, setProposedDiagramXmlPreview] = useState<string | null>(null)
  const [isAzureImpactDetailsExpanded, setIsAzureImpactDetailsExpanded] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    const loadProposedDiagram = async () => {
      if (!result) {
        setProposedDiagramXmlPreview(null)
        return
      }

      if (result.proposedArchitectureDiagramXml) {
        setProposedDiagramXmlPreview(result.proposedArchitectureDiagramXml)
        return
      }

      if (!result.proposedArchitectureDiagramPath) {
        setProposedDiagramXmlPreview(null)
        return
      }

      try {
        const response = await fetch(result.proposedArchitectureDiagramPath, { signal: controller.signal })
        if (!response.ok) {
          setProposedDiagramXmlPreview(null)
          return
        }
        const xml = await response.text()
        setProposedDiagramXmlPreview(xml)
      } catch {
        if (!controller.signal.aborted) {
          setProposedDiagramXmlPreview(null)
        }
      }
    }

    loadProposedDiagram()
    return () => controller.abort()
  }, [result])

  useEffect(() => {
    const controller = new AbortController()

    const loadApplicationDiagramFromPublicAssets = async () => {
      const normalizedName = applicationName.trim()
      if (normalizedName.length < 2) {
        setApplicationDiagramXml(null)
        setApplicationDiagramTitle(null)
        setApplicationDiagramMatched(false)
        return
      }

      try {
        const csvResponse = await fetch("/Architecture/applications.csv", { signal: controller.signal })
        if (!csvResponse.ok) {
          setApplicationDiagramXml(null)
          setApplicationDiagramTitle(null)
          setApplicationDiagramMatched(false)
          return
        }

        const csvText = await csvResponse.text()
        const rows = csvText
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean)

        const match = rows
          .slice(1)
          .map((line) => {
            const [name, path, title] = line.split(",")
            return {
              applicationName: name?.trim() || "",
              diagramPath: path?.trim() || "",
              diagramTitle: title?.trim() || "",
            }
          })
          .find((row) => row.applicationName.toLowerCase() === normalizedName.toLowerCase())

        if (!match?.diagramPath) {
          setApplicationDiagramXml(null)
          setApplicationDiagramTitle(null)
          setApplicationDiagramMatched(false)
          return
        }

        const diagramResponse = await fetch(match.diagramPath, { signal: controller.signal })
        if (!diagramResponse.ok) {
          setApplicationDiagramXml(null)
          setApplicationDiagramTitle(null)
          setApplicationDiagramMatched(false)
          return
        }

        const diagramXml = await diagramResponse.text()
        setApplicationDiagramXml(diagramXml)
        setApplicationDiagramTitle(match.diagramTitle || normalizedName)
        setApplicationDiagramMatched(true)
      } catch {
        if (!controller.signal.aborted) {
          setApplicationDiagramXml(null)
          setApplicationDiagramTitle(null)
          setApplicationDiagramMatched(false)
        }
      }
    }

    loadApplicationDiagramFromPublicAssets()
    return () => controller.abort()
  }, [applicationName])

  useEffect(() => {
    if (!sessionId) return
    let isActive = true
    let intervalId: ReturnType<typeof setInterval> | null = null

    const poll = async () => {
      if (!isActive) return
      try {
        const response = await fetch(getApiUrl("PROGRESS", sessionId))
        if (!response.ok) return

        const payload = await response.json()
        setWorkflowStatus(payload.status || "running")
        setProgressPct(payload.progress_percentage || 0)
        setCurrentAgent(payload.current_agent || null)
        setAgentLogs(payload.agent_logs || [])

        const thoughts: LiveThought[] = (payload.live_thoughts || []).map((t: any) => ({
          type: t.type || "reasoning",
          content: t.content || "",
          timestamp: t.timestamp || "",
          emoji: t.emoji || "🧠",
          agent: t.agent ? String(t.agent).replace("Agent", "") : undefined,
        }))
        setLiveThoughts(thoughts)

        const runningLog = (payload.agent_logs || []).find((log: any) => log.agent === payload.current_agent && log.status === "running")
        const s = runningLog?.output_summary
        if (payload.current_agent && s) {
          setCurrentAgentThought({
            agent_name: payload.current_agent,
            agent_emoji: s.agent_emoji || "🤖",
            agent_role: s.agent_persona || String(payload.current_agent).replace("Agent", ""),
            current_thought: s.thought || s.message || "Processing...",
            thought_type: s.thought_type || "reasoning",
            thoughts_count: s.thinking_summary?.thoughts?.length || 0,
            tools_used: s.thinking_summary?.tool_calls?.length || 0,
            messages_sent: s.thinking_summary?.messages_sent || 0,
            elapsed_ms: 0,
          })
        }

        if (payload.status === "completed") {
          const finalResult = payload?.result?.result as AnalyzerResult | undefined
          if (finalResult) {
            setResult(finalResult)
            setActiveResultTab("existing")
            toast({ title: "Analysis complete", description: "Architecture impact generated successfully." })
          }
          setIsAnalyzing(false)
          isActive = false
          if (intervalId) clearInterval(intervalId)
        } else if (payload.status === "error") {
          toast({
            title: "Analysis failed",
            description: payload.error || "Feature impact workflow failed",
            variant: "destructive",
          })
          setIsAnalyzing(false)
          isActive = false
          if (intervalId) clearInterval(intervalId)
        }
      } catch {
        // Ignore transient polling failures.
      }
    }

    poll()
    intervalId = setInterval(poll, UI_CONFIG.PROGRESS.POLL_INTERVAL_MS)

    return () => {
      isActive = false
      if (intervalId) clearInterval(intervalId)
    }
  }, [sessionId])

  const canAnalyze = useMemo(() => {
    return applicationName.trim().length > 1 && featureName.trim().length > 1 && featureDescription.trim().length > 10
  }, [applicationName, featureName, featureDescription])

  const impactedSystems = useMemo(() => {
    if (!result) return []
    if (result.systemsSummary?.impactedSystems?.length) return result.systemsSummary.impactedSystems
    return result.proposedArchitecture.components
      .filter((component) => component.changeStatus === "Impacted")
      .map((component) => component.name)
  }, [result])

  const newSystems = useMemo(() => {
    if (!result) return []
    if (result.systemsSummary?.newSystems?.length) return result.systemsSummary.newSystems
    return result.proposedArchitecture.components
      .filter((component) => component.changeStatus === "New")
      .map((component) => component.name)
  }, [result])

  const discussionComponents = useMemo(() => {
    if (!result) return []
    return result.proposedArchitecture.components.filter((component) => component.humanDiscussionRequired)
  }, [result])

  const impactedAzureComponents = useMemo(() => {
    if (!result) return []
    const components = result.proposedArchitecture.components.filter((component) => (
      component.changeStatus === "Impacted"
      && ["function_app", "web_app", "database"].includes(component.resourceType || "")
    ))
    const order = { function_app: 0, web_app: 1, database: 2 } as Record<string, number>
    return [...components].sort((left, right) => {
      const leftOrder = order[left.resourceType || ""] ?? 99
      const rightOrder = order[right.resourceType || ""] ?? 99
      if (leftOrder !== rightOrder) return leftOrder - rightOrder
      return left.name.localeCompare(right.name)
    })
  }, [result])

  const hasApplicationDiagram = Boolean(applicationDiagramMatched && applicationDiagramXml)

  const handleAnalyze = async () => {
    if (!canAnalyze || isAnalyzing) return
    setIsAnalyzing(true)
    setResult(null)
    setProgressPct(0)
    setCurrentAgent(null)
    setAgentLogs([])
    setLiveThoughts([])
    setCurrentAgentThought(null)
    setWorkflowStatus("queued")

    try {
      const requestBody = {
        application_name: applicationName,
        feature_name: featureName,
        feature_description: featureDescription,
        business_capability: businessCapability,
        change_type: changeType,
        priority,
        target_release: targetRelease || null,
        architecture_layer: architectureLayer.split("+").map((v) => v.trim()),
        impact_type: impactType.split("+").map((v) => v.trim()),
        environment,
        view_mode: viewMode,
        confidence_threshold: confidenceThreshold,
      }

      const response = await fetch(getApiUrl("FEATURE_IMPACT_ANALYZE"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `Request failed with ${response.status}`)
      }

      const payload = await response.json()
      setResult(payload.result as AnalyzerResult)
      setActiveResultTab("existing")
      setWorkflowStatus("completed")
      setSessionId(null)
      setIsAnalyzing(false)
      toast({ title: "Analysis complete", description: "Architecture impact generated successfully." })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      toast({ title: "Analysis failed", description: message, variant: "destructive" })
      setWorkflowStatus("error")
      setSessionId(null)
      setIsAnalyzing(false)
    } finally {
      // keep analyzing state until stream reaches completed/error
    }
  }

  return (
    <ResizablePanelGroup direction="horizontal" className="min-h-[calc(100vh-220px)] rounded-2xl overflow-hidden border border-border/30 bg-card/20 shadow-2xl shadow-black/10 backdrop-blur-sm">
      <ResizablePanel defaultSize={32} minSize={25} maxSize={45}>
        <div className="h-full overflow-y-auto custom-scrollbar bg-gradient-to-b from-card/80 to-card/40 backdrop-blur-xl">
          <Card className="border-0 shadow-none bg-transparent p-5">
            <div className="space-y-5">
              <div className="pb-3 border-b border-border/30">
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <Sparkles className="size-4 text-primary" />
                  Talk to Architecture
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">Understand architecture impact of a new feature before implementation.</p>
              </div>

              <div className="space-y-2">
                <Label>Application Name</Label>
                <Input value={applicationName} onChange={(e) => setApplicationName(e.target.value)} placeholder="AgentAssist" />
              </div>

              <div className="space-y-2">
                <Label>Feature Name</Label>
                <Input value={featureName} onChange={(e) => setFeatureName(e.target.value)} placeholder="Automated Refund Eligibility Check" />
              </div>

              <div className="space-y-2">
                <Label>Feature Description</Label>
                <Textarea
                  value={featureDescription}
                  onChange={(e) => setFeatureDescription(e.target.value)}
                  placeholder="Describe what the feature should do and who uses it"
                  className="min-h-[120px]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Business Capability</Label>
                  <Select value={businessCapability} onValueChange={setBusinessCapability}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="General">General</SelectItem>
                      <SelectItem value="Booking">Booking</SelectItem>
                      <SelectItem value="Payment">Payment</SelectItem>
                      <SelectItem value="Refund">Refund</SelectItem>
                      <SelectItem value="Servicing">Servicing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Change Type</Label>
                  <Select value={changeType} onValueChange={setChangeType}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="New Feature">New Feature</SelectItem>
                      <SelectItem value="Enhancement">Enhancement</SelectItem>
                      <SelectItem value="Integration">Integration</SelectItem>
                      <SelectItem value="Regulatory Change">Regulatory Change</SelectItem>
                      <SelectItem value="Performance Change">Performance Change</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select value={priority} onValueChange={setPriority}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Low">Low</SelectItem>
                      <SelectItem value="Medium">Medium</SelectItem>
                      <SelectItem value="High">High</SelectItem>
                      <SelectItem value="Critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Target Release</Label>
                  <Input value={targetRelease} onChange={(e) => setTargetRelease(e.target.value)} placeholder="2026.Q4" />
                </div>
              </div>

              <div className="pt-2 border-t border-border/30">
                <h3 className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Context Filters</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Architecture Layer</Label>
                    <Select value={architectureLayer} onValueChange={setArchitectureLayer}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UI+API+Service+Data+Integration">All Layers</SelectItem>
                        <SelectItem value="API+Data+Integration">API + Data + Integration</SelectItem>
                        <SelectItem value="Service+Data">Service + Data</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Impact Type</Label>
                    <Select value={impactType} onValueChange={setImpactType}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Functional+Technical+Security+Performance">All</SelectItem>
                        <SelectItem value="Functional+Security">Functional + Security</SelectItem>
                        <SelectItem value="Technical+Performance">Technical + Performance</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Environment</Label>
                    <Select value={environment} onValueChange={setEnvironment}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Dev">Dev</SelectItem>
                        <SelectItem value="Test">Test</SelectItem>
                        <SelectItem value="Pre-prod">Pre-prod</SelectItem>
                        <SelectItem value="Prod">Prod</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>View Mode</Label>
                    <Select value={viewMode} onValueChange={setViewMode}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Business View">Business View</SelectItem>
                        <SelectItem value="Technical View">Technical View</SelectItem>
                        <SelectItem value="Deployment View">Deployment View</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="mt-3 space-y-2">
                  <Label>Confidence Threshold</Label>
                  <Select value={confidenceThreshold} onValueChange={setConfidenceThreshold}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="All">All Possible Impacts</SelectItem>
                      <SelectItem value="High">High Confidence Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button onClick={handleAnalyze} disabled={!canAnalyze || isAnalyzing} className="w-full h-11 font-semibold">
                {isAnalyzing ? "Analyzing Architecture Impact..." : "Analyze Architecture Impact"}
              </Button>
            </div>
          </Card>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle className="bg-border/30" />

      <ResizablePanel defaultSize={68}>
        <div className="h-full overflow-y-auto custom-scrollbar bg-gradient-to-b from-background/80 to-background/40">
          {isAnalyzing && (
            <div className="p-5 pb-0 space-y-4">
              <Card className="p-4 bg-card/60">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h4 className="font-semibold">Feature Impact Agent Execution</h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      {currentAgent ? `Current agent: ${currentAgent}` : "Initializing workflow"} • Status: {workflowStatus}
                    </p>
                  </div>
                  <Badge variant="secondary">{progressPct}%</Badge>
                </div>
                <Progress value={progressPct} className="mt-3" />

                <div className="mt-4 space-y-2">
                  {agentLogs.map((log) => (
                    <div key={`${log.agent}-${log.status}-${log.timestamp}`} className="flex items-center justify-between text-xs rounded-md border border-border/40 px-2.5 py-2">
                      <div>
                        <p className="font-medium">{log.agent}</p>
                        <p className="text-muted-foreground">{log.output_summary?.message || log.status}</p>
                      </div>
                      <Badge variant={log.status === "completed" ? "secondary" : "outline"}>{log.status}</Badge>
                    </div>
                  ))}
                </div>
              </Card>

              <AgentThinkingLive
                thoughts={liveThoughts}
                currentAgent={currentAgentThought}
                isProcessing={isAnalyzing}
              />
            </div>
          )}

          {!result ? (
            <div className="h-full flex items-center justify-center p-8">
              <Card className="max-w-2xl w-full p-8 text-center border-dashed border-border/60 bg-card/40">
                <Layers3 className="size-10 mx-auto mb-4 text-primary/70" />
                <h3 className="text-lg font-semibold">Architecture Impact Advisor</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Provide application and feature details, then run analysis to compare existing vs proposed architecture,
                  highlight impacted components, and surface discussion-required decisions.
                </p>
              </Card>
            </div>
          ) : (
            <div className="p-5 space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold">{result.feature.name} Impact Analysis</h3>
                  <p className="text-sm text-muted-foreground">Application: {result.application.name} • {result.application.environment} • {result.application.viewMode}</p>
                </div>
                <Badge variant={result.impactSummary.discussionRequired ? "destructive" : "secondary"}>
                  {result.impactSummary.discussionRequired ? "Discussion Required" : "No Discussion Required"}
                </Badge>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="p-3"><p className="text-xs text-muted-foreground">Impact Level</p><p className="text-base font-semibold">{result.impactSummary.impactLevel}</p></Card>
                <Card className="p-3"><p className="text-xs text-muted-foreground">Impacted Components</p><p className="text-base font-semibold">{result.impactSummary.impactedComponentCount}</p></Card>
                <Card className="p-3"><p className="text-xs text-muted-foreground">New Components</p><p className="text-base font-semibold">{result.impactSummary.newComponentCount}</p></Card>
                <Card className="p-3"><p className="text-xs text-muted-foreground">Security Review</p><p className="text-base font-semibold">{result.impactSummary.securityReviewRequired ? "Required" : "No"}</p></Card>
              </div>

              <Card className="p-4 border-amber-500/20 bg-amber-500/5">
                <h4 className="font-semibold mb-3">Impacted Components</h4>
                <div className="flex flex-wrap gap-2">
                  {impactedSystems.length > 0 ? impactedSystems.map((component, idx) => (
                    <Badge key={`impacted-top-${idx}-${component}`} className="bg-amber-500/15 text-amber-400 border-amber-500/20">
                      {component}
                    </Badge>
                  )) : (
                    <span className="text-sm text-muted-foreground">No impacted components returned.</span>
                  )}
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <h4 className="font-semibold">Azure Component Impact Details</h4>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsAzureImpactDetailsExpanded((prev) => !prev)}
                    className="h-8 px-2 text-xs"
                  >
                    {isAzureImpactDetailsExpanded ? "Collapse" : "Expand"}
                  </Button>
                </div>
                {isAzureImpactDetailsExpanded && (
                  <div className="space-y-3">
                    {impactedAzureComponents.length > 0 ? impactedAzureComponents.map((component, idx) => (
                      <div key={`azure-impact-${component.id || component.name}-${idx}`} className="rounded-md border border-border/40 bg-card/40 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium">{component.name}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {(component.resourceType || component.layer).replaceAll("_", " ")} • {component.purpose}
                            </p>
                            {component.repoFolder && (
                              <p className="text-xs text-muted-foreground mt-1">Repository: {component.repoFolder}</p>
                            )}

                          </div>
                          <Badge className={statusBadge(component.changeStatus)}>{component.changeStatus}</Badge>
                        </div>
                        {component.impactReason && (
                          <p className="text-xs text-muted-foreground mt-2">{component.impactReason}</p>
                        )}
                        <p className="text-sm mt-2">{component.changeDescription || component.impactSummary || "Change details pending."}</p>
                      </div>
                    )) : (
                      <p className="text-sm text-muted-foreground">Azure component-level impacted names are not available yet.</p>
                    )}
                  </div>
                )}
              </Card>

              <Tabs value={activeResultTab} onValueChange={setActiveResultTab}>
                <TabsList className="grid grid-cols-5 h-11">
                  <TabsTrigger value="existing">Existing Architecture</TabsTrigger>
                  <TabsTrigger value="proposed">New Architecture</TabsTrigger>
                  <TabsTrigger value="summary">Impact Summary</TabsTrigger>
                  <TabsTrigger value="discussion">Discussion Items</TabsTrigger>
                  <TabsTrigger value="confidence">AI Confidence</TabsTrigger>
                </TabsList>

                <TabsContent value="existing" className="mt-4 space-y-4">
                  {/* Architecture diagram preview from public/Architecture assets */}
                  {hasApplicationDiagram && (
                    <Card className="p-4">
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <h4 className="font-semibold">Existing Architecture Diagram</h4>
                          <p className="text-xs text-muted-foreground mt-1">
                            {applicationDiagramTitle || applicationName.trim()} — source from Architecture folder
                          </p>
                        </div>
                        <Badge variant="secondary">Matched</Badge>
                      </div>
                      <DiagramEmbed xml={applicationDiagramXml} />
                    </Card>
                  )}

                  {/* Summary of impacted and new systems derived from the analysis */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <Card className="p-4">
                      <p className="text-xs uppercase tracking-wide text-amber-400 mb-2">Impacted Systems</p>
                      <ul className="space-y-1 text-sm text-muted-foreground">
                        {impactedSystems.length > 0
                          ? impactedSystems.map((s) => <li key={s}>• {s}</li>)
                          : <li className="text-muted-foreground/50">None identified</li>}
                      </ul>
                    </Card>
                    <Card className="p-4">
                      <p className="text-xs uppercase tracking-wide text-emerald-400 mb-2">New Systems</p>
                      <ul className="space-y-1 text-sm text-muted-foreground">
                        {newSystems.length > 0
                          ? newSystems.map((s) => <li key={s}>• {s}</li>)
                          : <li className="text-muted-foreground/50">None planned</li>}
                      </ul>
                    </Card>
                  </div>

                  {/* Component-level architecture breakdown from analysis result */}
                  <ArchitectureDiagram title="Existing Architecture — Component View" architecture={result.existingArchitecture} />
                </TabsContent>

                <TabsContent value="proposed" className="mt-4 space-y-4">
                  {proposedDiagramXmlPreview && (
                    <Card className="p-4">
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <h4 className="font-semibold">New Architecture Diagram</h4>
                          <p className="text-xs text-muted-foreground mt-1">
                            Generated proposed drawio with impacted components highlighted and new components added
                          </p>
                        </div>
                        <Badge variant="secondary">Generated</Badge>
                      </div>
                      <DiagramEmbed xml={proposedDiagramXmlPreview} />
                    </Card>
                  )}

                  <ArchitectureDiagram title="Updated Architecture Diagram (Impacted + New Highlighted)" architecture={result.proposedArchitecture} />

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">Change Description (New + Impacted Components)</h4>
                    <div className="space-y-2">
                      {result.proposedArchitecture.components
                        .filter((component) => component.changeStatus === "New" || component.changeStatus === "Impacted")
                        .map((component) => (
                          <div key={`change-desc-${component.id}`} className="rounded-md border border-border/40 bg-card/40 p-3">
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-sm font-medium">{component.name}</p>
                              <Badge className={statusBadge(component.changeStatus)}>{component.changeStatus}</Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">{component.layer} Layer</p>
                            <p className="text-sm mt-2">{component.changeDescription || component.impactSummary || "Change details pending."}</p>
                          </div>
                        ))}
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">New And Impacted Systems Below Diagram</h4>
                    <div className="grid md:grid-cols-2 gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-amber-400">Impacted Systems</p>
                        <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                          {impactedSystems.length > 0 ? impactedSystems.map((system) => <li key={system}>• {system}</li>) : <li>• None</li>}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-emerald-400">New Systems</p>
                        <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                          {newSystems.length > 0 ? newSystems.map((system) => <li key={system}>• {system}</li>) : <li>• None</li>}
                        </ul>
                      </div>
                    </div>
                  </Card>

                  {hasApplicationDiagram && (
                    <Card className="p-4">
                      <h4 className="font-semibold mb-3">Application Architecture Reference</h4>
                      <div className="grid md:grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Application</p>
                          <p className="mt-1 font-medium">{applicationName.trim()}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Diagram File</p>
                          <p className="mt-1 font-medium">Knowledgebase/AgentAssist-Architecture-Production.drawio</p>
                        </div>
                      </div>
                    </Card>
                  )}

                  <Card className="p-4 border-rose-500/30 bg-rose-500/5">
                    <h4 className="font-semibold mb-3 flex items-center gap-2">
                      <AlertTriangle className="size-4 text-rose-400" />
                      Parts Requiring Human Discussion
                    </h4>
                    <div className="space-y-2">
                      {discussionComponents.length > 0 ? discussionComponents.map((component) => (
                        <div key={`discussion-${component.id}`} className="rounded-md border border-rose-400/20 bg-background/60 p-2.5">
                          <p className="text-sm font-medium">{component.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{component.humanDiscussionReason || "Architecture alignment required."}</p>
                        </div>
                      )) : (
                        <p className="text-sm text-muted-foreground">No component-level human discussion is currently flagged.</p>
                      )}
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3 flex items-center gap-2"><GitCompareArrows className="size-4" /> Architecture Diff</h4>
                    <div className="grid md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="font-medium text-emerald-400">Added</p>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {result.architectureDiff.added.map((item, idx) => (
                            <li key={listKey("diff-added", item, idx)}>• {toDisplayText(item)}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="font-medium text-amber-400">Modified</p>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {result.architectureDiff.modified.map((item, idx) => (
                            <li key={listKey("diff-modified", item, idx)}>• {toDisplayText(item)}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </Card>
                </TabsContent>

                <TabsContent value="summary" className="mt-4 space-y-4">
                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">Detailed Impact Table</h4>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Component</TableHead>
                            <TableHead>Layer</TableHead>
                            <TableHead>Impact</TableHead>
                            <TableHead>Change Needed</TableHead>
                            <TableHead>Risk</TableHead>
                            <TableHead>Discussion</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {result.detailedImpactTable.map((row) => (
                            <TableRow key={`${row.component}-${row.layer}`}>
                              <TableCell className="font-medium">{row.component}</TableCell>
                              <TableCell>{row.layer}</TableCell>
                              <TableCell>{row.impact}</TableCell>
                              <TableCell>{row.changeNeeded}</TableCell>
                              <TableCell><Badge variant={riskBadge(row.risk)}>{row.risk}</Badge></TableCell>
                              <TableCell>{row.discussionRequired}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">New Component Recommendations</h4>
                    <div className="space-y-3">
                      {result.newComponentRecommendations.map((item) => (
                        <Card key={item.componentName} className="p-3 bg-card/50">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium text-sm">{item.componentName}</p>
                              <p className="text-xs text-muted-foreground mt-1">{item.componentType} • {item.purpose}</p>
                              <p className="text-xs text-muted-foreground mt-1">Reason: {item.reasonNeeded}</p>
                            </div>
                            <Badge variant="destructive">Discussion Required</Badge>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">Minimal Explanation</h4>
                    <div className="space-y-2 text-sm">
                      <p><span className="font-semibold">Why impacted?</span> {result.minimalExplanation.whyImpacted}</p>
                      <p><span className="font-semibold">What changes?</span> {result.minimalExplanation.whatChanges}</p>
                      <p><span className="font-semibold">Discussion required?</span> {result.minimalExplanation.discussionRequired}</p>
                    </div>
                  </Card>
                </TabsContent>

                <TabsContent value="discussion" className="mt-4 space-y-4">
                  <Card className="p-4">
                    <h4 className="font-semibold mb-3 flex items-center gap-2"><ClipboardList className="size-4" /> Discussion Required Items</h4>
                    <div className="space-y-3">
                      {result.discussionItems.map((item) => (
                        <Card key={item.topic} className="p-3 border-purple-500/30 bg-purple-500/5">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium text-sm">{item.topic}</p>
                              <p className="text-xs text-muted-foreground mt-1">{item.reason}</p>
                              <p className="text-xs mt-2 text-muted-foreground">
                                Participants: {Array.isArray(item.requiredParticipants) && item.requiredParticipants.length > 0 ? item.requiredParticipants.join(", ") : "TBD"}
                              </p>
                            </div>
                            <Badge variant={item.priority === "High" ? "destructive" : "secondary"}>{item.priority}</Badge>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">Architecture Decision Panel</h4>
                    <div className="space-y-3">
                      {result.decisionPanel.map((item) => (
                        <Card key={item.decision} className="p-3 bg-card/50">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-medium text-sm">{item.decision}</p>
                            <Badge variant={item.priority === "High" ? "destructive" : "secondary"}>{item.priority}</Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">{item.question}</p>
                          <p className="text-xs text-muted-foreground mt-2">
                            Participants: {Array.isArray(item.participants) && item.participants.length > 0 ? item.participants.join(", ") : "TBD"}
                          </p>
                        </Card>
                      ))}
                    </div>
                  </Card>
                </TabsContent>

                <TabsContent value="confidence" className="mt-4 space-y-4">
                  <Card className="p-4">
                    <h4 className="font-semibold mb-3 flex items-center gap-2"><Brain className="size-4" /> AI Confidence & Assumptions</h4>
                    <div className="grid md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="font-semibold">Confidence</p>
                        <p className="text-muted-foreground mt-1">{result.aiConfidence.confidence}</p>

                        <p className="font-semibold mt-4">Assumptions</p>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {result.aiConfidence.assumptions.map((item, idx) => (
                            <li key={listKey("assumption", item, idx)}>• {toDisplayText(item)}</li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <p className="font-semibold">Missing Information</p>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {result.aiConfidence.missingInformation.map((item, idx) => (
                            <li key={listKey("missing", item, idx)}>• {toDisplayText(item)}</li>
                          ))}
                        </ul>

                        <p className="font-semibold mt-4">Source Used</p>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {result.aiConfidence.sourceUsed.map((item, idx) => (
                            <li key={listKey("source", item, idx)}>• {toDisplayText(item)}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h4 className="font-semibold mb-3">Visual Legend</h4>
                    <div className="grid md:grid-cols-3 gap-2 text-xs">
                      <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-zinc-400" /> Existing unchanged</div>
                      <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-amber-400" /> Existing impacted</div>
                      <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-emerald-400" /> New component</div>
                      <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-rose-400" /> Removed/replaced</div>
                      <div className="flex items-center gap-2"><AlertTriangle className="size-3 text-purple-400" /> Discussion required</div>
                      <div className="flex items-center gap-2"><ShieldAlert className="size-3 text-rose-400" /> High risk/security</div>
                    </div>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
