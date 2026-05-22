"use client"

import type React from "react"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"
import { Upload, Sparkles, Download, Eye, Code, FileCode, Shield, CheckCircle, AlertTriangle, Users } from "lucide-react"

import DiagramEmbed from "@/components/DiagramEmbed"
import { AIAgentsProgress } from "@/components/ai-agents-progress"
import { ImprovementChat } from "@/components/improvement-chat"
import { FeedbackWidget } from "@/components/feedback-widget"
import { ClarifyingQuestionsDialog } from "@/components/clarifying-questions-dialog"
import { API_CONFIG } from "@/lib/config"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { toast } from "@/hooks/use-toast"
import type { ArchitectureResponse } from "@/types"

// Transform any backend result (multi-agent or other modes) to frontend ArchitectureResponse shape
function transformBackendResult(result: any): any {
  return {
    diagram_url: result.diagram_url,
    architecture: {
      services: result.architecture?.services || [],
      architecture_pattern: result.architecture?.architecture_pattern || 'Custom',
      connections: result.architecture?.connections || [],
      drawio_xml: result.diagrams?.drawio_xml || '',
      recommendations: result.architecture?.recommendations || [],
      detected_services_info: result.architecture?.detected_services_info || [],
      services_with_icons: result.architecture?.services_with_icons || []
    },
    validation: {
      validation_id: result.validation_id || result.timestamp,
      compliance_score: result.compliance_score ?? result.validation?.compliance_score ?? 0,
      critical_issues: result.critical_issues || [],
      quick_wins: result.quick_wins || [],
      ai_comparison: result.ai_comparison || result.detailed_analysis?.ai_comparison || {},
      agent_recommendations: result.agent_recommendations || result.workflow_results?.agent_recommendations || { agents_results: [] },
      recommendations: result.recommendations || { critical: [], high: [], medium: [] },
      validation_type: 'full',
      architecture_complexity: result.architecture_complexity || 'standard'
    },
    service_detection: {
      ai_detected: result.architecture?.services || [],
      prompt_detected: [],
      final_services: result.architecture?.services || [],
      detection_details: result.architecture?.detected_services_info || []
    },
    icon_sources: result.icon_sources || { local_icons: 0, portal_icons: 0, default_icons: 0 },
    diagrams: {
      drawio_xml: result.diagrams?.drawio_xml || '',
      mermaid: result.diagrams?.mermaid || '',
      terraform: result.diagrams?.terraform || '',
      image: result.diagrams?.image || ''
    },
    agent_type: result.agent_type || 'multi-agent-workflow',
    timestamp: result.timestamp,
    saved_files: result.saved_files || {}
  }
}

export function GenerateTab() {
  const [requirements, setRequirements] = useState("")
  const [fileName, setFileName] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [architectureResult, setArchitectureResult] = useState<ArchitectureResponse | null>(null)
  const [activeTab, setActiveTab] = useState("visual")
  
  // Generation Mode Settings
  const [generationMode, setGenerationMode] = useState<'generate' | 'multi-agent-workflow'>('multi-agent-workflow')
  const [projectName, setProjectName] = useState("")
  const [environment, setEnvironment] = useState("production")
  const [includeTerraform, setIncludeTerraform] = useState(true)
  const [includeMermaid, setIncludeMermaid] = useState(true)
  const [useProfessionalStyle, setUseProfessionalStyle] = useState(true)
  const [showAgentProgress, setShowAgentProgress] = useState(false)
  const [showClarifyingQuestions, setShowClarifyingQuestions] = useState(false)
  const [enrichedRequirements, setEnrichedRequirements] = useState("")
  const [sessionId] = useState(() => `gen-${Date.now()}`)

  // Handler for improvement updates
  const handleImprovementUpdate = (newArchitecture: any, newDiagramXml: string, mermaid?: string, terraform?: string) => {
    if (architectureResult) {
      setArchitectureResult({
        ...architectureResult,
        architecture: {
          ...architectureResult.architecture,
          services: newArchitecture.services || architectureResult.architecture.services,
          connections: newArchitecture.connections || architectureResult.architecture.connections,
        },
        diagrams: {
          ...architectureResult.diagrams,
          drawio_xml: newDiagramXml,
          mermaid: mermaid || architectureResult.diagrams.mermaid,
          terraform: terraform || architectureResult.diagrams.terraform,
        }
      })
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setFileName(file.name)
      const reader = new FileReader()
      reader.onload = (event) => {
        setRequirements(event.target?.result as string)
      }
      reader.readAsText(file)
    }
  }

  // Handler for when clarifying questions are answered
  const handleClarifyComplete = (enriched: string, answers: Record<string, string>) => {
    setEnrichedRequirements(enriched)
    setShowClarifyingQuestions(false)
    setShowAgentProgress(true)
  }

  // Handler for when user skips clarifying questions
  const handleClarifySkip = () => {
    setEnrichedRequirements(requirements)
    setShowClarifyingQuestions(false)
    setShowAgentProgress(true)
  }

  // Callback when AIAgentsProgress finishes
  const handleAgentWorkflowComplete = (result: any) => {
    console.log('✅ Multi-agent workflow completed:', result)
    // Transform the multi-agent result into standard shape
    const arch = result.final_architecture || {}
    const transformedResult = {
      diagram_url: result.diagram_url,
      architecture: {
        services: arch.services || [],
        architecture_pattern: arch.architecture_pattern || 'Custom',
        connections: arch.connections || [],
        drawio_xml: result.drawio_xml || '',
        recommendations: arch.security_insights?.critical_issues || [],
        detected_services_info: [],
        services_with_icons: arch.services || []
      },
      validation: {
        validation_id: result.timestamp || '',
        compliance_score: arch.security_insights?.compliance_score ?? 0,
        critical_issues: arch.security_insights?.critical_issues || [],
        quick_wins: arch.performance_insights?.quick_wins || [],
        ai_comparison: {
          strengths: [],
          gaps: [],
          insights: '',
          well_architected_scores: {
            security: arch.security_insights?.compliance_score || 0,
            reliability: 0,
            performance: arch.performance_insights?.performance_score || 0,
            cost_optimization: arch.cost_insights?.cost_score || 0,
            operational_excellence: 0,
          },
          overall_score: arch.validation?.overall_score || 0,
          architecture_assessment: {
            architecture_pattern: arch.architecture_pattern || '',
            resource_group_organization: '',
            network_design: '',
            security_implementation: '',
            monitoring_strategy: '',
            disaster_recovery: '',
          },
        },
        agent_recommendations: {
          agents_results: result.agents_executed || [],
          summary: {
            total_agents: (result.agents_executed || []).length,
            agents_completed: (result.agents_executed || []).length,
            critical_issues_found: (arch.security_insights?.critical_issues || []).length,
            recommendations_generated: Array.isArray(arch.validation?.recommendations) ? arch.validation.recommendations.length : 0,
          }
        },
        recommendations: {
          critical: Array.isArray(arch.validation?.recommendations) ? arch.validation.recommendations.filter((r: any) => r.priority === 'critical') : [],
          high: Array.isArray(arch.validation?.recommendations) ? arch.validation.recommendations.filter((r: any) => r.priority === 'high') : [],
          medium: Array.isArray(arch.validation?.recommendations) ? arch.validation.recommendations.filter((r: any) => r.priority === 'medium') : [],
        },
        validation_type: 'multi-agent',
        architecture_complexity: arch.component_extraction?.complexity_level || 'standard'
      },
      service_detection: {
        ai_detected: arch.services || [],
        prompt_detected: [],
        final_services: arch.services || [],
        detection_details: []
      },
      icon_sources: result.icon_sources || { local_icons: 0, portal_icons: 0, default_icons: 0 },
      diagrams: {
        drawio_xml: result.diagrams?.drawio_xml || result.drawio_xml || '',
        mermaid: result.diagrams?.mermaid || '',
        terraform: result.diagrams?.terraform || '',
        image: ''
      },
      agent_type: 'multi-agent-workflow',
      timestamp: result.timestamp,
      saved_files: result.saved_files || {},
      // Carry forward multi-agent specific data
      processing_timeline: result.processing_timeline || [],
      total_duration: result.total_duration || 0,
      agents_executed: result.agents_executed || [],
      final_architecture: arch
    }
    setArchitectureResult(transformedResult)
    setIsGenerating(false)
    setShowAgentProgress(false)
  }

  const handleGenerate = async () => {
    if (isGenerating) return // prevent duplicate calls
    setIsGenerating(true)
    setArchitectureResult(null)

    // For multi-agent-workflow, show clarifying questions first
    if (generationMode === 'multi-agent-workflow') {
      setShowClarifyingQuestions(true)
      return // ClarifyingQuestionsDialog will handle flow
    }
    
    try {
      console.log('🚀 Starting generation with mode:', generationMode)
      console.log('📊 Request data:', {
        requirements: requirements.substring(0, 100) + '...',
        mode: generationMode,
        projectName,
        environment
      })
      
      const endpoint = `${API_CONFIG.BASE_URL}/api/${generationMode}`
      const requestBody = {
        requirements: requirements,
        project_name: projectName || undefined,
        environment: environment,
        include_terraform: includeTerraform,
        include_mermaid: includeMermaid,
        use_professional_style: useProfessionalStyle
      }
      
      console.log('🌐 Making API call to:', endpoint)
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Server error:', errorText)
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }
      
      const result = await response.json()
      console.log('✅ Generation result:', result)
      
      const transformedResult = transformBackendResult(result)
      setArchitectureResult(transformedResult)
      setIsGenerating(false)
      
    } catch (error) {
      console.error('❌ Error generating diagram:', error)
      setIsGenerating(false)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast({ title: "Generation Failed", description: errorMessage, variant: "destructive" })
    }
  }

  const canGenerate = requirements.trim().length > 0

  return (
    <ResizablePanelGroup direction="horizontal" className="min-h-[calc(100vh-220px)] rounded-2xl overflow-hidden border border-border/30 bg-card/20 shadow-2xl shadow-black/10 backdrop-blur-sm">
      {/* Input Panel */}
      <ResizablePanel defaultSize={32} minSize={25} maxSize={45}>
        <div className="h-full overflow-y-auto custom-scrollbar bg-gradient-to-b from-card/80 to-card/40 backdrop-blur-xl">
        <Card className="border-0 shadow-none bg-transparent p-5">
        <div className="space-y-5 stagger-children">
          <div className="pb-3 border-b border-border/30">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <div className="relative flex size-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </div>
              Architecture Requirements
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Define your infrastructure needs and let AI design the architecture
            </p>
          </div>

          {/* Generation Mode Selection */}
          <div className="space-y-3 p-3 border border-border/50 rounded-lg bg-gradient-to-br from-muted/30 to-muted/10">
            <Label className="text-xs font-semibold text-foreground uppercase tracking-wide">AI Engine</Label>
            <Select value={generationMode} onValueChange={(value) => setGenerationMode(value as any)}>
              <SelectTrigger className="bg-card border-border/50 h-9">
                <SelectValue placeholder="Select generation mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="generate">
                  <div className="flex items-center gap-2">
                    <Sparkles className="size-4" />
                    <div>
                      <div className="font-medium">Comprehensive Generation</div>
                      <div className="text-xs text-muted-foreground">Full AI analysis with all agents</div>
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="multi-agent-workflow">
                  <div className="flex items-center gap-2">
                    <Users className="size-4" />
                    <div>
                      <div className="font-medium">Multi-Agent Workflow</div>
                      <div className="text-xs text-muted-foreground">Security → Performance → Architecture → Cost with live progress</div>
                    </div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Project Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="project-name" className="text-sm font-medium text-foreground">
                Project Name (Optional)
              </Label>
              <Input
                id="project-name"
                placeholder="My Azure Project"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="environment" className="text-sm font-medium text-foreground">
                Environment
              </Label>
              <Select value={environment} onValueChange={setEnvironment}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="development">Development</SelectItem>
                  <SelectItem value="staging">Staging</SelectItem>
                  <SelectItem value="production">Production</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Output Format Options */}
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground">Output Formats</Label>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCode className="size-4 text-orange-500" />
                  <span className="text-sm">Include Terraform</span>
                </div>
                <Switch checked={includeTerraform} onCheckedChange={setIncludeTerraform} />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code className="size-4 text-blue-500" />
                  <span className="text-sm">Include Mermaid</span>
                </div>
                <Switch checked={includeMermaid} onCheckedChange={setIncludeMermaid} />
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 text-purple-500" />
                  <span className="text-sm">Professional Style</span>
                </div>
                <Switch checked={useProfessionalStyle} onCheckedChange={setUseProfessionalStyle} />
              </div>
            </div>
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label htmlFor="file-upload" className="text-sm font-medium text-foreground">
              Upload Requirements File
            </Label>
            <div className="relative">
              <input
                id="file-upload"
                type="file"
                accept=".txt,.md,.doc,.docx"
                onChange={handleFileUpload}
                className="sr-only"
              />
              <label
                htmlFor="file-upload"
                className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-border bg-secondary/50 px-4 py-8 transition-colors hover:bg-secondary"
              >
                <Upload className="size-5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    {fileName || "Click to upload or drag and drop"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">TXT, MD, DOC up to 10MB</p>
                </div>
              </label>
            </div>
          </div>

          {/* Text Input */}
          <div className="space-y-2">
            <Label htmlFor="requirements" className="text-sm font-medium text-foreground">
              Or type requirements
            </Label>
            <div className="max-h-[300px] overflow-y-auto rounded-lg border border-border">
              <Textarea
                id="requirements"
                placeholder="Example: Create a web application with Azure App Service, connect to Azure SQL Database for storage, use Azure Key Vault for secrets management..."
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                className="min-h-[300px] resize-none border-0 bg-secondary text-foreground placeholder:text-muted-foreground focus-visible:ring-0"
              />
            </div>
            <p className="text-xs text-muted-foreground">{requirements.length} characters</p>
          </div>

          {/* Generate Button */}
          <Button 
            onClick={handleGenerate} 
            disabled={!canGenerate || isGenerating} 
            className="w-full gap-2.5 h-12 bg-gradient-to-r from-primary via-primary/95 to-accent hover:from-primary/90 hover:to-accent/90 shadow-lg shadow-primary/25 transition-all duration-500 hover:shadow-xl hover:shadow-primary/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:scale-100 rounded-xl text-sm font-semibold" 
            size="lg"
          >
            {isGenerating ? (
              <>
                <div className="relative flex size-4">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-foreground/50" />
                  <span className="relative inline-flex size-4 items-center justify-center">
                    <Users className="size-4 animate-spin" style={{ animationDuration: '2s' }} />
                  </span>
                </div>
                {generationMode === 'multi-agent-workflow' ? 'AI Agents Working...' : 'Analyzing...'}
              </>
            ) : (
              <>
                {generationMode === 'multi-agent-workflow' ? <Users className="size-4" /> : <Sparkles className="size-4" />}
                Generate Architecture
              </>
            )}
          </Button>
        </div>
        </Card>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle className="bg-border/20 hover:bg-primary/30 transition-colors duration-300 data-[resize-handle-active]:bg-primary/50" />

      {/* Output Panel */}
      <ResizablePanel defaultSize={68} minSize={40}>
        <div className="h-full overflow-y-auto custom-scrollbar bg-gradient-to-br from-card/30 to-muted/10 backdrop-blur-sm p-5">
        <div className="space-y-4">
        <div className="pb-3 border-b border-border/30">
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Eye className="size-4 text-primary" />
            Generation Results
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Your architecture diagram and artifacts will appear here
          </p>
        </div>
        <div className="space-y-6">
        {/* Clarifying Questions Phase */}
        {isGenerating && showClarifyingQuestions && (
          <ClarifyingQuestionsDialog
            requirements={requirements}
            onComplete={handleClarifyComplete}
            onSkip={handleClarifySkip}
          />
        )}

        {/* Multi-Agent Progress UI */}
        {isGenerating && showAgentProgress && (
          <AIAgentsProgress
            onComplete={handleAgentWorkflowComplete}
            requirements={enrichedRequirements || requirements}
          />
        )}

        {/* Generic spinner for non-multi-agent modes */}
        {isGenerating && !showAgentProgress && (
          <Card className="bg-card/60 backdrop-blur-xl p-8 border-border/30 animate-scale-in">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary/20 border-t-primary"></div>
                <Sparkles className="absolute inset-0 m-auto size-5 text-primary animate-pulse" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-foreground">Generating architecture...</p>
                <p className="text-sm text-muted-foreground mt-1">AI is analyzing your requirements</p>
              </div>
              <div className="typing-indicator flex gap-1 text-primary">
                <span /><span /><span />
              </div>
            </div>
          </Card>
        )}

        {!isGenerating && architectureResult && (
          <>
            <Card className="bg-card/60 backdrop-blur-xl p-6 border-border/30 animate-slide-up">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                      <CheckCircle className="size-5 text-emerald-500" />
                      Generated Architecture
                    </h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {architectureResult.architecture.services?.length || 0} services • 
                      Pattern: {architectureResult.architecture.architecture_pattern} • 
                      Mode: {generationMode}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => {
                        const xml = architectureResult.diagrams?.drawio_xml
                        if (!xml) return
                        const blob = new Blob([xml], { type: 'application/xml' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        const name = (architectureResult as any).timestamp
                          ? `architecture-${(architectureResult as any).timestamp}`
                          : `architecture-${Date.now()}`
                        a.download = `${name}.drawio`
                        document.body.appendChild(a)
                        a.click()
                        document.body.removeChild(a)
                        URL.revokeObjectURL(url)
                        toast({ title: "Saved", description: "Diagram exported as .drawio file." })
                      }}
                      disabled={!architectureResult.diagrams?.drawio_xml}
                    >
                      <Download className="size-3" />
                      Save as .drawio
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => {
                        const terraform = architectureResult.diagrams?.terraform
                        if (!terraform) return
                        const blob = new Blob([terraform], { type: 'text/plain' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        const name = (architectureResult as any).timestamp
                          ? `architecture-${(architectureResult as any).timestamp}`
                          : `architecture-${Date.now()}`
                        a.download = `${name}.tf`
                        document.body.appendChild(a)
                        a.click()
                        document.body.removeChild(a)
                        URL.revokeObjectURL(url)
                        toast({ title: "Saved", description: "Terraform template exported as .tf file." })
                      }}
                      disabled={!architectureResult.diagrams?.terraform}
                    >
                      <FileCode className="size-3" />
                      Save Terraform
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => {
                        const mermaid = architectureResult.diagrams?.mermaid
                        if (!mermaid) return
                        const blob = new Blob([mermaid], { type: 'text/plain' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        const name = (architectureResult as any).timestamp
                          ? `architecture-${(architectureResult as any).timestamp}`
                          : `architecture-${Date.now()}`
                        a.download = `${name}.mmd`
                        document.body.appendChild(a)
                        a.click()
                        document.body.removeChild(a)
                        URL.revokeObjectURL(url)
                        toast({ title: "Saved", description: "Mermaid diagram exported as .mmd file." })
                      }}
                      disabled={!architectureResult.diagrams?.mermaid}
                    >
                      <Code className="size-3" />
                      Save Mermaid
                    </Button>
                  </div>
                </div>

                {/* Animated Statistics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 stagger-children">
                  <div className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/20 p-4 text-center transition-all duration-300 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/10">
                    <div className="text-2xl font-bold text-emerald-400 stat-value">
                      {architectureResult.validation?.compliance_score ?? 0}%
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Compliance</div>
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/5 to-emerald-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </div>
                  <div className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20 p-4 text-center transition-all duration-300 hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/10">
                    <div className="text-2xl font-bold text-blue-400 stat-value" style={{ animationDelay: '0.1s' }}>
                      {architectureResult.architecture.services?.length || 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Services</div>
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/5 to-blue-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </div>
                  <div className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-500/20 p-4 text-center transition-all duration-300 hover:border-amber-500/40 hover:shadow-lg hover:shadow-amber-500/10">
                    <div className="text-2xl font-bold text-amber-400 stat-value" style={{ animationDelay: '0.2s' }}>
                      {architectureResult.validation.critical_issues?.length || 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Issues</div>
                    <div className="absolute inset-0 bg-gradient-to-r from-amber-500/0 via-amber-500/5 to-amber-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </div>
                  <div className="group relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20 p-4 text-center transition-all duration-300 hover:border-purple-500/40 hover:shadow-lg hover:shadow-purple-500/10">
                    <div className="text-2xl font-bold text-purple-400 stat-value" style={{ animationDelay: '0.3s' }}>
                      {architectureResult.architecture.connections?.length || 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">Connections</div>
                    <div className="absolute inset-0 bg-gradient-to-r from-purple-500/0 via-purple-500/5 to-purple-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </div>
                </div>

                {/* Architecture Info Bar */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <Badge variant="secondary" className="gap-1">
                    <Sparkles className="size-3" />
                    {architectureResult.architecture.architecture_pattern}
                  </Badge>
                  <Badge variant="outline" className="gap-1 capitalize">
                    {generationMode.replace(/-/g, ' ')}
                  </Badge>
                  {(architectureResult.architecture.services?.length || 0) > 10 ? (
                    <Badge variant="destructive" className="gap-1">High Complexity</Badge>
                  ) : (architectureResult.architecture.services?.length || 0) > 5 ? (
                    <Badge className="gap-1 bg-amber-500/15 text-amber-600 border-amber-500/30">Medium Complexity</Badge>
                  ) : (
                    <Badge className="gap-1 bg-emerald-500/15 text-emerald-600 border-emerald-500/30">Low Complexity</Badge>
                  )}
                </div>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-5 bg-muted/50 backdrop-blur-sm rounded-xl p-1 h-auto">
                    <TabsTrigger value="visual" className="gap-2 rounded-lg data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-accent data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300">
                      <Eye className="size-4" />
                      Visual
                    </TabsTrigger>
                    <TabsTrigger value="xml" className="gap-2 rounded-lg data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-accent data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300">
                      <Code className="size-4" />
                      XML
                    </TabsTrigger>
                    <TabsTrigger value="mermaid" className="gap-2 rounded-lg data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-accent data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300">
                      <FileCode className="size-4" />
                      Mermaid
                    </TabsTrigger>
                    <TabsTrigger value="terraform" className="gap-2 rounded-lg data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-accent data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300">
                      <FileCode className="size-4" />
                      Terraform
                    </TabsTrigger>
                    <TabsTrigger value="validation" className="gap-2 rounded-lg data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-accent data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300">
                      <Shield className="size-4" />
                      Analysis
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="visual" className="mt-4">
                    <div className="space-y-0">
                      {/* Visual Diagram Section */}
                      <div className="overflow-hidden rounded-t-xl border border-b-0 border-border/30 bg-white shadow-lg shadow-black/5 animate-scale-in">
                        {isGenerating ? (
                          <div className="p-12 text-center bg-gradient-to-br from-muted/30 to-muted/10">
                            <div className="relative inline-block">
                              <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary/20 border-t-primary mx-auto mb-4"></div>
                              <Sparkles className="absolute inset-0 m-auto size-4 text-primary animate-pulse" />
                            </div>
                            <p className="text-sm text-muted-foreground">Generating architecture diagram...</p>
                            <div className="typing-indicator flex gap-1 justify-center mt-3 text-primary">
                              <span /><span /><span />
                            </div>
                          </div>
                        ) : architectureResult?.diagrams?.drawio_xml ? (
                          <DiagramEmbed xml={architectureResult.diagrams.drawio_xml} />
                        ) : (
                          <div className="p-12 text-center text-muted-foreground space-y-3 bg-gradient-to-br from-muted/20 to-muted/5">
                            <Eye className="size-12 mx-auto opacity-20" />
                            <p className="text-sm">No diagram XML available yet.</p>
                          </div>
                        )}
                      </div>
                      
                      {/* Improvement Chat - Only show after generation */}
                      {architectureResult?.architecture?.services?.length > 0 && !isGenerating && (
                        <div className="rounded-b-xl border border-t border-border/30 overflow-hidden shadow-lg shadow-black/5">
                          <ImprovementChat
                            architecture={architectureResult.architecture}
                            onArchitectureUpdate={handleImprovementUpdate}
                            sessionId={sessionId}
                            currentXml={architectureResult.diagrams?.drawio_xml}
                            originalRequirements={requirements}
                          />
                        </div>
                      )}
                      
                      {/* Feedback Widget - Rate the generated architecture */}
                      {architectureResult?.architecture?.services?.length > 0 && !isGenerating && (
                        <div className="mt-3">
                          <FeedbackWidget
                            generationId={sessionId || `gen_${Date.now()}`}
                          />
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="xml" className="mt-4">
                    <Card className="overflow-hidden border-border/30 bg-card/60 backdrop-blur-xl">
                      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/30 bg-muted/30">
                        <span className="text-xs font-medium text-muted-foreground">DrawIO XML</span>
                        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" onClick={() => { navigator.clipboard.writeText(architectureResult.diagrams?.drawio_xml || ''); toast({ title: "Copied", description: "XML copied to clipboard" }) }}>
                          <Code className="size-3" /> Copy
                        </Button>
                      </div>
                      <div className="max-h-[600px] overflow-auto p-4 custom-scrollbar">
                        <pre className="text-sm text-emerald-400 font-mono whitespace-pre-wrap leading-relaxed">
                          {architectureResult.diagrams?.drawio_xml || 'XML content will appear here...'}
                        </pre>
                      </div>
                    </Card>
                  </TabsContent>

                  <TabsContent value="mermaid" className="mt-4">
                    <Card className="overflow-hidden border-border/30 bg-card/60 backdrop-blur-xl">
                      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/30 bg-muted/30">
                        <span className="text-xs font-medium text-muted-foreground">Mermaid Diagram</span>
                        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" onClick={() => { navigator.clipboard.writeText(architectureResult.diagrams?.mermaid || ''); toast({ title: "Copied", description: "Mermaid copied to clipboard" }) }}>
                          <Code className="size-3" /> Copy
                        </Button>
                      </div>
                      <div className="max-h-[600px] overflow-auto p-4 custom-scrollbar">
                        <pre className="text-sm text-blue-400 font-mono whitespace-pre-wrap leading-relaxed">
                          {architectureResult.diagrams?.mermaid || 'Mermaid diagram will appear here...'}
                        </pre>
                      </div>
                    </Card>
                  </TabsContent>

                  <TabsContent value="terraform" className="mt-4">
                    <Card className="overflow-hidden border-border/30 bg-card/60 backdrop-blur-xl">
                      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/30 bg-muted/30">
                        <span className="text-xs font-medium text-muted-foreground">Terraform Template</span>
                        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" onClick={() => { navigator.clipboard.writeText(architectureResult.diagrams?.terraform || ''); toast({ title: "Copied", description: "Terraform copied to clipboard" }) }}>
                          <Code className="size-3" /> Copy
                        </Button>
                      </div>
                      <div className="max-h-[600px] overflow-auto p-4 custom-scrollbar">
                        <pre className="text-sm text-orange-400 font-mono whitespace-pre-wrap leading-relaxed">
                          {architectureResult.diagrams?.terraform || 'Terraform template will appear here...'}
                        </pre>
                      </div>
                    </Card>
                  </TabsContent>

                  <TabsContent value="validation" className="mt-4">
                    <div className="space-y-5">
                      {/* Well-Architected Scores */}
                      {architectureResult.validation.ai_comparison?.well_architected_scores && (
                        <Card className="p-5 bg-card/60 backdrop-blur-xl border-border/30">
                          <h4 className="font-semibold mb-4 flex items-center gap-2">
                            <Shield className="size-4 text-primary" />
                            Well-Architected Framework
                          </h4>
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                            {Object.entries(architectureResult.validation.ai_comparison.well_architected_scores).map(([pillar, score]) => (
                              <div key={pillar} className="text-center p-3 rounded-xl bg-muted/30 border border-border/20">
                                <div className={`text-xl font-bold ${
                                  score >= 80 ? 'text-emerald-500' : score >= 60 ? 'text-amber-500' : 'text-red-500'
                                }`}>
                                  {score}%
                                </div>
                                <div className="text-[11px] text-muted-foreground capitalize mt-1">
                                  {pillar.replace('_', ' ')}
                                </div>
                                <Progress value={score} className="mt-2 h-1.5" />
                              </div>
                            ))}
                          </div>
                        </Card>
                      )}
                      
                      {/* Architecture Assessment */}
                      {architectureResult.validation.ai_comparison?.architecture_assessment && (
                        <Card className="p-5 bg-card/60 backdrop-blur-xl border-border/30">
                          <h4 className="font-semibold mb-3">Architecture Assessment</h4>
                          <div className="grid gap-3 md:grid-cols-2">
                            {Object.entries(architectureResult.validation.ai_comparison.architecture_assessment)
                              .filter(([key, value]) => value !== 'Not defined')
                              .map(([key, value]) => (
                              <div key={key} className="p-3 rounded-lg bg-muted/20 border border-border/20">
                                <h5 className="text-xs font-semibold text-foreground/80 capitalize mb-1">{key.replace('_', ' ')}</h5>
                                <p className="text-sm text-muted-foreground">{value}</p>
                              </div>
                            ))}
                          </div>
                        </Card>
                      )}
                      
                      {/* AI Insights */}
                      {architectureResult.validation.ai_comparison?.insights && (
                        <Card className="p-5 bg-gradient-to-r from-primary/5 to-accent/5 border-primary/20">
                          <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <Sparkles className="size-4 text-primary" />
                            AI Insights
                          </h4>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {architectureResult.validation.ai_comparison.insights}
                          </p>
                        </Card>
                      )}
                      
                      {/* Strengths and Gaps */}
                      <div className="grid gap-4 md:grid-cols-2">
                        {architectureResult.validation.ai_comparison?.strengths?.length > 0 && (
                          <Card className="p-5 bg-card/60 backdrop-blur-xl border-emerald-500/20">
                            <h4 className="font-semibold mb-3 text-emerald-500 flex items-center gap-2">
                              <CheckCircle className="size-4" />
                              Strengths
                            </h4>
                            <ul className="space-y-2">
                              {architectureResult.validation.ai_comparison.strengths.map((strength, index) => (
                                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                                  <div className="w-1 h-1 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                                  {strength}
                                </li>
                              ))}
                            </ul>
                          </Card>
                        )}
                        
                        {architectureResult.validation.ai_comparison?.gaps?.length > 0 && (
                          <Card className="p-5 bg-card/60 backdrop-blur-xl border-amber-500/20">
                            <h4 className="font-semibold mb-3 text-amber-500 flex items-center gap-2">
                              <AlertTriangle className="size-4" />
                              Improvements
                            </h4>
                            <ul className="space-y-2">
                              {architectureResult.validation.ai_comparison.gaps.map((gap, index) => (
                                <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                                  <div className="w-1 h-1 rounded-full bg-amber-500 mt-2 flex-shrink-0" />
                                  {gap}
                                </li>
                              ))}
                            </ul>
                          </Card>
                        )}
                      </div>

                      {/* AI Agent Results */}
                      {architectureResult.validation.agent_recommendations?.agents_results && (
                        <div className="grid gap-4 md:grid-cols-2">
                          {architectureResult.validation.agent_recommendations.agents_results.map((agent, index) => (
                            <Card key={index} className="p-4 bg-card/60 backdrop-blur-xl border-border/30">
                              <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                  {agent.agent === 'security' && <Shield className="size-4 text-red-500" />}
                                  {agent.agent === 'performance' && <CheckCircle className="size-4 text-green-500" />}
                                  {agent.agent === 'cost_optimization' && <AlertTriangle className="size-4 text-orange-500" />}
                                  {agent.agent === 'architecture' && <Code className="size-4 text-blue-500" />}
                                  <h4 className="font-medium capitalize text-sm">{agent.agent?.replace('_', ' ')}</h4>
                                  <Badge variant={agent.status === 'completed' ? 'default' : 'secondary'} className="text-[10px] ml-auto">
                                    {agent.status}
                                  </Badge>
                                </div>
                                {agent.recommendations && (
                                  <ul className="space-y-1">
                                    {agent.recommendations.slice(0, 3).map((rec, i) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <div className="w-1 h-1 bg-primary rounded-full mt-1.5 flex-shrink-0" />
                                        {typeof rec === 'string' ? rec : rec.recommendation || rec.feature}
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            </Card>
                          ))}
                        </div>
                      )}

                      {/* Prioritized Recommendations */}
                      {architectureResult.validation.recommendations && (
                        <Card className="p-5 bg-card/60 backdrop-blur-xl border-border/30">
                          <h4 className="font-semibold mb-3">Prioritized Recommendations</h4>
                          <div className="space-y-3">
                            {architectureResult.validation.recommendations.critical?.length > 0 && (
                              <div>
                                <h5 className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1.5">Critical</h5>
                                <ul className="space-y-1">
                                  {architectureResult.validation.recommendations.critical.map((rec, index) => (
                                    <li key={index} className="text-sm text-muted-foreground">• {rec.title}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {architectureResult.validation.recommendations.high?.length > 0 && (
                              <div>
                                <h5 className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-1.5">High</h5>
                                <ul className="space-y-1">
                                  {architectureResult.validation.recommendations.high.map((rec, index) => (
                                    <li key={index} className="text-sm text-muted-foreground">• {rec.title}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {architectureResult.validation.recommendations.medium?.length > 0 && (
                              <div>
                                <h5 className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-1.5">Medium</h5>
                                <ul className="space-y-1">
                                  {architectureResult.validation.recommendations.medium.map((rec, index) => (
                                    <li key={index} className="text-sm text-muted-foreground">• {rec.title}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </Card>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </Card>



          </>
        )}

        {!isGenerating && !architectureResult && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 animate-slide-up">
            <div className="relative">
              <div className="absolute inset-0 animate-pulse rounded-full bg-primary/10 blur-2xl scale-150" />
              <div className="relative flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 border border-border/30">
                <Sparkles className="size-8 text-primary/40" />
              </div>
            </div>
            <div className="text-center space-y-2 max-w-sm">
              <h3 className="text-lg font-semibold text-foreground">Ready to Generate</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Describe your architecture requirements and AI will design a complete Azure architecture diagram
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground/60">
              <span className="flex items-center gap-1"><Eye className="size-3" /> Visual Diagram</span>
              <span className="flex items-center gap-1"><Code className="size-3" /> XML + Mermaid</span>
              <span className="flex items-center gap-1"><Shield className="size-3" /> Validation</span>
            </div>
          </div>
        )}
        </div>
        </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}



