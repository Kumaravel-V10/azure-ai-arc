import os
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import asyncio
import time
import logging

# Import all agents from agents.py
from agents import (
    SecurityAgent, PerformanceAgent, ConnectionExpertAgent, ArchitectureAgent,
    ComponentExtractionAgent, AzureArchitectureReferenceAgent, RequirementsValidationAgent,
    AzureArchitectureReviewAgent, AgentOrchestrator, AgentMessage
)
from config import path_config, drawio_config, theme_config

# Import knowledge base for RL reward signals
try:
    from knowledge_base import get_knowledge_manager, get_rl_learner, learn_from_architecture
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

load_dotenv()

logger = logging.getLogger(__name__)

class MultiAgentWorkflowPipeline:
    """
    Multi-Agent Workflow Pipeline with full component-driven architecture generation.
    
    AGENTIC AI FEATURES:
    - Chain-of-Thought reasoning with visible thinking steps
    - Inter-agent communication via shared message bus
    - Self-reflection and critique on outputs
    - Tool usage protocol for Azure docs search
    - Agent personas with distinct identities
    
    Flow:
    Agent 0: ComponentExtractionAgent (extract APIs, NFRs, tech requirements, tech stack)
    Agent 1: AzureArchitectureReferenceAgent (map components to Azure Architecture Center diagrams)
    Agent 2: SecurityAgent (security analysis)
    Agent 3: PerformanceAgent (performance analysis)
    Agent 4: ArchitectureAgent (core architecture design)
    Agent 5: ConnectionExpertAgent (connection optimization - validates and enhances connections)
    Agent 6: RequirementsValidationAgent (validate all requirements are fulfilled)
    Agent 7: AzureArchitectureReviewAgent (FINAL REVIEW - comprehensive Azure expertise review with iterative correction)
    """
    
    def __init__(self):
        # Initialize shared message bus for inter-agent communication
        self.message_bus: Dict[str, List[AgentMessage]] = {}
        
        # Initialize all agents
        try:
            self.agent0_components = ComponentExtractionAgent()
            self.agent1_references = AzureArchitectureReferenceAgent()
            self.agent2_security = SecurityAgent()
            self.agent3_performance = PerformanceAgent() 
            self.agent4_architecture = ArchitectureAgent()
            self.agent5_connection = ConnectionExpertAgent()
            self.agent6_validation = RequirementsValidationAgent()
            self.agent7_review = AzureArchitectureReviewAgent()
            
            # Configure agents for better reliability and set message bus
            self.all_agents = [
                self.agent0_components, self.agent1_references,
                self.agent2_security, self.agent3_performance,
                self.agent4_architecture, self.agent5_connection,
                self.agent6_validation, self.agent7_review
            ]
            
            # Set message bus for all agents (enables inter-agent communication)
            for agent in self.all_agents:
                if hasattr(agent, 'set_message_bus'):
                    agent.set_message_bus(self.message_bus)
                if hasattr(agent, 'deployment_name'):
                    logger.info(f"Agent {agent.name} using deployment: {agent.deployment_name}")
                    
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise
        
    async def execute_workflow(self, user_prompt: str, project_name: str = None, include_connection_agent: bool = True, progress_callback: Optional[callable] = None, interaction_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Execute the complete multi-agent workflow pipeline.
        Flow: ComponentExtraction → AzureReference → Security → Performance → Architecture → Connection → Validation
        
        AGENTIC AI FEATURES:
        - Each agent broadcasts Chain-of-Thought reasoning via progress_callback
        - Agents communicate via shared message_bus
        - Self-reflection on outputs before passing to next agent
        - Human-in-the-loop: interaction_callback pauses for user approval at key checkpoints
        """
        print("🚀 Starting Multi-Agent Workflow Pipeline...")
        print("🔗 Agent Flow: ComponentExtraction → AzureReference → Security → Performance → Architecture → Connection → Validation")
        print("🧠 Agentic AI Mode: Chain-of-Thought reasoning, Inter-agent communication enabled")
        print("=" * 70)
        
        total_steps = 7 if include_connection_agent else 6
        workflow_results = {
            "user_prompt": user_prompt,
            "project_name": project_name,
            "workflow_id": f"workflow_{int(time.time())}",
            "agents_executed": [],
            "processing_timeline": [],
            "agentic_mode": True
        }
        
        try:
            # Set progress callback on all agents for real-time thinking updates
            if progress_callback:
                for agent in self.all_agents:
                    if hasattr(agent, 'set_progress_callback'):
                        agent.set_progress_callback(progress_callback)
            
            # Clear message bus for fresh workflow
            self.message_bus.clear()
            
            # ═══════════════════════════════════════════════════════════════════
            # Agent 0: Component Extraction
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("ComponentExtractionAgent", "running", 5, {
                    "message": "📝 Extracting APIs, NFRs, technical requirements and tech stack from your requirements..."
                })
            print(f"📋 Step 1/{total_steps}: Running Agent 0 - Component Extractor")
            agent0_start = time.time()
            
            agent0_result = await self.agent0_components.analyze(user_prompt)
            agent0_duration = time.time() - agent0_start
            
            workflow_results["agent0_component_extraction"] = agent0_result
            workflow_results["agents_executed"].append("ComponentExtractionAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 0 (Component Extraction)",
                "duration": agent0_duration,
                "status": agent0_result.get("status", "completed")
            })
            
            print(f"⏱️  Agent 0 (Component Extraction) completed in {agent0_duration:.2f} seconds")
            
            if progress_callback:
                thinking = self.agent0_components.get_thinking_summary() if hasattr(self.agent0_components, 'get_thinking_summary') else None
                progress_callback("ComponentExtractionAgent", "completed", 12, {
                    "message": f"✅ Found {len(agent0_result.get('apis', []))} APIs, {len(agent0_result.get('nfrs', []))} NFRs, pattern: {agent0_result.get('summary', {}).get('recommended_architecture_pattern', 'N/A')}",
                    "duration": round(agent0_duration, 2),
                    "apis_found": len(agent0_result.get("apis", [])),
                    "nfrs_found": len(agent0_result.get("nfrs", [])),
                    "tech_requirements": len(agent0_result.get("technical_requirements", [])),
                    "tech_stack": len(agent0_result.get("tech_stack", [])),
                    "integration_points": len(agent0_result.get("integration_points", [])),
                    "complexity": agent0_result.get("summary", {}).get("complexity_level", "N/A"),
                    "recommended_pattern": agent0_result.get("summary", {}).get("recommended_architecture_pattern", "N/A"),
                    "rg_hints": len(agent0_result.get("resource_group_hints", [])),
                    "data_passed_to_next": ["apis", "nfrs", "technical_requirements", "tech_stack", "business_requirements", "data_requirements", "integration_points", "resource_group_hints"],
                    "thinking_summary": thinking
                })
            
            print("-" * 50)

            # ═══════════════════════════════════════════════════════════════════
            # Agent 1: Azure Architecture Reference Mapping
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("AzureArchitectureReferenceAgent", "running", 15, {
                    "message": "🏢 Mapping to Azure Architecture Center reference patterns..."
                })
            print(f"🏛️  Step 2/{total_steps}: Running Agent 1 - Azure Architecture Reference Mapper")
            agent1_start = time.time()
            
            agent1_result = await self.agent1_references.analyze(
                user_prompt,
                context={"component_extraction": agent0_result}
            )
            agent1_duration = time.time() - agent1_start
            
            workflow_results["agent1_azure_references"] = agent1_result
            workflow_results["agents_executed"].append("AzureArchitectureReferenceAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 1 (Azure Reference)",
                "duration": agent1_duration,
                "status": agent1_result.get("status", "completed")
            })
            
            print(f"⏱️  Agent 1 (Azure Reference) completed in {agent1_duration:.2f} seconds")
            
            if progress_callback:
                thinking = self.agent1_references.get_thinking_summary() if hasattr(self.agent1_references, 'get_thinking_summary') else None
                progress_callback("AzureArchitectureReferenceAgent", "completed", 25, {
                    "message": f"✅ Matched {len(agent1_result.get('matched_reference_architectures', []))} reference architectures, {len(agent1_result.get('recommended_azure_services', []))} Azure services recommended",
                    "duration": round(agent1_duration, 2),
                    "matched_architectures": len(agent1_result.get("matched_reference_architectures", [])),
                    "recommended_services": len(agent1_result.get("recommended_azure_services", [])),
                    "design_decisions": len(agent1_result.get("design_decisions", [])),
                    "local_docs_matched": agent1_result.get("local_docs_matched", 0),
                    "recommended_pattern": agent1_result.get("recommended_architecture_pattern", "N/A"),
                    "top_references": [r.get("title", "") for r in agent1_result.get("matched_reference_architectures", [])[:3]],
                    "data_passed_to_next": ["matched_reference_architectures", "recommended_azure_services", "design_decisions"],
                    "thinking_summary": thinking
                })
            
            print("-" * 50)

            # ═══════════════════════════════════════════════════════════════════
            # Agent 2 & 3: Security + Performance Analysis (PARALLEL)
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("SecurityAgent", "running", 30, {
                    "message": "🔐 Analyzing security requirements, compliance, and Azure security services..."
                })
                progress_callback("PerformanceAgent", "running", 30, {
                    "message": "⚡ Analyzing performance requirements, scalability, and optimization strategies..."
                })
            print(f"🔐⚡ Step 3-4/{total_steps}: Running Security + Performance Agents IN PARALLEL")
            parallel_start = time.time()
            
            shared_context = {
                "component_extraction": agent0_result,
                "azure_references": agent1_result
            }
            
            agent2_result, agent3_result = await asyncio.gather(
                self.agent2_security.analyze(user_prompt, context=shared_context),
                self.agent3_performance.analyze(user_prompt, context=shared_context)
            )
            
            parallel_duration = time.time() - parallel_start
            
            # Record Security results
            workflow_results["agent2_security_result"] = agent2_result
            workflow_results["agents_executed"].append("SecurityAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 2 (Security) [parallel]",
                "duration": parallel_duration,
                "status": agent2_result.get("status", "completed")
            })
            
            # Record Performance results
            workflow_results["agent3_performance_result"] = agent3_result
            workflow_results["agents_executed"].append("PerformanceAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 3 (Performance) [parallel]",
                "duration": parallel_duration,
                "status": agent3_result.get("status", "completed")
            })
            
            print(f"⏱️  Security + Performance completed in parallel in {parallel_duration:.2f} seconds")

            if progress_callback:
                thinking_sec = self.agent2_security.get_thinking_summary() if hasattr(self.agent2_security, 'get_thinking_summary') else None
                progress_callback("SecurityAgent", "completed", 45, {
                    "message": f"✅ Security analysis complete: Compliance score {agent2_result.get('compliance_score', 0)}%, {len(agent2_result.get('security_services', []))} security services",
                    "duration": round(parallel_duration, 2),
                    "security_services": [s.get("service", "") for s in agent2_result.get("security_services", [])],
                    "compliance_score": agent2_result.get("compliance_score", 0),
                    "critical_issues": len(agent2_result.get("critical_issues", [])),
                    "quick_wins": len(agent2_result.get("quick_wins", [])),
                    "context_used": ["component_extraction", "azure_references"],
                    "data_passed_to_next": ["security_services", "compliance_score", "network_security", "identity_management"],
                    "thinking_summary": thinking_sec
                })
                
                thinking_perf = self.agent3_performance.get_thinking_summary() if hasattr(self.agent3_performance, 'get_thinking_summary') else None
                progress_callback("PerformanceAgent", "completed", 55, {
                    "message": f"✅ Performance score {agent3_result.get('performance_score', 0)}%, {len(agent3_result.get('optimization_strategies', []))} optimization strategies",
                    "duration": round(parallel_duration, 2),
                    "performance_services": [s.get("service", "") for s in agent3_result.get("performance_services", [])],
                    "performance_score": agent3_result.get("performance_score", 0),
                    "optimization_opportunities": len(agent3_result.get("optimization_opportunities", agent3_result.get("optimization_strategies", []))),
                    "quick_wins": len(agent3_result.get("quick_wins", [])),
                    "context_used": ["component_extraction", "azure_references"],
                    "data_passed_to_next": ["performance_services", "performance_score", "auto_scaling"],
                    "thinking_summary": thinking_perf
                })
            
            print("-" * 50)
            
            # ═══════════════════════════════════════════════════════════════════
            # HUMAN-IN-THE-LOOP CHECKPOINT 1: Review before Architecture Design
            # ═══════════════════════════════════════════════════════════════════
            if interaction_callback:
                print("🤝 Waiting for user approval before Architecture Design...")
                checkpoint_summary = {
                    "checkpoint": "pre_architecture",
                    "agent": "ArchitectureAgent",
                    "title": "Review Analysis Before Architecture Design",
                    "description": "The analysis agents have completed their work. Review their findings before the Architecture agent designs the solution.",
                    "findings": {
                        "components": {
                            "apis": len(agent0_result.get("apis", [])),
                            "nfrs": len(agent0_result.get("nfrs", [])),
                            "tech_stack": len(agent0_result.get("tech_stack", [])),
                            "complexity": agent0_result.get("summary", {}).get("complexity_level", "N/A"),
                            "pattern": agent0_result.get("summary", {}).get("recommended_architecture_pattern", "N/A"),
                        },
                        "references": {
                            "matched": len(agent1_result.get("matched_reference_architectures", [])),
                            "services_recommended": len(agent1_result.get("recommended_azure_services", [])),
                            "top_patterns": [r.get("title", "") for r in agent1_result.get("matched_reference_architectures", [])[:3]],
                        },
                        "security": {
                            "compliance_score": agent2_result.get("compliance_score", 0),
                            "critical_issues": len(agent2_result.get("critical_issues", [])),
                            "services": [s.get("service", "") for s in agent2_result.get("security_services", [])[:5]],
                        },
                        "performance": {
                            "score": agent3_result.get("performance_score", 0),
                            "optimizations": len(agent3_result.get("optimization_strategies", [])),
                            "services": [s.get("service", "") for s in agent3_result.get("performance_services", [])[:5]],
                        },
                    },
                    "recommendations": [
                        {"id": "rec_pattern", "text": f"Use {agent0_result.get('summary', {}).get('recommended_architecture_pattern', 'microservices')} pattern", "type": "pattern"},
                        *[{"id": f"rec_svc_{i}", "text": f"Include {s.get('service', s) if isinstance(s, dict) else s}", "type": "service"} 
                          for i, s in enumerate(agent1_result.get("recommended_azure_services", [])[:6])],
                        *[{"id": f"rec_sec_{i}", "text": issue if isinstance(issue, str) else issue.get("issue", ""), "type": "security_fix"} 
                          for i, issue in enumerate(agent2_result.get("critical_issues", [])[:3])],
                    ],
                }
                
                user_decision = await interaction_callback(
                    "pre_architecture", "ArchitectureAgent", checkpoint_summary
                )
                
                if user_decision and user_decision.get("decision") == "reject":
                    print("❌ User rejected - stopping workflow")
                    workflow_results["workflow_status"] = "rejected_by_user"
                    workflow_results["user_feedback"] = user_decision.get("feedback", "")
                    return workflow_results
                    
                if user_decision and user_decision.get("feedback"):
                    # Append user feedback to the prompt for the architecture agent
                    user_prompt = f"{user_prompt}\n\nUSER FEEDBACK AFTER ANALYSIS: {user_decision['feedback']}"
                    print(f"📝 User feedback incorporated: {user_decision['feedback'][:100]}")
            
            # ═══════════════════════════════════════════════════════════════════
            # Agent 4: Architecture Design (with all prior context)
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("ArchitectureAgent", "running", 60, {
                    "message": "🏗️ Designing Azure architecture with services, connections, and containers..."
                })
            print(f"🏗️  Step 5/{total_steps}: Running Agent 4 - Architecture Expert")
            agent4_start = time.time()
            
            combined_context = {
                "component_extraction": agent0_result,
                "azure_references": agent1_result,
                "security_analysis": agent2_result,
                "performance_analysis": agent3_result
            }
            
            agent4_result = await self.agent4_architecture.analyze(user_prompt, context=combined_context)
            
            agent4_duration = time.time() - agent4_start
            workflow_results["agent4_architecture_result"] = agent4_result
            workflow_results["agents_executed"].append("ArchitectureAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 4 (Architecture)",
                "duration": agent4_duration,
                "status": agent4_result.get("status", "completed")
            })
            
            print(f"⏱️  Agent 4 (Architecture) completed in {agent4_duration:.2f} seconds")
            
            if progress_callback:
                thinking = self.agent4_architecture.get_thinking_summary() if hasattr(self.agent4_architecture, 'get_thinking_summary') else None
                progress_callback("ArchitectureAgent", "completed", 72, {
                    "message": f"✅ Architecture designed: {len(agent4_result.get('services', []))} services, {len(agent4_result.get('connections', []))} connections, {len(agent4_result.get('containers', []))} containers",
                    "duration": round(agent4_duration, 2),
                    "services_designed": len(agent4_result.get("services", [])),
                    "connections_created": len(agent4_result.get("connections", [])),
                    "containers_defined": len(agent4_result.get("containers", [])),
                    "resource_groups": len([c for c in agent4_result.get("containers", []) if c.get("type") == "resource_group"]),
                    "virtual_networks": len([c for c in agent4_result.get("containers", []) if c.get("type") == "virtual_network"]),
                    "subnets": len([c for c in agent4_result.get("containers", []) if c.get("type") == "subnet"]),
                    "architecture_pattern": agent4_result.get("architecture_pattern", "N/A"),
                    "architecture_score": agent4_result.get("architecture_score", 0),
                    "service_names": [s.get("name", "") if isinstance(s, dict) else s for s in agent4_result.get("services", [])[:10]],
                    "annotations": len(agent4_result.get("annotations", [])),
                    "context_used": ["component_extraction", "azure_references", "security_analysis", "performance_analysis"],
                    "data_passed_to_next": ["services", "connections", "containers", "annotations", "architecture_pattern"],
                    "thinking_summary": thinking
                })

            print("-" * 50)
            
            # ═══════════════════════════════════════════════════════════════════
            # Agent 5: Connection Expert (validates and optimizes connections)
            # ═══════════════════════════════════════════════════════════════════
            agent5_result = None
            if include_connection_agent:
                if progress_callback:
                    progress_callback("ConnectionExpertAgent", "running", 75, {
                        "message": "🔗 Optimizing connections: validating flow direction, adding labels, connecting orphan services..."
                    })
                print(f"🔗 Step 6/{total_steps}: Running Agent 5 - Connection Expert")
                agent5_start = time.time()
                
                connection_context = {
                    "component_extraction": agent0_result,
                    "azure_references": agent1_result,
                    "security_analysis": agent2_result,
                    "performance_analysis": agent3_result,
                    "architecture_analysis": agent4_result
                }
                
                agent5_result = await self.agent5_connection.analyze(user_prompt, context=connection_context)
                
                # Update architecture_analysis with enhanced connections
                if agent5_result.get("status") == "completed":
                    enhanced_arch = agent5_result.get("enhanced_architecture", {})
                    if enhanced_arch:
                        agent4_result = enhanced_arch
                        workflow_results["agent4_architecture_result"] = agent4_result
                
                agent5_duration = time.time() - agent5_start
                workflow_results["agent5_connection_result"] = agent5_result
                workflow_results["agents_executed"].append("ConnectionExpertAgent")
                workflow_results["processing_timeline"].append({
                    "agent": "Agent 5 (Connection)",
                    "duration": agent5_duration,
                    "status": agent5_result.get("status", "completed")
                })
                
                connection_stats = agent5_result.get("connection_stats", {})
                print(f"⏱️  Agent 5 (Connection) optimized {connection_stats.get('total_connections', 0)} connections in {agent5_duration:.2f}s")
                if progress_callback:
                    thinking = self.agent5_connection.get_thinking_summary() if hasattr(self.agent5_connection, 'get_thinking_summary') else None
                    progress_callback("ConnectionExpertAgent", "completed", 82, {
                        "message": f"✅ Connections optimized: {connection_stats.get('total_connections', 0)} total, {connection_stats.get('services_connected', 0)} services connected, {connection_stats.get('orphan_services', 0)} orphans fixed",
                        "duration": round(agent5_duration, 2),
                        "total_connections": connection_stats.get("total_connections", 0),
                        "services_connected": connection_stats.get("services_connected", 0),
                        "orphan_services": connection_stats.get("orphan_services", 0),
                        "has_primary_chain": connection_stats.get("has_primary_chain", False),
                        "context_used": ["component_extraction", "azure_references", "security_analysis", "performance_analysis", "architecture_analysis"],
                        "data_passed_to_next": ["enhanced_architecture", "connection_stats", "primary_flow"],
                        "thinking_summary": thinking
                    })
                
                print("-" * 50)
            
            # ═══════════════════════════════════════════════════════════════════
            # HUMAN-IN-THE-LOOP CHECKPOINT 2: Review Architecture Before Validation
            # ═══════════════════════════════════════════════════════════════════
            if interaction_callback:
                print("🤝 Waiting for user approval of designed architecture...")
                
                services_list = []
                for s in agent4_result.get("services", [])[:15]:
                    if isinstance(s, dict):
                        services_list.append({"name": s.get("name", ""), "category": s.get("category", ""), "description": s.get("description", "")[:80]})
                    else:
                        services_list.append({"name": str(s), "category": "", "description": ""})
                
                connections_list = []
                for c in agent4_result.get("connections", [])[:10]:
                    connections_list.append({"source": c.get("source", ""), "target": c.get("target", ""), "label": c.get("label", "")})
                
                containers_list = []
                for c in agent4_result.get("containers", [])[:8]:
                    containers_list.append({"name": c.get("name", ""), "type": c.get("type", ""), "purpose": c.get("purpose", "")[:60]})
                
                checkpoint_summary = {
                    "checkpoint": "post_architecture",
                    "agent": "RequirementsValidationAgent",
                    "title": "Review Designed Architecture",
                    "description": "The Architecture and Connection agents have designed your solution. Review the services, connections, and resource groups before final validation.",
                    "architecture": {
                        "pattern": agent4_result.get("architecture_pattern", "N/A"),
                        "total_services": len(agent4_result.get("services", [])),
                        "total_connections": len(agent4_result.get("connections", [])),
                        "total_containers": len(agent4_result.get("containers", [])),
                        "services": services_list,
                        "connections": connections_list,
                        "containers": containers_list,
                    },
                    "recommendations": [
                        {"id": f"arch_svc_{i}", "text": f"{s['name']} ({s['category']})", "type": "service"}
                        for i, s in enumerate(services_list) if s.get("name")
                    ],
                }
                
                user_decision = await interaction_callback(
                    "post_architecture", "RequirementsValidationAgent", checkpoint_summary
                )
                
                if user_decision and user_decision.get("decision") == "reject":
                    print("❌ User rejected architecture - stopping workflow")
                    workflow_results["workflow_status"] = "rejected_by_user"
                    workflow_results["user_feedback"] = user_decision.get("feedback", "")
                    workflow_results["final_architecture"] = agent4_result
                    return workflow_results
                
                if user_decision and user_decision.get("feedback"):
                    user_prompt = f"{user_prompt}\n\nUSER FEEDBACK ON ARCHITECTURE: {user_decision['feedback']}"
                    print(f"📝 User feedback on architecture: {user_decision['feedback'][:100]}")
            
            # ═══════════════════════════════════════════════════════════════════
            # Agent 6: Requirements Validation (FINAL CHECK)
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("RequirementsValidationAgent", "running", 85, {
                    "message": "✅ Validating all requirements are fulfilled in the architecture..."
                })
            print(f"✅ Step {total_steps}/{total_steps}: Running Agent 6 - Requirements Validator")
            agent6_start = time.time()
            
            validation_context = {
                "component_extraction": agent0_result,
                "azure_references": agent1_result,
                "security_analysis": agent2_result,
                "performance_analysis": agent3_result,
                "architecture_analysis": agent4_result,
                "connection_analysis": agent5_result or {}
            }
            
            agent6_result = await self.agent6_validation.analyze(user_prompt, context=validation_context)
            
            agent6_duration = time.time() - agent6_start
            workflow_results["agent6_validation_result"] = agent6_result
            workflow_results["agents_executed"].append("RequirementsValidationAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 6 (Validation)",
                "duration": agent6_duration,
                "status": agent6_result.get("status", "completed")
            })
            
            print(f"⏱️  Agent 6 (Validation) completed in {agent6_duration:.2f} seconds")
            if progress_callback:
                thinking = self.agent6_validation.get_thinking_summary() if hasattr(self.agent6_validation, 'get_thinking_summary') else None
                progress_callback("RequirementsValidationAgent", "completed", 92, {
                    "message": f"✅ Validation complete: Score {agent6_result.get('overall_validation_score', 0)}%, Status: {agent6_result.get('overall_status', 'UNKNOWN')}",
                    "duration": round(agent6_duration, 2),
                    "validation_score": agent6_result.get("overall_validation_score", 0),
                    "validation_status": agent6_result.get("overall_status", "UNKNOWN"),
                    "requirements_coverage": agent6_result.get("requirements_coverage", {}),
                    "missing_components": len(agent6_result.get("missing_components", [])),
                    "recommendations": len(agent6_result.get("recommendations", [])),
                    "context_used": ["component_extraction", "azure_references", "security_analysis", "performance_analysis", "architecture_analysis", "connection_analysis"],
                    "thinking_summary": thinking
                })
            
            print("=" * 70)
            
            # ═══════════════════════════════════════════════════════════════════
            # Remediation Pass: Apply fixes identified by validation agent
            # ═══════════════════════════════════════════════════════════════════
            remediation_actions = agent6_result.get("remediation_actions", [])
            if remediation_actions:
                if progress_callback:
                    progress_callback("RemediationPass", "running", 93, {
                        "message": f"🔧 Applying {len(remediation_actions)} fixes from validation agent..."
                    })
                print(f"🔧 Remediation Pass: Applying {len(remediation_actions)} fixes from validation...")
                
                remediation_applied = []
                existing_service_names = {
                    s["name"].lower() if isinstance(s, dict) else s.lower()
                    for s in agent4_result.get("services", [])
                }
                existing_connections = {
                    (c.get("source", "").lower(), c.get("target", "").lower())
                    for c in agent4_result.get("connections", [])
                }
                
                for action in remediation_actions:
                    action_type = action.get("action_type", "")
                    details = action.get("details", {})
                    target_agent = action.get("target_agent", "")
                    reason = action.get("reason", "")
                    
                    try:
                        if action_type == "add_service":
                            svc_name = details.get("service_name", "")
                            if svc_name and svc_name.lower() not in existing_service_names:
                                new_svc = {
                                    "name": svc_name,
                                    "category": details.get("category", "compute"),
                                    "description": details.get("description", reason),
                                    "subnet": details.get("subnet", ""),
                                    "sku": details.get("sku", "Standard"),
                                    "icon": details.get("icon", ""),
                                    "remediation_added": True
                                }
                                agent4_result["services"].append(new_svc)
                                existing_service_names.add(svc_name.lower())
                                
                                # Add connections if specified
                                for conn in details.get("connections", []):
                                    conn_pair = (svc_name.lower(), conn.lower())
                                    if conn_pair not in existing_connections:
                                        agent4_result.setdefault("connections", []).append({
                                            "source": svc_name,
                                            "target": conn,
                                            "label": "connects to",
                                            "protocol": "HTTPS"
                                        })
                                        existing_connections.add(conn_pair)
                                
                                remediation_applied.append(f"Added service: {svc_name}")
                                print(f"  ✅ Added service: {svc_name} ({reason})")
                        
                        elif action_type == "add_connection":
                            src = details.get("source", "")
                            tgt = details.get("target", "")
                            conn_pair = (src.lower(), tgt.lower())
                            if src and tgt and conn_pair not in existing_connections:
                                agent4_result.setdefault("connections", []).append({
                                    "source": src,
                                    "target": tgt,
                                    "label": details.get("label", details.get("protocol", "connects to")),
                                    "protocol": details.get("protocol", "HTTPS")
                                })
                                existing_connections.add(conn_pair)
                                remediation_applied.append(f"Added connection: {src} → {tgt}")
                                print(f"  ✅ Added connection: {src} → {tgt} ({reason})")
                        
                        elif action_type == "modify_service":
                            svc_name = details.get("service_name", "")
                            if svc_name:
                                for svc in agent4_result.get("services", []):
                                    if isinstance(svc, dict) and svc.get("name", "").lower() == svc_name.lower():
                                        for key, val in details.items():
                                            if key != "service_name" and val:
                                                svc[key] = val
                                        svc["remediation_modified"] = True
                                        remediation_applied.append(f"Modified service: {svc_name}")
                                        print(f"  ✅ Modified service: {svc_name} ({reason})")
                                        break
                        
                        elif action_type == "add_container":
                            container_name = details.get("name", details.get("service_name", ""))
                            if container_name:
                                existing_containers = {
                                    c.get("name", "").lower()
                                    for c in agent4_result.get("containers", [])
                                }
                                if container_name.lower() not in existing_containers:
                                    agent4_result.setdefault("containers", []).append({
                                        "name": container_name,
                                        "type": details.get("type", "subnet"),
                                        "cidr": details.get("cidr", ""),
                                        "purpose": details.get("purpose", reason),
                                        "remediation_added": True
                                    })
                                    remediation_applied.append(f"Added container: {container_name}")
                                    print(f"  ✅ Added container: {container_name} ({reason})")
                    
                    except Exception as e:
                        logger.warning(f"Remediation action failed: {action_type} - {e}")
                
                print(f"🔧 Remediation complete: {len(remediation_applied)} fixes applied")
                
                workflow_results["remediation_applied"] = remediation_applied
                workflow_results["remediation_actions_total"] = len(remediation_actions)
                
                if progress_callback:
                    progress_callback("RemediationPass", "completed", 95, {
                        "fixes_applied": len(remediation_applied),
                        "total_actions": len(remediation_actions),
                        "applied_details": remediation_applied[:10]
                    })
            else:
                workflow_results["remediation_applied"] = []
                workflow_results["remediation_actions_total"] = 0
                print("✅ No remediation needed - validation passed cleanly")
            
            # ═══════════════════════════════════════════════════════════════════
            # Agent 7: Azure Architecture Review (FINAL EXPERT REVIEW)
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("AzureArchitectureReviewAgent", "running", 93, {
                    "message": "🔍 Final Azure Architecture Review: Checking WAF pillars, best practices, and corrections..."
                })
            print(f"\n🔍 Running Agent 7 - Azure Architecture Review Expert")
            print("=" * 70)
            agent7_start = time.time()
            
            # Build comprehensive context for review
            review_context = {
                "component_extraction": agent0_result,
                "azure_references": agent1_result,
                "security_analysis": agent2_result,
                "performance_analysis": agent3_result,
                "architecture_analysis": agent4_result,
                "connection_analysis": agent5_result or {},
                "validation_result": agent6_result
            }
            
            agent7_result = await self.agent7_review.analyze(user_prompt, context=review_context)
            
            agent7_duration = time.time() - agent7_start
            workflow_results["agent7_review_result"] = agent7_result
            workflow_results["agents_executed"].append("AzureArchitectureReviewAgent")
            workflow_results["processing_timeline"].append({
                "agent": "Agent 7 (Architecture Review)",
                "duration": agent7_duration,
                "status": agent7_result.get("status", "completed")
            })
            
            print(f"⏱️  Agent 7 (Architecture Review) completed in {agent7_duration:.2f} seconds")
            
            # ═══════════════════════════════════════════════════════════════════
            # Iterative Correction Loop: Apply corrections from review agent
            # ═══════════════════════════════════════════════════════════════════
            review_status = agent7_result.get("review_status", "UNKNOWN")
            correction_tasks = agent7_result.get("correction_tasks", [])
            max_correction_iterations = 2  # Limit iterations to prevent infinite loops
            correction_iteration = 0
            
            while review_status == "NEEDS_CORRECTION" and correction_tasks and correction_iteration < max_correction_iterations:
                correction_iteration += 1
                print(f"\n🔄 Correction Iteration {correction_iteration}: Applying {len(correction_tasks)} corrections from review...")
                
                if progress_callback:
                    progress_callback("CorrectionPass", "running", 94, {
                        "iteration": correction_iteration,
                        "tasks": len(correction_tasks)
                    })
                
                corrections_applied = []
                
                # Group tasks by target agent
                agent_tasks = self.agent7_review.get_agents_for_correction(correction_tasks)
                
                # Apply corrections for each agent type
                for target_agent, tasks in agent_tasks.items():
                    for task in tasks:
                        task_id = task.get("task_id", "N/A")
                        task_type = task.get("task_type", "")
                        details = task.get("details", {})
                        reason = task.get("description", task.get("details", {}).get("reason", ""))
                        
                        try:
                            if task_type == "add_service":
                                svc_name = details.get("service_name", "")
                                existing_names = {
                                    s.get("name", s).lower() if isinstance(s, dict) else s.lower()
                                    for s in agent4_result.get("services", [])
                                }
                                if svc_name and svc_name.lower() not in existing_names:
                                    new_svc = {
                                        "name": svc_name,
                                        "category": details.get("category", "compute"),
                                        "description": reason,
                                        "subnet": details.get("subnet", ""),
                                        "review_correction": True,
                                        "correction_task_id": task_id
                                    }
                                    agent4_result.setdefault("services", []).append(new_svc)
                                    corrections_applied.append(f"[{task_id}] Added service: {svc_name}")
                                    print(f"  ✅ [{task_id}] Added service: {svc_name}")
                            
                            elif task_type == "add_connection":
                                src = details.get("source", "")
                                tgt = details.get("target", "")
                                existing_conns = {
                                    (c.get("source", "").lower(), c.get("target", "").lower())
                                    for c in agent4_result.get("connections", [])
                                }
                                if src and tgt and (src.lower(), tgt.lower()) not in existing_conns:
                                    agent4_result.setdefault("connections", []).append({
                                        "source": src,
                                        "target": tgt,
                                        "label": details.get("label", "connects to"),
                                        "protocol": details.get("protocol", "HTTPS"),
                                        "review_correction": True,
                                        "correction_task_id": task_id
                                    })
                                    corrections_applied.append(f"[{task_id}] Added connection: {src} → {tgt}")
                                    print(f"  ✅ [{task_id}] Added connection: {src} → {tgt}")
                            
                            elif task_type == "modify_service":
                                svc_name = details.get("service_name", "")
                                for svc in agent4_result.get("services", []):
                                    if isinstance(svc, dict) and svc.get("name", "").lower() == svc_name.lower():
                                        for key, val in details.items():
                                            if key not in ["service_name"] and val:
                                                svc[key] = val
                                        svc["review_modified"] = True
                                        svc["correction_task_id"] = task_id
                                        corrections_applied.append(f"[{task_id}] Modified service: {svc_name}")
                                        print(f"  ✅ [{task_id}] Modified service: {svc_name}")
                                        break
                            
                            elif task_type == "remove_service":
                                svc_name = details.get("service_name", "")
                                original_count = len(agent4_result.get("services", []))
                                agent4_result["services"] = [
                                    s for s in agent4_result.get("services", [])
                                    if (isinstance(s, dict) and s.get("name", "").lower() != svc_name.lower()) or
                                       (isinstance(s, str) and s.lower() != svc_name.lower())
                                ]
                                if len(agent4_result.get("services", [])) < original_count:
                                    corrections_applied.append(f"[{task_id}] Removed service: {svc_name}")
                                    print(f"  ✅ [{task_id}] Removed service: {svc_name}")
                            
                            elif task_type == "add_container":
                                container_name = details.get("name", details.get("service_name", ""))
                                if container_name:
                                    existing_containers = {
                                        c.get("name", "").lower() for c in agent4_result.get("containers", [])
                                    }
                                    if container_name.lower() not in existing_containers:
                                        agent4_result.setdefault("containers", []).append({
                                            "name": container_name,
                                            "type": details.get("type", "subnet"),
                                            "cidr": details.get("cidr", ""),
                                            "purpose": reason,
                                            "review_correction": True,
                                            "correction_task_id": task_id
                                        })
                                        corrections_applied.append(f"[{task_id}] Added container: {container_name}")
                                        print(f"  ✅ [{task_id}] Added container: {container_name}")
                        
                        except Exception as e:
                            logger.warning(f"Correction task {task_id} failed: {e}")
                            print(f"  ⚠️ [{task_id}] Failed: {e}")
                
                print(f"🔧 Correction iteration {correction_iteration} complete: {len(corrections_applied)} corrections applied")
                
                workflow_results[f"review_corrections_iteration_{correction_iteration}"] = corrections_applied
                
                # Re-run review agent to check if corrections are sufficient
                if correction_iteration < max_correction_iterations:
                    print(f"\n🔄 Re-running review to verify corrections...")
                    review_context["architecture_analysis"] = agent4_result  # Updated architecture
                    review_context["previous_review"] = agent7_result
                    review_context["corrections_applied"] = corrections_applied
                    
                    agent7_result = await self.agent7_review.analyze(user_prompt, context=review_context)
                    review_status = agent7_result.get("review_status", "APPROVED")
                    correction_tasks = agent7_result.get("correction_tasks", [])
                    
                    workflow_results["agent7_review_result"] = agent7_result  # Update with latest
            
            # Log final review status
            final_review_status = agent7_result.get("review_status", "UNKNOWN")
            final_review_score = agent7_result.get("overall_score", 0)
            review_verdict = agent7_result.get("final_verdict", {})
            
            workflow_results["review_status"] = final_review_status
            workflow_results["review_score"] = final_review_score
            workflow_results["review_verdict"] = review_verdict
            workflow_results["correction_iterations"] = correction_iteration
            
            if progress_callback:
                thinking = self.agent7_review.get_thinking_summary() if hasattr(self.agent7_review, 'get_thinking_summary') else None
                progress_callback("AzureArchitectureReviewAgent", "completed", 96, {
                    "message": f"✅ Review complete: Score {final_review_score}%, Status: {final_review_status}, {correction_iteration} correction iterations",
                    "duration": round(agent7_duration, 2),
                    "review_status": final_review_status,
                    "review_score": final_review_score,
                    "correction_tasks": len(agent7_result.get("correction_tasks", [])),
                    "correction_iterations": correction_iteration,
                    "waf_pillar_scores": agent7_result.get("waf_pillar_scores", {}),
                    "critical_issues": len(agent7_result.get("critical_issues", [])),
                    "ready_for_production": review_verdict.get("ready_for_production", False),
                    "thinking_summary": thinking
                })
            
            print("=" * 70)
            
            # ═══════════════════════════════════════════════════════════════════
            # Compile final comprehensive architecture
            # ═══════════════════════════════════════════════════════════════════
            if progress_callback:
                progress_callback("Finalizing", "running", 97, {
                    "message": "📊 Generating Draw.io diagram with professional layout..."
                })
            
            final_architecture = self._compile_comprehensive_architecture(
                agent0_result, agent1_result, agent2_result, agent3_result,
                agent4_result, agent5_result, agent6_result, agent7_result,
                user_prompt, project_name
            )
            
            # Generate Draw.io XML file using AI layout
            drawio_xml = await self._generate_drawio_xml(final_architecture, user_prompt)
            
            # Save Draw.io file
            drawio_filename = f"multi-agent-drawio-{int(time.time() * 1000)}.drawio"
            drawio_filepath = os.path.join(path_config.SAVED_XML_DIR, drawio_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(drawio_filepath), exist_ok=True)
            
            with open(drawio_filepath, 'w', encoding='utf-8') as f:
                f.write(drawio_xml)
            
            print(f"💾 Draw.io file saved: {drawio_filename}")
            
            if progress_callback:
                progress_callback("Finalizing", "completed", 100, {
                    "message": f"✅ Architecture diagram complete! {len(final_architecture.get('services', []))} services, {len(final_architecture.get('connections', []))} connections"
                })
            
            workflow_results["final_architecture"] = final_architecture
            workflow_results["drawio_xml"] = drawio_xml
            workflow_results["drawio_filename"] = drawio_filename
            workflow_results["drawio_filepath"] = drawio_filepath
            workflow_results["total_duration"] = sum([t["duration"] for t in workflow_results["processing_timeline"]])
            workflow_results["workflow_status"] = "completed"
            workflow_results["validation_score"] = agent6_result.get("overall_validation_score", 0)
            workflow_results["validation_status"] = agent6_result.get("overall_status", "UNKNOWN")
            
            print("🎉 Multi-Agent Workflow Pipeline COMPLETED!")
            print(f"📊 Total processing time: {workflow_results['total_duration']:.2f} seconds")
            print(f"🔧 Agents executed: {', '.join(workflow_results['agents_executed'])}")
            print(f"📋 Total services identified: {len(final_architecture.get('all_services', []))}")
            print(f"✅ Validation Score: {workflow_results['validation_score']}/100 ({workflow_results['validation_status']})")
            
            # ═══════════════════════════════════════════════════════════════
            # REINFORCEMENT LEARNING: Reward signal from workflow outcome
            # ═══════════════════════════════════════════════════════════════
            if KB_AVAILABLE:
                try:
                    rl = get_rl_learner()
                    km = get_knowledge_manager()
                    
                    # Calculate reward from validation + review scores
                    val_score = workflow_results.get("validation_score", 0)
                    review_score = agent7_result.get("overall_score", 0) if isinstance(agent7_result, dict) else 0
                    combined_score = (val_score * 0.5 + review_score * 0.5) / 100.0  # normalize to 0-1
                    
                    # Map score to reward: 0→-1, 50→0, 100→+1
                    reward = (combined_score - 0.5) * 2.0
                    
                    # Give reward to RL learner for the pattern used
                    pattern_id = agent4_result.get("_knowledge_pattern_id", "") if isinstance(agent4_result, dict) else ""
                    if pattern_id:
                        rl.receive_reward(reward, pattern_id)
                        logger.info(f"RL: Reward {reward:.3f} for pattern {pattern_id} (val={val_score}, review={review_score})")
                    
                    # End KB session
                    km.end_session()
                    
                    workflow_results["rl_reward"] = round(reward, 3)
                    workflow_results["rl_exploration_rate"] = round(rl.exploration_rate, 4)
                except Exception as e:
                    logger.warning(f"RL reward signal failed (non-fatal): {e}")
            
            if progress_callback:
                progress_callback("Completed", "completed", 100)
            
            return workflow_results
            
        except Exception as e:
            print(f"❌ Workflow pipeline failed: {str(e)}")
            workflow_results["workflow_status"] = "failed"
            workflow_results["error"] = str(e)
            return workflow_results
    
    def _compile_comprehensive_architecture(self, component_result: Dict, reference_result: Dict,
                                          security_result: Dict, performance_result: Dict, 
                                          architecture_result: Dict, connection_result: Optional[Dict],
                                          validation_result: Dict, review_result: Dict,
                                          user_prompt: str, project_name: str) -> Dict[str, Any]:
        """
        Compile results from all agents into a comprehensive architecture.
        Uses the ArchitectureAgent's structured output as the PRIMARY source,
        enhanced with insights from all other agents including the final review.
        """
        print("🔄 Compiling comprehensive architecture from all agents...")
        
        # The ArchitectureAgent is the PRIMARY source of truth for diagram generation
        # It already incorporates security and performance context in its analysis
        services = architecture_result.get("services", [])
        connections = architecture_result.get("connections", [])
        containers = architecture_result.get("containers", [])
        
        # Normalize services to consistent format
        normalized_services = []
        for svc in services:
            if isinstance(svc, dict) and "name" in svc:
                normalized_services.append(svc)
            elif isinstance(svc, str):
                normalized_services.append({"name": svc, "category": "compute"})
        
        # Build service name list for backward compatibility
        all_service_names = [s["name"] for s in normalized_services]
        
        comprehensive_architecture = {
            "project_name": project_name or architecture_result.get("project_name", "Azure Architecture"),
            "architecture_pattern": architecture_result.get("architecture_pattern", "Enterprise Architecture"),
            "user_requirements": user_prompt,
            
            # PRIMARY diagram data (used by Draw.io generator)
            "services": normalized_services,
            "all_services": all_service_names,
            "connections": connections,
            "containers": containers,
            "annotations": architecture_result.get("annotations", []),
            "total_services": len(normalized_services),
            
            # Component extraction insights
            "component_extraction": {
                "apis": component_result.get("apis", []),
                "nfrs": component_result.get("nfrs", []),
                "technical_requirements": component_result.get("technical_requirements", []),
                "tech_stack": component_result.get("tech_stack", []),
                "business_requirements": component_result.get("business_requirements", []),
                "data_requirements": component_result.get("data_requirements", []),
                "integration_points": component_result.get("integration_points", []),
                "resource_group_hints": component_result.get("resource_group_hints", []),
                "complexity_level": component_result.get("summary", {}).get("complexity_level", "N/A"),
                "recommended_pattern": component_result.get("summary", {}).get("recommended_architecture_pattern", "N/A")
            },
            
            # Azure Architecture Center references
            "azure_references": {
                "matched_architectures": reference_result.get("matched_reference_architectures", []),
                "recommended_services": reference_result.get("recommended_azure_services", []),
                "design_decisions": reference_result.get("design_decisions", []),
                "architecture_guidance": reference_result.get("architecture_guidance", {})
            },
            
            # Agent insights (for display in frontend, not for diagram generation)
            "security_insights": {
                "compliance_score": security_result.get("compliance_score", 0),
                "critical_issues": security_result.get("critical_issues", [])[:5],
                "security_services": security_result.get("security_services", [])[:5]
            },
            "performance_insights": {
                "performance_score": performance_result.get("performance_score", 0),
                "optimization_strategies": performance_result.get("optimization_strategies", [])[:5],
                "quick_wins": performance_result.get("quick_wins", [])[:3]
            },
            "architecture_insights": {
                "architecture_score": architecture_result.get("architecture_score", 0),
                "design_rationale": architecture_result.get("design_rationale", ""),
            },
            "connection_insights": {
                "total_connections": connection_result.get("connection_stats", {}).get("total_connections", 0) if connection_result else 0,
                "services_connected": connection_result.get("connection_stats", {}).get("services_connected", 0) if connection_result else 0,
                "orphan_services": connection_result.get("connection_stats", {}).get("orphan_services", 0) if connection_result else 0,
                "has_primary_chain": connection_result.get("connection_stats", {}).get("has_primary_chain", False) if connection_result else False,
                "primary_flow": connection_result.get("primary_flow", []) if connection_result else [],
                "optimizations_applied": connection_result.get("optimizations_applied", []) if connection_result else []
            } if connection_result else None,
            
            # Validation results
            "validation": {
                "overall_score": validation_result.get("overall_validation_score", 0),
                "overall_status": validation_result.get("overall_status", "UNKNOWN"),
                "requirements_coverage": validation_result.get("requirements_coverage", {}),
                "requirement_checks": validation_result.get("requirement_checks", []),
                "connection_validation": validation_result.get("connection_validation", {}),
                "flow_validation": validation_result.get("flow_validation", {}),
                "nfr_compliance": validation_result.get("nfr_compliance", []),
                "missing_components": validation_result.get("missing_components", []),
                "security_validation": validation_result.get("security_validation", {}),
                "recommendations": validation_result.get("recommendations", [])
            },
            
            # Architecture Review results (from Azure Architecture Review Agent)
            "architecture_review": {
                "review_status": review_result.get("review_status", "UNKNOWN"),
                "overall_score": review_result.get("overall_score", 0),
                "waf_pillar_scores": review_result.get("waf_pillar_scores", {}),
                "service_review": review_result.get("service_review", {}),
                "connection_review": review_result.get("connection_review", {}),
                "flow_review": review_result.get("flow_review", {}),
                "critical_issues": review_result.get("critical_issues", []),
                "correction_tasks_applied": review_result.get("correction_tasks", []),
                "improvement_suggestions": review_result.get("improvement_suggestions", []),
                "final_verdict": review_result.get("final_verdict", {})
            },
            
            # Metadata
            "multi_agent_metadata": {
                "agents_used": [
                    "ComponentExtractionAgent", "AzureArchitectureReferenceAgent",
                    "SecurityAgent", "PerformanceAgent", "ArchitectureAgent"
                ] + (["ConnectionExpertAgent"] if connection_result else []) + [
                    "RequirementsValidationAgent", "AzureArchitectureReviewAgent"
                ],
                "workflow_type": "component_driven_sequential_with_review",
                "generation_method": "multi_agent_collaboration_with_iterative_review",
                "total_agents": 8 if connection_result else 7,
                "review_iterations": review_result.get("correction_iterations", 0) if isinstance(review_result, dict) else 0
            }
        }
        
        return comprehensive_architecture
    
    async def _generate_drawio_xml(self, architecture: Dict[str, Any], requirements: str) -> str:
        """Generate Draw.io XML from the compiled architecture.
        Uses DrawioParser with algorithmic tiered layout - no extra LLM call needed."""
        from drawio_parser import generate_drawio_from_architecture
        try:
            return await generate_drawio_from_architecture(architecture, requirements)
        except Exception as e:
            logger.error(f"Error generating Draw.io XML: {e}")
            # Return valid .drawio XML with error message (all values escaped)
            safe_name = str(architecture.get("project_name", "Architecture")).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="{drawio_config.HOST_APP}" agent="{drawio_config.GENERATOR_AGENT}" version="{drawio_config.VERSION}" type="device">
  <diagram name="{safe_name}" id="fallback">
    <mxGraphModel dx="{drawio_config.MODEL_DX}" dy="{drawio_config.MODEL_DY}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{drawio_config.PAGE_WIDTH}" pageHeight="{drawio_config.PAGE_HEIGHT}">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Diagram generation encountered an error. Please try again." 
             style="rounded=1;whiteSpace=wrap;html=1;fillColor={theme_config.WARNING_BG};strokeColor={theme_config.WARNING_STROKE};fontSize=14;" 
             vertex="1" parent="1">
          <mxGeometry x="400" y="350" width="600" height="80" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''


# Convenience function for easy import
async def run_multi_agent_workflow(user_prompt: str, project_name: str = None, include_connection_agent: bool = True) -> Dict[str, Any]:
    """
    Convenience function to run the complete multi-agent workflow using existing agents
    """
    workflow = MultiAgentWorkflowPipeline()
    return await workflow.execute_workflow(user_prompt, project_name, include_connection_agent)