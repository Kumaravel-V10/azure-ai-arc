"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Shield, Zap, DollarSign, AlertTriangle, CheckCircle2, 
  ChevronDown, ChevronRight, ArrowRight, Globe, Database,
  Server, Network, Lock, Eye, TrendingUp, Users, Layers,
  Target, Lightbulb, AlertCircle, Info, BookOpen, Cpu
} from "lucide-react"
import { cn } from "@/lib/utils"

interface StoryData {
  overview?: {
    title?: string
    description?: string
    architecture_style?: string
    primary_purpose?: string
    target_audience?: string
  }
  data_flow?: {
    summary?: string
    entry_points?: string[]
    processing_layers?: string[]
    data_stores?: string[]
    exit_points?: string[]
  }
  key_capabilities?: Array<{
    capability?: string
    description?: string
    services_involved?: string[]
  }>
  strengths?: string[]
  weaknesses?: string[]
  use_cases?: string[]
  scalability_profile?: {
    horizontal?: string
    vertical?: string
    bottlenecks?: string[]
    max_load_estimate?: string
  }
  disaster_recovery?: {
    rpo?: string
    rto?: string
    ha_features?: string[]
    gaps?: string[]
  }
  compliance_readiness?: string[]
  estimated_monthly_cost?: {
    range?: string
    breakdown?: Array<{ service?: string; estimated_cost?: string }>
    optimization_tips?: string[]
  }
}

interface AgentResults {
  security?: {
    score?: number
    critical_issues?: string[]
    recommendations?: string[]
    compliance?: string[]
    assessment?: string
  }
  performance?: {
    score?: number
    bottlenecks?: string[]
    recommendations?: string[]
    assessment?: string
  }
  cost?: {
    score?: number
    monthly_estimate?: string
    savings_opportunities?: string[]
    recommendations?: string[]
  }
}

interface ArchitectureStoryProps {
  story: StoryData
  agents: AgentResults
  wellArchitectedScores?: Record<string, number>
  missingServices?: string[]
  missingConnections?: Array<{ from?: string; to?: string; label?: string }>
  recommendations?: string[]
  isLoading?: boolean
}

function ScoreRing({ score, label, color, icon: Icon }: { score: number; label: string; color: string; icon: any }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const displayScore = Math.round(score)

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative size-16">
        <svg className="size-16 -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r={radius} fill="none" stroke="currentColor" strokeWidth="4" className="text-muted/20" />
          <circle
            cx="32" cy="32" r={radius} fill="none"
            stroke={color} strokeWidth="4" strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color }}>{displayScore}</span>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <Icon className="size-3" style={{ color }} />
        <span className="text-[10px] font-medium text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}

function CollapsibleSection({ title, icon: Icon, children, defaultOpen = true, badge }: {
  title: string; icon: any; children: React.ReactNode; defaultOpen?: boolean; badge?: string
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  return (
    <div className="border border-border/40 rounded-xl overflow-hidden bg-card/50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors"
      >
        <Icon className="size-4 text-primary shrink-0" />
        <span className="font-semibold text-sm flex-1 text-left">{title}</span>
        {badge && <Badge variant="secondary" className="text-xs">{badge}</Badge>}
        {isOpen ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
      </button>
      {isOpen && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  )
}

export function ArchitectureStory({
  story, agents, wellArchitectedScores = {}, missingServices = [],
  missingConnections = [], recommendations = [], isLoading = false
}: ArchitectureStoryProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <Card key={i} className="p-5">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-3 bg-muted rounded w-2/3" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </div>
          </Card>
        ))}
      </div>
    )
  }

  const overview = story.overview || {}
  const dataFlow = story.data_flow || {}
  const securityAgent = agents.security || {}
  const perfAgent = agents.performance || {}
  const costAgent = agents.cost || {}

  return (
    <div className="space-y-4">
      {/* ─── Overview Hero ─── */}
      <Card className="p-5 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-pink-500/5 border-blue-500/20">
        <div className="space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-xl font-bold text-foreground">{overview.title || "Architecture Analysis"}</h2>
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{overview.description || "AI-analyzed architecture"}</p>
            </div>
            {overview.architecture_style && (
              <Badge className="bg-blue-500/10 text-blue-600 border-blue-500/30 shrink-0 ml-3">
                {overview.architecture_style}
              </Badge>
            )}
          </div>
          <div className="flex flex-wrap gap-3 text-xs">
            {overview.primary_purpose && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Target className="size-3.5 text-violet-500" />
                <span><b>Purpose:</b> {overview.primary_purpose}</span>
              </div>
            )}
            {overview.target_audience && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Users className="size-3.5 text-green-500" />
                <span><b>Audience:</b> {overview.target_audience}</span>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* ─── Well-Architected Scores ─── */}
      {Object.keys(wellArchitectedScores).length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            Well-Architected Framework Scores
          </h3>
          <div className="flex items-center justify-around">
            <ScoreRing score={wellArchitectedScores.security || 0} label="Security" color="#ef4444" icon={Shield} />
            <ScoreRing score={wellArchitectedScores.reliability || 0} label="Reliability" color="#f59e0b" icon={CheckCircle2} />
            <ScoreRing score={wellArchitectedScores.performance || 0} label="Performance" color="#3b82f6" icon={Zap} />
            <ScoreRing score={wellArchitectedScores.cost_optimization || 0} label="Cost" color="#22c55e" icon={DollarSign} />
            <ScoreRing score={wellArchitectedScores.operational_excellence || 0} label="Operations" color="#a855f7" icon={Eye} />
          </div>
        </Card>
      )}

      {/* ─── Data Flow ─── */}
      {dataFlow.summary && (
        <CollapsibleSection title="Data Flow" icon={ArrowRight} badge={`${(dataFlow.entry_points?.length || 0) + (dataFlow.processing_layers?.length || 0) + (dataFlow.data_stores?.length || 0)} layers`}>
          <p className="text-sm text-muted-foreground mb-3">{dataFlow.summary}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(dataFlow.entry_points?.length || 0) > 0 && (
              <div className="rounded-lg bg-green-500/5 border border-green-500/20 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Globe className="size-3.5 text-green-500" />
                  <span className="text-xs font-semibold text-green-700 dark:text-green-400">Entry Points</span>
                </div>
                <ul className="space-y-1">
                  {dataFlow.entry_points!.map((ep, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                      <ArrowRight className="size-3 mt-0.5 text-green-500 shrink-0" />
                      {ep}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(dataFlow.processing_layers?.length || 0) > 0 && (
              <div className="rounded-lg bg-blue-500/5 border border-blue-500/20 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Cpu className="size-3.5 text-blue-500" />
                  <span className="text-xs font-semibold text-blue-700 dark:text-blue-400">Processing Layers</span>
                </div>
                <ul className="space-y-1">
                  {dataFlow.processing_layers!.map((pl, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                      <ArrowRight className="size-3 mt-0.5 text-blue-500 shrink-0" />
                      {pl}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(dataFlow.data_stores?.length || 0) > 0 && (
              <div className="rounded-lg bg-purple-500/5 border border-purple-500/20 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="size-3.5 text-purple-500" />
                  <span className="text-xs font-semibold text-purple-700 dark:text-purple-400">Data Stores</span>
                </div>
                <ul className="space-y-1">
                  {dataFlow.data_stores!.map((ds, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                      <ArrowRight className="size-3 mt-0.5 text-purple-500 shrink-0" />
                      {ds}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(dataFlow.exit_points?.length || 0) > 0 && (
              <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Network className="size-3.5 text-amber-500" />
                  <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">Exit Points</span>
                </div>
                <ul className="space-y-1">
                  {dataFlow.exit_points!.map((ep, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                      <ArrowRight className="size-3 mt-0.5 text-amber-500 shrink-0" />
                      {ep}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ─── Key Capabilities ─── */}
      {(story.key_capabilities?.length || 0) > 0 && (
        <CollapsibleSection title="Key Capabilities" icon={Lightbulb} badge={`${story.key_capabilities!.length}`}>
          <div className="space-y-2.5">
            {story.key_capabilities!.map((cap, i) => (
              <div key={i} className="rounded-lg bg-muted/30 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="size-3.5 text-amber-500" />
                  <span className="text-sm font-medium">{cap.capability}</span>
                </div>
                <p className="text-xs text-muted-foreground ml-5.5">{cap.description}</p>
                {(cap.services_involved?.length || 0) > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5 ml-5.5">
                    {cap.services_involved!.map((s, j) => (
                      <Badge key={j} variant="outline" className="text-[10px] py-0">{s}</Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* ─── Security Analysis (Agent) ─── */}
      <CollapsibleSection title="Security Analysis" icon={Shield} badge={securityAgent.score ? `${securityAgent.score}/100` : undefined}>
        <div className="space-y-3">
          {securityAgent.assessment && (
            <p className="text-sm text-muted-foreground">{securityAgent.assessment}</p>
          )}
          {(securityAgent.critical_issues?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-red-600 dark:text-red-400">Critical Issues</span>
              {securityAgent.critical_issues!.map((issue, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-red-600 dark:text-red-400 bg-red-500/5 rounded-lg px-3 py-2">
                  <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />
                  <span>{typeof issue === 'string' ? issue : JSON.stringify(issue)}</span>
                </div>
              ))}
            </div>
          )}
          {(securityAgent.recommendations?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-muted-foreground">Recommendations</span>
              {securityAgent.recommendations!.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="size-3.5 mt-0.5 shrink-0 text-green-500" />
                  <span>{typeof rec === 'string' ? rec : JSON.stringify(rec)}</span>
                </div>
              ))}
            </div>
          )}
          {(securityAgent.compliance?.length || 0) > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {securityAgent.compliance!.map((c, i) => (
                <Badge key={i} variant="outline" className="text-[10px] border-green-500/30 text-green-600">{typeof c === 'string' ? c : JSON.stringify(c)}</Badge>
              ))}
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* ─── Performance Analysis (Agent) ─── */}
      <CollapsibleSection title="Performance Analysis" icon={Zap} badge={perfAgent.score ? `${perfAgent.score}/100` : undefined}>
        <div className="space-y-3">
          {perfAgent.assessment && (
            <p className="text-sm text-muted-foreground">{perfAgent.assessment}</p>
          )}
          {(perfAgent.bottlenecks?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">Potential Bottlenecks</span>
              {perfAgent.bottlenecks!.map((b, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400 bg-amber-500/5 rounded-lg px-3 py-2">
                  <AlertCircle className="size-3.5 mt-0.5 shrink-0" />
                  <span>{typeof b === 'string' ? b : JSON.stringify(b)}</span>
                </div>
              ))}
            </div>
          )}
          {(perfAgent.recommendations?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-muted-foreground">Recommendations</span>
              {perfAgent.recommendations!.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <TrendingUp className="size-3.5 mt-0.5 shrink-0 text-blue-500" />
                  <span>{typeof rec === 'string' ? rec : JSON.stringify(rec)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* ─── Cost Analysis (Agent) ─── */}
      <CollapsibleSection title="Cost Analysis" icon={DollarSign} badge={costAgent.monthly_estimate || (costAgent.score ? `${costAgent.score}/100` : undefined)}>
        <div className="space-y-3">
          {story.estimated_monthly_cost?.range && (
            <div className="rounded-lg bg-green-500/5 border border-green-500/20 p-3 text-center">
              <p className="text-xs text-muted-foreground mb-1">Estimated Monthly Cost</p>
              <p className="text-lg font-bold text-green-600">{story.estimated_monthly_cost.range}</p>
            </div>
          )}
          {(story.estimated_monthly_cost?.breakdown?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-muted-foreground">Cost Breakdown</span>
              {story.estimated_monthly_cost!.breakdown!.map((item, i) => (
                <div key={i} className="flex items-center justify-between text-xs px-3 py-1.5 rounded bg-muted/30">
                  <span className="text-muted-foreground">{item.service}</span>
                  <span className="font-medium">{item.estimated_cost}</span>
                </div>
              ))}
            </div>
          )}
          {(costAgent.savings_opportunities?.length || 0) > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-green-600">Savings Opportunities</span>
              {costAgent.savings_opportunities!.map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <DollarSign className="size-3.5 mt-0.5 shrink-0 text-green-500" />
                  <span>{typeof s === 'string' ? s : JSON.stringify(s)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* ─── Strengths & Weaknesses ─── */}
      {((story.strengths?.length || 0) > 0 || (story.weaknesses?.length || 0) > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {(story.strengths?.length || 0) > 0 && (
            <Card className="p-4 border-green-500/20">
              <h4 className="text-sm font-semibold mb-2.5 flex items-center gap-2 text-green-600">
                <CheckCircle2 className="size-4" /> Strengths
              </h4>
              <ul className="space-y-1.5">
                {story.strengths!.map((s, i) => (
                  <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                    <span className="text-green-500 mt-0.5">✓</span> {s}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {(story.weaknesses?.length || 0) > 0 && (
            <Card className="p-4 border-amber-500/20">
              <h4 className="text-sm font-semibold mb-2.5 flex items-center gap-2 text-amber-600">
                <AlertTriangle className="size-4" /> Weaknesses
              </h4>
              <ul className="space-y-1.5">
                {story.weaknesses!.map((w, i) => (
                  <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                    <span className="text-amber-500 mt-0.5">!</span> {w}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {/* ─── Missing Services & Connections ─── */}
      {(missingServices.length > 0 || missingConnections.length > 0) && (
        <CollapsibleSection title="Gap Analysis" icon={AlertTriangle} defaultOpen={true} badge={`${missingServices.length + missingConnections.length} gaps`}>
          <div className="space-y-3">
            {missingServices.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-red-600 mb-1.5 block">Missing Services</span>
                <div className="flex flex-wrap gap-1.5">
                  {missingServices.map((s, i) => (
                    <Badge key={i} variant="outline" className="text-xs border-red-500/30 text-red-600 bg-red-500/5">{s}</Badge>
                  ))}
                </div>
              </div>
            )}
            {missingConnections.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-amber-600 mb-1.5 block">Missing Connections</span>
                {missingConnections.map((c, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground py-1">
                    <span className="font-medium">{c.from}</span>
                    <ArrowRight className="size-3 text-amber-500" />
                    <span className="font-medium">{c.to}</span>
                    {c.label && <span className="text-muted-foreground/60 ml-1">({c.label})</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ─── Use Cases ─── */}
      {(story.use_cases?.length || 0) > 0 && (
        <CollapsibleSection title="Supported Use Cases" icon={BookOpen} defaultOpen={false}>
          <div className="flex flex-wrap gap-2">
            {story.use_cases!.map((uc, i) => (
              <Badge key={i} variant="secondary" className="text-xs py-1 px-3">{uc}</Badge>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* ─── Recommendations ─── */}
      {recommendations.length > 0 && (
        <CollapsibleSection title="AI Recommendations" icon={Lightbulb} badge={`${recommendations.length}`}>
          <div className="space-y-2">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground bg-primary/5 rounded-lg px-3 py-2.5">
                <span className="text-primary font-bold text-xs mt-0.5">{i + 1}</span>
                <span className="text-xs">{rec}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  )
}
