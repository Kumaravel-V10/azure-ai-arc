/**
 * Application Configuration
 * Centralizes all configurable values to avoid hardcoded strings
 */

// API Configuration
export const API_CONFIG = {
  // Base URL for backend API - uses environment variable or defaults to localhost
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  
  // API endpoints
  ENDPOINTS: {
    GENERATE: "/api/generate",
    GENERATE_STREAM: "/api/generate-stream",
    GENERATE_DIAGRAM: "/api/generate-diagram",
    GENERATE_TERRAFORM_FROM_DRAWIO: "/api/generate-terraform-from-drawio",
    PARSE_DIAGRAM: "/api/parse-diagram",
    MULTI_AGENT_WORKFLOW: "/api/multi-agent-workflow",
    VALIDATE: "/api/validate",
    VALIDATE_IMAGE: "/api/validate/image",
    VALIDATION_REPORT: "/api/validation-report",
    PROGRESS: "/api/progress",
    HEALTH: "/api/health",
    REVERSE_ENGINEER_DRAWIO: "/api/reverse-engineer/drawio",
    REVERSE_ENGINEER_VISIO: "/api/reverse-engineer/visio",
    REVERSE_ENGINEER_IMAGE: "/api/reverse-engineer/image",
    REVERSE_ENGINEER_TERRAFORM: "/api/reverse-engineer/terraform",
    COMPARE: "/api/compare",
    COMPARE_DIAGRAMS: "/api/compare/diagrams",
    DIFF_REPORT: "/api/diff-report",
    KNOWLEDGE_STATS: "/api/knowledge/stats",
    KNOWLEDGE_FEEDBACK: "/api/knowledge/feedback",
    KNOWLEDGE_SEARCH: "/api/knowledge/search",
    KNOWLEDGE_LEARN: "/api/knowledge/learn",
    KNOWLEDGE_SUGGESTIONS: "/api/knowledge/suggestions",
    RL_STATS: "/api/rl/stats",
    SESSIONS_LIST: "/api/sessions",
    SESSION_HISTORY: "/api/session",  // + /{id}/history
    SESSION_RESUME: "/api/session",   // + /{id}/resume
    SESSION_DELETE: "/api/session",    // + /{id}  (DELETE)
    SESSION_BY_ID: "/api/knowledge/session",  // + /{id}
    DIAGRAM_IMPROVE: "/api/diagram/improve",
    DIAGRAM_MODIFY: "/api/diagram/modify",
    REVERSE_ENGINEER_STORY: "/api/reverse-engineer/analyze-story",
    INTERACTION_RESPOND: "/api/interaction",  // + /{session_id}/respond
    CLARIFY: "/api/clarify",  // Pre-generation clarifying questions
  },
  
  // Timeouts (in milliseconds)
  TIMEOUTS: {
    DEFAULT: 30000,
    LONG_RUNNING: 120000,
    POLLING_INTERVAL: 1500,
  },
} as const;

// Build full API URL
export function getApiUrl(endpoint: keyof typeof API_CONFIG.ENDPOINTS, ...params: string[]): string {
  let url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS[endpoint]}`;
  if (params.length > 0) {
    url += `/${params.join("/")}`;
  }
  return url;
}

// UI Configuration
export const UI_CONFIG = {
  // Animation durations (in ms)
  ANIMATIONS: {
    FADE_IN: 300,
    SLIDE_IN: 200,
  },
  
  // Progress display
  PROGRESS: {
    POLL_INTERVAL_MS: 1500,
    MAX_THOUGHTS_DISPLAYED: 6,
  },
  
  // Clipboard/copy feedback delay (ms)
  COPY_FEEDBACK_DELAY: 2000,
  
  // Toast configuration
  TOAST_LIMIT: 1,
  TOAST_REMOVE_DELAY: 1000000,  // ms — auto-dismiss delay
  
  // Diagram embed
  DIAGRAM: {
    LOAD_DELAY_MS: 1000,
    RETRY_DELAY_MS: 2000,
    EMBED_URL: process.env.NEXT_PUBLIC_DRAWIO_EMBED_URL || "https://embed.diagrams.net/?embed=1&proto=json&ui=min",
    FRAME_HEIGHT: "800px",
  },
} as const;

// Application metadata
export const APP_CONFIG = {
  TITLE: process.env.NEXT_PUBLIC_APP_TITLE || "AIDA - Azure Infrastructure Diagram Assistant",
  DESCRIPTION: process.env.NEXT_PUBLIC_APP_DESCRIPTION || "Generate, reverse engineer, and validate Azure architecture diagrams",
  LLM_MODEL_DISPLAY: process.env.NEXT_PUBLIC_LLM_MODEL_NAME || "AI Vision",
  HEADER_TITLE: "Azure Architecture Studio",
  HEADER_SUBTITLE: "Powered by Agentic AI • Enterprise Ready",
  STATUS_BADGE: "Multi-Agent System Active",
  FOOTER_TEXT: "Azure Architecture Studio • Multi-Agent AI System • Professional Architecture Generation",
  COMPLIANCE_TARGET: 85,
  MAX_SERVICES_DISPLAYED: 12,
  MAX_FILE_SIZE_DISPLAY: "TXT, MD, DOC up to 10MB",
} as const;

// Agent Configuration
export const AGENT_CONFIG = {
  // Agent names and their display properties
  AGENTS: {
    ComponentExtractionAgent: { id: "components", name: "Component Extractor" },
    AzureArchitectureReferenceAgent: { id: "references", name: "Azure Reference Mapper" },
    SecurityAgent: { id: "security", name: "Security Expert" },
    PerformanceAgent: { id: "performance", name: "Performance Expert" },
    ArchitectureAgent: { id: "architecture", name: "Architecture Expert" },
    ConnectionExpertAgent: { id: "connection", name: "Connection Expert" },
    RequirementsValidationAgent: { id: "validation", name: "Requirements Validator" },
    AzureArchitectureReviewAgent: { id: "review", name: "Architecture Reviewer" },
  },
} as const;

export default API_CONFIG;
