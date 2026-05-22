"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  MessageCircleQuestion,
  Sparkles,
  ArrowRight,
  Brain,
  Loader2,
  CheckCircle2,
  SkipForward,
  Target,
  Layers,
  Shield,
  Zap,
  Globe,
  Database,
  Users,
} from "lucide-react"
import { API_CONFIG, getApiUrl } from "@/lib/config"

interface ClarifyingQuestion {
  id: string
  question: string
  category: "architecture" | "security" | "performance" | "scale" | "integration" | "business"
  options?: string[]
  placeholder?: string
  type: "select" | "text" | "multi-select"
  importance: "critical" | "recommended" | "optional"
  why: string
}

interface ClarifyingQuestionsDialogProps {
  requirements: string
  onComplete: (enrichedRequirements: string, answers: Record<string, string>) => void
  onSkip: () => void
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  architecture: <Layers className="size-3.5 text-blue-400" />,
  security: <Shield className="size-3.5 text-red-400" />,
  performance: <Zap className="size-3.5 text-amber-400" />,
  scale: <Globe className="size-3.5 text-emerald-400" />,
  integration: <Database className="size-3.5 text-purple-400" />,
  business: <Users className="size-3.5 text-cyan-400" />,
}

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  recommended: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  optional: "bg-blue-500/10 text-blue-400 border-blue-500/20",
}

export function ClarifyingQuestionsDialog({ requirements, onComplete, onSkip }: ClarifyingQuestionsDialogProps) {
  const [questions, setQuestions] = useState<ClarifyingQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState(0)

  // Fetch clarifying questions from the backend
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setIsLoading(true)
        const response = await fetch(`${API_CONFIG.BASE_URL}/api/clarify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ requirements }),
        })
        
        if (!response.ok) {
          throw new Error(`Failed to get questions: ${response.status}`)
        }
        
        const data = await response.json()
        setQuestions(data.questions || [])
      } catch (err: any) {
        console.error("Failed to fetch clarifying questions:", err)
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchQuestions()
  }, [requirements])

  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }))
  }

  const handleSubmit = () => {
    setIsSubmitting(true)
    
    // Build enriched requirements from answers
    const enrichments: string[] = []
    for (const q of questions) {
      const answer = answers[q.id]
      if (answer && answer.trim()) {
        enrichments.push(`[${q.category.toUpperCase()}] ${q.question}: ${answer}`)
      }
    }
    
    const enrichedRequirements = enrichments.length > 0
      ? `${requirements}\n\n--- CLARIFIED REQUIREMENTS ---\n${enrichments.join("\n")}`
      : requirements
    
    onComplete(enrichedRequirements, answers)
  }

  const answeredCount = Object.values(answers).filter(v => v && v.trim()).length
  const criticalQuestions = questions.filter(q => q.importance === "critical")
  const criticalAnswered = criticalQuestions.filter(q => answers[q.id]?.trim()).length
  const allCriticalAnswered = criticalAnswered === criticalQuestions.length

  if (isLoading) {
    return (
      <Card className="bg-card/80 backdrop-blur-xl border-primary/20 p-8 shadow-2xl animate-scale-in">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <Brain className="size-8 text-primary animate-pulse" />
            <span className="absolute -top-1 -right-1 flex size-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex size-3 rounded-full bg-primary" />
            </span>
          </div>
          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold text-foreground">Analyzing Your Requirements</h3>
            <p className="text-sm text-muted-foreground">
              AI is reading your requirements and preparing intelligent questions to ensure the best architecture...
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3 animate-spin" />
            <span>Identifying gaps and ambiguities...</span>
          </div>
        </div>
      </Card>
    )
  }

  if (error) {
    // On error, allow skipping directly
    return (
      <Card className="bg-card/80 backdrop-blur-xl border-amber-500/20 p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Could not generate clarifying questions. You can proceed directly.</p>
          <Button onClick={onSkip} variant="default" size="sm">
            Continue Without Questions <ArrowRight className="ml-2 size-3.5" />
          </Button>
        </div>
      </Card>
    )
  }

  if (questions.length === 0) {
    // No questions needed - requirements are clear
    return (
      <Card className="bg-card/80 backdrop-blur-xl border-emerald-500/20 p-6 shadow-xl animate-scale-in">
        <div className="flex items-center gap-4">
          <CheckCircle2 className="size-6 text-emerald-500" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-foreground">Requirements are clear!</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Your requirements are detailed enough. Proceeding with architecture generation...
            </p>
          </div>
          <Loader2 className="size-4 text-primary animate-spin" />
        </div>
      </Card>
    )
  }

  return (
    <Card className="bg-card/80 backdrop-blur-xl border-primary/20 shadow-2xl shadow-primary/5 overflow-hidden animate-scale-in">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary/10 via-accent/5 to-primary/10 px-6 py-4 border-b border-border/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <MessageCircleQuestion className="size-5 text-primary" />
              <span className="absolute -top-0.5 -right-0.5 flex size-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Before I design your architecture...</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                A few quick questions to ensure the best possible result
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] px-2 py-0.5">
              {answeredCount}/{questions.length} answered
            </Badge>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onSkip}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              <SkipForward className="size-3 mr-1" />
              Skip
            </Button>
          </div>
        </div>
      </div>

      {/* Questions */}
      <div className="p-6 space-y-4 max-h-[500px] overflow-y-auto custom-scrollbar">
        {questions.map((q, idx) => (
          <div
            key={q.id}
            className="group rounded-xl border border-border/30 bg-gradient-to-br from-muted/20 to-transparent p-4 space-y-3 transition-all duration-300 hover:border-primary/20 hover:shadow-lg hover:shadow-primary/5"
            style={{ animationDelay: `${idx * 80}ms` }}
          >
            {/* Question header */}
            <div className="flex items-start gap-3">
              <div className="shrink-0 mt-0.5 flex size-7 items-center justify-center rounded-lg bg-muted/50">
                {CATEGORY_ICONS[q.category]}
              </div>
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-foreground leading-snug">{q.question}</p>
                  <Badge variant="outline" className={`text-[9px] px-1.5 py-0 shrink-0 ${IMPORTANCE_COLORS[q.importance]}`}>
                    {q.importance}
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground/80 italic">
                  <Target className="size-2.5 inline mr-1" />
                  {q.why}
                </p>
              </div>
            </div>

            {/* Answer input */}
            <div className="ml-10">
              {q.type === "select" && q.options ? (
                <Select
                  value={answers[q.id] || ""}
                  onValueChange={(val) => handleAnswerChange(q.id, val)}
                >
                  <SelectTrigger className="bg-card/60 border-border/50 h-9 text-xs">
                    <SelectValue placeholder={q.placeholder || "Select an option..."} />
                  </SelectTrigger>
                  <SelectContent>
                    {q.options.map((opt) => (
                      <SelectItem key={opt} value={opt} className="text-xs">
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : q.type === "multi-select" && q.options ? (
                <div className="flex flex-wrap gap-1.5">
                  {q.options.map((opt) => {
                    const selected = (answers[q.id] || "").split(",").includes(opt)
                    return (
                      <button
                        key={opt}
                        onClick={() => {
                          const current = answers[q.id] ? answers[q.id].split(",").filter(Boolean) : []
                          const updated = selected
                            ? current.filter(v => v !== opt)
                            : [...current, opt]
                          handleAnswerChange(q.id, updated.join(","))
                        }}
                        className={`text-[11px] px-2.5 py-1 rounded-full border transition-all duration-200 ${
                          selected
                            ? "bg-primary/10 border-primary/40 text-primary font-medium"
                            : "bg-muted/30 border-border/40 text-muted-foreground hover:border-primary/20"
                        }`}
                      >
                        {opt}
                      </button>
                    )
                  })}
                </div>
              ) : (
                <Input
                  value={answers[q.id] || ""}
                  onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                  placeholder={q.placeholder || "Type your answer..."}
                  className="bg-card/60 border-border/50 h-9 text-xs"
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-border/30 bg-muted/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {!allCriticalAnswered && criticalQuestions.length > 0 ? (
              <>
                <AlertCircleIcon className="size-3.5 text-amber-400" />
                <span>{criticalQuestions.length - criticalAnswered} critical question(s) unanswered</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="size-3.5 text-emerald-400" />
                <span>All critical questions answered</span>
              </>
            )}
          </div>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="gap-2 bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 shadow-lg shadow-primary/20"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Sparkles className="size-3.5" />
                Generate Architecture
                <ArrowRight className="size-3.5" />
              </>
            )}
          </Button>
        </div>
      </div>
    </Card>
  )
}

function AlertCircleIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}
