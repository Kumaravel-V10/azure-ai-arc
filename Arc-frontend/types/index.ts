// Types for the architecture diagram API response

export interface ServiceWithIcon {
  name: string
  icon_source: string
  icon_url: string
  icon_path?: string
  full_path: string
}

export interface Connection {
  source: string
  target: string
  type: string
  port?: string
}

export interface DetectedService {
  name: string
  confidence: number
  keywords_matched: string[]
  icon_source: string
  icon_url: string
}

export interface AgentResult {
  agent: string
  recommendations: (string | any)[]
  status: string
  critical_issues?: (string | any)[]
  quick_wins?: (string | any)[]
  compliance_score?: number
  security_services?: any[]
  performance_services?: any[]
  cost_optimization_services?: any[]
  network_security?: any[]
  identity_management?: any[]
  data_protection?: any[]
  performance_score?: number
  cost_score?: number
  [key: string]: any
}

export interface AgentRecommendations {
  agents_results: AgentResult[]
  summary: {
    total_agents: number
    agents_completed: number
    critical_issues_found: number
    recommendations_generated: number
  }
}

export interface ServiceDetection {
  ai_detected: string[]
  prompt_detected: string[]
  final_services: string[]
  detection_details: DetectedService[]
}

export interface IconSources {
  local_icons: number
  portal_icons: number
  default_icons: number
}

export interface Architecture {
  services: string[]
  architecture_pattern: string
  connections: Connection[]
  drawio_xml: string
  recommendations: string[]
  detected_services_info: DetectedService[]
  services_with_icons: ServiceWithIcon[]
}

export interface Validation {
  validation_id: string
  compliance_score: number
  critical_issues: string[]
  quick_wins: string[]
  ai_comparison: {
    strengths: string[]
    gaps: string[]
    insights: string
    well_architected_scores: {
      security: number
      reliability: number
      performance: number
      cost_optimization: number
      operational_excellence: number
    }
    overall_score: number
    architecture_assessment: {
      architecture_pattern: string
      resource_group_organization: string
      network_design: string
      security_implementation: string
      monitoring_strategy: string
      disaster_recovery: string
    }
  }
  agent_recommendations: AgentRecommendations
  recommendations: {
    critical: { title: string; description: string; priority: string; effort: string }[]
    high: { title: string; description: string; priority: string; effort: string }[]
    medium: { title: string; description: string; priority: string; effort: string }[]
  }
  validation_type: string
  architecture_complexity: string
}

export interface Diagrams {
  drawio_xml: string
  mermaid: string
  terraform: string
  image: string
}

export interface Principles {
  implemented: string[]
  missing: string[]
}

export interface AvailableIcons {
  [category: string]: string[]
}

export interface ArchitectureResponse {
  diagram_url: string
  architecture: Architecture
  validation: Validation
  service_detection: ServiceDetection
  icon_sources: IconSources
  diagrams: Diagrams
  principles?: Principles
  available_icons?: AvailableIcons
  agent_recommendations?: AgentRecommendations
  recommendations?: {
    critical: { title: string; description: string; priority: string; effort: string }[]
    high: { title: string; description: string; priority: string; effort: string }[]
    medium: { title: string; description: string; priority: string; effort: string }[]
  }
}

export interface ValidationResult {
  validation_id?: string
  compliance_score: number
  critical_issues: (string | any)[]
  quick_wins: (string | any)[]
  ai_comparison?: {
    strengths?: string[]
    gaps?: string[]
    insights?: string
    well_architected_scores?: {
      security: number
      reliability: number
      performance: number
      cost_optimization: number
      operational_excellence: number
    }
    overall_score?: number
    architecture_assessment?: any
    error?: string
  }
  agent_recommendations?: {
    agents_results?: any[]
    summary?: any
  }
  recommendations?: {
    critical?: any[]
    high?: any[]
    medium?: any[]
  }
  detailed_analysis?: any // Keep for backward compatibility
  error?: boolean
  message?: string
  validation_type?: string
  architecture_complexity?: string
  timestamp?: string
}

// ==================== DIAGRAM MODIFICATION TYPES ====================

export interface ModificationThinkingStep {
  type: string
  content: string
  timestamp: string
  emoji: string
}

export interface ModificationDiff {
  services_added: { name: string; category: string }[]
  services_removed: { name: string; category: string }[]
  connections_added: { source: string; target: string; label: string }[]
  connections_removed: { source: string; target: string; label: string }[]
}

export interface ModificationValidation {
  connection_validation: {
    orphan_services: string[]
    valid_flow: boolean
    issues: string[]
  }
  waf_scores: {
    security: number
    reliability: number
    performance: number
    cost_optimization: number
    operational_excellence: number
  }
  requirements_fulfillment: {
    score: number
    missing_requirements: string[]
    covered_requirements: string[]
  }
  xml_validation: {
    valid: boolean
    issues: string[]
  }
}

export interface ModificationResult {
  success: boolean
  strategy_used: string
  architecture: any
  diagram_xml: string
  mermaid?: string
  terraform?: string
  changes_applied: string[]
  validation_results: ModificationValidation
  thinking_process: ModificationThinkingStep[]
  diff_summary: ModificationDiff
  timestamp: string
}

export interface ModificationHistoryEntry {
  id: string
  prompt: string
  strategy: string
  changes: string[]
  timestamp: Date
  diff: ModificationDiff
  validation: ModificationValidation
}