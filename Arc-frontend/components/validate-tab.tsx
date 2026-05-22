"use client"

import type React from "react"
import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Shield, FileImage, Upload, Brain, Zap, XCircle, Download, ExternalLink, FileCode } from "lucide-react"
import Image from "next/image"
import { AIValidationResults } from "./ai-validation-results"
import { getApiUrl, API_CONFIG } from "@/lib/config"
import type { ValidationResult } from "@/types"

export function ValidateTab() {
  const [actualFile, setActualFile] = useState<{ name: string; url: string; content?: string } | null>(null)
  const [expectedFile, setExpectedFile] = useState<{ name: string; url: string } | null>(null)
  const [requirements, setRequirements] = useState("")
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [useAI, setUseAI] = useState(true)
  const [showReportModal, setShowReportModal] = useState(false)
  const [isGeneratingTerraform, setIsGeneratingTerraform] = useState(false)
  const [terraformResult, setTerraformResult] = useState<{ terraform: string; services: string[] } | null>(null)

  const handleViewReport = async (validationId: string) => {
    try {
      const response = await fetch(getApiUrl("VALIDATION_REPORT", validationId))
      if (response.ok) {
        const reportData = await response.json()
        console.log('📋 Validation Report:', reportData)
        // For now, just log the report. You could open a modal or new tab
        window.open(getApiUrl("VALIDATION_REPORT", validationId), '_blank')
      }
    } catch (error) {
      console.error('Error fetching validation report:', error)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: "actual" | "expected") => {
    const file = e.target.files?.[0]
    if (file) {
      const url = URL.createObjectURL(file)
      const fileData: { name: string; url: string; content?: string } = { name: file.name, url }

      // Read file content for .drawio files
      if (file.name.endsWith('.drawio')) {
        const content = await file.text()
        fileData.content = content
      }

      if (type === "actual") {
        setActualFile(fileData)
        setTerraformResult(null) // Reset terraform result when new file uploaded
      } else {
        setExpectedFile(fileData)
      }
      setValidationResult(null)
    }
  }

  const handleGenerateTerraform = async () => {
    if (!actualFile?.content) {
      console.error('No Draw.io content available')
      return
    }
    
    setIsGeneratingTerraform(true)
    console.log('🏗️ Generating Terraform from Draw.io...')
    
    try {
      const formData = new FormData()
      formData.append('drawio_xml', actualFile.content)
      
      const response = await fetch(getApiUrl("GENERATE_TERRAFORM_FROM_DRAWIO"), {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      console.log('✅ Terraform generated:', result)
      setTerraformResult({
        terraform: result.terraform,
        services: result.services_detected || []
      })
    } catch (error) {
      console.error('❌ Terraform generation error:', error)
    } finally {
      setIsGeneratingTerraform(false)
    }
  }

  const handleDownloadTerraform = () => {
    if (!terraformResult?.terraform) return
    const blob = new Blob([terraformResult.terraform], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${actualFile?.name?.replace('.drawio', '') || 'architecture'}-terraform.tf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleValidate = async () => {
    setIsValidating(true)
    console.log('🚀 Starting validation...')
    console.log('📊 Request data:', {
      endpoint: '/api/validate',
      actualFile: actualFile?.name,
      expectedFile: expectedFile?.name,
      requirements: requirements.substring(0, 100) + '...'
    })
    
    try {
      let response: Response
      
      if (actualFile || expectedFile) {
        // Use image validation endpoint when files are uploaded
        const formData = new FormData()
        
        // Convert blob URL back to file
        if (actualFile?.url) {
          const actualBlob = await fetch(actualFile.url).then(r => r.blob())
          formData.append('actual_diagram', actualBlob, actualFile.name)
        }
        
        if (expectedFile?.url) {
          const expectedBlob = await fetch(expectedFile.url).then(r => r.blob())
          formData.append('expected_diagram', expectedBlob, expectedFile.name)
        }
        
        if (requirements.trim()) {
          formData.append('requirements', requirements)
        }
        
        console.log('🖼️ Using image validation endpoint with files')
        response = await fetch(getApiUrl("VALIDATE_IMAGE"), {
          method: 'POST',
          body: formData
        })
      } else {
        // Use text validation endpoint when no files uploaded
        console.log('📝 Using text validation endpoint')
        response = await fetch(getApiUrl("VALIDATE"), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            actual_diagram: '',
            expected_diagram: '',
            requirements: requirements || 'General architecture validation',
            validation_type: useAI ? 'full' : 'quick'
          })
        })
      }
      
      console.log('📡 Response status:', response.status)
      console.log('📡 Response ok:', response.ok)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Response error:', errorText)
        throw new Error(`Validation failed: ${response.status} - ${errorText}`)
      }
      
      const result = await response.json()
      console.log('✅ Validation result:', result)
      
      // Transform backend response to match frontend expectations
      const transformedResult = {
        validation_id: result.validation_id || `validation_${Date.now()}`,
        validation_score: result.validation_score || result.compliance_score || 0,
        compliance_score: result.compliance_score || result.validation_score || 0,
        critical_issues: result.critical_issues || [],
        quick_wins: result.quick_wins || [],
        ai_comparison: result.ai_comparison || {},
        agent_recommendations: result.agent_recommendations || { agents_results: [], summary: {} },
        recommendations: result.recommendations || { critical: [], high: [], medium: [] },
        validation_type: result.validation_type || (useAI ? 'full' : 'quick'),
        architecture_complexity: result.architecture_complexity || 'standard',
        processing_details: result.processing_details || {},
        status: result.status || { overall: 'completed' },
        timestamp: result.timestamp || result.processing_details?.validation_timestamp || new Date().toISOString()
      }
      
      setValidationResult(transformedResult)
      
    } catch (error) {
      console.error('❌ Validation error:', error)
      setValidationResult({
        error: true,
        message: error instanceof Error ? error.message : 'Backend service unavailable. Please start the backend server.',
        validation_id: 'error_' + Date.now(),
        compliance_score: 0,
        critical_issues: [{ issue: 'Backend connection failed', severity: 'critical' }],
        quick_wins: [{ improvement: 'Start backend server', impact: 'Required for validation' }],
        ai_comparison: { error: 'Service unavailable' },
        agent_recommendations: { agents_results: [] },
        recommendations: { critical: [], high: [], medium: [] }
      })
    }
    
    setIsValidating(false)
    console.log('🏁 Validation completed')
  }

  const canValidate = (actualFile !== null || expectedFile !== null) || requirements.trim().length > 0

  return (
    <div className="space-y-6">
      {/* AI Toggle */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="size-6 text-blue-600" />
            <div>
              <h3 className="font-semibold text-foreground">AI-Powered Validation</h3>
              <p className="text-sm text-muted-foreground">Use OpenAI + Agents for comprehensive analysis</p>
            </div>
          </div>
          <Button
            variant={useAI ? "default" : "outline"}
            size="sm"
            onClick={() => setUseAI(!useAI)}
            className="gap-2"
          >
            {useAI ? <Brain className="size-4" /> : <Zap className="size-4" />}
            {useAI ? "AI Mode" : "Quick Mode"}
          </Button>
        </div>
      </Card>

      {/* Requirements Input */}
      <Card className="p-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="requirements" className="text-sm font-medium text-foreground">
              Architecture Requirements {!actualFile && !expectedFile ? '(Required)' : '(Optional)'}
            </Label>
            <p className="mt-1 text-xs text-muted-foreground">
              {!actualFile && !expectedFile 
                ? 'Provide requirements for text-based validation or upload diagrams for image validation'
                : 'Provide context for better AI analysis of uploaded diagrams'
              }
            </p>
          </div>
          <Textarea
            id="requirements"
            placeholder={!actualFile && !expectedFile 
              ? "Describe your architecture requirements for validation..."
              : "e.g., Multi-tenant SaaS application with high availability, security compliance, and global distribution..."
            }
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            className="min-h-[100px]"
            required={!actualFile && !expectedFile}
          />
        </div>
      </Card>
      {/* Upload Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Actual Diagram Upload */}
        <Card className="bg-card p-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="actual-upload" className="text-sm font-medium text-foreground">
                Actual Architecture Diagram
              </Label>
              <p className="mt-1 text-xs text-muted-foreground">Upload the implemented architecture</p>
            </div>

            <div className="relative">
              <input
                id="actual-upload"
                type="file"
                accept=".png,.jpg,.jpeg,.drawio"
                onChange={(e) => handleFileUpload(e, "actual")}
                className="sr-only"
              />
              <label
                htmlFor="actual-upload"
                className="flex cursor-pointer flex-col items-center gap-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 px-4 py-8 transition-colors hover:bg-secondary"
              >
                {actualFile ? (
                  <div className="relative h-48 w-full">
                    <Image
                      src={actualFile.url || "/placeholder.svg"}
                      alt="Actual diagram"
                      fill
                      className="object-contain"
                    />
                  </div>
                ) : (
                  <>
                    <Upload className="size-10 text-muted-foreground" />
                    <div className="text-center">
                      <p className="text-sm font-medium text-foreground">Click to upload</p>
                      <p className="mt-1 text-xs text-muted-foreground">PNG, JPG, or Draw.io file</p>
                    </div>
                  </>
                )}
              </label>
            </div>

            {actualFile && (
              <div className="space-y-3">
                <div className="rounded-lg bg-secondary/50 p-3">
                  <div className="flex items-center gap-2">
                    <FileImage className="size-4 text-accent" />
                    <p className="text-xs font-medium text-foreground">{actualFile.name}</p>
                  </div>
                </div>
                
                {/* Terraform Generation for .drawio files */}
                {actualFile.name.endsWith('.drawio') && actualFile.content && (
                  <div className="space-y-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-2"
                      onClick={handleGenerateTerraform}
                      disabled={isGeneratingTerraform}
                    >
                      <FileCode className="size-4" />
                      {isGeneratingTerraform ? "Generating Terraform..." : "Generate Terraform from Draw.io"}
                    </Button>
                    
                    {terraformResult && (
                      <div className="rounded-lg bg-green-50 border border-green-200 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-green-700">
                            Terraform Ready ({terraformResult.services.length} services)
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 h-7 text-xs"
                            onClick={handleDownloadTerraform}
                          >
                            <Download className="size-3" />
                            Download .tf
                          </Button>
                        </div>
                        {terraformResult.services.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {terraformResult.services.slice(0, 5).map((service, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {service}
                              </Badge>
                            ))}
                            {terraformResult.services.length > 5 && (
                              <Badge variant="secondary" className="text-xs">
                                +{terraformResult.services.length - 5} more
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>

        {/* Expected Diagram Upload */}
        <Card className="bg-card p-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="expected-upload" className="text-sm font-medium text-foreground">
                Expected Architecture Diagram
              </Label>
              <p className="mt-1 text-xs text-muted-foreground">Upload the target architecture</p>
            </div>

            <div className="relative">
              <input
                id="expected-upload"
                type="file"
                accept=".png,.jpg,.jpeg,.drawio"
                onChange={(e) => handleFileUpload(e, "expected")}
                className="sr-only"
              />
              <label
                htmlFor="expected-upload"
                className="flex cursor-pointer flex-col items-center gap-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 px-4 py-8 transition-colors hover:bg-secondary"
              >
                {expectedFile ? (
                  <div className="relative h-48 w-full">
                    <Image
                      src={expectedFile.url || "/placeholder.svg"}
                      alt="Expected diagram"
                      fill
                      className="object-contain"
                    />
                  </div>
                ) : (
                  <>
                    <Upload className="size-10 text-muted-foreground" />
                    <div className="text-center">
                      <p className="text-sm font-medium text-foreground">Click to upload</p>
                      <p className="mt-1 text-xs text-muted-foreground">PNG, JPG, or Draw.io file</p>
                    </div>
                  </>
                )}
              </label>
            </div>

            {expectedFile && (
              <div className="rounded-lg bg-secondary/50 p-3">
                <div className="flex items-center gap-2">
                  <FileImage className="size-4 text-accent" />
                  <p className="text-xs font-medium text-foreground">{expectedFile.name}</p>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Validate Button */}
      <div className="flex justify-center">
        <Button
          onClick={handleValidate}
          disabled={!canValidate || isValidating}
          className="w-full gap-2 lg:w-auto lg:px-16"
          size="lg"
        >
          <Shield className="size-4" />
          {isValidating 
            ? (useAI ? "AI Multi-Agent Analysis..." : "Quick Analysis...") 
            : "Validate Architecture"
          }
        </Button>
      </div>

      {/* Validation Results Section */}
      {isValidating && (
        <Card className="bg-card p-8 border-2 border-blue-200">
          <div className="flex flex-col items-center justify-center space-y-6">
            <div className="size-16 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
            <div className="text-center space-y-2">
              <h3 className="text-lg font-semibold text-foreground">Analyzing Architecture...</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                {useAI 
                  ? "Multi-Agent AI analyzing architecture (Security → Performance → Architecture → Cost)..." 
                  : "Processing validation with intelligent design analysis..."
                }
              </p>
            </div>
            <div className="flex gap-2 mt-4">
              <div className="h-2 w-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="h-2 w-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="h-2 w-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </Card>
      )}

      {validationResult && !isValidating && (
        <Card className="bg-card p-6">
          {validationResult.error ? (
            <div className="text-center py-8">
              <div className="text-red-500 mb-4">
                <XCircle className="size-12 mx-auto mb-2" />
                <h3 className="text-lg font-semibold">Validation Failed</h3>
              </div>
              <p className="text-muted-foreground mb-4">{validationResult.message}</p>
              <Button onClick={() => setValidationResult(null)} variant="outline">
                Try Again
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Validation Results Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">Validation Results</h3>
                  {validationResult.processing_details?.total_duration && (
                    <p className="text-sm text-muted-foreground">
                      Completed in {validationResult.processing_details.total_duration.toFixed(2)}s
                    </p>
                  )}
                </div>
                <div className="flex gap-2 items-center">
                  {validationResult.validation_id && (
                    <Button 
                      onClick={() => handleViewReport(validationResult.validation_id!)}
                      variant="outline" 
                      size="sm"
                      className="gap-2"
                    >
                      <ExternalLink className="size-4" />
                      Detailed Report
                    </Button>
                  )}
                  <Badge variant={validationResult.compliance_score >= 80 ? 'default' : validationResult.compliance_score >= 60 ? 'secondary' : 'destructive'}>
                    Score: {validationResult.compliance_score}%
                  </Badge>
                  {validationResult.status?.overall && (
                    <Badge variant="outline">
                      {validationResult.status.overall}
                    </Badge>
                  )}
                </div>
              </div>
              
              {/* Processing Details Summary */}
              {validationResult.processing_details && (
                <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2 text-sm text-blue-800">
                    <Brain className="size-4" />
                    <span className="font-medium">Multi-Agent Analysis:</span>
                    <span>
                      {validationResult.processing_details.components_executed?.join(', ') || 'Standard validation'}
                    </span>
                    {validationResult.processing_details.services_detected > 0 && (
                      <span className="ml-auto">
                        • {validationResult.processing_details.services_detected} services detected
                      </span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Main Validation Component */}
              <AIValidationResults result={validationResult} />
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
