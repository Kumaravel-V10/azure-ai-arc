"use client"

import { Badge } from "@/components/ui/badge"
import { Plus, Minus, ArrowRight, ArrowLeftRight } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ModificationDiff } from "@/types"

interface ModificationDiffViewProps {
  diff: ModificationDiff
  changesApplied: string[]
  className?: string
}

export function ModificationDiffView({ diff, changesApplied, className }: ModificationDiffViewProps) {
  if (!diff && (!changesApplied || changesApplied.length === 0)) return null

  const totalAdded = (diff?.services_added?.length || 0) + (diff?.connections_added?.length || 0)
  const totalRemoved = (diff?.services_removed?.length || 0) + (diff?.connections_removed?.length || 0)

  return (
    <div className={cn("rounded-lg border border-border/50 bg-muted/20 overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="size-4 text-blue-500" />
          <span className="text-xs font-semibold text-foreground">Changes</span>
        </div>
        <div className="flex items-center gap-1.5">
          {totalAdded > 0 && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-green-500/10 text-green-600 border-green-500/20">
              +{totalAdded}
            </Badge>
          )}
          {totalRemoved > 0 && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-red-500/10 text-red-600 border-red-500/20">
              -{totalRemoved}
            </Badge>
          )}
        </div>
      </div>

      <div className="px-3 py-2 space-y-1.5">
        {/* Services Added */}
        {diff?.services_added?.map((svc, idx) => (
          <div key={`sa-${idx}`} className="flex items-center gap-2 px-2 py-1 rounded-md bg-green-500/5 text-xs">
            <Plus className="size-3 text-green-500 shrink-0" />
            <span className="text-green-700 dark:text-green-400 font-medium">{svc.name}</span>
            {svc.category && (
              <Badge variant="outline" className="text-[9px] px-1 py-0 ml-auto">{svc.category}</Badge>
            )}
          </div>
        ))}

        {/* Services Removed */}
        {diff?.services_removed?.map((svc, idx) => (
          <div key={`sr-${idx}`} className="flex items-center gap-2 px-2 py-1 rounded-md bg-red-500/5 text-xs">
            <Minus className="size-3 text-red-500 shrink-0" />
            <span className="text-red-700 dark:text-red-400 font-medium line-through">{svc.name}</span>
            {svc.category && (
              <Badge variant="outline" className="text-[9px] px-1 py-0 ml-auto">{svc.category}</Badge>
            )}
          </div>
        ))}

        {/* Connections Added */}
        {diff?.connections_added?.map((conn, idx) => (
          <div key={`ca-${idx}`} className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-green-500/5 text-xs">
            <Plus className="size-3 text-green-500 shrink-0" />
            <span className="text-green-700 dark:text-green-400">{conn.source}</span>
            <ArrowRight className="size-3 text-muted-foreground" />
            <span className="text-green-700 dark:text-green-400">{conn.target}</span>
          </div>
        ))}

        {/* Connections Removed */}
        {diff?.connections_removed?.map((conn, idx) => (
          <div key={`cr-${idx}`} className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-red-500/5 text-xs">
            <Minus className="size-3 text-red-500 shrink-0" />
            <span className="text-red-700 dark:text-red-400 line-through">{conn.source}</span>
            <ArrowRight className="size-3 text-muted-foreground" />
            <span className="text-red-700 dark:text-red-400 line-through">{conn.target}</span>
          </div>
        ))}

        {/* Fallback: show raw changes if no diff */}
        {(!diff || (totalAdded === 0 && totalRemoved === 0)) && changesApplied?.map((change, idx) => (
          <div key={`ch-${idx}`} className="flex items-center gap-2 px-2 py-1 rounded-md bg-blue-500/5 text-xs">
            <ArrowRight className="size-3 text-blue-500 shrink-0" />
            <span className="text-foreground">{change}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
