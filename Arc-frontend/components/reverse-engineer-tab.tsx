"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  GitBranch,
  FileArchive,
  Shield,
  FileCode,
  Image as ImageIcon,
  FileText,
  Upload,
  Download,
  Server,
  ArrowRight,
  CheckCircle2,
  Copy,
  Loader2,
  BookOpen,
  Sparkles,
  Network,
  Eye,
  AlertTriangle,
} from "lucide-react"
import { DiffViewer } from "@/components/diff-viewer"
import { ArchitectureStory } from "@/components/architecture-story"
import DiagramEmbed from "@/components/DiagramEmbed"
import { getApiUrl, UI_CONFIG, APP_CONFIG } from "@/lib/config"

type SourceType = "drawio" | "visio" | "image" | "bicep" | "terraform"

// ─── Matches actual backend _build_response shape ───
interface BackendResponse {
  status: string
  source_type: string
  source_filename?: string
  architecture: {
    services: Array<{ name: string; type: string; category: string }>
    connections: Array<{ source: string; target: string; label: string; connection_type?: string; type?: string }>
    architecture_pattern?: string
    complexity?: string
    requirements_inferred?: string
    resource_groups?: any[]
  }
  drawio_xml?: string
  requirements_analysis?: {
    score?: number | null
    missing_requirements?: string[]
    covered_requirements?: string[]
    deviations?: string[]
    requirements_source?: string
    applied_requirements?: string
  }
  ai_enhancement: {
    well_architected_scores?: Record<string, number>
    missing_services?: string[]
    missing_connections?: Array<{ from?: string; to?: string; label?: string }>
    security_assessment?: string
    performance_assessment?: string
    recommendations?: string[]
    inferred_requirements?: string
    architecture_pattern?: string
  }
  summary: {
    total_services: number
    total_connections: number
    architecture_pattern?: string
    complexity?: string
    inferred_requirements?: string
    categories: Record<string, number>
  }
  timestamp?: string
}

function buildFallbackDeviations(result: BackendResponse | null): string[] {
  if (!result) return []

  const missingServices = (result.ai_enhancement?.missing_services || []).map(
    (service) => `Missing enterprise baseline service: ${service}`,
  )
  const missingConnections = (result.ai_enhancement?.missing_connections || []).map((connection) => {
    const source = connection.from || "Unknown source"
    const target = connection.to || "Unknown target"
    const label = connection.label ? ` (${connection.label})` : ""
    return `Missing recommended connection: ${source} -> ${target}${label}`
  })

  return [...missingServices, ...missingConnections]
}

interface StoryResponse {
  status: string
  story: Record<string, any>
  agents: Record<string, any>
  well_architected_scores: Record<string, number>
  missing_services: string[]
  missing_connections: Array<{ from?: string; to?: string; label?: string }>
  recommendations: string[]
  processing_time: number
}

interface ReverseEngineerTabProps {
  onNavigateToValidate?: () => void
}

type ViewMode = "overview" | "story"

const SOURCE_OPTIONS: { type: SourceType; label: string; icon: React.ReactNode; accept: string; description: string }[] = [
  { type: "drawio", label: "Draw.io", icon: <FileCode className="size-5" />, accept: ".drawio,.xml", description: "Draw.io XML files" },
  { type: "visio", label: "Visio", icon: <FileText className="size-5" />, accept: ".vsdx,.vsdm", description: "Visio .vsdx files" },
  { type: "image", label: "Image", icon: <ImageIcon className="size-5" />, accept: ".png,.jpg,.jpeg,.webp", description: "Architecture screenshots" },
  { type: "bicep", label: "Bicep", icon: <FileCode className="size-5" />, accept: ".bicep", description: "Azure Bicep files" },
  { type: "terraform", label: "Terraform", icon: <FileArchive className="size-5" />, accept: ".zip", description: "Terraform ZIP archive" },
]

const STORY_STEPS = [
  { label: "Extracting architecture...", detail: "Parsing services and connections" },
  { label: "Analyzing with AI agents...", detail: "Security, Performance & Cost analysis" },
  { label: "Building story narrative...", detail: "Creating comprehensive architecture story" },
]

export function ReverseEngineerTab({ onNavigateToValidate }: ReverseEngineerTabProps) {
  const [sourceType, setSourceType] = useState<SourceType>("drawio")
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingStep, setProcessingStep] = useState(0)
  const [result, setResult] = useState<BackendResponse | null>(null)
  const [storyData, setStoryData] = useState<StoryResponse | null>(null)
  const [isLoadingStory, setIsLoadingStory] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>("overview")
  const [error, setError] = useState<string | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareFile, setCompareFile] = useState<File | null>(null)
  const [diffReport, setDiffReport] = useState<Record<string, unknown> | null>(null)
  const [isComparing, setIsComparing] = useState(false)
  const [xmlCopied, setXmlCopied] = useState(false)

  // Helper to safely get services/connections from nested backend response
  const getServices = (r: BackendResponse | null) => r?.architecture?.services || []
  const getConnections = (r: BackendResponse | null) => r?.architecture?.connections || []
  const getPattern = (r: BackendResponse | null) => r?.summary?.architecture_pattern || r?.architecture?.architecture_pattern || ""
  const getRequirements = (r: BackendResponse | null) => r?.summary?.inferred_requirements || r?.architecture?.requirements_inferred || ""
  const getRequirementsAnalysis = (r: BackendResponse | null) => r?.requirements_analysis

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      setResult(null)
      setStoryData(null)
      setError(null)
      setDiffReport(null)
      setViewMode("overview")
    }
  }

  const handleCompareFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setCompareFile(file)
      setDiffReport(null)
    }
  }

  const endpointForType = useCallback((type: SourceType) => {
    const map: Record<SourceType, string> = {
      drawio: "REVERSE_ENGINEER_DRAWIO",
      visio: "REVERSE_ENGINEER_VISIO",
      image: "REVERSE_ENGINEER_IMAGE",
      bicep: "REVERSE_ENGINEER_BICEP",
      terraform: "REVERSE_ENGINEER_TERRAFORM",
    }
    return map[type] as "REVERSE_ENGINEER_DRAWIO" | "REVERSE_ENGINEER_VISIO" | "REVERSE_ENGINEER_IMAGE" | "REVERSE_ENGINEER_BICEP" | "REVERSE_ENGINEER_TERRAFORM"
  }, [])

  // ─── Step 1: Extract architecture ───
  const handleProcess = async () => {
    if (!uploadedFile) return
    setIsProcessing(true)
    setProcessingStep(0)
    setError(null)
    setResult(null)
    setStoryData(null)
    setViewMode("overview")

    try {
      const formData = new FormData()

      if (sourceType === "drawio") {
        const content = await uploadedFile.text()
        formData.append("drawio_xml", content)
      } else {
        formData.append("file", uploadedFile)
      }

      const endpoint = endpointForType(sourceType)
      const response = await fetch(getApiUrl(endpoint), {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(`Server error ${response.status}: ${errText}`)
      }

      const data: BackendResponse = await response.json()
      setResult(data)

      // ─── Step 2: Automatically fetch story analysis ───
      setProcessingStep(1)
      await fetchStory(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred during reverse engineering")
    } finally {
      setIsProcessing(false)
    }
  }

  // ─── Fetch full architecture story from agents ───
  const fetchStory = async (backendResult: BackendResponse) => {
    setIsLoadingStory(true)
    setProcessingStep(2)
    try {
      const response = await fetch(getApiUrl("REVERSE_ENGINEER_STORY"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          architecture: backendResult.architecture,
          ai_enhancement: backendResult.ai_enhancement || {},
          source_type: backendResult.source_type,
        }),
      })

      if (!response.ok) {
        console.warn("Story analysis failed, continuing with basic view")
        return
      }

      const storyResult: StoryResponse = await response.json()
      setStoryData(storyResult)
    } catch (err) {
      console.warn("Story analysis failed:", err)
    } finally {
      setIsLoadingStory(false)
    }
  }

  const handleCompare = async () => {
    if (!uploadedFile || !compareFile) return
    setIsComparing(true)
    setDiffReport(null)

    try {
      const formData = new FormData()
      formData.append("file1", uploadedFile, uploadedFile.name)
      formData.append("file2", compareFile, compareFile.name)

      const response = await fetch(getApiUrl("COMPARE_DIAGRAMS"), {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error(`Compare failed: ${response.status}`)
      const data = await response.json()
      setDiffReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed")
    } finally {
      setIsComparing(false)
    }
  }

  const handleCopyXml = () => {
    if (result?.drawio_xml) {
      navigator.clipboard.writeText(result.drawio_xml)
      setXmlCopied(true)
      setTimeout(() => setXmlCopied(false), UI_CONFIG.COPY_FEEDBACK_DELAY)
    }
  }

  const handleDownloadXml = () => {
    if (!result?.drawio_xml) return
    const blob = new Blob([result.drawio_xml], { type: "application/xml" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${uploadedFile?.name?.replace(/\.[^.]+$/, "") || "architecture"}-reverse-engineered.drawio`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleDownloadDiffReport = async () => {
    if (!diffReport) return
    try {
      const response = await fetch(getApiUrl("DIFF_REPORT"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actual_architecture: diffReport,
          expected_architecture: {},
          report_format: "markdown",
        }),
      })
      if (response.ok) {
        const data = await response.json()
        const blob = new Blob([data.markdown_report || JSON.stringify(data, null, 2)], { type: "text/markdown" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = "diff-report.md"
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
    } catch {}
  }

  const currentOption = SOURCE_OPTIONS.find((o) => o.type === sourceType)!
  const services = getServices(result)
  const connections = getConnections(result)
  const pattern = getPattern(result)
  const requirements = getRequirements(result)
  const requirementsAnalysis = getRequirementsAnalysis(result)
  const fallbackDeviations = buildFallbackDeviations(result)
  const deviations = requirementsAnalysis?.deviations || requirementsAnalysis?.missing_requirements || fallbackDeviations
  const hasRequirementsComparison = (!!requirementsAnalysis?.requirements_source && requirementsAnalysis.requirements_source !== "not_provided") || fallbackDeviations.length > 0
  const usesStandardBaseline = requirementsAnalysis?.requirements_source === "enterprise_default" || !requirementsAnalysis?.requirements_source

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      {/* ═══ Left Panel: Input + Quick Summary ═══ */}
      <div className="space-y-4">
        <Card className="bg-card p-5">
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <GitBranch className="size-5 text-primary" />
                Reverse Engineer
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Upload any architecture file to get the complete story
              </p>
            </div>

            {/* Source Type Selector */}
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Source Type</Label>
              <div className="grid grid-cols-4 gap-1.5">
                {SOURCE_OPTIONS.map((opt) => (
                  <button
                    key={opt.type}
                    onClick={() => {
                      setSourceType(opt.type)
                      setUploadedFile(null)
                      setResult(null)
                      setStoryData(null)
                      setError(null)
                      setDiffReport(null)
                    }}
                    className={`flex flex-col items-center gap-1 rounded-lg border-2 p-2.5 text-[11px] transition-all ${
                      sourceType === opt.type
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-secondary/30 text-muted-foreground hover:bg-secondary"
                    }`}
                  >
                    {opt.icon}
                    <span className="font-medium">{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* File Upload */}
            <div className="space-y-2">
              <input
                id="re-upload"
                type="file"
                accept={currentOption.accept}
                onChange={handleFileUpload}
                className="sr-only"
              />
              <label
                htmlFor="re-upload"
                className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border bg-secondary/30 px-4 py-6 transition-colors hover:bg-secondary/70 hover:border-primary/50"
              >
                <Upload className="size-8 text-muted-foreground" />
                <div className="text-center">
                  <p className="text-sm font-medium text-foreground">
                    {uploadedFile?.name || `Upload ${currentOption.description}`}
                  </p>
                  <p className="text-[11px] text-muted-foreground">{currentOption.accept}</p>
                </div>
              </label>
            </div>

            <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2.5">
              <p className="text-xs font-medium text-foreground">Standard enterprise baseline enabled</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Reverse engineering automatically checks the extracted architecture against an internal enterprise baseline for security, observability, resilience, and production readiness.
              </p>
            </div>

            {uploadedFile && (
              <div className="rounded-lg bg-primary/5 border border-primary/20 p-2.5">
                <div className="flex items-center gap-2.5">
                  {currentOption.icon}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{uploadedFile.name}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {(uploadedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Process Button */}
            <Button
              onClick={handleProcess}
              disabled={!uploadedFile || isProcessing}
              className="w-full gap-2 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white"
              size="lg"
            >
              {isProcessing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              {isProcessing ? "Analyzing..." : "Analyze Architecture"}
            </Button>

            {error && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3">
                <p className="text-xs text-destructive">{error}</p>
              </div>
            )}
          </div>
        </Card>

        {/* ─── Quick Stats (visible after extraction) ─── */}
        {result && (
          <Card className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Quick Summary</h3>
              <Badge variant="outline" className="text-[10px]">{result.source_type}</Badge>
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-center">
              <div className="rounded-lg bg-blue-500/10 py-2">
                <p className="text-xl font-bold text-blue-600">{result.summary?.total_services || 0}</p>
                <p className="text-[10px] text-muted-foreground">Services</p>
              </div>
              <div className="rounded-lg bg-purple-500/10 py-2">
                <p className="text-xl font-bold text-purple-600">{result.summary?.total_connections || 0}</p>
                <p className="text-[10px] text-muted-foreground">Connections</p>
              </div>
              <div className="rounded-lg bg-amber-500/10 py-2">
                <p className="text-xl font-bold text-amber-600">{Object.keys(result.summary?.categories || {}).length}</p>
                <p className="text-[10px] text-muted-foreground">Categories</p>
              </div>
            </div>

            {pattern && (
              <div className="flex items-center gap-2 text-xs">
                <Network className="size-3.5 text-primary shrink-0" />
                <span className="text-muted-foreground"><b>Pattern:</b> {pattern}</span>
              </div>
            )}

            {/* View Mode Toggle */}
            <div className="flex gap-1.5 pt-1">
              <Button
                variant={viewMode === "overview" ? "default" : "outline"}
                size="sm"
                className="flex-1 gap-1.5 text-xs h-8"
                onClick={() => setViewMode("overview")}
              >
                <Eye className="size-3" />
                Overview
              </Button>
              <Button
                variant={viewMode === "story" ? "default" : "outline"}
                size="sm"
                className="flex-1 gap-1.5 text-xs h-8"
                onClick={() => {
                  if (storyData) {
                    setViewMode("story")
                  } else if (!isLoadingStory && result) {
                    fetchStory(result)
                  }
                }}
                disabled={isLoadingStory}
              >
                {isLoadingStory ? <Loader2 className="size-3 animate-spin" /> : <BookOpen className="size-3" />}
                Full Story
              </Button>
            </div>

            {/* Compare & Download */}
            <div className="flex gap-1.5 pt-1 border-t">
              {result.drawio_xml && (
                <>
                  <Button variant="ghost" size="sm" className="gap-1 text-xs h-7 flex-1" onClick={handleCopyXml}>
                    <Copy className="size-3" />
                    {xmlCopied ? "Copied!" : "Copy XML"}
                  </Button>
                  <Button variant="ghost" size="sm" className="gap-1 text-xs h-7 flex-1" onClick={handleDownloadXml}>
                    <Download className="size-3" />
                    Download
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs h-7 flex-1"
                onClick={() => setCompareMode(!compareMode)}
              >
                <Shield className="size-3" />
                Compare
              </Button>
            </div>

            {/* Compare Mode inline */}
            {compareMode && (
              <div className="space-y-2 pt-2 border-t">
                <input
                  id="compare-upload"
                  type="file"
                  accept=".drawio,.xml,.vsdx,.vsdm,.png,.jpg,.jpeg,.webp,.zip"
                  onChange={handleCompareFileUpload}
                  className="sr-only"
                />
                <label
                  htmlFor="compare-upload"
                  className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-border bg-secondary/30 px-3 py-2.5 text-xs text-muted-foreground hover:bg-secondary transition-colors"
                >
                  <Upload className="size-4" />
                  {compareFile?.name || "Upload second diagram"}
                </label>
                <Button
                  onClick={handleCompare}
                  disabled={!compareFile || isComparing}
                  className="w-full gap-2 text-xs"
                  variant="secondary"
                  size="sm"
                >
                  {isComparing ? <Loader2 className="size-3 animate-spin" /> : <ArrowRight className="size-3" />}
                  {isComparing ? "Comparing..." : "Run Comparison"}
                </Button>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* ═══ Right Panel: Results ═══ */}
      <div className="space-y-4">
        {/* Processing Animation */}
        {isProcessing && (
          <Card className="p-8">
            <div className="flex flex-col items-center text-center">
              <div className="relative mb-6">
                <div className="size-20 rounded-full bg-gradient-to-br from-blue-500/20 to-violet-500/20 flex items-center justify-center">
                  <Loader2 className="size-10 animate-spin text-primary" />
                </div>
                <div className="absolute -inset-2 rounded-full border-2 border-primary/10 animate-pulse" />
              </div>
              <div className="space-y-4 w-full max-w-sm">
                {STORY_STEPS.map((step, i) => (
                  <div key={i} className={`flex items-center gap-3 transition-all duration-500 ${
                    i < processingStep ? "opacity-50" : i === processingStep ? "opacity-100" : "opacity-30"
                  }`}>
                    {i < processingStep ? (
                      <CheckCircle2 className="size-5 text-green-500 shrink-0" />
                    ) : i === processingStep ? (
                      <Loader2 className="size-5 animate-spin text-primary shrink-0" />
                    ) : (
                      <div className="size-5 rounded-full border-2 border-muted shrink-0" />
                    )}
                    <div className="text-left">
                      <p className="text-sm font-medium">{step.label}</p>
                      <p className="text-xs text-muted-foreground">{step.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* Empty State */}
        {!isProcessing && !result && !diffReport && (
          <Card className="p-16 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="size-20 rounded-full bg-gradient-to-br from-blue-500/10 to-violet-500/10 flex items-center justify-center">
                <BookOpen className="size-10 text-muted-foreground/50" />
              </div>
              <div>
                <p className="text-lg font-medium text-foreground mb-1">Architecture Story Analyzer</p>
                <p className="text-sm text-muted-foreground max-w-md">
                  Upload a diagram and our AI agents will analyze it to tell the complete story — 
                  what it does, how data flows, security posture, performance profile, and more.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* ─── Overview Mode ─── */}
        {result && !diffReport && viewMode === "overview" && (
          <ScrollArea className="h-[calc(100vh-200px)]">
            <div className="space-y-4 pr-2">
              {/* Services Grid */}
              {result.drawio_xml && (
                <Card className="p-4 space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="font-semibold text-sm">Generated Architecture Diagram</h4>
                      <p className="text-xs text-muted-foreground">Rendered from the reverse-engineered architecture output</p>
                    </div>
                    <Badge variant="outline" className="text-[10px]">Draw.io</Badge>
                  </div>
                  <DiagramEmbed xml={result.drawio_xml} />
                </Card>
              )}

              <Card className="p-4 border-primary/20 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="font-semibold text-sm">Deviations From {usesStandardBaseline ? "Standard Enterprise Requirements" : "Enterprise Requirements"}</h4>
                    <p className="text-xs text-muted-foreground">
                      {usesStandardBaseline
                        ? "Items expected by the built-in enterprise baseline but not evidenced in the extracted architecture"
                        : "Items expected by the enterprise requirements but not evidenced in the extracted architecture"}
                    </p>
                  </div>
                  {typeof requirementsAnalysis?.score === "number" && (
                    <Badge variant="outline" className="text-[10px]">
                      Match {requirementsAnalysis.score}%
                    </Badge>
                  )}
                </div>

                {hasRequirementsComparison ? (
                  deviations.length > 0 ? (
                    <div className="space-y-2">
                      {deviations.map((deviation, idx) => (
                        <div key={idx} className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm">
                          <AlertTriangle className="size-4 shrink-0 text-amber-600 mt-0.5" />
                          <span className="text-foreground/90">{deviation}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {usesStandardBaseline && (
                        <div className="rounded-lg border border-border bg-secondary/30 px-3 py-2 text-xs text-muted-foreground">
                          Built-in baseline applied automatically for this analysis.
                        </div>
                      )}
                      <div className="flex items-start gap-2 rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-2 text-sm">
                        <CheckCircle2 className="size-4 shrink-0 text-green-600 mt-0.5" />
                        <span className="text-foreground/90">No deviations detected against the selected enterprise baseline.</span>
                      </div>
                    </div>
                  )
                ) : (
                  <div className="flex items-start gap-2 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-sm">
                    <AlertTriangle className="size-4 shrink-0 text-muted-foreground mt-0.5" />
                    <span className="text-muted-foreground">No deviations were detected from the standard enterprise baseline for this result.</span>
                  </div>
                )}
              </Card>

              <Card className="p-4">
                <h4 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                  <Server className="size-4 text-blue-500" /> Services ({services.length})
                </h4>
                <div className="grid gap-1.5 sm:grid-cols-2 max-h-72 overflow-y-auto">
                  {services.map((svc, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm py-1.5 px-2.5 rounded-lg hover:bg-secondary/50 transition-colors">
                      <CheckCircle2 className="size-3.5 text-green-500 shrink-0" />
                      <span className="font-medium truncate">{svc.name}</span>
                      <Badge variant="outline" className="text-[10px] ml-auto shrink-0">{svc.category}</Badge>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Connections */}
              {connections.length > 0 && (
                <Card className="p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                    <ArrowRight className="size-4 text-purple-500" /> Connections ({connections.length})
                  </h4>
                  <div className="space-y-1 max-h-56 overflow-y-auto">
                    {connections.map((conn, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-sm py-1.5 px-2.5 rounded-lg hover:bg-secondary/50 transition-colors">
                        <span className="font-medium truncate max-w-[140px]">{conn.source}</span>
                        <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate max-w-[140px]">{conn.target}</span>
                        {conn.label && <span className="text-xs text-muted-foreground ml-auto truncate max-w-[120px]">({conn.label})</span>}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Categories Breakdown */}
              {result.summary?.categories && Object.keys(result.summary.categories).length > 0 && (
                <Card className="p-4">
                  <h4 className="font-semibold mb-3 text-sm">Service Categories</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.summary.categories).map(([cat, count]) => (
                      <Badge key={cat} variant="secondary" className="text-xs py-1 px-3">
                        {cat} <span className="ml-1.5 text-primary font-bold">{count}</span>
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}

              {/* Requirements */}
              {requirements && (
                <Card className="p-4">
                  <h4 className="font-semibold mb-2 text-sm">Inferred Requirements</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{requirements}</p>
                </Card>
              )}

              {/* AI Enhancement Data (if available) */}
              {result.ai_enhancement?.recommendations && result.ai_enhancement.recommendations.length > 0 && (
                <Card className="p-4 border-primary/20">
                  <h4 className="font-semibold mb-2 text-sm flex items-center gap-2">
                    <Sparkles className="size-4 text-primary" /> AI Recommendations
                  </h4>
                  <ul className="space-y-1.5">
                    {result.ai_enhancement.recommendations.slice(0, 5).map((rec, idx) => (
                      <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                        <span className="text-primary font-bold text-xs mt-0.5">{idx + 1}</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              
              {/* Validate Button */}
              <div className="flex justify-center pt-2">
                <Button
                  onClick={onNavigateToValidate}
                  variant="outline"
                  className="gap-2 border-primary/50 bg-primary/5 hover:bg-primary/10"
                >
                  <Shield className="size-4" />
                  Validate Architecture
                </Button>
              </div>
            </div>
          </ScrollArea>
        )}

        {/* ─── Story Mode ─── */}
        {result && !diffReport && viewMode === "story" && (
          <ScrollArea className="h-[calc(100vh-200px)]">
            <div className="pr-2">
              {isLoadingStory ? (
                <ArchitectureStory
                  story={{}}
                  agents={{}}
                  isLoading={true}
                />
              ) : storyData ? (
                <ArchitectureStory
                  story={storyData.story || {}}
                  agents={storyData.agents || {}}
                  wellArchitectedScores={storyData.well_architected_scores || {}}
                  missingServices={storyData.missing_services || []}
                  missingConnections={storyData.missing_connections || []}
                  recommendations={storyData.recommendations || []}
                />
              ) : (
                <Card className="p-8 text-center">
                  <BookOpen className="size-10 text-muted-foreground/50 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">
                    Story analysis could not be loaded. 
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 gap-2"
                    onClick={() => result && fetchStory(result)}
                  >
                    <Sparkles className="size-3" />
                    Retry Analysis
                  </Button>
                </Card>
              )}
              
              {/* Validate Button */}
              {storyData && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-xs text-muted-foreground">
                    Analysis completed in {storyData.processing_time || 0}s
                  </p>
                  <Button
                    onClick={onNavigateToValidate}
                    variant="outline"
                    className="gap-2 border-primary/50 bg-primary/5 hover:bg-primary/10"
                    size="sm"
                  >
                    <Shield className="size-4" />
                    Validate Architecture
                  </Button>
                </div>
              )}
            </div>
          </ScrollArea>
        )}

        {/* Diff Report */}
        {diffReport && (
          <DiffViewer report={diffReport as any} onDownloadReport={handleDownloadDiffReport} />
        )}
      </div>
    </div>
  )
}
