"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Shield,
  Zap,
  Server,
  DollarSign,
  Settings,
  Download,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { useState } from "react"

interface ServiceDiff {
  service_name: string
  diff_type: string
  category: string
  impact_severity: string
  impact_categories: string[]
  impact_description: string
  remediation: string
}

interface ConnectionDiff {
  source: string
  target: string
  diff_type: string
  label: string
  impact_severity: string
  impact_description: string
  remediation: string
}

interface DiffReport {
  report_type?: string
  executive_summary?: string
  overall_match?: {
    percentage: number
    service_match: number
    connection_match: number
    pattern_match: boolean
  }
  impact_analysis?: {
    risk_score: number
    risk_level: string
    severity_counts: Record<string, number>
    category_impacts: Record<string, number>
    total_differences: number
    total_missing: number
    total_extra: number
  }
  services?: {
    matching: ServiceDiff[]
    missing: ServiceDiff[]
    extra: ServiceDiff[]
  }
  connections?: {
    matching: ConnectionDiff[]
    missing: ConnectionDiff[]
    extra: ConnectionDiff[]
  }
  remediation_plan?: Array<{
    priority: number
    type: string
    item: string
    severity: string
    action: string
    impact: string
    estimated_effort: string
  }>
  detailed_findings?: string[]
  ai_expert_analysis?: {
    enhanced: boolean
    expert_assessment?: string
    priority_actions?: string[]
    risk_analysis?: string
    well_architected_impact?: Record<string, string>
  }
  markdown_report?: string
}

interface DiffViewerProps {
  report: DiffReport
  onDownloadReport?: () => void
}

const severityColor = (severity: string) => {
  switch (severity) {
    case "critical": return "destructive"
    case "high": return "destructive"
    case "medium": return "secondary"
    case "low": return "outline"
    default: return "secondary"
  }
}

const severityIcon = (severity: string) => {
  switch (severity) {
    case "critical": return <XCircle className="size-4 text-red-500" />
    case "high": return <AlertTriangle className="size-4 text-orange-500" />
    case "medium": return <AlertTriangle className="size-4 text-yellow-500" />
    case "low": return <CheckCircle2 className="size-4 text-blue-500" />
    default: return null
  }
}

const categoryIcon = (category: string) => {
  switch (category) {
    case "security": return <Shield className="size-3.5" />
    case "performance": return <Zap className="size-3.5" />
    case "reliability": return <Server className="size-3.5" />
    case "cost": return <DollarSign className="size-3.5" />
    case "operational": return <Settings className="size-3.5" />
    default: return null
  }
}

export function DiffViewer({ report, onDownloadReport }: DiffViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    missing: true,
    extra: false,
    matching: false,
    connections: true,
    remediation: true,
  })

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const matchPct = report.overall_match?.percentage ?? 0
  const impact = report.impact_analysis

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <Card className="p-6 border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <h3 className="text-lg font-semibold mb-2">Executive Summary</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{report.executive_summary}</p>
      </Card>

      {/* Match Scores */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Overall Match</p>
          <p className={`text-3xl font-bold ${matchPct >= 80 ? "text-green-600" : matchPct >= 50 ? "text-yellow-600" : "text-red-600"}`}>
            {matchPct.toFixed(0)}%
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Service Match</p>
          <p className="text-3xl font-bold text-blue-600">
            {(report.overall_match?.service_match ?? 0).toFixed(0)}%
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Connection Match</p>
          <p className="text-3xl font-bold text-purple-600">
            {(report.overall_match?.connection_match ?? 0).toFixed(0)}%
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Risk Level</p>
          <Badge
            variant={impact?.risk_level === "Critical" ? "destructive" : impact?.risk_level === "High" ? "destructive" : "secondary"}
            className="text-lg px-4 py-1"
          >
            {impact?.risk_level ?? "Unknown"}
          </Badge>
        </Card>
      </div>

      {/* Impact by Severity */}
      {impact && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold">Impact by Severity</h4>
            <span className="text-sm text-muted-foreground">{impact.total_differences} total differences</span>
          </div>
          <div className="flex gap-3">
            {Object.entries(impact.severity_counts || {}).map(([severity, count]) =>
              count > 0 ? (
                <div key={severity} className="flex items-center gap-1.5">
                  {severityIcon(severity)}
                  <span className="text-sm font-medium capitalize">{severity}:</span>
                  <span className="text-sm">{count}</span>
                </div>
              ) : null
            )}
          </div>
          {impact.category_impacts && Object.keys(impact.category_impacts).length > 0 && (
            <div className="flex gap-3 mt-3 pt-3 border-t">
              {Object.entries(impact.category_impacts).map(([cat, count]) => (
                <div key={cat} className="flex items-center gap-1">
                  {categoryIcon(cat)}
                  <span className="text-xs capitalize">{cat}: {count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Missing Services */}
      {report.services?.missing && report.services.missing.length > 0 && (
        <Card className="p-4 border-red-200">
          <button
            className="flex items-center justify-between w-full"
            onClick={() => toggleSection("missing")}
          >
            <div className="flex items-center gap-2">
              <XCircle className="size-5 text-red-500" />
              <h4 className="font-semibold">Missing Services ({report.services.missing.length})</h4>
            </div>
            {expandedSections.missing ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {expandedSections.missing && (
            <div className="mt-4 space-y-3">
              {report.services.missing.map((svc, idx) => (
                <div key={idx} className="rounded-lg bg-red-50 border border-red-200 p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {severityIcon(svc.impact_severity)}
                      <span className="font-medium">{svc.service_name}</span>
                      <Badge variant="outline" className="text-xs">{svc.category}</Badge>
                    </div>
                    <Badge variant={severityColor(svc.impact_severity) as any}>
                      {svc.impact_severity}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1.5">{svc.impact_description}</p>
                  <p className="text-xs text-blue-700 mt-1">💡 {svc.remediation}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Extra Services */}
      {report.services?.extra && report.services.extra.length > 0 && (
        <Card className="p-4 border-yellow-200">
          <button
            className="flex items-center justify-between w-full"
            onClick={() => toggleSection("extra")}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-yellow-500" />
              <h4 className="font-semibold">Extra Services ({report.services.extra.length})</h4>
            </div>
            {expandedSections.extra ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {expandedSections.extra && (
            <div className="mt-4 space-y-2">
              {report.services.extra.map((svc, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded-lg bg-yellow-50 border border-yellow-200 p-3">
                  <AlertTriangle className="size-4 text-yellow-500" />
                  <span className="font-medium text-sm">{svc.service_name}</span>
                  <Badge variant="outline" className="text-xs">{svc.category}</Badge>
                  <span className="text-xs text-muted-foreground ml-auto">Not in expected</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Matching Services */}
      {report.services?.matching && report.services.matching.length > 0 && (
        <Card className="p-4 border-green-200">
          <button
            className="flex items-center justify-between w-full"
            onClick={() => toggleSection("matching")}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-5 text-green-500" />
              <h4 className="font-semibold">Matching Services ({report.services.matching.length})</h4>
            </div>
            {expandedSections.matching ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {expandedSections.matching && (
            <div className="mt-4 flex flex-wrap gap-2">
              {report.services.matching.map((svc, idx) => (
                <Badge key={idx} variant="outline" className="bg-green-50 text-green-700 border-green-300">
                  <CheckCircle2 className="size-3 mr-1" />
                  {svc.service_name}
                </Badge>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Missing Connections */}
      {report.connections?.missing && report.connections.missing.length > 0 && (
        <Card className="p-4 border-orange-200">
          <button
            className="flex items-center justify-between w-full"
            onClick={() => toggleSection("connections")}
          >
            <div className="flex items-center gap-2">
              <ArrowRight className="size-5 text-orange-500" />
              <h4 className="font-semibold">Missing Connections ({report.connections.missing.length})</h4>
            </div>
            {expandedSections.connections ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {expandedSections.connections && (
            <div className="mt-4 space-y-2">
              {report.connections.missing.map((conn, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded-lg bg-orange-50 border border-orange-200 p-3">
                  {severityIcon(conn.impact_severity)}
                  <span className="text-sm font-medium">{conn.source}</span>
                  <ArrowRight className="size-3 text-muted-foreground" />
                  <span className="text-sm font-medium">{conn.target}</span>
                  {conn.label && <span className="text-xs text-muted-foreground">({conn.label})</span>}
                  <Badge variant={severityColor(conn.impact_severity) as any} className="ml-auto text-xs">
                    {conn.impact_severity}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Remediation Plan */}
      {report.remediation_plan && report.remediation_plan.length > 0 && (
        <Card className="p-4">
          <button
            className="flex items-center justify-between w-full"
            onClick={() => toggleSection("remediation")}
          >
            <h4 className="font-semibold">Remediation Plan ({report.remediation_plan.length} items)</h4>
            {expandedSections.remediation ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {expandedSections.remediation && (
            <div className="mt-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-2 w-12">#</th>
                      <th className="text-left py-2 px-2">Item</th>
                      <th className="text-left py-2 px-2 w-24">Severity</th>
                      <th className="text-left py-2 px-2">Action</th>
                      <th className="text-left py-2 px-2 w-20">Effort</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.remediation_plan.slice(0, 15).map((item, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="py-2 px-2 text-muted-foreground">{item.priority}</td>
                        <td className="py-2 px-2 font-medium">{item.item}</td>
                        <td className="py-2 px-2">
                          <Badge variant={severityColor(item.severity) as any} className="text-xs">
                            {item.severity}
                          </Badge>
                        </td>
                        <td className="py-2 px-2 text-muted-foreground text-xs max-w-xs truncate">
                          {item.action}
                        </td>
                        <td className="py-2 px-2">
                          <Badge variant="outline" className="text-xs">{item.estimated_effort}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* AI Expert Analysis */}
      {report.ai_expert_analysis?.enhanced && (
        <Card className="p-6 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
          <h4 className="font-semibold mb-3 flex items-center gap-2">
            🧠 AI Expert Analysis
          </h4>
          {report.ai_expert_analysis.expert_assessment && (
            <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
              {report.ai_expert_analysis.expert_assessment}
            </p>
          )}
          {report.ai_expert_analysis.priority_actions && (
            <div className="mb-4">
              <h5 className="text-sm font-medium mb-2">Priority Actions:</h5>
              <ol className="list-decimal list-inside space-y-1">
                {report.ai_expert_analysis.priority_actions.map((action, idx) => (
                  <li key={idx} className="text-sm text-muted-foreground">{action}</li>
                ))}
              </ol>
            </div>
          )}
          {report.ai_expert_analysis.risk_analysis && (
            <div>
              <h5 className="text-sm font-medium mb-1">Risk Analysis:</h5>
              <p className="text-sm text-muted-foreground">{report.ai_expert_analysis.risk_analysis}</p>
            </div>
          )}
        </Card>
      )}

      {/* Download Report */}
      {onDownloadReport && (
        <div className="flex justify-center">
          <Button onClick={onDownloadReport} variant="outline" className="gap-2">
            <Download className="size-4" />
            Download Full Report
          </Button>
        </div>
      )}
    </div>
  )
}
