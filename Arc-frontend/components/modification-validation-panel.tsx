"use client"

import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import {
  ShieldCheck, Activity, Target, FileCode,
  CheckCircle2, XCircle, AlertTriangle, Info,
  Shield, Gauge, DollarSign, Settings, Zap
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { ModificationValidation } from "@/types"

interface ModificationValidationPanelProps {
  validation: ModificationValidation
  className?: string
}

const WAF_PILLARS: {
  key: keyof ModificationValidation["waf_scores"]
  label: string
  icon: React.ReactNode
}[] = [
  { key: "security", label: "Security", icon: <Shield className="size-4 text-red-500" /> },
  { key: "reliability", label: "Reliability", icon: <Zap className="size-4 text-blue-500" /> },
  { key: "performance", label: "Performance", icon: <Gauge className="size-4 text-amber-500" /> },
  { key: "cost_optimization", label: "Cost Optimization", icon: <DollarSign className="size-4 text-green-500" /> },
  { key: "operational_excellence", label: "Operations", icon: <Settings className="size-4 text-purple-500" /> },
]

function scoreColor(value: number): string {
  if (value >= 75) return "text-green-600 dark:text-green-400"
  if (value >= 50) return "text-amber-600 dark:text-amber-400"
  return "text-red-600 dark:text-red-400"
}

function progressColor(value: number): string {
  if (value >= 75) return "[&>div]:bg-green-500"
  if (value >= 50) return "[&>div]:bg-amber-500"
  return "[&>div]:bg-red-500"
}

function bannerStyle(healthy: boolean, score: number): string {
  if (!healthy) return "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-300"
  if (score >= 75) return "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-300"
  if (score >= 50) return "bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-300"
  return "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-300"
}

export function ModificationValidationPanel({ validation, className }: ModificationValidationPanelProps) {
  if (!validation) return null

  const connValid = validation.connection_validation
  const waf = validation.waf_scores
  const reqs = validation.requirements_fulfillment
  const xml = validation.xml_validation

  // Compute overall health
  const wafAvg = waf
    ? Math.round(Object.values(waf).reduce((a, b) => a + b, 0) / Math.max(Object.keys(waf).length, 1))
    : 0
  const reqsScore = reqs?.score ?? 0
  const isHealthy = (connValid?.valid_flow ?? true) && (xml?.valid ?? true)
  const overallScore = Math.round((wafAvg + reqsScore) / 2)
  const issueCount = (connValid?.issues?.length ?? 0)
  const orphanCount = (connValid?.orphan_services?.length ?? 0)

  return (
    <div className={cn("space-y-4", className)}>
      {/* Overall Health Banner */}
      <div className={cn(
        "flex items-center gap-3 rounded-lg border px-4 py-3",
        bannerStyle(isHealthy, overallScore)
      )}>
        {isHealthy && overallScore >= 75 ? (
          <CheckCircle2 className="size-5 shrink-0" />
        ) : isHealthy && overallScore >= 50 ? (
          <Info className="size-5 shrink-0" />
        ) : (
          <AlertTriangle className="size-5 shrink-0" />
        )}
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {isHealthy && overallScore >= 75
              ? "Architecture looks healthy"
              : isHealthy && overallScore >= 50
                ? "Architecture has some areas for improvement"
                : "Architecture has issues that need attention"}
          </p>
          <p className="text-xs opacity-80">
            WAF avg: {wafAvg} | Requirements: {reqsScore}%
            {issueCount > 0 && ` | ${issueCount} connection issue${issueCount !== 1 ? "s" : ""}`}
            {orphanCount > 0 && ` | ${orphanCount} orphan${orphanCount !== 1 ? "s" : ""}`}
          </p>
        </div>
        <Badge variant="outline" className={cn("text-xs font-bold", scoreColor(overallScore))}>
          {overallScore}%
        </Badge>
      </div>

      {/* Connection Validation */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-blue-500" />
          <span className="text-sm font-semibold">Connection Validation</span>
          {connValid?.valid_flow ? (
            <Badge variant="outline" className="ml-auto text-xs bg-green-500/10 text-green-600 border-green-500/20">
              Valid
            </Badge>
          ) : (
            <Badge variant="outline" className="ml-auto text-xs bg-red-500/10 text-red-600 border-red-500/20">
              Issues Found
            </Badge>
          )}
        </div>

        {connValid?.issues?.length > 0 ? (
          <Alert variant="destructive">
            <AlertTriangle className="size-4" />
            <AlertTitle>Connection Issues</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4 space-y-0.5">
                {connValid.issues.map((issue, i) => (
                  <li key={i} className="text-xs">{issue}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : (
          <div className="flex items-center gap-2 rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-2">
            <CheckCircle2 className="size-4 text-green-500" />
            <span className="text-sm text-green-700 dark:text-green-400">All connections are valid</span>
          </div>
        )}

        {connValid?.orphan_services?.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">Orphan Services (no connections)</span>
            <div className="flex flex-wrap gap-1.5">
              {connValid.orphan_services.map((svc, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  {svc}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      <Separator />

      {/* WAF Pillar Scores */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-emerald-500" />
          <span className="text-sm font-semibold">WAF Pillars</span>
          {waf && (
            <Badge variant="outline" className={cn("ml-auto text-xs font-bold", scoreColor(wafAvg))}>
              avg {wafAvg}
            </Badge>
          )}
        </div>

        {waf ? (
          <div className="space-y-2.5">
            {WAF_PILLARS.map(({ key, label, icon }) => {
              const value = waf[key] ?? 0
              return (
                <div key={key} className="flex items-center gap-3">
                  <div className="shrink-0">{icon}</div>
                  <span className="text-sm text-muted-foreground w-28 shrink-0">{label}</span>
                  <div className={cn("flex-1", progressColor(value))}>
                    <Progress value={value} className="h-2" />
                  </div>
                  <span className={cn("text-sm font-medium w-10 text-right tabular-nums", scoreColor(value))}>
                    {value}
                  </span>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">WAF scores not available</p>
        )}
      </div>

      <Separator />

      {/* Requirements Fulfillment */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Target className="size-4 text-violet-500" />
          <span className="text-sm font-semibold">Requirements</span>
          {reqs && (
            <Badge variant="outline" className={cn("ml-auto text-xs font-bold", scoreColor(reqsScore))}>
              {reqsScore}%
            </Badge>
          )}
        </div>

        {reqs ? (
          <div className="space-y-2.5">
            <div className={cn("w-full", progressColor(reqsScore))}>
              <Progress value={reqsScore} className="h-2" />
            </div>

            {reqs.missing_requirements?.length > 0 && (
              <div className="space-y-1">
                {reqs.missing_requirements.map((req, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <XCircle className="size-4 text-red-500 shrink-0 mt-0.5" />
                    <span className="text-red-700 dark:text-red-400">{req}</span>
                  </div>
                ))}
              </div>
            )}

            {reqs.covered_requirements?.length > 0 && (
              <div className="space-y-1">
                {reqs.covered_requirements.map((req, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="size-4 text-green-500 shrink-0 mt-0.5" />
                    <span className="text-green-700 dark:text-green-400">{req}</span>
                  </div>
                ))}
              </div>
            )}

            {(!reqs.missing_requirements?.length && !reqs.covered_requirements?.length) && (
              <p className="text-sm text-green-700 dark:text-green-400 flex items-center gap-2">
                <CheckCircle2 className="size-4" />
                All requirements met
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Requirements check not available</p>
        )}
      </div>

      <Separator />

      {/* XML Validation */}
      <div className="flex items-center gap-3 rounded-lg border px-3 py-2.5">
        <FileCode className="size-4 text-sky-500" />
        <span className="text-sm font-medium">XML Structure</span>
        <div className="flex-1" />
        {xml?.valid ? (
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="size-4 text-green-500" />
            <span className="text-sm text-green-700 dark:text-green-400">Valid</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <XCircle className="size-4 text-red-500" />
            <span className="text-sm text-red-700 dark:text-red-400">Invalid</span>
          </div>
        )}
      </div>
      {xml && !xml.valid && xml.issues?.length > 0 && (
        <div className="space-y-1 pl-7">
          {xml.issues.map((issue, i) => (
            <p key={i} className="text-xs text-red-600 dark:text-red-400">{issue}</p>
          ))}
        </div>
      )}
    </div>
  )
}
