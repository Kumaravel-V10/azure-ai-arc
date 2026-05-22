"""
Agents Package - Multi-Agent Architecture for Azure Architecture Generation

Split from monolithic agents.py for maintainability.
All public classes are re-exported here for backward compatibility.
"""

from agents.base import (
    AgentThought,
    AgentMessage,
    ToolCall,
    AgentPersona,
    AgentTools,
    AGENT_PERSONAS,
    AgenticMixin,
    AgentStatus,
    BaseAgent,
)
from agents.security import SecurityAgent
from agents.performance import PerformanceAgent
from agents.cost import CostOptimizationAgent
from agents.architecture import ArchitectureAgent
from agents.connection import ConnectionExpertAgent
from agents.components import ComponentExtractionAgent
from agents.references import AzureArchitectureReferenceAgent
from agents.validation import RequirementsValidationAgent
from agents.review import AzureArchitectureReviewAgent
from agents.orchestrator import AgentOrchestrator

__all__ = [
    # Base framework
    "AgentThought",
    "AgentMessage",
    "ToolCall",
    "AgentPersona",
    "AgentTools",
    "AGENT_PERSONAS",
    "AgenticMixin",
    "AgentStatus",
    "BaseAgent",
    # Specialized agents
    "SecurityAgent",
    "PerformanceAgent",
    "CostOptimizationAgent",
    "ArchitectureAgent",
    "ConnectionExpertAgent",
    "ComponentExtractionAgent",
    "AzureArchitectureReferenceAgent",
    "RequirementsValidationAgent",
    "AzureArchitectureReviewAgent",
    # Orchestrator
    "AgentOrchestrator",
]
