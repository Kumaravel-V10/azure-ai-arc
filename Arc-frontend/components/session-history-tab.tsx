"use client"

import { useState, useEffect, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { API_CONFIG } from "@/lib/config"
import {
  History,
  Search,
  Trash2,
  PlayCircle,
  ChevronRight,
  Clock,
  Layers,
  GitBranch,
  MessageSquare,
  FileOutput,
  RefreshCw,
  Loader2,
  AlertCircle,
  Inbox,
} from "lucide-react"

interface SessionSummary {
  session_id: string
  requirements: string
  started_at: string
  ended_at: string
  services_count: number
  patterns_count: number
  feedback_count: number
  outputs_count: number
}

interface SessionDetail {
  session_id: string
  requirements: string
  started_at: string
  ended_at: string
  services_used: string[]
  patterns_applied: string[]
  feedback_received: Array<{ rating: string; comment: string }>
  outputs_generated: Array<{ type: string; path: string }>
  related_files: Array<{ type: string; filename: string }>
}

export function SessionHistoryTab() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [resumeDialogOpen, setResumeDialogOpen] = useState(false)
  const [resumeSessionId, setResumeSessionId] = useState("")
  const [additionalRequirements, setAdditionalRequirements] = useState("")
  const [resumeLoading, setResumeLoading] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const pageSize = 10

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSIONS_LIST}?limit=${pageSize}&offset=${page * pageSize}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`)
      const data = await res.json()
      setSessions(data.sessions || [])
      setTotal(data.total || 0)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error"
      toast({
        title: "Error loading sessions",
        description: message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const openSessionDetail = async (sessionId: string) => {
    setDetailLoading(true)
    setSelectedSession(null)
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSION_HISTORY}/${sessionId}/history`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to load session: ${res.status}`)
      const data = await res.json()
      setSelectedSession(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error"
      toast({ title: "Error loading session details", description: message, variant: "destructive" })
    } finally {
      setDetailLoading(false)
    }
  }

  const handleResume = async () => {
    setResumeLoading(true)
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSION_RESUME}/${resumeSessionId}/resume`
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: resumeSessionId,
          additional_requirements: additionalRequirements,
        }),
      })
      if (!res.ok) throw new Error(`Resume failed: ${res.status}`)
      const data = await res.json()
      toast({
        title: "Session Resumed",
        description: `New session ${data.new_session_id} created with ${data.inherited_services?.length || 0} inherited services.`,
      })
      setResumeDialogOpen(false)
      setAdditionalRequirements("")
      fetchSessions()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error"
      toast({ title: "Resume failed", description: message, variant: "destructive" })
    } finally {
      setResumeLoading(false)
    }
  }

  const handleDelete = async (sessionId: string) => {
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSION_DELETE}/${sessionId}`
      const res = await fetch(url, { method: "DELETE" })
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
      toast({ title: "Session deleted", description: `Session ${sessionId} removed.` })
      setDeleteConfirmId(null)
      if (selectedSession?.session_id === sessionId) setSelectedSession(null)
      fetchSessions()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error"
      toast({ title: "Delete failed", description: message, variant: "destructive" })
    }
  }

  const filteredSessions = searchQuery
    ? sessions.filter(
        (s) =>
          s.session_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          s.requirements.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : sessions

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "—"
    try {
      const d = new Date(dateStr)
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return dateStr
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Panel – Session List */}
      <div className="lg:col-span-1 space-y-4">
        <Card className="p-4 border-border/50 bg-card/80 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <History className="size-5 text-primary" />
              <h3 className="font-semibold text-sm">Session History</h3>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchSessions}
              disabled={loading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>

          {/* Search */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9 text-sm bg-background/50"
            />
          </div>

          {/* Session List */}
          <ScrollArea className="h-[520px]">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="size-6 animate-spin mb-2" />
                <p className="text-sm">Loading sessions...</p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Inbox className="size-8 mb-2 opacity-50" />
                <p className="text-sm font-medium">No sessions found</p>
                <p className="text-xs mt-1">Generate an architecture to start a session</p>
              </div>
            ) : (
              <div className="space-y-2 pr-2">
                {filteredSessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => openSessionDetail(session.session_id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-150 hover:shadow-sm group ${
                      selectedSession?.session_id === session.session_id
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border-border/40 bg-background/50 hover:border-primary/30 hover:bg-background/80"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-mono text-muted-foreground truncate">
                          {session.session_id}
                        </p>
                        <p className="text-sm font-medium mt-1 line-clamp-2 text-foreground/90">
                          {session.requirements || "No description"}
                        </p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="size-3" />
                            {formatDate(session.started_at)}
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="size-4 text-muted-foreground/50 group-hover:text-primary transition-colors mt-1 shrink-0" />
                    </div>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {session.services_count > 0 && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          <Layers className="size-2.5 mr-0.5" />
                          {session.services_count} services
                        </Badge>
                      )}
                      {session.patterns_count > 0 && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          <GitBranch className="size-2.5 mr-0.5" />
                          {session.patterns_count} patterns
                        </Badge>
                      )}
                      {session.outputs_count > 0 && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          <FileOutput className="size-2.5 mr-0.5" />
                          {session.outputs_count} outputs
                        </Badge>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-3 border-t border-border/40 mt-3">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="h-7 text-xs"
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="h-7 text-xs"
              >
                Next
              </Button>
            </div>
          )}
        </Card>
      </div>

      {/* Right Panel – Session Detail */}
      <div className="lg:col-span-2">
        {detailLoading ? (
          <Card className="p-12 border-border/50 bg-card/80 backdrop-blur flex flex-col items-center justify-center">
            <Loader2 className="size-8 animate-spin text-primary mb-3" />
            <p className="text-sm text-muted-foreground">Loading session details...</p>
          </Card>
        ) : selectedSession ? (
          <Card className="border-border/50 bg-card/80 backdrop-blur overflow-hidden">
            {/* Detail Header */}
            <div className="p-5 border-b border-border/40 bg-gradient-to-r from-primary/5 to-transparent">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {selectedSession.session_id}
                    </Badge>
                    {selectedSession.ended_at && (
                      <Badge className="text-[10px] bg-green-500/10 text-green-600 border-green-500/20">
                        Completed
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm font-medium text-foreground/90 mt-2 leading-relaxed">
                    {selectedSession.requirements || "No description"}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    <span>Started: {formatDate(selectedSession.started_at)}</span>
                    {selectedSession.ended_at && (
                      <span>Ended: {formatDate(selectedSession.ended_at)}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    onClick={() => {
                      setResumeSessionId(selectedSession.session_id)
                      setResumeDialogOpen(true)
                    }}
                  >
                    <PlayCircle className="size-3.5" />
                    Resume
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 text-xs text-destructive hover:bg-destructive/10"
                    onClick={() => setDeleteConfirmId(selectedSession.session_id)}
                  >
                    <Trash2 className="size-3.5" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>

            {/* Detail Body */}
            <div className="p-5 space-y-5">
              {/* Services Used */}
              {selectedSession.services_used?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Layers className="size-3.5" />
                    Services Used ({selectedSession.services_used.length})
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedSession.services_used.map((svc, i) => (
                      <Badge
                        key={i}
                        variant="secondary"
                        className="text-xs font-medium bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20"
                      >
                        {svc}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Patterns Applied */}
              {selectedSession.patterns_applied?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <GitBranch className="size-3.5" />
                    Patterns Applied ({selectedSession.patterns_applied.length})
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedSession.patterns_applied.map((pat, i) => (
                      <Badge
                        key={i}
                        variant="secondary"
                        className="text-xs font-medium bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20"
                      >
                        {pat}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback */}
              {selectedSession.feedback_received?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <MessageSquare className="size-3.5" />
                    Feedback ({selectedSession.feedback_received.length})
                  </h4>
                  <div className="space-y-2">
                    {selectedSession.feedback_received.map((fb, i) => (
                      <div
                        key={i}
                        className="p-2.5 rounded-md border border-border/40 bg-background/50 text-sm"
                      >
                        <Badge variant="outline" className="text-[10px] mb-1">
                          {fb.rating}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">{fb.comment}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Outputs */}
              {selectedSession.outputs_generated?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <FileOutput className="size-3.5" />
                    Outputs ({selectedSession.outputs_generated.length})
                  </h4>
                  <div className="space-y-1.5">
                    {selectedSession.outputs_generated.map((out, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 p-2 rounded-md border border-border/30 bg-background/30 text-xs"
                      >
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          {out.type}
                        </Badge>
                        <span className="font-mono truncate text-muted-foreground">
                          {out.path}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Related Files */}
              {selectedSession.related_files?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Related Files ({selectedSession.related_files.length})
                  </h4>
                  <div className="grid grid-cols-2 gap-1.5">
                    {selectedSession.related_files.map((rf, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 p-2 rounded-md border border-border/30 bg-background/30 text-xs"
                      >
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          {rf.type}
                        </Badge>
                        <span className="font-mono truncate text-muted-foreground">
                          {rf.filename}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty state if no data */}
              {!selectedSession.services_used?.length &&
                !selectedSession.patterns_applied?.length &&
                !selectedSession.feedback_received?.length &&
                !selectedSession.outputs_generated?.length && (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <AlertCircle className="size-8 mb-2 opacity-50" />
                    <p className="text-sm font-medium">No data recorded</p>
                    <p className="text-xs mt-1">This session has no tracked services, patterns, or outputs</p>
                  </div>
                )}
            </div>
          </Card>
        ) : (
          <Card className="p-12 border-border/50 bg-card/80 backdrop-blur flex flex-col items-center justify-center min-h-[400px]">
            <div className="size-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <History className="size-7 text-primary/60" />
            </div>
            <h3 className="font-semibold text-foreground/80 mb-1">Select a Session</h3>
            <p className="text-sm text-muted-foreground text-center max-w-xs">
              Choose a session from the list to view its details, resume it, or manage its history.
            </p>
          </Card>
        )}
      </div>

      {/* Resume Dialog */}
      <Dialog open={resumeDialogOpen} onOpenChange={setResumeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Resume Session</DialogTitle>
            <DialogDescription>
              Continue from session <span className="font-mono text-xs">{resumeSessionId}</span>. Previous services and patterns will be inherited.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <Textarea
              placeholder="Add any additional requirements (optional)..."
              value={additionalRequirements}
              onChange={(e) => setAdditionalRequirements(e.target.value)}
              className="min-h-[80px] text-sm"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResumeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleResume} disabled={resumeLoading} className="gap-1.5">
              {resumeLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <PlayCircle className="size-4" />
              )}
              Resume Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirmId} onOpenChange={() => setDeleteConfirmId(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Session?</DialogTitle>
            <DialogDescription>
              This will permanently remove session <span className="font-mono text-xs">{deleteConfirmId}</span> and its data. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
              className="gap-1.5"
            >
              <Trash2 className="size-4" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
