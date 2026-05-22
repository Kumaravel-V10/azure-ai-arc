"""
Backend Configuration Module
Centralizes all configurable values to avoid hardcoded magic numbers
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class APIConfig:
    """API Server configuration"""
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # CORS Origins - comma separated list or "*" for all
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    
    # Add wildcard if in development mode
    @classmethod
    def get_cors_origins(cls) -> List[str]:
        origins = cls.CORS_ORIGINS.copy()
        if cls.DEBUG or os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true":
            origins.append("*")
        return origins


class AgentConfig:
    """Agent-related configuration"""
    
    # Default scores when AI analysis fails or returns invalid data
    DEFAULT_COMPLIANCE_SCORE: int = int(os.getenv("DEFAULT_COMPLIANCE_SCORE", "0"))
    DEFAULT_PERFORMANCE_SCORE: int = int(os.getenv("DEFAULT_PERFORMANCE_SCORE", "0"))
    DEFAULT_ARCHITECTURE_SCORE: int = int(os.getenv("DEFAULT_ARCHITECTURE_SCORE", "0"))
    DEFAULT_SECURITY_SCORE: int = int(os.getenv("DEFAULT_SECURITY_SCORE", "0"))
    DEFAULT_VALIDATION_SCORE: int = int(os.getenv("DEFAULT_VALIDATION_SCORE", "0"))
    
    # Fallback score when averaging multiple scores (used when no scores available)
    FALLBACK_AVERAGE_SCORE: int = int(os.getenv("FALLBACK_AVERAGE_SCORE", "0"))
    
    # Agent timeouts (in seconds)
    AGENT_TIMEOUT_BASE: float = float(os.getenv("AGENT_TIMEOUT_BASE", "60.0"))
    AGENT_TIMEOUT_INCREMENT: float = float(os.getenv("AGENT_TIMEOUT_INCREMENT", "30.0"))
    
    # Max retries for agent API calls
    AGENT_MAX_RETRIES: int = int(os.getenv("AGENT_MAX_RETRIES", "3"))
    
    # Token limits
    AGENT_MAX_TOKENS_DEFAULT: int = int(os.getenv("AGENT_MAX_TOKENS_DEFAULT", "3000"))
    AGENT_MAX_TOKENS_ARCHITECTURE: int = int(os.getenv("AGENT_MAX_TOKENS_ARCHITECTURE", "6000"))
    
    # Temperature for LLM calls
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.1"))


class AzureOpenAIConfig:
    """Azure OpenAI configuration"""
    API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")


class ValidationConfig:
    """Validation and scoring thresholds"""
    
    # Score thresholds for quality gates
    SCORE_THRESHOLD_EXCELLENT: int = int(os.getenv("SCORE_THRESHOLD_EXCELLENT", "90"))
    SCORE_THRESHOLD_GOOD: int = int(os.getenv("SCORE_THRESHOLD_GOOD", "70"))
    SCORE_THRESHOLD_ACCEPTABLE: int = int(os.getenv("SCORE_THRESHOLD_ACCEPTABLE", "50"))
    
    # Complexity classification based on compliance score
    @classmethod
    def get_complexity_label(cls, score: int) -> str:
        if score >= cls.SCORE_THRESHOLD_GOOD:
            return "standard"
        elif score >= cls.SCORE_THRESHOLD_ACCEPTABLE:
            return "needs_improvement"
        else:
            return "requires_attention"


class PathConfig:
    """File and directory paths"""
    SAVED_DIAGRAMS_DIR: str = os.getenv("SAVED_DIAGRAMS_DIR", "saved_diagrams")
    SAVED_XML_DIR: str = os.path.join(os.getenv("SAVED_DIAGRAMS_DIR", "saved_diagrams"), "xml")
    SAVED_RESPONSES_DIR: str = os.path.join(os.getenv("SAVED_DIAGRAMS_DIR", "saved_diagrams"), "responses")
    SAVED_TERRAFORM_DIR: str = os.path.join(os.getenv("SAVED_DIAGRAMS_DIR", "saved_diagrams"), "terraform")
    AZURE_DOCS_DIR: str = os.getenv("AZURE_DOCS_DIR", "azure-docs")
    DRAWIO_TEMPLATES_DIR: str = os.getenv("DRAWIO_TEMPLATES_DIR", "drawio_templates")
    KNOWLEDGE_SESSIONS_DIR: str = os.getenv("KB_SESSIONS_DIR", os.path.join("knowledge_base", "sessions"))
    FRONTEND_DIAGRAMS_DIR: str = os.getenv("FRONTEND_DIAGRAMS_DIR", os.path.join("front", "arc-front", "public", "diagrams"))


class DrawioConfig:
    """Draw.io diagram layout and dimensions"""
    PAGE_WIDTH: int = int(os.getenv("DRAWIO_PAGE_WIDTH", "1400"))
    PAGE_HEIGHT: int = int(os.getenv("DRAWIO_PAGE_HEIGHT", "900"))
    FALLBACK_PAGE_WIDTH: int = int(os.getenv("DRAWIO_FALLBACK_PAGE_WIDTH", "1169"))
    FALLBACK_PAGE_HEIGHT: int = int(os.getenv("DRAWIO_FALLBACK_PAGE_HEIGHT", "827"))
    MODEL_DX: int = int(os.getenv("DRAWIO_MODEL_DX", "1674"))
    MODEL_DY: int = int(os.getenv("DRAWIO_MODEL_DY", "1014"))
    MIN_CANVAS_WIDTH: int = int(os.getenv("DRAWIO_MIN_CANVAS_WIDTH", "1000"))
    MIN_CANVAS_HEIGHT: int = int(os.getenv("DRAWIO_MIN_CANVAS_HEIGHT", "700"))
    DEFAULT_CANVAS_WIDTH: int = int(os.getenv("DRAWIO_DEFAULT_CANVAS_WIDTH", "1200"))
    DEFAULT_CANVAS_HEIGHT: int = int(os.getenv("DRAWIO_DEFAULT_CANVAS_HEIGHT", "800"))
    EMBED_URL: str = os.getenv("DRAWIO_EMBED_URL", "https://embed.diagrams.net/?embed=1&proto=json&ui=min")
    HOST_APP: str = "app.diagrams.net"
    GENERATOR_AGENT: str = "multi-agent-generator"
    VERSION: str = "24.7.17"


class ThemeConfig:
    """Draw.io diagram color theme"""
    # Resource group alternating color pairs (fill, stroke)
    RG_COLORS: List[tuple] = [
        ("#dae8fc", "#0078d4"),
        ("#d5e8d4", "#82b366"),
        ("#fff2cc", "#d6b656"),
        ("#f8cecc", "#b85450"),
        ("#e1d5e7", "#9673a6"),
        ("#dae8fc", "#6c8ebf"),
    ]
    # Subnet alternating color pairs
    SUBNET_COLORS: List[tuple] = [
        ("#F0F7FF", "#4A90D9"),
        ("#F0FFF0", "#4CAF50"),
        ("#FFF8F0", "#FF9800"),
        ("#F5F0FF", "#9C27B0"),
        ("#FFF0F0", "#F44336"),
        ("#F0FFFF", "#00BCD4"),
    ]
    SUBSCRIPTION_BG: str = os.getenv("DRAWIO_SUBSCRIPTION_BG", "#f5f5f5")
    SUBSCRIPTION_STROKE: str = os.getenv("DRAWIO_SUBSCRIPTION_STROKE", "#666666")
    SUBSCRIPTION_FONT: str = os.getenv("DRAWIO_SUBSCRIPTION_FONT", "#333333")
    LABEL_FONT: str = os.getenv("DRAWIO_LABEL_FONT", "#999999")
    AZURE_PRIMARY: str = "#0078d4"
    WARNING_BG: str = "#fff2cc"
    WARNING_STROKE: str = "#d6b656"


class WorkflowConfig:
    """Workflow thresholds and orchestration limits"""
    MIN_SERVICES_REQUIRED: int = int(os.getenv("MIN_SERVICES_REQUIRED", "2"))
    MIN_QUALITY_THRESHOLD: float = float(os.getenv("MIN_QUALITY_THRESHOLD", "0.5"))
    MAX_RETRIES: int = int(os.getenv("WORKFLOW_MAX_RETRIES", "2"))
    MAX_ITERATIONS: int = int(os.getenv("WORKFLOW_MAX_ITERATIONS", "2"))
    POLLING_INTERVAL_SEC: float = float(os.getenv("POLLING_INTERVAL_SEC", "1.0"))
    SESSION_ID_LENGTH: int = int(os.getenv("SESSION_ID_LENGTH", "12"))


class ContentConfig:
    """Content truncation limits and thresholds"""
    CONTENT_EXCERPT_LIMIT: int = int(os.getenv("CONTENT_EXCERPT_LIMIT", "1500"))
    XML_CONTENT_LIMIT: int = int(os.getenv("XML_CONTENT_LIMIT", "2000"))
    SUMMARY_TRUNCATION: int = int(os.getenv("SUMMARY_TRUNCATION", "300"))
    MAX_DIFF_ITEMS: int = int(os.getenv("MAX_DIFF_ITEMS", "10"))
    MAX_REMEDIATION_ITEMS: int = int(os.getenv("MAX_REMEDIATION_ITEMS", "15"))
    COMPLEXITY_THRESHOLD: int = int(os.getenv("COMPLEXITY_THRESHOLD", "10"))
    MAX_SERVICES_THRESHOLD: int = int(os.getenv("MAX_SERVICES_THRESHOLD", "15"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))
    YAML_HEADER_PEEK: int = int(os.getenv("YAML_HEADER_PEEK", "100"))


class ExternalURLConfig:
    """External service URLs"""
    AZURE_ARCH_BASE_URL: str = os.getenv("AZURE_ARCH_BASE_URL", "https://learn.microsoft.com/en-us/azure/architecture")
    AZURE_ICON_BASE_URL: str = os.getenv("AZURE_ICON_BASE_URL", "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services")


class TerraformConfig:
    """Terraform template defaults"""
    DEFAULT_ADMIN_LOGIN: str = os.getenv("TF_DEFAULT_ADMIN_LOGIN", "var.admin_username")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("TF_DEFAULT_ADMIN_PASSWORD", "var.admin_password")
    DEFAULT_HTTP_PORT: int = int(os.getenv("TF_DEFAULT_HTTP_PORT", "80"))
    DEFAULT_REQUEST_TIMEOUT: int = int(os.getenv("TF_DEFAULT_REQUEST_TIMEOUT", "60"))


# Export singleton instances
api_config = APIConfig()
agent_config = AgentConfig()
azure_openai_config = AzureOpenAIConfig()
validation_config = ValidationConfig()
path_config = PathConfig()
drawio_config = DrawioConfig()
theme_config = ThemeConfig()
workflow_config = WorkflowConfig()
content_config = ContentConfig()
external_url_config = ExternalURLConfig()
terraform_config = TerraformConfig()


# ---------------------------------------------------------------------------
# Shared Constants
# ---------------------------------------------------------------------------

SERVICE_LAYERS = {
    # Layer 0 — Edge / Entry points
    "users": 0, "user": 0, "client": 0, "internet": 0,
    "azure front door": 0, "front door": 0,
    "azure cdn": 0, "cdn": 0,
    "azure traffic manager": 0, "traffic manager": 0,
    "waf": 0, "azure waf": 0, "web application firewall": 0,
    "azure ddos protection": 0, "ddos protection": 0,
    # Layer 1 — Gateway / Ingress
    "azure application gateway": 1, "application gateway": 1, "app gateway": 1,
    "azure api management": 1, "api management": 1, "apim": 1,
    "azure firewall": 1, "firewall": 1,
    "azure load balancer": 1, "load balancer": 1,
    # Layer 2 — Compute / Integration
    "azure app service": 2, "app service": 2,
    "azure functions": 2, "functions": 2, "function app": 2,
    "azure kubernetes service": 2, "aks": 2, "kubernetes": 2,
    "azure container apps": 2, "container apps": 2,
    "azure service bus": 2, "service bus": 2,
    "azure event hubs": 2, "event hubs": 2, "event hub": 2,
    "azure event grid": 2, "event grid": 2,
    "azure logic apps": 2, "logic apps": 2, "logic app": 2,
    # Layer 3 — Data / Storage
    "azure sql database": 3, "sql database": 3, "sql server": 3,
    "azure cosmos db": 3, "cosmos db": 3, "cosmosdb": 3,
    "azure cache for redis": 3, "redis": 3, "redis cache": 3,
    "azure storage": 3, "storage account": 3, "blob storage": 3,
    "azure database for postgresql": 3, "postgresql": 3,
    "azure database for mysql": 3, "mysql": 3,
    "azure data lake": 3, "data lake": 3,
    # Cross-cutting (-1) — connects horizontally to many layers
    "azure key vault": -1, "key vault": -1,
    "azure monitor": -1, "monitor": -1,
    "application insights": -1, "app insights": -1,
    "azure log analytics": -1, "log analytics": -1,
    "entra id": -1, "azure active directory": -1, "microsoft entra id": -1,
    "microsoft defender": -1, "defender for cloud": -1,
    "azure sentinel": -1, "sentinel": -1,
}
