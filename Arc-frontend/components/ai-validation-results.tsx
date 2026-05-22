"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { CheckCircle, XCircle, AlertTriangle, Brain, Users, Shield, Zap } from "lucide-react"
import { FeedbackWidget } from "@/components/feedback-widget"
import type { ValidationResult } from "@/types"
import { APP_CONFIG } from "@/lib/config"

// Utility function to safely render text from string or object
const renderDisplayText = (item: any, fallback = 'No description available'): string => {
  if (typeof item === 'string') {
    return item;
  } else if (typeof item === 'object' && item !== null) {
    // Try common property names in order of preference
    return item.feature || 
           item.improvement || 
           item.issue || 
           item.title || 
           item.service || 
           item.component || 
           item.capability || 
           item.protection_type || 
           item.description || 
           item.text || 
           fallback;
  }
  return fallback;
};

interface AIValidationResultsProps {
  result: ValidationResult
}

export function AIValidationResults({ result }: AIValidationResultsProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600"
    if (score >= 60) return "text-yellow-600"
    return "text-red-600"
  }

  const getScoreBg = (score: number) => {
    if (score >= 80) return "bg-green-100"
    if (score >= 60) return "bg-yellow-100"
    return "bg-red-100"
  }

  return (
    <div className="space-y-6">
      {/* AI Analysis Header */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 p-6">
        <div className="flex items-center gap-4">
          <div className="flex size-12 items-center justify-center rounded-full bg-blue-100">
            <Brain className="size-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-foreground">AI-Powered Architecture Validation</h3>
            <p className="text-sm text-muted-foreground">
              Analysis ID: {result.validation_id} • {result.validation_type || "Architecture Analysis"}
              {result.architecture_complexity && ` • ${result.architecture_complexity}`}
            </p>
            {result.timestamp && (
              <p className="text-xs text-muted-foreground mt-1">
                Analyzed: {new Date(result.timestamp).toLocaleString()}
              </p>
            )}
            {result.processing_details?.total_duration && (
              <p className="text-xs text-blue-600 mt-1 font-medium">
                ⚡ Completed in {result.processing_details.total_duration.toFixed(2)}s
              </p>
            )}
          </div>
          <div className="text-right">
            <div className={`text-3xl font-bold ${getScoreColor(result.compliance_score)}`}>
              {result.compliance_score}%
            </div>
            <p className="text-xs text-muted-foreground">
              {result.validation_score ? 'Validation Score' : 'Compliance Score'}
            </p>
            {result.status?.overall && (
              <Badge variant={result.status.overall === 'completed' ? 'default' : 'secondary'} className="mt-2">
                {result.status.overall}
              </Badge>
            )}
          </div>
        </div>
      </Card>

      {/* Feedback */}
      <div className="flex justify-end">
        <FeedbackWidget generationId={result.validation_id || `val_${Date.now()}`} compact />
      </div>

      {/* Quick Overview */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <XCircle className="size-5 text-red-500" />
            <div>
              <h4 className="font-semibold text-foreground">Critical Issues</h4>
              <p className="text-sm text-muted-foreground">{result.critical_issues.length} issues found</p>
            </div>
          </div>
          <div className="mt-3 space-y-1">
            {result.critical_issues.slice(0, 3).map((issue: any, index: number) => (
              <div key={index} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                {renderDisplayText(issue, 'Critical issue identified')}
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="size-5 text-green-500" />
            <div>
              <h4 className="font-semibold text-foreground">Quick Wins</h4>
              <p className="text-sm text-muted-foreground">{result.quick_wins.length} improvements</p>
            </div>
          </div>
          <div className="mt-3 space-y-1">
            {result.quick_wins.slice(0, 3).map((win: any, index: number) => (
              <div key={index} className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                {renderDisplayText(win, 'Quick win identified')}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Detailed Analysis Tabs */}
      <Tabs defaultValue="comparison" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="comparison">AI Comparison</TabsTrigger>
          <TabsTrigger value="agents">Agent Analysis</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="diagrams">Diagram Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="comparison" className="mt-4">
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="size-5 text-blue-600" />
              <h4 className="text-lg font-semibold">AI Architecture Comparison</h4>
            </div>
            
            {result.ai_comparison?.error ? (
              <Alert>
                <AlertTriangle className="size-4" />
                <AlertDescription>
                  {result.ai_comparison?.error}
                </AlertDescription>
              </Alert>
            ) : result.ai_comparison ? (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h5 className="font-medium text-green-600 mb-2">✅ Strengths Identified</h5>
                    <div className="text-sm text-muted-foreground space-y-1">
                      {result.ai_comparison.strengths?.map((strength: string, index: number) => (
                        <div key={index}>• {strength}</div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h5 className="font-medium text-red-600 mb-2">❌ Critical Gaps</h5>
                    <div className="text-sm text-muted-foreground space-y-1">
                      {result.ai_comparison.gaps?.map((gap: string, index: number) => (
                        <div key={index}>• {gap}</div>
                      ))}
                    </div>
                  </div>
                </div>
                
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h5 className="font-medium text-blue-800 mb-2">🤖 AI Insights</h5>
                  <p className="text-sm text-blue-700">
                    {result.ai_comparison.insights || "The architecture shows good foundational patterns but requires attention to specific areas for improvement."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Brain className="size-12 mx-auto mb-4 opacity-50" />
                <p>AI comparison analysis not available.</p>
                <p className="text-sm">The detailed analysis may still be processing or unavailable.</p>
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="mt-4">
          {(result.agent_recommendations?.agents_results?.length || 0) > 0 ? (
            <div className="space-y-4">
              {/* Agent Summary Card */}
              {result.agent_recommendations?.summary && (
                <Card className="p-4 bg-gradient-to-r from-purple-50 to-blue-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Users className="size-5 text-purple-600" />
                      <div>
                        <h5 className="font-semibold">Multi-Agent Analysis Summary</h5>
                        <p className="text-sm text-muted-foreground">
                          {result.agent_recommendations.summary.agents_completed || 0} of {result.agent_recommendations.summary.total_agents || 0} agents completed
                        </p>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <div className="text-red-600 font-medium">
                        {result.agent_recommendations.summary.critical_issues_found || 0} critical issues
                      </div>
                      <div className="text-green-600 font-medium">
                        {result.agent_recommendations.summary.recommendations_generated || 0} recommendations
                      </div>
                    </div>
                  </div>
                </Card>
              )}
              
              {/* Agent Results Grid */}
              <div className="grid gap-4 md:grid-cols-2">
                {result.agent_recommendations!.agents_results!.map((agent: any, index: number) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      {agent.agent?.includes("Security") || agent.agent?.includes("security") ? <Shield className="size-5 text-red-500" /> : null}
                      {agent.agent?.includes("Network") || agent.agent?.includes("network") ? <Users className="size-5 text-blue-500" /> : null}
                      {agent.agent?.includes("Storage") || agent.agent?.includes("storage") ? <Zap className="size-5 text-green-500" /> : null}
                      {agent.agent?.includes("Database") || agent.agent?.includes("database") ? <Brain className="size-5 text-purple-500" /> : null}
                      {agent.agent?.includes("performance") || agent.agent?.includes("Performance") ? <Zap className="size-5 text-orange-500" /> : null}
                      {agent.agent?.includes("cost") || agent.agent?.includes("Cost") ? <Users className="size-5 text-green-500" /> : null}
                      {agent.agent?.includes("architecture") || agent.agent?.includes("Architecture") ? <Brain className="size-5 text-blue-500" /> : null}
                      <div className="flex-1">
                        <h5 className="font-semibold capitalize">{agent.agent || 'Agent'}</h5>
                        {agent.results?.status && (
                          <Badge variant={agent.results.status === 'completed' ? 'default' : 'secondary'} className="text-xs mt-1">
                            {agent.results.status}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="space-y-3">
                      {/* Agent-specific scores */}
                      {agent.results?.security_score !== undefined && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-muted-foreground">Security Score:</span>
                          <span className={`font-bold ${getScoreColor(agent.results.security_score)}`}>
                            {agent.results.security_score}%
                          </span>
                        </div>
                      )}
                      {agent.results?.performance_score !== undefined && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-muted-foreground">Performance Score:</span>
                          <span className={`font-bold ${getScoreColor(agent.results.performance_score)}`}>
                            {agent.results.performance_score}%
                          </span>
                        </div>
                      )}
                      {agent.results?.architecture_score !== undefined && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-muted-foreground">Architecture Score:</span>
                          <span className={`font-bold ${getScoreColor(agent.results.architecture_score)}`}>
                            {agent.results.architecture_score}%
                          </span>
                        </div>
                      )}
                      {agent.results?.cost_score !== undefined && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-muted-foreground">Cost Score:</span>
                          <span className={`font-bold ${getScoreColor(agent.results.cost_score)}`}>
                            {agent.results.cost_score}%
                          </span>
                        </div>
                      )}
                      
                      {/* Recommendations */}
                      {(agent.recommendations || agent.results?.recommendations) && (
                        <div className="space-y-2">
                          <h6 className="text-sm font-medium">Recommendations:</h6>
                          <div className="space-y-1">
                            {(agent.recommendations || agent.results.recommendations).slice(0, 3).map((rec: any, i: number) => (
                              <div key={i} className="text-xs bg-blue-50 px-2 py-1 rounded border border-blue-200">
                                {renderDisplayText(rec, 'Recommendation available')}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Critical Issues */}
                      {(agent.critical_issues || agent.results?.critical_issues) && (agent.critical_issues || agent.results.critical_issues).length > 0 && (
                        <div className="space-y-2">
                          <h6 className="text-sm font-medium text-red-600">Critical Issues:</h6>
                          <Badge variant="destructive" className="text-xs">
                            {(agent.critical_issues || agent.results.critical_issues).length} issues found
                          </Badge>
                        </div>
                      )}
                      
                      {/* Quick Wins */}
                      {(agent.quick_wins || agent.results?.quick_wins) && (agent.quick_wins || agent.results.quick_wins).length > 0 && (
                        <div className="space-y-2">
                          <h6 className="text-sm font-medium text-green-600">Quick Wins:</h6>
                          <Badge variant="default" className="text-xs bg-green-100 text-green-800">
                            {(agent.quick_wins || agent.results.quick_wins).length} opportunities
                          </Badge>
                        </div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            <Card className="p-6">
              <div className="text-center text-muted-foreground">
                <Brain className="size-12 mx-auto mb-4 opacity-50" />
                <p>No agent recommendations available yet.</p>
                <p className="text-sm">The analysis may still be in progress or detailed analysis data is unavailable.</p>
              </div>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="recommendations" className="mt-4">
          <div className="space-y-4">
            {/* Critical Recommendations */}
            {(result.recommendations?.critical?.length || 0) > 0 ? (
              <Card className="p-4 border-red-200">
                <div className="flex items-center gap-2 mb-3">
                  <XCircle className="size-5 text-red-500" />
                  <h5 className="font-semibold text-red-700">Critical Issues ({result.recommendations!.critical!.length})</h5>
                </div>
                <div className="space-y-2">
                  {result.recommendations!.critical!.map((rec: any, index: number) => (
                    <div key={index} className="bg-red-50 p-3 rounded border-l-4 border-red-400">
                      <div className="font-medium text-red-800">{rec.title || renderDisplayText(rec, "Critical Issue")}</div>
                      <div className="text-sm text-red-600 mt-1">{rec.description || renderDisplayText(rec, "Requires immediate attention")}</div>
                      <div className="flex justify-between items-center mt-2 text-xs">
                        <span className="text-red-500">Priority: {rec.priority || "Critical"}</span>
                        <span className="text-red-500">Effort: {rec.effort || "Medium"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ) : null}

            {/* High Priority */}
            {(result.recommendations?.high?.length || 0) > 0 ? (
              <Card className="p-4 border-yellow-200">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="size-5 text-yellow-500" />
                  <h5 className="font-semibold text-yellow-700">High Priority ({result.recommendations!.high!.length})</h5>
                </div>
                <div className="space-y-2">
                  {result.recommendations!.high!.map((rec: any, index: number) => (
                    <div key={index} className="bg-yellow-50 p-3 rounded border-l-4 border-yellow-400">
                      <div className="font-medium text-yellow-800">{rec.title || renderDisplayText(rec, "High Priority Item")}</div>
                      <div className="text-sm text-yellow-600 mt-1">{rec.description || renderDisplayText(rec, "Should be addressed soon")}</div>
                      <div className="flex justify-between items-center mt-2 text-xs">
                        <span className="text-yellow-500">Priority: {rec.priority || "High"}</span>
                        <span className="text-yellow-500">Effort: {rec.effort || "Low-Medium"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ) : null}

            {/* Medium Priority */}
            {(result.recommendations?.medium?.length || 0) > 0 ? (
              <Card className="p-4 border-blue-200">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle className="size-5 text-blue-500" />
                  <h5 className="font-semibold text-blue-700">Medium Priority ({result.recommendations!.medium!.length})</h5>
                </div>
                <div className="space-y-2">
                  {result.recommendations!.medium!.map((rec: any, index: number) => (
                    <div key={index} className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                      <div className="font-medium text-blue-800">{rec.title || renderDisplayText(rec, "Medium Priority Item")}</div>
                      <div className="text-sm text-blue-600 mt-1">{rec.description || renderDisplayText(rec, "Can be addressed in future iterations")}</div>
                      <div className="flex justify-between items-center mt-2 text-xs">
                        <span className="text-blue-500">Priority: {rec.priority || "Medium"}</span>
                        <span className="text-blue-500">Effort: {rec.effort || "Medium"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ) : null}

            {/* Fallback when no recommendations */}
            {(!result.recommendations || 
              (!(result.recommendations.critical?.length) && !(result.recommendations.high?.length) && !(result.recommendations.medium?.length))) && (
              <Card className="p-6">
                <div className="text-center text-muted-foreground">
                  <CheckCircle className="size-12 mx-auto mb-4 opacity-50" />
                  <p>No specific recommendations available.</p>
                  <p className="text-sm">Check the Critical Issues and Quick Wins sections for actionable items.</p>
                </div>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="diagrams" className="mt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-4">
              <h5 className="font-semibold mb-3">Architecture Analysis</h5>
              <div className="space-y-2 text-sm">
                <div>• Services detected: {result.ai_comparison?.architecture_assessment?.detected_services?.length || "N/A"}</div>
                <div>• Architecture pattern: {result.ai_comparison?.architecture_assessment?.architecture_pattern || "N/A"}</div>
                <div>• Complexity: {result.ai_comparison?.architecture_assessment?.complexity_level || result.architecture_complexity || "Medium"}</div>
                <div>• Validation type: {result.validation_type || "N/A"}</div>
              </div>
              {result.ai_comparison?.architecture_assessment?.detected_services && (
                <div className="mt-4">
                  <h6 className="text-sm font-medium mb-2">Detected Services:</h6>
                  <div className="flex flex-wrap gap-1">
                    {result.ai_comparison.architecture_assessment.detected_services.slice(0, 6).map((service: string, index: number) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {service}
                      </Badge>
                    ))}
                    {result.ai_comparison.architecture_assessment.detected_services.length > 6 && (
                      <Badge variant="outline" className="text-xs">
                        +{result.ai_comparison.architecture_assessment.detected_services.length - 6} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </Card>
            
            <Card className="p-4">
              <h5 className="font-semibold mb-3 flex items-center gap-2">
                📊 Well-Architected Framework
                <Badge variant="secondary" className="text-xs">
                  Azure Well-Architected
                </Badge>
              </h5>
              {result.ai_comparison?.well_architected_scores ? (
                <div className="space-y-3">
                  {Object.entries(result.ai_comparison.well_architected_scores).map(([pillar, score]: [string, any]) => {
                    const pillarName = pillar.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const getIcon = (name: string) => {
                      if (name.includes('Security')) return '🛡️';
                      if (name.includes('Reliability')) return '🔄';
                      if (name.includes('Performance')) return '⚡';
                      if (name.includes('Cost')) return '💰';
                      if (name.includes('Operational')) return '🔧';
                      return '📊';
                    };
                    return (
                      <div key={pillar}>
                        <div className="flex justify-between items-center text-sm mb-2">
                          <span className="flex items-center gap-2 font-medium">
                            <span>{getIcon(pillarName)}</span>
                            {pillarName}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className={`font-bold ${
                              score >= 85 ? 'text-green-600' : 
                              score >= 70 ? 'text-blue-600' :
                              score >= 55 ? 'text-yellow-600' : 
                              'text-red-600'
                            }`}>
                              {score}%
                            </span>
                            <Badge 
                              variant={score >= 70 ? 'default' : 'secondary'} 
                              className={`text-xs ${
                                score >= 85 ? 'bg-green-100 text-green-800' :
                                score >= 70 ? 'bg-blue-100 text-blue-800' :
                                score >= 55 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}
                            >
                              {score >= 85 ? 'Excellent' :
                               score >= 70 ? 'Good' :
                               score >= 55 ? 'Needs Work' : 'Critical'}
                            </Badge>
                          </div>
                        </div>
                        <Progress 
                          value={score} 
                          className={`h-2 ${
                            score >= 85 ? '[&>div]:bg-green-500' :
                            score >= 70 ? '[&>div]:bg-blue-500' :
                            score >= 55 ? '[&>div]:bg-yellow-500' :
                            '[&>div]:bg-red-500'
                          }`} 
                        />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="bg-muted p-3 rounded-lg border border-border">
                    <div className="text-sm space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-2 text-foreground">
                          📊 Overall Compliance
                        </span>
                        <span className={`font-bold ${
                          result.compliance_score >= 80 ? 'text-green-400' :
                          result.compliance_score >= 60 ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {result.compliance_score}%
                        </span>
                      </div>
                      <Progress value={result.compliance_score} className="h-2" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Critical issues</span>
                      <Badge variant="destructive" className="text-xs bg-red-900 text-red-200">
                        {result.critical_issues?.length || 0}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Quick wins</span>
                      <Badge variant="default" className="text-xs bg-green-900 text-green-200">
                        {result.quick_wins?.length || 0}
                      </Badge>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Compliance Progress */}
      <Card className="p-6 bg-gradient-to-r from-muted to-muted/80 border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex size-12 items-center justify-center rounded-full bg-blue-900/50">
            <CheckCircle className="size-6 text-blue-400" />
          </div>
          <div>
            <h4 className="text-xl font-semibold text-foreground">Architecture Compliance Progress</h4>
            <p className="text-sm text-muted-foreground">Overall system health and compliance metrics</p>
          </div>
        </div>
        
        <div className="space-y-6">
          {/* Overall Compliance */}
          <div className="bg-muted/50 p-4 rounded-lg border border-border">
            <div className="flex justify-between items-center mb-3">
              <div>
                <span className="text-foreground font-medium">Overall Compliance</span>
                <p className="text-xs text-muted-foreground">Combined architecture assessment</p>
              </div>
              <div className="text-right">
                <span className={`text-2xl font-bold ${getScoreColor(result.compliance_score)}`}>
                  {result.compliance_score}%
                </span>
                <p className="text-xs text-muted-foreground">Target: {APP_CONFIG.COMPLIANCE_TARGET}%</p>
              </div>
            </div>
            <Progress 
              value={result.compliance_score} 
              className={`h-3 ${
                result.compliance_score >= 80 ? '[&>div]:bg-green-500' :
                result.compliance_score >= 60 ? '[&>div]:bg-yellow-500' :
                '[&>div]:bg-red-500'
              }`}
            />
          </div>
          
          {/* Individual Metrics */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="bg-muted/30 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="size-4 text-red-400" />
                <span className="text-sm font-medium text-foreground">Security</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-muted-foreground">Compliance Level</span>
                <span className="text-lg font-bold text-red-400">
                  {result.ai_comparison?.well_architected_scores?.security || 0}%
                </span>
              </div>
              <Progress 
                value={result.ai_comparison?.well_architected_scores?.security || 0} 
                className="h-2 [&>div]:bg-red-500" 
              />
              <p className="text-xs text-muted-foreground mt-1">
                {(result.ai_comparison?.well_architected_scores?.security || 0) < 60 ? 'Needs immediate attention' : 'Good'}
              </p>
            </div>
            
            <div className="bg-muted/30 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="size-4 text-yellow-400" />
                <span className="text-sm font-medium text-foreground">Performance</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-muted-foreground">Efficiency Score</span>
                <span className="text-lg font-bold text-yellow-400">
                  {result.ai_comparison?.well_architected_scores?.performance || 0}%
                </span>
              </div>
              <Progress 
                value={result.ai_comparison?.well_architected_scores?.performance || 0} 
                className="h-2 [&>div]:bg-yellow-500" 
              />
              <p className="text-xs text-muted-foreground mt-1">
                {(result.ai_comparison?.well_architected_scores?.performance || 0) < 70 ? 'Room for improvement' : 'Good'}
              </p>
            </div>
            
            <div className="bg-muted/30 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="size-4 text-green-400" />
                <span className="text-sm font-medium text-foreground">Best Practices</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-muted-foreground">Implementation</span>
                <span className="text-lg font-bold text-green-400">
                  {result.ai_comparison?.well_architected_scores?.operational_excellence || 0}%
                </span>
              </div>
              <Progress 
                value={result.ai_comparison?.well_architected_scores?.operational_excellence || 0} 
                className="h-2 [&>div]:bg-green-500" 
              />
              <p className="text-xs text-muted-foreground mt-1">
                {(result.ai_comparison?.well_architected_scores?.operational_excellence || 0) >= 80 ? 'Well implemented' : 'Needs work'}
              </p>
            </div>
          </div>
          
          {/* Action Items Summary */}
          <div className="bg-muted/50 p-4 rounded-lg border border-border">
            <h5 className="text-sm font-semibold text-foreground mb-3">Action Items Summary</h5>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">🔴 Critical Issues</span>
                <Badge variant="destructive" className="bg-red-900/50 text-red-200 border-red-700">
                  {result.critical_issues?.length || 0}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">🟢 Quick Wins</span>
                <Badge variant="default" className="bg-green-900/50 text-green-200 border-green-700">
                  {result.quick_wins?.length || 0}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}