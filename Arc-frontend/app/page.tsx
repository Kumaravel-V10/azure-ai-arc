"use client"
import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { GenerateTab } from "@/components/generate-tab"
import { ReverseEngineerTab } from "@/components/reverse-engineer-tab"
import { ValidateTab } from "@/components/validate-tab"
import { SessionHistoryTab } from "@/components/session-history-tab"
import { GitBranch, Shield, Sparkles, History, Cpu, Zap } from "lucide-react"
import { APP_CONFIG } from "@/lib/config"

export default function Home() {
  const [activeTab, setActiveTab] = useState("generate")
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Animated background gradient orbs */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute -top-40 -left-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl animate-float" />
        <div className="absolute top-1/3 -right-32 h-96 w-96 rounded-full bg-accent/5 blur-3xl animate-float-delayed" />
        <div className="absolute -bottom-40 left-1/3 h-72 w-72 rounded-full bg-primary/3 blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/40 bg-card/60 backdrop-blur-2xl">
        <div className="mx-auto max-w-[1600px] px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Logo + Title */}
            <div className={`flex items-center gap-4 transition-all duration-700 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'}`}>
              <div className="relative group">
                <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-primary/90 to-accent shadow-lg shadow-primary/25 transition-transform duration-300 group-hover:scale-110">
                  <Cpu className="size-5 text-primary-foreground" />
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 size-3 rounded-full border-2 border-card bg-emerald-400 animate-pulse" />
                <div className="absolute inset-0 rounded-xl bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                  {APP_CONFIG.HEADER_TITLE}
                </h1>
                <p className="text-[11px] font-medium text-muted-foreground/80">
                  {APP_CONFIG.HEADER_SUBTITLE}
                </p>
              </div>
            </div>

            {/* Status badge */}
            <div className={`flex items-center gap-3 transition-all duration-700 delay-200 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'}`}>
              <div className="hidden md:flex items-center gap-2.5 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <div className="relative flex size-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
                </div>
                <span className="text-xs font-semibold text-emerald-400">{APP_CONFIG.STATUS_BADGE}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 mx-auto max-w-[1600px] px-6 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          {/* Tab Navigation */}
          <div className={`mb-6 transition-all duration-700 delay-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <TabsList className="h-12 p-1 bg-card/60 backdrop-blur-xl border border-border/40 shadow-xl shadow-black/5 rounded-2xl gap-1">
              {[
                { value: "generate", icon: Sparkles, label: "Generate" },
                { value: "reverse", icon: GitBranch, label: "Reverse Engineer" },
                { value: "validate", icon: Shield, label: "Validate" },
                { value: "history", icon: History, label: "Sessions" },
              ].map((tab) => (
                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                  className="gap-2 px-5 rounded-xl data-[state=active]:bg-gradient-to-r data-[state=active]:from-primary data-[state=active]:to-primary/80 data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/25 transition-all duration-300 hover:bg-muted/50"
                >
                  <tab.icon className="size-4" />
                  <span className="font-medium">{tab.label}</span>
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          {/* Tab Content */}
          <div className={`transition-all duration-700 delay-500 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
            <TabsContent value="generate" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
              <GenerateTab />
            </TabsContent>
            <TabsContent value="reverse" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
              <ReverseEngineerTab />
            </TabsContent>
            <TabsContent value="validate" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
              <ValidateTab />
            </TabsContent>
            <TabsContent value="history" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
              <SessionHistoryTab />
            </TabsContent>
          </div>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border/30 bg-card/20 backdrop-blur-sm py-4 mt-12">
        <div className="mx-auto max-w-[1600px] px-6 flex items-center justify-center gap-2">
          <Zap className="size-3 text-primary/60" />
          <p className="text-[11px] text-muted-foreground/60">
            {APP_CONFIG.FOOTER_TEXT}
          </p>
        </div>
      </footer>
    </div>
  )
}
