"use client"

import { useEffect, useRef, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { RefreshCw, Eye, Sparkles, Check, X, ChevronDown, AlertTriangle, Wrench, Network, Shield } from "lucide-react"
import DiagramEmbed, { type DiagramEmbedHandle } from "@/components/DiagramEmbed"
import { API_CONFIG } from "@/lib/config"
import { toast } from "@/hooks/use-toast"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

type DiagramOption = {
  id: string
  name: string
  filename: string
  relative_path: string
}

type ReviewResult = {
  review_status?: string
  overall_score?: number
  critical_issues?: Array<{
    issue?: string
    category?: string
    severity?: string
    impact?: string
    resolution?: string
  }>
  correction_tasks?: Array<{
    task_id?: string
    priority?: string
    description?: string
    target_agent?: string
  }>
  connection_review?: {
    missing_connections?: Array<{ source?: string; target?: string; reason?: string }>
    orphan_services?: string[]
  }
  service_review?: {
    missing_services?: Array<{ service?: string; reason?: string; priority?: string }>
    redundant_services?: Array<{ service?: string; reason?: string }>
  }
  flow_review?: {
    bottlenecks?: Array<{ description?: string; impact?: string }>
    single_points_of_failure?: Array<{ description?: string; impact?: string }>
  }
  waf_pillar_scores?: Record<string, { score?: number; issues?: Array<{ description?: string; impact?: string; recommendations?: string[] }> }>
}

const priorityRank: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

function getPriorityRank(priority?: string): number {
  return priorityRank[(priority || "").toLowerCase()] ?? 99
}

function getSeverityClass(value?: string): string {
  const v = (value || "").toLowerCase()
  if (v === "critical") return "bg-red-100 text-red-700 border-red-200"
  if (v === "high") return "bg-orange-100 text-orange-700 border-orange-200"
  if (v === "medium") return "bg-amber-100 text-amber-700 border-amber-200"
  if (v === "low") return "bg-emerald-100 text-emerald-700 border-emerald-200"
  return "bg-muted text-muted-foreground border-border"
}

export function UpdateTab() {
  const diagramEmbedRef = useRef<DiagramEmbedHandle | null>(null)
  const [updateRequest, setUpdateRequest] = useState("")
  const [architectures, setArchitectures] = useState<DiagramOption[]>([])
  const [selectedArchitecture, setSelectedArchitecture] = useState("")
  const [lockId, setLockId] = useState("")
  const [previewXml, setPreviewXml] = useState<string | null>(null)
  const [hasStagedChanges, setHasStagedChanges] = useState(false)
  const [isLoadingDiagrams, setIsLoadingDiagrams] = useState(false)
  const [isLocking, setIsLocking] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApplyingDecision, setIsApplyingDecision] = useState(false)
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)

  const isSelectionLocked = Boolean(lockId)

  useEffect(() => {
    const fetchDiagrams = async () => {
      setIsLoadingDiagrams(true)
      try {
        const response = await fetch(
          `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_FILES}`,
        )
        if (!response.ok) {
          throw new Error(`Failed to load diagrams (${response.status})`)
        }
        const result = await response.json()
        setArchitectures(Array.isArray(result.diagrams) ? result.diagrams : [])
      } catch (error: any) {
        toast({
          title: "Unable to load diagrams",
          description: error?.message || "Check backend availability and configured diagram folder.",
        })
      } finally {
        setIsLoadingDiagrams(false)
      }
    }

    fetchDiagrams()
  }, [])

  const handleArchitectureSelect = async (diagramId: string) => {
    setSelectedArchitecture(diagramId)
    setPreviewXml(null)
    setHasStagedChanges(false)
    setIsLocking(true)

    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_LOCK}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ diagram_id: diagramId }),
        },
      )

      if (!response.ok) {
        throw new Error(`Failed to lock diagram (${response.status})`)
      }

      const result = await response.json()
      setLockId(result.lock_id || "")
      setPreviewXml(result.preview_xml || null)

      toast({
        title: "Diagram locked",
        description: "The selected diagram path is now locked for this update session.",
      })
    } catch (error: any) {
      setSelectedArchitecture("")
      setLockId("")
      setPreviewXml(null)
      toast({
        title: "Failed to lock diagram",
        description: error?.message || "Please try selecting the architecture again.",
      })
    } finally {
      setIsLocking(false)
    }
  }

  const handleGenerate = async () => {
    if (!lockId || !updateRequest.trim()) {
      return
    }

    setIsGenerating(true)
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-diagram-lock-id": lockId,
          },
          body: JSON.stringify({
            modification_prompt: updateRequest,
          }),
        },
      )

      if (!response.ok) {
        throw new Error(`Update failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || null)
      setHasStagedChanges(Boolean(result.staged))
      setReviewResult(result.review_result || null)

      toast({
        title: "Update generated",
        description: "Preview updated. Accept to persist, reject to discard.",
      })
    } catch (error: any) {
      toast({
        title: "Update failed",
        description: error?.message || "Unable to generate architecture update.",
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleAccept = async () => {
    if (!lockId) return
    setIsApplyingDecision(true)
    try {
      const manualXml = await diagramEmbedRef.current?.exportCurrentXml()
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_ACCEPT}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            lock_id: lockId,
            manual_xml: manualXml || undefined,
          }),
        },
      )

      if (!response.ok) {
        throw new Error(`Accept failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || previewXml)
      setHasStagedChanges(false)
      setLockId("")

      toast({
        title: "Changes accepted",
        description: "Diagram has been updated and saved.",
      })
    } catch (error: any) {
      toast({
        title: "Accept failed",
        description: error?.message || "Unable to persist staged changes.",
      })
    } finally {
      setIsApplyingDecision(false)
    }
  }

  const handleReject = async () => {
    if (!lockId) return
    setIsApplyingDecision(true)
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_REJECT}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ lock_id: lockId }),
        },
      )

      if (!response.ok) {
        throw new Error(`Reject failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || null)
      setHasStagedChanges(false)
      setLockId("")

      toast({
        title: "Changes rejected",
        description: "Staged update discarded and original diagram restored.",
      })
    } catch (error: any) {
      toast({
        title: "Reject failed",
        description: error?.message || "Unable to reject staged changes.",
      })
    } finally {
      setIsApplyingDecision(false)
    }
  }

  const criticalIssues = reviewResult?.critical_issues || []
  const correctionTasks = [...(reviewResult?.correction_tasks || [])].sort(
    (a, b) => getPriorityRank(a.priority) - getPriorityRank(b.priority),
  )
  const missingConnections = reviewResult?.connection_review?.missing_connections || []
  const orphanServices = reviewResult?.connection_review?.orphan_services || []
  const missingServices = reviewResult?.service_review?.missing_services || []
  const redundantServices = reviewResult?.service_review?.redundant_services || []
  const bottlenecks = reviewResult?.flow_review?.bottlenecks || []
  const spofs = reviewResult?.flow_review?.single_points_of_failure || []
  const pillarEntries = Object.entries(reviewResult?.waf_pillar_scores || {})

  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="h-[calc(100vh-220px)] rounded-2xl overflow-hidden border border-border/30 bg-card/20 shadow-2xl shadow-black/10 backdrop-blur-sm"
    >
      {/* LEFT PANEL */}
      <ResizablePanel defaultSize={32} minSize={25}>
        <div className="h-full bg-gradient-to-b from-card/80 to-card/40 p-5">
          <Card className="border-0 shadow-none bg-transparent">
            <div className="space-y-6">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <RefreshCw className="size-4 text-primary" />
                  Update Architecture
                </h2>

                <p className="text-xs text-muted-foreground mt-1">
                  Select an architecture and provide update requirements
                </p>
              </div>

              {/* Architecture Dropdown */}
              <div className="space-y-2">
                <Label>Select Architecture</Label>

                <Select
                  value={selectedArchitecture}
                  onValueChange={handleArchitectureSelect}
                  disabled={isSelectionLocked || isLocking || isGenerating || isApplyingDecision}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingDiagrams ? "Loading diagrams..." : "Choose architecture"} />
                  </SelectTrigger>

                  <SelectContent>
                    {architectures.map((diagram) => (
                      <SelectItem key={diagram.id} value={diagram.id}>
                        {diagram.filename}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {isSelectionLocked && (
                  <p className="text-[11px] text-muted-foreground">
                    Diagram path is locked for this session until you Accept or Reject.
                  </p>
                )}
              </div>

              {/* Update Request */}
              <div className="space-y-2">
                <Label>Update Requirements</Label>

                <Textarea
                  placeholder="Example: Add Azure Front Door, WAF, and Azure Monitor to the existing architecture..."
                  value={updateRequest}
                  onChange={(e) => setUpdateRequest(e.target.value)}
                  className="min-h-[300px]"
                />
              </div>

              {/* Generate Button */}
              <Button
                className="w-full gap-2"
                size="lg"
                onClick={handleGenerate}
                disabled={
                  !lockId ||
                  !updateRequest.trim() ||
                  isGenerating ||
                  isApplyingDecision
                }
              >
                <Sparkles className="size-4" />

                {isGenerating
                  ? "Updating Architecture..."
                  : "Generate Update"}
              </Button>
            </div>

            {hasStagedChanges && (
              <Card className="p-4 border-primary/20 bg-primary/5">
                <div className="flex gap-3">
                  <Button
                    className="flex-1 gap-2"
                    onClick={handleAccept}
                    disabled={isApplyingDecision || isGenerating}
                  >
                    <Check className="size-4" />
                    Accept Change
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 gap-2"
                    onClick={handleReject}
                    disabled={isApplyingDecision || isGenerating}
                  >
                    <X className="size-4" />
                    Reject Change
                  </Button>
                </div>
              </Card>
            )}
          </Card>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* RIGHT PANEL */}
      <ResizablePanel defaultSize={68}>
        <div className="h-full overflow-y-auto p-5">
          <div className="space-y-4">
            <div className="pb-3 border-b border-border/30">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Eye className="size-4 text-primary" />
                Architecture Preview
              </h2>

              <p className="text-xs text-muted-foreground mt-1">
                Selected diagram preview and staged updates appear here
              </p>
            </div>

            {!previewXml && !isGenerating && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
                <div className="flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 border border-border/30">
                  <Sparkles className="size-8 text-primary/40" />
                </div>

                <div className="text-center">
                  <h3 className="text-lg font-semibold">
                    Ready to Preview
                  </h3>

                  <p className="text-sm text-muted-foreground mt-2">
                    Select an architecture file to preview it here,
                    then provide update requirements.
                  </p>
                </div>
              </div>
            )}

            {isGenerating && (
              <Card className="p-10 text-center">
                <RefreshCw className="size-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="font-medium">
                  Updating Architecture...
                </p>
              </Card>
            )}

            {previewXml && !isGenerating && (
              <Card className="p-4">
                <DiagramEmbed ref={diagramEmbedRef} xml={previewXml} />
              </Card>
            )}

            {reviewResult && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Collapsible>
                  <Card className="p-4 border-border/50 bg-gradient-to-br from-card to-muted/20 shadow-sm transition-all duration-300 hover:shadow-md">
                    <CollapsibleTrigger className="group w-full text-left rounded-md transition-colors hover:bg-muted/30 px-1 py-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Critical Issues</p>
                          <h3 className="font-semibold flex items-center gap-2 mt-0.5">
                            <span className="inline-flex size-6 items-center justify-center rounded-md bg-amber-100/70">
                              <AlertTriangle className="size-3.5 text-amber-600" />
                            </span>
                            {criticalIssues.length} issue(s)
                          </h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {criticalIssues[0]?.issue || "No critical issues reported."}
                          </p>
                        </div>
                        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-300 group-data-[state=open]:rotate-180" />
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="overflow-hidden will-change-[height,opacity] data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                      <div className="mt-3 space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
                        {criticalIssues.map((issue, idx) => (
                          <div key={`critical-${idx}`} className="rounded-md border border-border/40 p-3">
                            <p className="text-sm font-medium">{issue.issue || "Issue"}</p>
                            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                              <span>{issue.category || "Category"}</span>
                              <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium ${getSeverityClass(issue.severity)}`}>
                                {issue.severity || "Severity"}
                              </span>
                            </p>
                            {issue.impact && <p className="text-xs mt-1">Impact: {issue.impact}</p>}
                            {issue.resolution && <p className="text-xs mt-1">Fix: {issue.resolution}</p>}
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>

                <Collapsible>
                  <Card className="p-4 border-border/50 bg-gradient-to-br from-card to-muted/20 shadow-sm transition-all duration-300 hover:shadow-md">
                    <CollapsibleTrigger className="group w-full text-left rounded-md transition-colors hover:bg-muted/30 px-1 py-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Corrective Measures</p>
                          <h3 className="font-semibold flex items-center gap-2 mt-0.5">
                            <span className="inline-flex size-6 items-center justify-center rounded-md bg-emerald-100/70">
                              <Wrench className="size-3.5 text-emerald-600" />
                            </span>
                            {correctionTasks.length} task(s)
                          </h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {correctionTasks[0]?.description || "No corrective tasks generated."}
                          </p>
                        </div>
                        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-300 group-data-[state=open]:rotate-180" />
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="overflow-hidden will-change-[height,opacity] data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                      <div className="mt-3 space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
                        {correctionTasks.map((task, idx) => (
                          <div key={`task-${idx}`} className="rounded-md border border-border/40 p-3">
                            <p className="text-sm font-medium">{task.description || "Correction task"}</p>
                            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                              <span>{task.task_id || "Task"}</span>
                              <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium ${getSeverityClass(task.priority)}`}>
                                {task.priority || "Priority"}
                              </span>
                              <span>{task.target_agent || "Agent"}</span>
                            </p>
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>

                <Collapsible>
                  <Card className="p-4 border-border/50 bg-gradient-to-br from-card to-muted/20 shadow-sm transition-all duration-300 hover:shadow-md">
                    <CollapsibleTrigger className="group w-full text-left rounded-md transition-colors hover:bg-muted/30 px-1 py-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Architecture Quality Gaps</p>
                          <h3 className="font-semibold flex items-center gap-2 mt-0.5">
                            <span className="inline-flex size-6 items-center justify-center rounded-md bg-sky-100/70">
                              <Network className="size-3.5 text-sky-600" />
                            </span>
                            {missingConnections.length + missingServices.length + orphanServices.length} gap(s)
                          </h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            Missing services: {missingServices.length}, missing links: {missingConnections.length}, orphan: {orphanServices.length}
                          </p>
                        </div>
                        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-300 group-data-[state=open]:rotate-180" />
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="overflow-hidden will-change-[height,opacity] data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                      <div className="mt-3 space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
                        {missingServices.map((svc, idx) => (
                          <div key={`missing-svc-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            Missing service: {svc.service || "Unknown"} ({svc.priority || "Priority"})
                            {svc.reason ? ` — ${svc.reason}` : ""}
                          </div>
                        ))}
                        {missingConnections.map((conn, idx) => (
                          <div key={`missing-conn-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            Missing connection: {conn.source || "Source"} → {conn.target || "Target"}
                            {conn.reason ? ` — ${conn.reason}` : ""}
                          </div>
                        ))}
                        {orphanServices.map((svc, idx) => (
                          <div key={`orphan-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            Orphan service: {svc}
                          </div>
                        ))}
                        {redundantServices.map((svc, idx) => (
                          <div key={`redundant-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            Redundant service: {svc.service || "Unknown"}
                            {svc.reason ? ` — ${svc.reason}` : ""}
                          </div>
                        ))}
                        {bottlenecks.map((b, idx) => (
                          <div key={`bottleneck-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            Bottleneck: {b.description || "Unknown"}
                            {b.impact ? ` — ${b.impact}` : ""}
                          </div>
                        ))}
                        {spofs.map((s, idx) => (
                          <div key={`spof-${idx}`} className="rounded-md border border-border/40 p-3 text-xs">
                            SPOF: {s.description || "Unknown"}
                            {s.impact ? ` — ${s.impact}` : ""}
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>

                <Collapsible>
                  <Card className="p-4 border-border/50 bg-gradient-to-br from-card to-muted/20 shadow-sm transition-all duration-300 hover:shadow-md">
                    <CollapsibleTrigger className="group w-full text-left rounded-md transition-colors hover:bg-muted/30 px-1 py-1">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Well-Architected Pillars</p>
                          <h3 className="font-semibold flex items-center gap-2 mt-0.5">
                            <span className="inline-flex size-6 items-center justify-center rounded-md bg-violet-100/70">
                              <Shield className="size-3.5 text-violet-600" />
                            </span>
                            {pillarEntries.length} pillar(s)
                          </h3>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {pillarEntries.slice(0, 2).map(([name, data]) => `${name}: ${data?.score ?? 0}`).join(" • ") || "No pillar scores available."}
                          </p>
                        </div>
                        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-300 group-data-[state=open]:rotate-180" />
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="overflow-hidden will-change-[height,opacity] data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                      <div className="mt-3 space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
                        {pillarEntries.map(([name, data]) => (
                          <div key={name} className="rounded-md border border-border/40 p-3">
                            <p className="text-sm font-medium capitalize">{name.replace(/_/g, " ")}</p>
                            <p className="text-xs text-muted-foreground mt-1">Score: {data?.score ?? 0}</p>
                            <div className="mt-2 space-y-2">
                              {(data?.issues || []).slice(0, 5).map((issue, idx) => (
                                <div key={`${name}-issue-${idx}`} className="text-xs rounded bg-muted/40 p-2">
                                  <p>{issue.description || "Issue"}</p>
                                  {issue.recommendations?.[0] && (
                                    <p className="text-muted-foreground mt-1">Fix: {issue.recommendations[0]}</p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              </div>
            )}
          </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}