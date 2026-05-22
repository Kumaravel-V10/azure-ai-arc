"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
  ThumbsUp,
  ThumbsDown,
  Star,
  MessageSquare,
  Brain,
  Loader2,
  CheckCircle2,
} from "lucide-react"
import { getApiUrl } from "@/lib/config"
import { toast } from "@/hooks/use-toast"

interface FeedbackWidgetProps {
  generationId: string
  compact?: boolean
  onFeedbackSent?: (type: string) => void
}

export function FeedbackWidget({ generationId, compact = false, onFeedbackSent }: FeedbackWidgetProps) {
  const [feedbackSent, setFeedbackSent] = useState<string | null>(null)
  const [showRating, setShowRating] = useState(false)
  const [showComment, setShowComment] = useState(false)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [rlExploration, setRlExploration] = useState<number | null>(null)

  const sendFeedback = async (type: string, value: unknown = null) => {
    setIsSending(true)
    try {
      const response = await fetch(getApiUrl("KNOWLEDGE_FEEDBACK"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generation_id: generationId,
          feedback_type: type,
          value: value,
          context: { source: "ui", timestamp: new Date().toISOString() },
        }),
      })
      if (response.ok) {
        const data = await response.json()
        setFeedbackSent(type)
        setRlExploration(data.exploration_rate ?? null)
        onFeedbackSent?.(type)
      }
    } catch (err) {
      console.error("Feedback error:", err)
      toast({ title: "Feedback failed", description: "Could not send feedback. Please try again.", variant: "destructive" })
    } finally {
      setIsSending(false)
    }
  }

  const handleThumbsUp = () => sendFeedback("positive", true)
  const handleThumbsDown = () => sendFeedback("negative", true)
  const handleRating = (r: number) => {
    setRating(r)
    sendFeedback("rating", r)
  }
  const handleComment = () => {
    if (comment.trim()) {
      sendFeedback("comment", comment.trim())
      setComment("")
      setShowComment(false)
    }
  }

  if (feedbackSent) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <CheckCircle2 className="size-4 text-green-500" />
        <span className="text-muted-foreground">
          {feedbackSent === "positive" ? "Thanks! Positive feedback recorded" :
           feedbackSent === "negative" ? "Thanks! We'll improve" :
           feedbackSent === "rating" ? `Rated ${rating}/5 — thank you!` :
           "Comment recorded — thank you!"}
        </span>
        {rlExploration !== null && (
          <Badge variant="outline" className="text-xs ml-2">
            <Brain className="size-3 mr-1" />
            RL explore: {(rlExploration * 100).toFixed(1)}%
          </Badge>
        )}
      </div>
    )
  }

  if (compact) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground mr-1">Rate:</span>
        <Button
          variant="ghost" size="sm" className="h-7 w-7 p-0"
          onClick={handleThumbsUp} disabled={isSending}
        >
          <ThumbsUp className="size-3.5 text-green-600" />
        </Button>
        <Button
          variant="ghost" size="sm" className="h-7 w-7 p-0"
          onClick={handleThumbsDown} disabled={isSending}
        >
          <ThumbsDown className="size-3.5 text-red-500" />
        </Button>
        {isSending && <Loader2 className="size-3 animate-spin" />}
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-secondary/30 p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">How was this architecture?</span>
        {isSending && <Loader2 className="size-4 animate-spin" />}
      </div>

      {/* Thumbs */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline" size="sm" className="gap-1.5"
          onClick={handleThumbsUp} disabled={isSending}
        >
          <ThumbsUp className="size-3.5" /> Good
        </Button>
        <Button
          variant="outline" size="sm" className="gap-1.5"
          onClick={handleThumbsDown} disabled={isSending}
        >
          <ThumbsDown className="size-3.5" /> Needs work
        </Button>
        <Button
          variant="ghost" size="sm" className="gap-1.5 ml-auto"
          onClick={() => setShowRating(!showRating)}
        >
          <Star className="size-3.5" /> Rate
        </Button>
        <Button
          variant="ghost" size="sm" className="gap-1.5"
          onClick={() => setShowComment(!showComment)}
        >
          <MessageSquare className="size-3.5" /> Comment
        </Button>
      </div>

      {/* Star Rating */}
      {showRating && (
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((r) => (
            <button
              key={r}
              onClick={() => handleRating(r)}
              disabled={isSending}
              className="p-0.5"
            >
              <Star
                className={`size-5 ${r <= rating ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
              />
            </button>
          ))}
        </div>
      )}

      {/* Comment */}
      {showComment && (
        <div className="flex gap-2">
          <Textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What could be improved?"
            className="text-sm h-16 resize-none"
          />
          <Button size="sm" onClick={handleComment} disabled={isSending || !comment.trim()}>
            Send
          </Button>
        </div>
      )}
    </div>
  )
}
