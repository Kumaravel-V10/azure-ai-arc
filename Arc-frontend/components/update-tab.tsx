"use client"

import { useEffect, useRef, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { RefreshCw, Eye, Sparkles, Check, X } from "lucide-react"
import DiagramEmbed, { type DiagramEmbedHandle } from "@/components/DiagramEmbed"
import { API_CONFIG } from "@/lib/config"
import { toast } from "@/hooks/use-toast"

type DiagramOption = {
  id: string
  name: string
  filename: string
  relative_path: string
}

export function UpdateTab() {
  const diagramEmbedRef = useRef<DiagramEmbedHandle | null>(null)
  const [updateRequest, setUpdateRequest] = useState("")
  const [architectures, setArchitectures] = useState<DiagramOption[]>([])
  const [selectedArchitecture, setSelectedArchitecture] = useState("")
  const [lockId, setLockId] = useState("")
  const [previewXml, setPreviewXml] = useState<string | null>(null)
  const [hasStagedChanges, setHasStagedChanges] = useState(false)
  const [isLoadingDiagrams, setIsLoadingDiagrams] = useState(false)
  const [isLocking, setIsLocking] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApplyingDecision, setIsApplyingDecision] = useState(false)

  const isSelectionLocked = Boolean(lockId)

  useEffect(() => {
    const fetchDiagrams = async () => {
      setIsLoadingDiagrams(true)
      try {
        const response = await fetch(
          `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_FILES}`,
        )
        if (!response.ok) {
          throw new Error(`Failed to load diagrams (${response.status})`)
        }
        const result = await response.json()
        setArchitectures(Array.isArray(result.diagrams) ? result.diagrams : [])
      } catch (error: any) {
        toast({
          title: "Unable to load diagrams",
          description: error?.message || "Check backend availability and configured diagram folder.",
        })
      } finally {
        setIsLoadingDiagrams(false)
      }
    }

    fetchDiagrams()
  }, [])

  const handleArchitectureSelect = async (diagramId: string) => {
    setSelectedArchitecture(diagramId)
    setPreviewXml(null)
    setHasStagedChanges(false)
    setIsLocking(true)

    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_LOCK}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ diagram_id: diagramId }),
        },
      )

      if (!response.ok) {
        throw new Error(`Failed to lock diagram (${response.status})`)
      }

      const result = await response.json()
      setLockId(result.lock_id || "")
      setPreviewXml(result.preview_xml || null)

      toast({
        title: "Diagram locked",
        description: "The selected diagram path is now locked for this update session.",
      })
    } catch (error: any) {
      setSelectedArchitecture("")
      setLockId("")
      setPreviewXml(null)
      toast({
        title: "Failed to lock diagram",
        description: error?.message || "Please try selecting the architecture again.",
      })
    } finally {
      setIsLocking(false)
    }
  }

  const handleGenerate = async () => {
    if (!lockId || !updateRequest.trim()) {
      return
    }

    setIsGenerating(true)
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-diagram-lock-id": lockId,
          },
          body: JSON.stringify({
            modification_prompt: updateRequest,
          }),
        },
      )

      if (!response.ok) {
        throw new Error(`Update failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || null)
      setHasStagedChanges(Boolean(result.staged))

      toast({
        title: "Update generated",
        description: "Preview updated. Accept to persist, reject to discard.",
      })
    } catch (error: any) {
      toast({
        title: "Update failed",
        description: error?.message || "Unable to generate architecture update.",
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleAccept = async () => {
    if (!lockId) return
    setIsApplyingDecision(true)
    try {
      const manualXml = await diagramEmbedRef.current?.exportCurrentXml()
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_ACCEPT}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            lock_id: lockId,
            manual_xml: manualXml || undefined,
          }),
        },
      )

      if (!response.ok) {
        throw new Error(`Accept failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || previewXml)
      setHasStagedChanges(false)
      setLockId("")

      toast({
        title: "Changes accepted",
        description: "Diagram has been updated and saved.",
      })
    } catch (error: any) {
      toast({
        title: "Accept failed",
        description: error?.message || "Unable to persist staged changes.",
      })
    } finally {
      setIsApplyingDecision(false)
    }
  }

  const handleReject = async () => {
    if (!lockId) return
    setIsApplyingDecision(true)
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DIAGRAM_MODIFY_ARCH_REJECT}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ lock_id: lockId }),
        },
      )

      if (!response.ok) {
        throw new Error(`Reject failed (${response.status})`)
      }

      const result = await response.json()
      setPreviewXml(result.preview_xml || null)
      setHasStagedChanges(false)
      setLockId("")

      toast({
        title: "Changes rejected",
        description: "Staged update discarded and original diagram restored.",
      })
    } catch (error: any) {
      toast({
        title: "Reject failed",
        description: error?.message || "Unable to reject staged changes.",
      })
    } finally {
      setIsApplyingDecision(false)
    }
  }

  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="min-h-[calc(100vh-220px)] rounded-2xl overflow-hidden border border-border/30 bg-card/20 shadow-2xl shadow-black/10 backdrop-blur-sm"
    >
      {/* LEFT PANEL */}
      <ResizablePanel defaultSize={32} minSize={25}>
        <div className="h-full overflow-y-auto bg-gradient-to-b from-card/80 to-card/40 p-5">
          <Card className="border-0 shadow-none bg-transparent">
            <div className="space-y-6">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <RefreshCw className="size-4 text-primary" />
                  Update Architecture
                </h2>

                <p className="text-xs text-muted-foreground mt-1">
                  Select an architecture and provide update requirements
                </p>
              </div>

              {/* Architecture Dropdown */}
              <div className="space-y-2">
                <Label>Select Architecture</Label>

                <Select
                  value={selectedArchitecture}
                  onValueChange={handleArchitectureSelect}
                  disabled={isSelectionLocked || isLocking || isGenerating || isApplyingDecision}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingDiagrams ? "Loading diagrams..." : "Choose architecture"} />
                  </SelectTrigger>

                  <SelectContent>
                    {architectures.map((diagram) => (
                      <SelectItem key={diagram.id} value={diagram.id}>
                        {diagram.filename}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {isSelectionLocked && (
                  <p className="text-[11px] text-muted-foreground">
                    Diagram path is locked for this session until you Accept or Reject.
                  </p>
                )}
              </div>

              {/* Update Request */}
              <div className="space-y-2">
                <Label>Update Requirements</Label>

                <Textarea
                  placeholder="Example: Add Azure Front Door, WAF, and Azure Monitor to the existing architecture..."
                  value={updateRequest}
                  onChange={(e) => setUpdateRequest(e.target.value)}
                  className="min-h-[300px]"
                />
              </div>

              {/* Generate Button */}
              <Button
                className="w-full gap-2"
                size="lg"
                onClick={handleGenerate}
                disabled={
                  !lockId ||
                  !updateRequest.trim() ||
                  isGenerating ||
                  isApplyingDecision
                }
              >
                <Sparkles className="size-4" />

                {isGenerating
                  ? "Updating Architecture..."
                  : "Generate Update"}
              </Button>
            </div>

            {hasStagedChanges && (
              <Card className="p-4 border-primary/20 bg-primary/5">
                <div className="flex gap-3">
                  <Button
                    className="flex-1 gap-2"
                    onClick={handleAccept}
                    disabled={isApplyingDecision || isGenerating}
                  >
                    <Check className="size-4" />
                    Accept Change
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 gap-2"
                    onClick={handleReject}
                    disabled={isApplyingDecision || isGenerating}
                  >
                    <X className="size-4" />
                    Reject Change
                  </Button>
                </div>
              </Card>
            )}
          </Card>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* RIGHT PANEL */}
      <ResizablePanel defaultSize={68}>
        <div className="h-full overflow-y-auto p-5">
          <div className="space-y-4">
            <div className="pb-3 border-b border-border/30">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Eye className="size-4 text-primary" />
                Architecture Preview
              </h2>

              <p className="text-xs text-muted-foreground mt-1">
                Selected diagram preview and staged updates appear here
              </p>
            </div>

            {!previewXml && !isGenerating && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
                <div className="flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 border border-border/30">
                  <Sparkles className="size-8 text-primary/40" />
                </div>

                <div className="text-center">
                  <h3 className="text-lg font-semibold">
                    Ready to Preview
                  </h3>

                  <p className="text-sm text-muted-foreground mt-2">
                    Select an architecture file to preview it here,
                    then provide update requirements.
                  </p>
                </div>
              </div>
            )}

            {isGenerating && (
              <Card className="p-10 text-center">
                <RefreshCw className="size-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="font-medium">
                  Updating Architecture...
                </p>
              </Card>
            )}

            {previewXml && !isGenerating && (
              <Card className="p-4">
                <DiagramEmbed ref={diagramEmbedRef} xml={previewXml} />
              </Card>
            )}
          </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}