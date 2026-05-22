import asyncio
from typing import Dict, List, Any, Optional, Callable, Tuple
from openai import AsyncAzureOpenAI
import json
import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from exceptions import AgentTimeoutError, AgentAPIError, JSONParseError
from azure_docs_scanner import get_scanner
from drawio_reference_analyzer import get_reference_analyzer
from config import azure_openai_config, agent_config

# Import accuracy enhancements for improved service detection and scoring
try:
    from accuracy_enhancements import (
        get_service_detector,
        get_accuracy_scorer,
        get_learned_patterns,
        FEW_SHOT_ARCHITECTURE_EXAMPLES,
        FEW_SHOT_CONNECTION_EXAMPLES,
    )
    ACCURACY_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    ACCURACY_ENHANCEMENTS_AVAILABLE = False
    # Fallback empty implementations
    def get_service_detector(): return None
    def get_accuracy_scorer(): return None
    def get_learned_patterns(): return None
    FEW_SHOT_ARCHITECTURE_EXAMPLES = ""
    FEW_SHOT_CONNECTION_EXAMPLES = ""

# Import knowledge base for learning and reinforcement
try:
    from knowledge_base import (
        get_knowledge_manager,
        get_rl_learner,
        PatternType,
        FeedbackType,
        learn_from_architecture,
        get_suggestions_for_services
    )
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    def get_knowledge_manager(): return None
    def get_rl_learner(): return None
    def learn_from_architecture(*args, **kwargs): return None
    def get_suggestions_for_services(*args, **kwargs): return {}

logger = logging.getLogger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AGENTIC AI FRAMEWORK - Chain-of-Thought, Tools, Reflection, Inter-Agent Comms
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class AgentThought:
    """Represents a single thought/reasoning step from an agent"""
    thought_type: str  # "reasoning", "tool_call", "observation", "reflection", "decision", "communication"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class AgentMessage:
    """Inter-agent communication message"""
    from_agent: str
    to_agent: str
    message_type: str  # "request", "response", "insight", "warning", "recommendation"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ToolCall:
    """Represents a tool invocation by an agent"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    duration_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentPersona:
    """Defines an agent's identity and expertise"""
    role: str
    expertise: List[str]
    personality: str
    thinking_style: str
    communication_style: str
    avatar_emoji: str


class AgentTools:
    """Available tools for agentic operations"""
    
    SEARCH_AZURE_DOCS = "search_azure_docs"
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    VALIDATE_ARCHITECTURE = "validate_architecture"
    CHECK_COMPLIANCE = "check_compliance"
    ESTIMATE_COST = "estimate_cost"
    ANALYZE_CONNECTIONS = "analyze_connections"
    QUERY_REFERENCE_PATTERNS = "query_reference_patterns"
    SEND_MESSAGE = "send_message"
    REFLECT_ON_OUTPUT = "reflect_on_output"


# Agent Personas for each specialized role
AGENT_PERSONAS = {
    "security": AgentPersona(
        role="Principal Security Architect",
        expertise=["Zero Trust", "Azure Security", "Compliance", "Identity", "Network Security"],
        personality="Vigilant, thorough, and protective. Always considers worst-case scenarios.",
        thinking_style="Risk-first analysis. Identifies threats before proposing solutions.",
        communication_style="Clear warnings with actionable recommendations.",
        avatar_emoji="ðŸ”"
    ),
    "performance": AgentPersona(
        role="Principal Performance Engineer",
        expertise=["Scalability", "Latency Optimization", "Caching", "Load Balancing", "Auto-scaling"],
        personality="Efficiency-obsessed, data-driven, and proactive about bottlenecks.",
        thinking_style="Metrics-first. Quantifies impact before recommending changes.",
        communication_style="Performance benchmarks with clear trade-offs.",
        avatar_emoji="âš¡"
    ),
    "architecture": AgentPersona(
        role="Principal Azure Solutions Architect",
        expertise=["Enterprise Architecture", "Microservices", "Event-Driven Design", "Azure Services"],
        personality="Strategic thinker who balances innovation with reliability.",
        thinking_style="Pattern-based. Matches requirements to proven reference architectures.",
        communication_style="Explains 'why' behind each design decision.",
        avatar_emoji="ðŸ—ï¸"
    ),
    "connection": AgentPersona(
        role="Principal Integration Architect",
        expertise=["Service Mesh", "API Design", "Data Flow", "Event-Driven Integration", "Connection Patterns"],
        personality="Systematic and detail-oriented. Ensures clean data flow between services.",
        thinking_style="Flow-first. Traces data paths end-to-end before optimizing.",
        communication_style="Visual thinker who explains connection topology clearly.",
        avatar_emoji="ðŸ”—"
    ),
    "validation": AgentPersona(
        role="Principal Quality Assurance Architect",
        expertise=["Requirements Validation", "Gap Analysis", "Compliance Checking", "Test Coverage"],
        personality="Meticulous and thorough. Catches what others miss.",
        thinking_style="Checklist-driven. Systematically validates against requirements.",
        communication_style="Clear pass/fail criteria with detailed justification.",
        avatar_emoji="âœ…"
    ),
    "components": AgentPersona(
        role="Principal Requirements Analyst",
        expertise=["Requirements Extraction", "NFR Analysis", "API Design", "Tech Stack Selection"],
        personality="Analytical and curious. Asks clarifying questions to uncover hidden requirements.",
        thinking_style="Decomposition-based. Breaks complex requirements into components.",
        communication_style="Structured extraction with clear categorization.",
        avatar_emoji="ðŸ“‹"
    ),
    "references": AgentPersona(
        role="Principal Azure Reference Specialist",
        expertise=["Azure Architecture Center", "Reference Architectures", "Best Practices", "Design Patterns"],
        personality="Knowledge curator. Connects requirements to proven Azure patterns.",
        thinking_style="Pattern-matching. Finds closest reference architectures first.",
        communication_style="Cites specific Azure guidance with rationale.",
        avatar_emoji="ðŸ›ï¸"
    ),
    "review": AgentPersona(
        role="Principal Architecture Reviewer",
        expertise=["Well-Architected Framework", "Architecture Governance", "Best Practice Validation"],
        personality="Critical but constructive. Identifies issues with improvement paths.",
        thinking_style="WAF-pillar analysis. Evaluates across reliability, security, performance, cost, operations.",
        communication_style="Balanced critique with specific improvement recommendations.",
        avatar_emoji="ðŸ”"
    ),
    "modification": AgentPersona(
        role="Principal Diagram Modification Specialist",
        expertise=["Draw.io XML", "Architecture Modification", "Layout Preservation", "Incremental Updates"],
        personality="Precise and surgical. Makes minimal changes to achieve the desired result.",
        thinking_style="Diff-first. Analyzes what exists before deciding what to change.",
        communication_style="Clear before/after descriptions with rationale.",
        avatar_emoji="âœï¸"
    )
}


class AgenticMixin:
    """Mixin class that adds agentic AI capabilities to any agent.
    
    Features:
    - Chain-of-Thought reasoning with visible thinking steps
    - Tool usage protocol with explicit tool calls
    - Self-reflection and critique
    - Inter-agent communication
    - Agent personas with distinct identities
    """
    
    def __init_agentic__(self, agent_type: str, progress_callback: Callable = None):
        """Initialize agentic capabilities. Call this in the agent's __init__."""
        self.agent_type = agent_type
        self.persona = AGENT_PERSONAS.get(agent_type, AGENT_PERSONAS["architecture"])
        self.thoughts: List[AgentThought] = []
        self.tool_calls: List[ToolCall] = []
        self.messages_sent: List[AgentMessage] = []
        self.messages_received: List[AgentMessage] = []
        self.progress_callback = progress_callback
        self.reflection_enabled = True
        self._message_bus: Dict[str, List[AgentMessage]] = {}
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for real-time progress updates"""
        self.progress_callback = callback
    
    def set_message_bus(self, bus: Dict[str, List[AgentMessage]]):
        """Set shared message bus for inter-agent communication"""
        self._message_bus = bus
    
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Chain-of-Thought Reasoning
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    def think(self, thought: str, thought_type: str = "reasoning", metadata: Dict = None) -> AgentThought:
        """Record a thought/reasoning step and broadcast to progress callback"""
        agent_thought = AgentThought(
            thought_type=thought_type,
            content=thought,
            metadata=metadata or {}
        )
        self.thoughts.append(agent_thought)
        
        # Broadcast thought to progress callback
        if self.progress_callback:
            self.progress_callback(
                agent_name=self.name,
                status="thinking",
                percentage=-1,  # -1 indicates this is a thought update, not progress
                output_summary={
                    "thought_type": thought_type,
                    "thought": thought,
                    "emoji": self._get_thought_emoji(thought_type),
                    "agent_persona": self.persona.role,
                    "agent_emoji": self.persona.avatar_emoji
                }
            )
        
        logger.info(f"{self.persona.avatar_emoji} [{self.name}] {thought_type.upper()}: {thought}")
        return agent_thought
    
    def _get_thought_emoji(self, thought_type: str) -> str:
        """Get emoji for thought type"""
        return {
            "reasoning": "ðŸ§ ",
            "tool_call": "ðŸ”§",
            "observation": "ðŸ‘ï¸",
            "reflection": "ðŸªž",
            "decision": "âœ¨",
            "communication": "ðŸ’¬",
            "warning": "âš ï¸",
            "success": "âœ…"
        }.get(thought_type, "ðŸ’­")
    
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Tool Usage Protocol
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    async def use_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool and record the call"""
        import time
        start_time = time.time()
        
        self.think(f"Invoking tool: {tool_name}", "tool_call", {"arguments": arguments})
        
        result = None
        try:
            # Route to actual tool implementations
            if tool_name == AgentTools.SEARCH_AZURE_DOCS:
                result = self._tool_search_azure_docs(**arguments)
            elif tool_name == AgentTools.ANALYZE_REQUIREMENTS:
                result = self._tool_analyze_requirements(**arguments)
            elif tool_name == AgentTools.VALIDATE_ARCHITECTURE:
                result = await self._tool_validate_architecture(**arguments)
            elif tool_name == AgentTools.QUERY_REFERENCE_PATTERNS:
                result = self._tool_query_reference_patterns(**arguments)
            elif tool_name == AgentTools.ANALYZE_CONNECTIONS:
                result = self._tool_analyze_connections(**arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            duration_ms = (time.time() - start_time) * 1000
            
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                duration_ms=duration_ms
            )
            self.tool_calls.append(tool_call)
            
            # Record observation
            result_summary = str(result)[:200] if result else "No result"
            self.think(f"Tool result ({duration_ms:.0f}ms): {result_summary}", "observation")
            
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            self.think(f"Tool {tool_name} failed: {str(e)}", "warning")
            return {"error": str(e)}
    
    def _tool_search_azure_docs(self, query: str, domain_terms: List[str] = None, max_results: int = 5) -> str:
        """Tool: Search Azure documentation"""
        return self._search_local_docs(query, domain_terms, max_results)
    
    def _tool_analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """Tool: Extract structured requirements"""
        # Basic keyword extraction
        keywords = []
        for keyword in ["api", "database", "cache", "queue", "authentication", "monitoring", "scaling"]:
            if keyword.lower() in requirements.lower():
                keywords.append(keyword)
        return {"extracted_keywords": keywords, "length": len(requirements)}
    
    async def _tool_validate_architecture(self, services: List, connections: List) -> Dict[str, Any]:
        """Tool: Validate architecture structure"""
        issues = []
        if len(services) == 0:
            issues.append("No services defined")
        if len(connections) == 0:
            issues.append("No connections defined")
        # Check for orphan services
        connected = set()
        for conn in connections:
            connected.add(conn.get("source", ""))
            connected.add(conn.get("target", ""))
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}
        orphans = service_names - connected
        if orphans:
            issues.append(f"Orphan services: {', '.join(orphans)}")
        return {"valid": len(issues) == 0, "issues": issues}
    
    def _tool_query_reference_patterns(self, requirements: str, max_refs: int = 3) -> str:
        """Tool: Query Draw.io reference patterns"""
        return self._get_drawio_reference_context(requirements, max_refs)
    
    def _tool_analyze_connections(self, connections: List) -> Dict[str, Any]:
        """Tool: Analyze connection patterns"""
        flow_types = {}
        for conn in connections:
            ft = conn.get("flow_type", "unknown")
            flow_types[ft] = flow_types.get(ft, 0) + 1
        return {"total": len(connections), "flow_distribution": flow_types}
    
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Self-Reflection & Critique
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    def reflect(self, output: Dict[str, Any], criteria: List[str] = None) -> Dict[str, Any]:
        """Self-reflect on output quality with detailed analysis"""
        if not self.reflection_enabled:
            return {"reflection_skipped": True}
        
        criteria = criteria or ["completeness", "correctness", "clarity"]
        
        self.think(f"Reflecting on my output quality against {len(criteria)} criteria: {', '.join(criteria)}", "reflection")
        
        reflection = {
            "criteria_evaluated": criteria,
            "assessments": {},
            "improvements_suggested": []
        }
        
        # Detailed self-assessment based on output content
        if "services" in output:
            services_count = len(output.get("services", []))
            service_names = [s.get("name", s) if isinstance(s, dict) else s for s in output.get("services", [])[:5]]
            if services_count < 3:
                reflection["improvements_suggested"].append(f"Only {services_count} services defined - may be insufficient for production architecture")
                self.think(f"Concern: Only {services_count} services. Typical architectures need 5-15 services for production.", "warning")
            else:
                self.think(f"Service coverage looks adequate: {services_count} services including {', '.join(service_names[:3])}", "observation")
            reflection["assessments"]["services_coverage"] = "adequate" if services_count >= 3 else "limited"
        
        if "connections" in output:
            connections_count = len(output.get("connections", []))
            services_count = len(output.get("services", []))
            if connections_count < 2:
                reflection["improvements_suggested"].append(f"Only {connections_count} connections for {services_count} services - services may be isolated")
                self.think(f"Concern: {connections_count} connections for {services_count} services. Need at least n-1 connections for a connected graph.", "warning")
            else:
                ratio = connections_count / max(services_count, 1)
                self.think(f"Connection density: {ratio:.1f} connections per service ({connections_count} total). Architecture is {'well-connected' if ratio >= 1.5 else 'adequately connected'}.", "observation")
            reflection["assessments"]["connectivity"] = "adequate" if connections_count >= 2 else "limited"
        
        if "apis" in output:
            apis = output.get("apis", [])
            nfrs = output.get("nfrs", [])
            if len(apis) == 0:
                self.think("No APIs detected - unusual for a cloud architecture. Will rely on downstream agents to infer service endpoints.", "warning")
            else:
                self.think(f"Extracted {len(apis)} APIs and {len(nfrs)} NFRs. Coverage looks {'comprehensive' if len(nfrs) >= 3 else 'partial'}.", "observation")
        
        if "compliance_score" in output:
            score = output.get("compliance_score", 0)
            if score < 70:
                self.think(f"Security compliance score is {score}% - below threshold. Critical security gaps need addressing.", "warning")
                reflection["improvements_suggested"].append(f"Compliance score {score}% is below 70% threshold")
            else:
                self.think(f"Security compliance score: {score}% - {'excellent' if score >= 90 else 'acceptable'}.", "observation")
        
        improvement_count = len(reflection['improvements_suggested'])
        if improvement_count > 0:
            self.think(f"Self-review found {improvement_count} areas for improvement. Flagging for downstream agents.", "reflection")
        else:
            self.think("Self-review passed all criteria. Output quality is satisfactory.", "success")
        
        return reflection
    
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Inter-Agent Communication
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    def send_message(self, to_agent: str, message_type: str, content: str) -> AgentMessage:
        """Send a message to another agent"""
        message = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            content=content
        )
        self.messages_sent.append(message)
        
        # Add to shared message bus if available
        if self._message_bus is not None:
            if to_agent not in self._message_bus:
                self._message_bus[to_agent] = []
            self._message_bus[to_agent].append(message)
        
        self.think(f"Sent {message_type} to {to_agent}: {content[:100]}", "communication")
        
        return message
    
    def receive_messages(self, from_agent: str = None) -> List[AgentMessage]:
        """Receive messages from other agents"""
        if self._message_bus is None:
            return []
        
        my_messages = self._message_bus.get(self.name, [])
        
        if from_agent:
            my_messages = [m for m in my_messages if m.from_agent == from_agent]
        
        self.messages_received.extend(my_messages)
        
        # Clear received messages from bus
        if self.name in self._message_bus:
            self._message_bus[self.name] = []
        
        return my_messages
    
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Agentic Analysis Wrapper
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    async def agentic_analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Wrapper that adds agentic behavior to the standard analyze method.
        Override this in subclasses or call from analyze()."""
        
        # Step 1: Announce ourselves
        self.think(f"I am the {self.persona.role}. Beginning analysis...", "reasoning")
        self.think(f"My expertise: {', '.join(self.persona.expertise)}", "reasoning")
        
        # Step 2: Check for messages from other agents
        messages = self.receive_messages()
        if messages:
            self.think(f"Received {len(messages)} messages from other agents", "communication")
            for msg in messages:
                self.think(f"From {msg.from_agent}: {msg.content[:100]}", "observation")
        
        # Step 3: Analyze requirements (search docs as a tool)
        self.think("Analyzing requirements to identify key patterns...", "reasoning")
        
        # Step 4: Call the actual analyze implementation (to be done by subclass)
        # This is where the actual LLM call happens
        
        return {"agentic_initialized": True}
    
    def get_thinking_summary(self) -> Dict[str, Any]:
        """Get a summary of all agent thinking for display"""
        return {
            "agent": self.name,
            "persona": {
                "role": self.persona.role,
                "emoji": self.persona.avatar_emoji,
                "expertise": self.persona.expertise
            },
            "thoughts": [
                {
                    "type": t.thought_type,
                    "content": t.content,
                    "timestamp": t.timestamp,
                    "emoji": self._get_thought_emoji(t.thought_type)
                }
                for t in self.thoughts
            ],
            "tool_calls": [
                {
                    "tool": tc.tool_name,
                    "duration_ms": tc.duration_ms
                }
                for tc in self.tool_calls
            ],
            "messages_sent": len(self.messages_sent),
            "messages_received": len(self.messages_received)
        }

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    COMPLETED = "completed"

class BaseAgent(AgenticMixin, ABC):
    """Base class for all architecture agents with Agentic AI capabilities.
    
    Features from AgenticMixin:
    - Chain-of-Thought reasoning with visible thinking steps
    - Tool usage protocol with explicit tool calls  
    - Self-reflection and critique
    - Inter-agent communication
    - Agent personas with distinct identities
    """
    
    def __init__(self, name: str, openai_client: Optional[AsyncAzureOpenAI] = None, agent_type: str = "architecture"):
        self.name = name
        self.status = AgentStatus.IDLE
        self.openai_client = openai_client or AsyncAzureOpenAI(
            api_key=azure_openai_config.API_KEY or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=azure_openai_config.API_VERSION,
            azure_endpoint=azure_openai_config.ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = azure_openai_config.DEPLOYMENT_NAME
        # All agents share the singleton local azure-docs scanner (index built once at startup)
        self.scanner = get_scanner()
        # Draw.io reference analyzer for connection patterns and layouts
        self.reference_analyzer = get_reference_analyzer()
        
        # Initialize agentic capabilities
        self.__init_agentic__(agent_type=agent_type, progress_callback=None)
    
    def _get_drawio_reference_context(self, requirements: str, max_references: int = 3) -> str:
        """Get reference context from analyzed Draw.io diagrams for better connections and layouts."""
        return self.reference_analyzer.get_prompt_context(requirements, max_references)
    
    def _get_connection_label(self, source: str, target: str) -> str:
        """Get a meaningful connection label based on learned patterns."""
        return self.reference_analyzer.generate_connection_label(source, target)
    
    def _search_local_docs(self, query: str, domain_terms: List[str] = None, max_results: int = 6) -> str:
        """Search local azure-docs and format results as a prompt section.
        Args:
            query: The search query (requirements text or domain keywords).
            domain_terms: Extra domain-specific terms to boost relevance (e.g. ['security', 'firewall', 'identity']).
            max_results: Max entries to return.
        Returns:
            A formatted string block ready to insert into an LLM prompt.
        """
        combined_query = query
        if domain_terms:
            combined_query = query + " " + " ".join(domain_terms)
        
        results = self.scanner.search(combined_query, max_results=max_results)
        if not results:
            return ""
        
        section = "\n\nLOCAL AZURE ARCHITECTURE CENTER REFERENCE DOCS:\n"
        for i, entry in enumerate(results, 1):
            prompt_entry = self.scanner.get_entry_for_prompt(entry, include_content=True)
            diagrams = prompt_entry.get("diagrams", [])
            diagrams_info = f" | Diagrams: {len(diagrams)} available" if diagrams else ""
            section += f"\n--- Reference {i} ---\n"
            section += f"Title: {prompt_entry.get('title', 'N/A')}\n"
            section += f"URL: {prompt_entry.get('url', 'N/A')}\n"
            section += f"Category: {prompt_entry.get('category', 'N/A')}\n"
            section += f"Products: {', '.join(prompt_entry.get('products', []))}\n"
            section += f"Summary: {prompt_entry.get('summary', 'N/A')}{diagrams_info}\n"
            if prompt_entry.get("content_excerpt"):
                section += f"Content Excerpt:\n{prompt_entry['content_excerpt'][:1200]}\n"
        return section
        
    @abstractmethod
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze requirements and return recommendations"""
        pass
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and prepare JSON response for parsing"""
        if not response or not isinstance(response, str) or response.strip() == "":
            return "{}"
        
        cleaned = response.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Find the start of the JSON object
        start_brace = cleaned.find('{')
        if start_brace == -1:
            return "{}"
        
        # Find the end of the JSON object
        end_brace = cleaned.rfind('}')
        if end_brace == -1:
            return "{}"
            
        cleaned = cleaned[start_brace:end_brace+1]
        
        # Fix trailing commas using a more robust regex
        import re
        cleaned = re.sub(r',\s*([\}\]])', r'\1', cleaned)

        return cleaned
    
    def _extract_partial_data(self, response: str, default_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract partial data from malformed/truncated JSON responses.
        Tries to recover services, connections, containers, and recommendations arrays."""
        result = default_response.copy()
        
        # Try to recover each major array field from the partial response
        for field in ["services", "connections", "containers", "recommendations", "annotations"]:
            if f'"{field}"' in response:
                try:
                    start_idx = response.find(f'"{field}"')
                    if start_idx >= 0:
                        remaining = response[start_idx:]
                        bracket_start = remaining.find('[')
                        if bracket_start == -1:
                            continue
                        # Find matching closing bracket (handle nested arrays/objects)
                        depth = 0
                        bracket_end = -1
                        for i in range(bracket_start, len(remaining)):
                            if remaining[i] == '[':
                                depth += 1
                            elif remaining[i] == ']':
                                depth -= 1
                                if depth == 0:
                                    bracket_end = i
                                    break
                        if bracket_end > bracket_start:
                            array_content = remaining[bracket_start:bracket_end + 1]
                            # Fix trailing commas before attempting parse
                            import re
                            array_content = re.sub(r',\s*([\}\]])', r'\1', array_content)
                            parsed_array = json.loads(array_content)
                            if parsed_array:
                                result[field] = parsed_array
                                logger.info(f"Recovered {len(parsed_array)} items from partial '{field}' data")
                except Exception as e:
                    logger.warning(f"Failed to recover '{field}' from partial response: {e}")
        
        return result
    
    def _safe_json_parse(self, response: str, default_response: Dict[str, Any]) -> Dict[str, Any]:
        """Safely parse JSON with fallback to default response"""
        try:
            # Check for error responses from _call_openai
            if response and '"error":' in response:
                logger.warning(f"Agent {self.name} received error response: {response}")
                return default_response
                
            cleaned_response = self._clean_json_response(response)
            if not cleaned_response or cleaned_response == "{}":
                logger.warning(f"Empty response received by {self.name}")
                return default_response
            
            # Try to parse the cleaned JSON
            parsed = json.loads(cleaned_response)
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {self.name}: {str(e)}, Response: {response[:300]}...")
            print(f"Agent {self.name} failed: {repr(response[:100])}")  # Debug output for console
            # Try to extract any usable information from partial response
            if '"recommendations"' in response or '"services"' in response:
                logger.info(f"Attempting to extract partial data from {self.name} response")
                return self._extract_partial_data(response, default_response)
            return default_response
        except Exception as e:
            logger.error(f"Unexpected error in {self.name} JSON parsing: {str(e)}")
            return default_response
    
    async def _call_openai(self, messages: List[Dict[str, str]], model: str = None) -> str:
        """Make async call to OpenAI API with improved error handling and retry logic"""
        max_retries = agent_config.AGENT_MAX_RETRIES
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self.status = AgentStatus.WORKING
                
                # Add system message to ensure valid JSON output
                enhanced_messages = messages.copy()
                if enhanced_messages[0]["role"] == "system":
                    enhanced_messages[0]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON without any trailing commas, ensure all brackets and braces are properly closed, and do not include any explanatory text outside the JSON."
                
                # Exponential backoff timeout based on attempt
                timeout_duration = agent_config.AGENT_TIMEOUT_BASE + (attempt * agent_config.AGENT_TIMEOUT_INCREMENT)
                
                # Add timeout and improve parameters for better completion
                # Use higher token limit for ArchitectureAgent which must output
                # services + containers + connections + annotations in one JSON
                agent_max_tokens = agent_config.AGENT_MAX_TOKENS_ARCHITECTURE if "architect" in self.name.lower() else agent_config.AGENT_MAX_TOKENS_DEFAULT
                
                response = await asyncio.wait_for(
                    self.openai_client.chat.completions.create(
                        model=model or self.deployment_name,
                        messages=enhanced_messages,
                        temperature=agent_config.AGENT_TEMPERATURE,
                        max_tokens=agent_max_tokens,
                        top_p=0.95,      # High quality responses
                        frequency_penalty=0.0,
                        presence_penalty=0.0
                    ),
                    timeout=timeout_duration
                )

            
                
                self.status = AgentStatus.COMPLETED
                content = response.choices[0].message.content
                
                # Check if response is empty or None
                if not content or content.strip() == "":
                    if attempt < max_retries - 1:
                        logger.warning(f"Empty response from {self.name}, retrying... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(base_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"OpenAI returned empty content for {self.name}")
                        raise AgentAPIError(self.name, "Empty response from OpenAI")
                
                # Success - return the content
                return content
                
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"OpenAI API timeout for {self.name}, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.status = AgentStatus.ERROR
                    logger.error(f"OpenAI API timeout for {self.name} after {max_retries} attempts")
                    raise AgentTimeoutError(self.name, max_retries)
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"OpenAI API error in {self.name}: {str(e)}, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.status = AgentStatus.ERROR
                    logger.error(f"OpenAI API error in {self.name} after {max_retries} attempts: {str(e)}")
                    raise AgentAPIError(self.name, str(e))
        
        # This should never be reached, but just in case
        self.status = AgentStatus.ERROR
        raise AgentAPIError(self.name, "Unexpected error in retry logic")

