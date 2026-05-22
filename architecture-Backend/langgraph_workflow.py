"""
LangGraph-based Multi-Agent Workflow for Architecture Generation

This module provides a LangGraph implementation that wraps the existing agents
for improved accuracy through:
- Structured state management with TypedDict
- Conditional routing based on analysis quality
- Checkpointing for resumable workflows
- Retry logic with quality validation
- Inter-agent feedback loops
"""

import os
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Literal, Annotated, TypedDict, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph not installed. Install with: pip install langgraph langchain-core langchain-openai")

# Import existing agents
from agents import (
    SecurityAgent, PerformanceAgent, ConnectionExpertAgent, ArchitectureAgent,
    ComponentExtractionAgent, AzureArchitectureReferenceAgent, RequirementsValidationAgent,
    AzureArchitectureReviewAgent, AgentOrchestrator, AgentMessage
)
from config import agent_config, workflow_config

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# STATE SCHEMA - Structured state for accurate data passing
# ═══════════════════════════════════════════════════════════════════════════════

class AgentOutput(TypedDict, total=False):
    """Output from a single agent"""
    status: str
    duration: float
    data: Dict[str, Any]
    quality_score: float
    errors: List[str]
    warnings: List[str]


class WorkflowState(TypedDict, total=False):
    """
    Structured state for the multi-agent workflow.
    Using TypedDict ensures type safety and clear data contracts.
    """
    # Input
    user_requirements: str
    project_name: str
    workflow_id: str
    
    # Control flags
    include_connection_agent: bool
    require_high_quality: bool
    max_retries: int
    
    # Agent outputs
    component_extraction: AgentOutput
    azure_references: AgentOutput
    security_analysis: AgentOutput
    performance_analysis: AgentOutput
    architecture_design: AgentOutput
    connection_optimization: AgentOutput
    requirements_validation: AgentOutput
    final_review: AgentOutput
    
    # Aggregated results
    all_services: List[Dict[str, Any]]
    all_connections: List[Dict[str, Any]]
    combined_architecture: Dict[str, Any]
    
    # Quality metrics
    overall_quality_score: float
    quality_issues: List[str]
    iteration_count: int
    
    # Workflow metadata
    current_agent: str
    agents_executed: List[str]
    processing_timeline: List[Dict[str, Any]]
    workflow_status: str
    error_message: Optional[str]
    
    # Callback for progress updates
    progress_callback: Optional[Callable]


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY VALIDATORS - Ensure accurate outputs
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_quality_score(output: Dict[str, Any], agent_type: str) -> float:
    """
    Calculate quality score for agent output based on completeness and validity.
    Returns score from 0.0 to 1.0
    """
    score = 0.0
    
    if agent_type == "component_extraction":
        # Check required fields
        if output.get("apis"):
            score += 0.2
        if output.get("nfrs"):
            score += 0.2
        if output.get("technical_requirements"):
            score += 0.2
        if output.get("summary", {}).get("recommended_architecture_pattern"):
            score += 0.2
        if output.get("tech_stack"):
            score += 0.2
            
    elif agent_type == "security":
        if output.get("security_recommendations"):
            score += 0.25
        if output.get("threat_assessment"):
            score += 0.25
        if output.get("compliance_requirements"):
            score += 0.25
        if output.get("identity_design"):
            score += 0.25
            
    elif agent_type == "architecture":
        services = output.get("services", [])
        connections = output.get("connections", [])
        
        if services and len(services) >= workflow_config.MIN_SERVICES_REQUIRED:
            score += 0.3
        if connections and len(connections) >= 1:
            score += 0.3
        if output.get("architecture_pattern"):
            score += 0.2
        if output.get("resource_groups"):
            score += 0.2
            
    elif agent_type == "validation":
        if output.get("validation_status") in ["valid", "valid_with_warnings"]:
            score += 0.5
        if output.get("requirements_coverage"):
            score += 0.3
        if output.get("validation_details"):
            score += 0.2
            
    elif agent_type == "review":
        if output.get("waf_assessment"):
            score += 0.3
        if output.get("overall_score") is not None:
            score += 0.3
        if output.get("recommendations"):
            score += 0.2
        if output.get("improved_architecture"):
            score += 0.2
    else:
        # Generic scoring
        if output and not output.get("error"):
            score = 0.7
        if len(output.keys()) >= 5:
            score = 0.9
            
    return min(score, 1.0)


def validate_architecture_quality(state: WorkflowState) -> Tuple[bool, List[str]]:
    """
    Validate overall architecture quality.
    Returns (is_valid, issues)
    """
    issues = []
    
    # Check services
    services = state.get("all_services", [])
    if len(services) < workflow_config.MIN_SERVICES_REQUIRED:
        issues.append("Architecture has too few services")
    
    # Check connections
    connections = state.get("all_connections", [])
    if len(connections) == 0:
        issues.append("No connections defined between services")
    
    # Check for orphan services
    if services and connections:
        connected_services = set()
        for conn in connections:
            connected_services.add(conn.get("source", ""))
            connected_services.add(conn.get("target", ""))
        
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}
        orphans = service_names - connected_services - {""}
        if orphans:
            issues.append(f"Orphan services found: {', '.join(orphans)}")
    
    # Check quality scores
    min_quality = 0.6
    for key in ["security_analysis", "architecture_design", "validation"]:
        output = state.get(key, {})
        if output.get("quality_score", 0) < min_quality:
            issues.append(f"{key} quality below threshold ({output.get('quality_score', 0):.2f} < {min_quality})")
    
    return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════════════════
# LANGGRAPH NODE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class LangGraphAgentNodes:
    """
    Node functions for LangGraph workflow.
    Each node wraps an existing agent and updates the structured state.
    """
    
    def __init__(self):
        """Initialize all agents"""
        self.component_agent = ComponentExtractionAgent()
        self.reference_agent = AzureArchitectureReferenceAgent()
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.architecture_agent = ArchitectureAgent()
        self.connection_agent = ConnectionExpertAgent()
        self.validation_agent = RequirementsValidationAgent()
        self.review_agent = AzureArchitectureReviewAgent()
        
        self.all_agents = [
            self.component_agent, self.reference_agent,
            self.security_agent, self.performance_agent,
            self.architecture_agent, self.connection_agent,
            self.validation_agent, self.review_agent
        ]
    
    def _broadcast_progress(self, state: WorkflowState, agent_name: str, status: str, 
                           percentage: int, message: str, **extra):
        """Broadcast progress update if callback is set"""
        callback = state.get("progress_callback")
        if callback:
            callback(agent_name, status, percentage, {"message": message, **extra})
            
    async def component_extraction_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Extract components from requirements"""
        agent_name = "ComponentExtractionAgent"
        self._broadcast_progress(state, agent_name, "running", 5, 
                                 "📝 Extracting APIs, NFRs, and technical requirements...")
        
        start_time = time.time()
        try:
            result = await self.component_agent.analyze(state["user_requirements"])
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "component_extraction")
            
            state["component_extraction"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["current_agent"] = agent_name
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            self._broadcast_progress(state, agent_name, "completed", 12,
                f"✅ Found {len(result.get('apis', []))} APIs, {len(result.get('nfrs', []))} NFRs",
                quality_score=quality, duration=round(duration, 2))
            
        except Exception as e:
            logger.error(f"Component extraction failed: {e}")
            state["component_extraction"] = AgentOutput(
                status="error",
                duration=time.time() - start_time,
                data={},
                quality_score=0.0,
                errors=[str(e)],
                warnings=[]
            )
            state["error_message"] = str(e)
            
        return state
    
    async def azure_references_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Find Azure reference architectures"""
        agent_name = "AzureArchitectureReferenceAgent"
        self._broadcast_progress(state, agent_name, "running", 18,
                                 "🔍 Searching Azure Architecture Center for reference patterns...")
        
        start_time = time.time()
        try:
            # Build context from component extraction
            context = {
                "component_extraction": state.get("component_extraction", {}).get("data", {}),
                "tech_stack": state.get("component_extraction", {}).get("data", {}).get("tech_stack", [])
            }
            
            result = await self.reference_agent.analyze(state["user_requirements"], context)
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "references")
            
            state["azure_references"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            refs_count = len(result.get("reference_architectures", []))
            self._broadcast_progress(state, agent_name, "completed", 25,
                f"✅ Found {refs_count} reference architectures",
                quality_score=quality, duration=round(duration, 2))
            
        except Exception as e:
            logger.error(f"Azure references failed: {e}")
            state["azure_references"] = AgentOutput(
                status="error", duration=time.time() - start_time, data={},
                quality_score=0.0, errors=[str(e)], warnings=[]
            )
            
        return state
    
    async def security_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Security analysis with retry for quality"""
        agent_name = "SecurityAgent"
        self._broadcast_progress(state, agent_name, "running", 32,
                                 "🔐 Analyzing security requirements and compliance...")
        
        start_time = time.time()
        max_retries = state.get("max_retries", workflow_config.MAX_RETRIES)
        
        for attempt in range(max_retries + 1):
            try:
                context = {
                    "component_extraction": state.get("component_extraction", {}).get("data", {}),
                    "azure_references": state.get("azure_references", {}).get("data", {})
                }
                
                result = await self.security_agent.analyze(state["user_requirements"], context)
                quality = calculate_quality_score(result, "security")
                
                # Retry if quality is too low and we have attempts left
                if quality < workflow_config.MIN_QUALITY_THRESHOLD and attempt < max_retries:
                    logger.warning(f"Security analysis quality low ({quality}), retrying...")
                    continue
                
                duration = time.time() - start_time
                state["security_analysis"] = AgentOutput(
                    status="completed",
                    duration=duration,
                    data=result,
                    quality_score=quality,
                    errors=[],
                    warnings=[f"Retry count: {attempt}"] if attempt > 0 else []
                )
                state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
                state["processing_timeline"] = state.get("processing_timeline", []) + [{
                    "agent": agent_name,
                    "duration": duration,
                    "quality_score": quality,
                    "attempts": attempt + 1
                }]
                
                self._broadcast_progress(state, agent_name, "completed", 40,
                    f"✅ Security analysis complete (quality: {quality:.0%})",
                    quality_score=quality, duration=round(duration, 2))
                break
                
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Security analysis failed after {max_retries} retries: {e}")
                    state["security_analysis"] = AgentOutput(
                        status="error", duration=time.time() - start_time, data={},
                        quality_score=0.0, errors=[str(e)], warnings=[]
                    )
                    
        return state
    
    async def performance_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Performance analysis"""
        agent_name = "PerformanceAgent"
        self._broadcast_progress(state, agent_name, "running", 48,
                                 "⚡ Analyzing performance requirements and scalability...")
        
        start_time = time.time()
        try:
            context = {
                "component_extraction": state.get("component_extraction", {}).get("data", {}),
                "azure_references": state.get("azure_references", {}).get("data", {}),
                "security_analysis": state.get("security_analysis", {}).get("data", {})
            }
            
            result = await self.performance_agent.analyze(state["user_requirements"], context)
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "performance")
            
            state["performance_analysis"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            self._broadcast_progress(state, agent_name, "completed", 55,
                f"✅ Performance analysis complete",
                quality_score=quality, duration=round(duration, 2))
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            state["performance_analysis"] = AgentOutput(
                status="error", duration=time.time() - start_time, data={},
                quality_score=0.0, errors=[str(e)], warnings=[]
            )
            
        return state
    
    async def architecture_design_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Core architecture design with quality validation"""
        agent_name = "ArchitectureAgent"
        self._broadcast_progress(state, agent_name, "running", 62,
                                 "🏗️ Designing Azure architecture based on all analyses...")
        
        start_time = time.time()
        max_retries = state.get("max_retries", workflow_config.MAX_RETRIES)
        
        for attempt in range(max_retries + 1):
            try:
                context = {
                    "component_extraction": state.get("component_extraction", {}).get("data", {}),
                    "azure_references": state.get("azure_references", {}).get("data", {}),
                    "security_analysis": state.get("security_analysis", {}).get("data", {}),
                    "performance_analysis": state.get("performance_analysis", {}).get("data", {})
                }
                
                result = await self.architecture_agent.analyze(state["user_requirements"], context)
                quality = calculate_quality_score(result, "architecture")
                
                # Validate architecture has minimum requirements
                services = result.get("services", [])
                connections = result.get("connections", [])
                
                if (len(services) < workflow_config.MIN_SERVICES_REQUIRED or len(connections) == 0) and attempt < max_retries:
                    logger.warning(f"Architecture incomplete (services={len(services)}, connections={len(connections)}), retrying...")
                    continue
                
                duration = time.time() - start_time
                
                # Update aggregated state
                state["all_services"] = services
                state["all_connections"] = connections
                state["combined_architecture"] = result
                
                state["architecture_design"] = AgentOutput(
                    status="completed",
                    duration=duration,
                    data=result,
                    quality_score=quality,
                    errors=[],
                    warnings=[f"Retry count: {attempt}"] if attempt > 0 else []
                )
                state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
                state["processing_timeline"] = state.get("processing_timeline", []) + [{
                    "agent": agent_name,
                    "duration": duration,
                    "quality_score": quality,
                    "services_count": len(services),
                    "connections_count": len(connections)
                }]
                
                self._broadcast_progress(state, agent_name, "completed", 72,
                    f"✅ Architecture designed: {len(services)} services, {len(connections)} connections",
                    quality_score=quality, duration=round(duration, 2))
                break
                
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Architecture design failed: {e}")
                    state["architecture_design"] = AgentOutput(
                        status="error", duration=time.time() - start_time, data={},
                        quality_score=0.0, errors=[str(e)], warnings=[]
                    )
                    
        return state
    
    async def connection_optimization_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Connection optimization (conditional)"""
        if not state.get("include_connection_agent", True):
            return state
            
        agent_name = "ConnectionExpertAgent"
        self._broadcast_progress(state, agent_name, "running", 78,
                                 "🔗 Optimizing service connections and data flows...")
        
        start_time = time.time()
        try:
            context = {
                "architecture_design": state.get("architecture_design", {}).get("data", {}),
                "security_analysis": state.get("security_analysis", {}).get("data", {}),
                "performance_analysis": state.get("performance_analysis", {}).get("data", {})
            }
            
            result = await self.connection_agent.analyze(state["user_requirements"], context)
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "connections")
            
            # Update connections if improved
            if result.get("optimized_connections"):
                state["all_connections"] = result["optimized_connections"]
                
            state["connection_optimization"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            self._broadcast_progress(state, agent_name, "completed", 82,
                f"✅ Connections optimized",
                quality_score=quality, duration=round(duration, 2))
            
        except Exception as e:
            logger.error(f"Connection optimization failed: {e}")
            state["connection_optimization"] = AgentOutput(
                status="error", duration=time.time() - start_time, data={},
                quality_score=0.0, errors=[str(e)], warnings=[]
            )
            
        return state
    
    async def validation_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Requirements validation"""
        agent_name = "RequirementsValidationAgent"
        self._broadcast_progress(state, agent_name, "running", 88,
                                 "✅ Validating architecture against requirements...")
        
        start_time = time.time()
        try:
            context = {
                "component_extraction": state.get("component_extraction", {}).get("data", {}),
                "architecture_design": state.get("architecture_design", {}).get("data", {}),
                "all_services": state.get("all_services", []),
                "all_connections": state.get("all_connections", [])
            }
            
            result = await self.validation_agent.analyze(state["user_requirements"], context)
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "validation")
            
            state["requirements_validation"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            coverage = result.get("requirements_coverage", {}).get("percentage", 0)
            self._broadcast_progress(state, agent_name, "completed", 92,
                f"✅ Validation complete: {coverage}% requirements covered",
                quality_score=quality, duration=round(duration, 2))
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state["requirements_validation"] = AgentOutput(
                status="error", duration=time.time() - start_time, data={},
                quality_score=0.0, errors=[str(e)], warnings=[]
            )
            
        return state
    
    async def final_review_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Final architecture review with WAF assessment"""
        agent_name = "AzureArchitectureReviewAgent"
        self._broadcast_progress(state, agent_name, "running", 95,
                                 "🔍 Final review with Azure Well-Architected Framework...")
        
        start_time = time.time()
        try:
            # Collect all results for comprehensive review
            context = {
                "component_extraction": state.get("component_extraction", {}).get("data", {}),
                "azure_references": state.get("azure_references", {}).get("data", {}),
                "security_analysis": state.get("security_analysis", {}).get("data", {}),
                "performance_analysis": state.get("performance_analysis", {}).get("data", {}),
                "architecture_design": state.get("architecture_design", {}).get("data", {}),
                "connection_optimization": state.get("connection_optimization", {}).get("data", {}),
                "requirements_validation": state.get("requirements_validation", {}).get("data", {}),
                "all_services": state.get("all_services", []),
                "all_connections": state.get("all_connections", [])
            }
            
            result = await self.review_agent.analyze(state["user_requirements"], context)
            duration = time.time() - start_time
            quality = calculate_quality_score(result, "review")
            
            # Update architecture if review provides improvements
            if result.get("improved_architecture"):
                improved = result["improved_architecture"]
                if improved.get("services"):
                    state["all_services"] = improved["services"]
                if improved.get("connections"):
                    state["all_connections"] = improved["connections"]
                state["combined_architecture"] = {
                    **state.get("combined_architecture", {}),
                    **improved
                }
            
            state["final_review"] = AgentOutput(
                status="completed",
                duration=duration,
                data=result,
                quality_score=quality,
                errors=[],
                warnings=[]
            )
            state["agents_executed"] = state.get("agents_executed", []) + [agent_name]
            state["processing_timeline"] = state.get("processing_timeline", []) + [{
                "agent": agent_name,
                "duration": duration,
                "quality_score": quality
            }]
            
            # Calculate overall quality
            all_qualities = [
                state.get("security_analysis", {}).get("quality_score", 0),
                state.get("architecture_design", {}).get("quality_score", 0),
                state.get("requirements_validation", {}).get("quality_score", 0),
                quality
            ]
            state["overall_quality_score"] = sum(all_qualities) / len(all_qualities)
            state["workflow_status"] = "completed"
            
            overall_score = result.get("overall_score", 0)
            self._broadcast_progress(state, agent_name, "completed", 100,
                f"✅ Review complete: WAF score {overall_score}/100",
                quality_score=quality, duration=round(duration, 2),
                overall_waf_score=overall_score)
            
        except Exception as e:
            logger.error(f"Final review failed: {e}")
            state["final_review"] = AgentOutput(
                status="error", duration=time.time() - start_time, data={},
                quality_score=0.0, errors=[str(e)], warnings=[]
            )
            state["workflow_status"] = "completed_with_errors"
            
        return state


# ═══════════════════════════════════════════════════════════════════════════════
# CONDITIONAL ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

def should_retry_architecture(state: WorkflowState) -> Literal["retry", "continue"]:
    """
    Determine if architecture needs to be regenerated based on quality.
    """
    arch_output = state.get("architecture_design", {})
    quality = arch_output.get("quality_score", 0)
    iteration = state.get("iteration_count", 0)
    max_iterations = workflow_config.MAX_ITERATIONS
    
    if quality < workflow_config.MIN_QUALITY_THRESHOLD and iteration < max_iterations:
        state["iteration_count"] = iteration + 1
        return "retry"
    return "continue"


def should_include_connections(state: WorkflowState) -> Literal["include", "skip"]:
    """Determine if connection agent should run"""
    return "include" if state.get("include_connection_agent", True) else "skip"


# ═══════════════════════════════════════════════════════════════════════════════
# LANGGRAPH WORKFLOW BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class LangGraphWorkflow:
    """
    LangGraph-based workflow that provides:
    - Structured state management
    - Conditional routing
    - Checkpointing for resumable workflows
    - Quality validation with retry logic
    """
    
    def __init__(self):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph not installed. Run: pip install langgraph langchain-core")
        
        self.nodes = LangGraphAgentNodes()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph"""
        
        # Create graph with our state schema
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("component_extraction", self.nodes.component_extraction_node)
        workflow.add_node("azure_references", self.nodes.azure_references_node)
        workflow.add_node("security_analysis", self.nodes.security_analysis_node)
        workflow.add_node("performance_analysis", self.nodes.performance_analysis_node)
        workflow.add_node("architecture_design", self.nodes.architecture_design_node)
        workflow.add_node("connection_optimization", self.nodes.connection_optimization_node)
        workflow.add_node("validation", self.nodes.validation_node)
        workflow.add_node("final_review", self.nodes.final_review_node)
        
        # Add edges (linear flow with conditional connection agent)
        workflow.add_edge(START, "component_extraction")
        workflow.add_edge("component_extraction", "azure_references")
        workflow.add_edge("azure_references", "security_analysis")
        workflow.add_edge("security_analysis", "performance_analysis")
        workflow.add_edge("performance_analysis", "architecture_design")
        
        # Conditional edge for connection agent
        workflow.add_conditional_edges(
            "architecture_design",
            should_include_connections,
            {
                "include": "connection_optimization",
                "skip": "validation"
            }
        )
        
        workflow.add_edge("connection_optimization", "validation")
        workflow.add_edge("validation", "final_review")
        workflow.add_edge("final_review", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def execute(
        self,
        requirements: str,
        project_name: str = None,
        include_connection_agent: bool = True,
        progress_callback: Callable = None,
        thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute the LangGraph workflow.
        
        Args:
            requirements: User requirements text
            project_name: Optional project name
            include_connection_agent: Whether to include connection optimization
            progress_callback: Callback for progress updates
            thread_id: Thread ID for checkpointing (enables resume)
            
        Returns:
            Workflow results dictionary
        """
        logger.info("🚀 Starting LangGraph Multi-Agent Workflow...")
        logger.info("🧠 LangGraph Mode: Structured state, conditional routing, checkpointing enabled")
        
        # Initialize state
        initial_state: WorkflowState = {
            "user_requirements": requirements,
            "project_name": project_name or "architecture_project",
            "workflow_id": f"lg_workflow_{int(time.time())}",
            "include_connection_agent": include_connection_agent,
            "require_high_quality": True,
            "max_retries": 2,
            "all_services": [],
            "all_connections": [],
            "combined_architecture": {},
            "overall_quality_score": 0.0,
            "quality_issues": [],
            "iteration_count": 0,
            "current_agent": "",
            "agents_executed": [],
            "processing_timeline": [],
            "workflow_status": "running",
            "error_message": None,
            "progress_callback": progress_callback
        }
        
        # Config for checkpointing
        config = {"configurable": {"thread_id": thread_id or initial_state["workflow_id"]}}
        
        start_time = time.time()
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state, config)
            
            total_duration = time.time() - start_time
            
            # Build response matching existing format
            result = {
                "workflow_id": final_state["workflow_id"],
                "user_prompt": requirements,
                "project_name": project_name,
                "workflow_status": final_state.get("workflow_status", "completed"),
                "agents_executed": final_state.get("agents_executed", []),
                "processing_timeline": final_state.get("processing_timeline", []),
                "total_duration": total_duration,
                "langgraph_mode": True,
                
                # Agent results
                "agent0_component_extraction": final_state.get("component_extraction", {}).get("data", {}),
                "agent1_azure_references": final_state.get("azure_references", {}).get("data", {}),
                "security_analysis": final_state.get("security_analysis", {}).get("data", {}),
                "performance_analysis": final_state.get("performance_analysis", {}).get("data", {}),
                "architecture_design": final_state.get("architecture_design", {}).get("data", {}),
                "connection_optimization": final_state.get("connection_optimization", {}).get("data", {}),
                "requirements_validation": final_state.get("requirements_validation", {}).get("data", {}),
                "final_review": final_state.get("final_review", {}).get("data", {}),
                
                # Aggregated results
                "combined_architecture": final_state.get("combined_architecture", {}),
                "all_services": final_state.get("all_services", []),
                "all_connections": final_state.get("all_connections", []),
                
                # Quality metrics
                "overall_quality_score": final_state.get("overall_quality_score", 0),
                "quality_issues": final_state.get("quality_issues", [])
            }
            
            logger.info(f"✅ LangGraph workflow completed in {total_duration:.2f}s")
            logger.info(f"   Quality Score: {final_state.get('overall_quality_score', 0):.0%}")
            
            return result
            
        except Exception as e:
            logger.error(f"LangGraph workflow failed: {e}")
            return {
                "workflow_id": initial_state["workflow_id"],
                "workflow_status": "error",
                "error_message": str(e),
                "total_duration": time.time() - start_time,
                "langgraph_mode": True
            }
    
    def get_checkpoint(self, thread_id: str) -> Optional[Dict]:
        """Get checkpoint state for a thread (for resuming)"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            return self.checkpointer.get(config)
        except:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_langgraph_workflow() -> Optional[LangGraphWorkflow]:
    """
    Factory function to get LangGraph workflow.
    Returns None if LangGraph is not installed.
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("LangGraph not available, falling back to standard workflow")
        return None
    return LangGraphWorkflow()


async def run_langgraph_workflow(
    requirements: str,
    project_name: str = None,
    include_connection_agent: bool = True,
    progress_callback: Callable = None
) -> Dict[str, Any]:
    """
    Convenience function to run LangGraph workflow.
    Falls back to standard workflow if LangGraph unavailable.
    """
    workflow = get_langgraph_workflow()
    
    if workflow:
        return await workflow.execute(
            requirements=requirements,
            project_name=project_name,
            include_connection_agent=include_connection_agent,
            progress_callback=progress_callback
        )
    else:
        # Fallback to standard workflow
        from multi_agent_workflow import run_multi_agent_workflow
        return await run_multi_agent_workflow(
            requirements, project_name, include_connection_agent, progress_callback
        )
