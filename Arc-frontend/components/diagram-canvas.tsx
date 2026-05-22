import type React from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"

interface DiagramCanvasProps {
  title: string
  diagram: string | null
  isLoading: boolean
  emptyIcon: React.ReactNode
  emptyMessage: string
}

export function DiagramCanvas({ title, diagram, isLoading, emptyIcon, emptyMessage }: DiagramCanvasProps) {
  return (
    <Card className="bg-card p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {diagram ? "Click to download or export" : "Waiting for generation"}
            </p>
          </div>
          {diagram && (
            <Button variant="outline" size="sm" className="gap-2 bg-transparent">
              <Download className="size-4" />
              Export
            </Button>
          )}
        </div>

        <div className="aspect-[4/3] overflow-hidden rounded-lg border-2 border-dashed border-border bg-secondary/30">
          {isLoading && (
            <div className="flex size-full items-center justify-center">
              <div className="text-center">
                <div className="mx-auto size-12 animate-spin rounded-full border-4 border-border border-t-primary" />
                <p className="mt-4 text-sm text-muted-foreground">Generating diagram...</p>
              </div>
            </div>
          )}

          {!isLoading && !diagram && (
            <div className="flex size-full flex-col items-center justify-center gap-3 px-6">
              {emptyIcon}
              <p className="text-center text-sm text-muted-foreground">{emptyMessage}</p>
            </div>
          )}

          {!isLoading && diagram && (
            <div className="size-full overflow-auto bg-white p-4">
              <img
                src={diagram}
                alt="Azure Architecture Diagram"
                className="h-auto w-full object-contain"
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
