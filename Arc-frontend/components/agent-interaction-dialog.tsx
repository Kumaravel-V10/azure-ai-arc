"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
  CheckCircle2,
  XCircle,
  MessageSquare,
  Shield,
  Zap,
  Layers,
  ArrowRight,
  Sparkles,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  PenLine,
} from "lucide-react"

interface InteractionRequest {
  checkpoint: string
  agent: string
  title: string
  description: string
  findings?: {
    components?: { apis: number; nfrs: number; tech_stack: number; complexity: string; pattern: string }
    references?: { matched: number; services_recommended: number; top_patterns: string[] }
    security?: { compliance_score: number; critical_issues: number; services: string[] }
    performance?: { score: number; optimizations: number; services: string[] }
  }
  architecture?: {
    pattern: string
    total_services: number
    total_connections: number
    total_containers: number
    services: Array<{ name: string; category: string; description: string }>
    connections: Array<{ source: string; target: string; label: string }>
    containers: Array<{ name: string; type: string; purpose: string }>
  }
  recommendations: Array<{ id: string; text: string; type: string }>
}

interface AgentInteractionDialogProps {
  interaction: InteractionRequest
  onRespond: (decision: string, feedback?: string) => void
}

export function AgentInteractionDialog({ interaction, onRespond }: AgentInteractionDialogProps) {
  const [feedback, setFeedback] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedAction, setSelectedAction] = useState<string | null>(null)

  const handleRespond = async (decision: string) => {
    setIsSubmitting(true)
    setSelectedAction(decision)
    onRespond(decision, feedback || undefined)
  }

  const isPreArchitecture = interaction.checkpoint === "pre_architecture"
  const isPostArchitecture = interaction.checkpoint === "post_architecture"

  return (
    <Card className="bg-card/80 backdrop-blur-xl border-primary/30 shadow-2xl shadow-primary/10 overflow-hidden animate-scale-in">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-accent/10 px-6 py-4 border-b border-border/30">
        <div className="flex items-center gap-3">
          <div className="relative flex size-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex size-3 rounded-full bg-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <MessageSquare className="size-4 text-primary" />
              {interaction.title}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">{interaction.description}</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* Pre-Architecture: Show analysis findings */}
        {isPreArchitecture && interaction.findings && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              Analysis Summary
            </h4>
            <div className="grid grid-cols-2 gap-3 stagger-children">
              {/* Components */}
              <div className="rounded-xl bg-blue-500/5 border border-blue-500/20 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-blue-400">
                  <Layers className="size-3" /> Components Extracted
                </div>
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div className="flex justify-between"><span>APIs:</span><span className="font-medium text-foreground">{interaction.findings.components?.apis}</span></div>
                  <div className="flex justify-between"><span>NFRs:</span><span className="font-medium text-foreground">{interaction.findings.components?.nfrs}</span></div>
                  <div className="flex justify-between"><span>Tech Stack:</span><span className="font-medium text-foreground">{interaction.findings.components?.tech_stack}</span></div>
                  <div className="flex justify-between"><span>Complexity:</span><span className="font-medium text-foreground">{interaction.findings.components?.complexity}</span></div>
                </div>
              </div>
              {/* Security */}
              <div className="rounded-xl bg-red-500/5 border border-red-500/20 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-red-400">
                  <Shield className="size-3" /> Security Analysis
                </div>
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div className="flex justify-between"><span>Compliance:</span><span className="font-medium text-foreground">{interaction.findings.security?.compliance_score}%</span></div>
                  <div className="flex justify-between"><span>Critical Issues:</span><span className={`font-medium ${(interaction.findings.security?.critical_issues || 0) > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{interaction.findings.security?.critical_issues}</span></div>
                  {interaction.findings.security?.services?.slice(0, 2).map((s, i) => (
                    <div key={i} className="truncate text-[10px]">• {s}</div>
                  ))}
                </div>
              </div>
              {/* Performance */}
              <div className="rounded-xl bg-amber-500/5 border border-amber-500/20 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-amber-400">
                  <Zap className="size-3" /> Performance Analysis
                </div>
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div className="flex justify-between"><span>Score:</span><span className="font-medium text-foreground">{interaction.findings.performance?.score}%</span></div>
                  <div className="flex justify-between"><span>Optimizations:</span><span className="font-medium text-foreground">{interaction.findings.performance?.optimizations}</span></div>
                </div>
              </div>
              {/* References */}
              <div className="rounded-xl bg-purple-500/5 border border-purple-500/20 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-purple-400">
                  <Layers className="size-3" /> Reference Patterns
                </div>
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div className="flex justify-between"><span>Matched:</span><span className="font-medium text-foreground">{interaction.findings.references?.matched}</span></div>
                  <div className="flex justify-between"><span>Recommended:</span><span className="font-medium text-foreground">{interaction.findings.references?.services_recommended} services</span></div>
                  <div className="flex justify-between"><span>Pattern:</span><span className="font-medium text-foreground truncate">{interaction.findings.components?.pattern}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Post-Architecture: Show designed architecture */}
        {isPostArchitecture && interaction.architecture && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Layers className="size-4 text-primary" />
              Designed Architecture — {interaction.architecture.pattern}
            </h4>
            
            {/* Stats row */}
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 p-2 text-center">
                <div className="text-lg font-bold text-blue-400">{interaction.architecture.total_services}</div>
                <div className="text-[10px] text-muted-foreground">Services</div>
              </div>
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-2 text-center">
                <div className="text-lg font-bold text-emerald-400">{interaction.architecture.total_connections}</div>
                <div className="text-[10px] text-muted-foreground">Connections</div>
              </div>
              <div className="rounded-lg bg-purple-500/10 border border-purple-500/20 p-2 text-center">
                <div className="text-lg font-bold text-purple-400">{interaction.architecture.total_containers}</div>
                <div className="text-[10px] text-muted-foreground">Resource Groups</div>
              </div>
            </div>

            {/* Services list */}
            <div className="rounded-xl border border-border/20 bg-muted/10 p-3 space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar">
              <div className="text-xs font-medium text-muted-foreground mb-1">Services:</div>
              {interaction.architecture.services.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
                  <span className="font-medium text-foreground">{s.name}</span>
                  {s.category && <Badge variant="outline" className="text-[9px] px-1 py-0">{s.category}</Badge>}
                </div>
              ))}
            </div>

            {/* Key connections */}
            {interaction.architecture.connections.length > 0 && (
              <div className="rounded-xl border border-border/20 bg-muted/10 p-3 space-y-1 max-h-28 overflow-y-auto custom-scrollbar">
                <div className="text-xs font-medium text-muted-foreground mb-1">Key Connections:</div>
                {interaction.architecture.connections.slice(0, 6).map((c, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="text-foreground font-medium">{c.source}</span>
                    <ArrowRight className="size-3 text-primary/60" />
                    <span className="text-foreground font-medium">{c.target}</span>
                    {c.label && <span className="text-[9px] opacity-60">({c.label})</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recommendations / Critical issues */}
        {interaction.recommendations?.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recommendations</h4>
            <div className="space-y-1 max-h-24 overflow-y-auto custom-scrollbar">
              {interaction.recommendations.slice(0, 5).map((rec, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  {rec.type === "security_fix" ? (
                    <AlertTriangle className="size-3 text-amber-400 mt-0.5 flex-shrink-0" />
                  ) : (
                    <CheckCircle2 className="size-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                  )}
                  <span>{rec.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Feedback input */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <PenLine className="size-3" />
            Feedback (optional)
          </label>
          <Textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={isPreArchitecture 
              ? "E.g., 'Also add Redis Cache for session management' or 'Use hub-spoke network topology'..."
              : "E.g., 'Remove the cost optimization service' or 'Add VNet peering between the two networks'..."
            }
            className="min-h-[60px] text-sm bg-muted/20 border-border/30 resize-none"
            disabled={isSubmitting}
          />
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <Button
            onClick={() => handleRespond("approve")}
            disabled={isSubmitting}
            className="flex-1 gap-2 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-lg shadow-emerald-500/20 transition-all duration-300 hover:shadow-xl hover:shadow-emerald-500/30"
          >
            {isSubmitting && selectedAction === "approve" ? (
              <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <ThumbsUp className="size-4" />
            )}
            {isPreArchitecture ? "Continue to Design" : "Approve & Finalize"}
          </Button>
          <Button
            onClick={() => handleRespond("modify")}
            disabled={isSubmitting || !feedback}
            variant="outline"
            className="flex-1 gap-2 border-primary/30 hover:bg-primary/10 transition-all duration-300"
          >
            <PenLine className="size-4" />
            Apply Feedback
          </Button>
          <Button
            onClick={() => handleRespond("reject")}
            disabled={isSubmitting}
            variant="outline"
            className="gap-2 border-red-500/30 text-red-400 hover:bg-red-500/10 transition-all duration-300"
          >
            {isSubmitting && selectedAction === "reject" ? (
              <div className="h-4 w-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
            ) : (
              <ThumbsDown className="size-4" />
            )}
            Stop
          </Button>
        </div>
      </div>
    </Card>
  )
}
