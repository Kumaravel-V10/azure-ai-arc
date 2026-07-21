import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from openai import AsyncAzureOpenAI
from agents.base import (
    BaseAgent, AgentTools,
    ACCURACY_ENHANCEMENTS_AVAILABLE, KNOWLEDGE_BASE_AVAILABLE,
    get_learned_patterns, get_knowledge_manager, get_rl_learner,
    FEW_SHOT_ARCHITECTURE_EXAMPLES, FEW_SHOT_CONNECTION_EXAMPLES,
)

# Conditional imports for knowledge base
try:
    from knowledge_base import PatternType
except ImportError:
    PatternType = None

try:
    from accuracy_enhancements import get_suggestions_for_services
except ImportError:
    def get_suggestions_for_services(*args, **kwargs): return {}

logger = logging.getLogger(__name__)


class ArchitectureAgent(BaseAgent):
    """Principal Azure Solutions Architect - the CORE agent that designs the full architecture.
    Receives context from Security and Performance agents to produce a complete,
    diagram-ready architecture with categorized services, connections, and containers.
    Uses local azure-docs for verified architecture patterns, reference architectures, and diagram references.
    
    EXPERTISE DOMAINS:
    - Azure Well-Architected Framework (All 5 Pillars)
    - Cloud Design Patterns (Reliability, Scalability, Security)
    - Azure Reference Architectures (100+ patterns)
    - Microservices & Distributed Systems Design
    - Event-Driven Architecture & CQRS
    - Multi-tenant & SaaS Architecture Patterns
    - Hybrid & Multi-cloud Architectures
    """
    
    # Architecture knowledge base
    ARCHITECTURE_KNOWLEDGE_BASE = {
        "architecture_patterns": {
            "n_tier": {
                "description": "Traditional layered architecture",
                "tiers": ["Presentation", "Business Logic", "Data Access", "Data"],
                "azure_services": {
                    "presentation": ["Azure App Service", "Azure Static Web Apps", "Azure Front Door"],
                    "business": ["Azure Functions", "Azure App Service", "AKS"],
                    "data_access": ["Azure API Management", "Azure Service Bus"],
                    "data": ["Azure SQL Database", "Cosmos DB", "Azure Cache for Redis"]
                },
                "best_for": "Traditional web applications, CRUD operations"
            },
            "microservices": {
                "description": "Decomposed services with independent deployment",
                "azure_services": ["AKS", "Azure Functions", "Azure Service Bus", "Azure API Management", "Azure Container Apps"],
                "patterns": ["Service Mesh", "API Gateway", "Circuit Breaker", "Saga"],
                "best_for": "Complex domains, independent scaling, polyglot persistence"
            },
            "event_driven": {
                "description": "Loosely coupled services communicating via events",
                "azure_services": ["Azure Event Grid", "Azure Event Hubs", "Azure Service Bus", "Azure Functions"],
                "patterns": ["Event Sourcing", "CQRS", "Pub/Sub", "Competing Consumers"],
                "best_for": "Real-time processing, IoT, decoupled systems"
            },
            "serverless": {
                "description": "Pay-per-execution compute without server management",
                "azure_services": ["Azure Functions", "Azure Logic Apps", "Azure Static Web Apps", "Cosmos DB Serverless"],
                "best_for": "Variable workloads, event processing, cost optimization"
            },
            "hub_spoke": {
                "description": "Centralized shared services with isolated workloads",
                "azure_services": ["Azure Virtual Network", "Azure Firewall", "VNet Peering", "Azure Bastion"],
                "best_for": "Enterprise network topology, workload isolation"
            }
        },
        "cloud_design_patterns": {
            "reliability": [
                {"pattern": "Retry", "description": "Handle transient failures with retry logic"},
                {"pattern": "Circuit Breaker", "description": "Prevent cascading failures"},
                {"pattern": "Bulkhead", "description": "Isolate failures to prevent propagation"},
                {"pattern": "Queue-Based Load Leveling", "description": "Buffer requests during spikes"},
                {"pattern": "Health Endpoint Monitoring", "description": "Implement health checks for monitoring"}
            ],
            "performance": [
                {"pattern": "Cache-Aside", "description": "Load data into cache on demand"},
                {"pattern": "CQRS", "description": "Separate read and write models"},
                {"pattern": "Event Sourcing", "description": "Store state as sequence of events"},
                {"pattern": "Index Table", "description": "Create indexes for querying"},
                {"pattern": "Static Content Hosting", "description": "Deploy static content to CDN"}
            ],
            "security": [
                {"pattern": "Gatekeeper", "description": "Protect backend with validation layer"},
                {"pattern": "Valet Key", "description": "Use tokens for direct resource access"},
                {"pattern": "Federated Identity", "description": "Delegate authentication to IdP"}
            ]
        },
        "service_categories": {
            "networking": {
                "edge": ["Azure Front Door", "Azure CDN", "Azure Traffic Manager"],
                "gateway": ["Azure Application Gateway", "Azure API Management", "Azure Firewall"],
                "connectivity": ["Virtual Network", "VNet Peering", "ExpressRoute", "VPN Gateway"]
            },
            "compute": {
                "paas": ["Azure App Service", "Azure Functions", "Azure Container Apps"],
                "containers": ["Azure Kubernetes Service", "Azure Container Instances"],
                "iaas": ["Azure Virtual Machines", "Virtual Machine Scale Sets"]
            },
            "data": {
                "relational": ["Azure SQL Database", "Azure Database for PostgreSQL", "Azure Database for MySQL"],
                "nosql": ["Azure Cosmos DB", "Azure Table Storage"],
                "cache": ["Azure Cache for Redis"],
                "analytics": ["Azure Synapse Analytics", "Azure Data Factory", "Azure Databricks"]
            },
            "integration": {
                "messaging": ["Azure Service Bus", "Azure Queue Storage"],
                "streaming": ["Azure Event Hubs", "Azure Event Grid"],
                "workflow": ["Azure Logic Apps", "Azure Durable Functions"]
            }
        },
        "layout_guidelines": {
            "layer_0_top": {
                "description": "Edge services and user entry points",
                "services": ["Users", "Azure Front Door", "Azure CDN", "Azure Traffic Manager", "WAF"]
            },
            "layer_1": {
                "description": "Gateways and load balancers",
                "services": ["Application Gateway", "API Management", "Azure Firewall", "Load Balancer"]
            },
            "layer_2": {
                "description": "Compute and integration",
                "services": ["App Service", "Functions", "AKS", "Service Bus", "Event Hub"]
            },
            "layer_3_bottom": {
                "description": "Data and storage",
                "services": ["SQL Database", "Cosmos DB", "Storage Account", "Redis Cache"]
            },
            "cross_cutting": {
                "description": "Security and monitoring (distributed across layers)",
                "services": ["Key Vault", "Entra ID", "Azure Monitor", "Log Analytics", "Defender"]
            }
        },
        "connection_flow_rules": {
            "description": "Professional architecture diagrams follow TOP-DOWN data flow with clear layer boundaries",
            "primary_flow": "Users â†’ Edge â†’ Gateway â†’ Compute â†’ Data (LEFT-TO-RIGHT or TOP-TO-BOTTOM)",
            "layer_connections": {
                "layer_0_to_layer_1": {
                    "description": "Edge to Gateway connections",
                    "examples": [
                        {"source": "Azure Front Door", "target": "Application Gateway", "label": "HTTPS routing"},
                        {"source": "Azure CDN", "target": "Azure App Service", "label": "Static content delivery"},
                        {"source": "Users", "target": "Azure Front Door", "label": "User requests"}
                    ]
                },
                "layer_1_to_layer_2": {
                    "description": "Gateway to Compute connections", 
                    "examples": [
                        {"source": "Application Gateway", "target": "Azure App Service", "label": "Backend routing"},
                        {"source": "API Management", "target": "Azure Functions", "label": "API requests"},
                        {"source": "Azure Firewall", "target": "AKS", "label": "Filtered traffic"}
                    ]
                },
                "layer_2_to_layer_3": {
                    "description": "Compute to Data connections",
                    "examples": [
                        {"source": "Azure App Service", "target": "Azure SQL Database", "label": "SQL queries"},
                        {"source": "Azure Functions", "target": "Azure Cosmos DB", "label": "Document operations"},
                        {"source": "AKS", "target": "Azure Cache for Redis", "label": "Cache operations"}
                    ]
                },
                "layer_2_to_integration": {
                    "description": "Compute to Integration (same layer, horizontal)",
                    "examples": [
                        {"source": "Azure App Service", "target": "Azure Service Bus", "label": "Message publishing"},
                        {"source": "Azure Service Bus", "target": "Azure Functions", "label": "Message processing"}
                    ]
                },
                "cross_cutting_connections": {
                    "description": "Security/Monitoring connect FROM compute TO cross-cutting services",
                    "examples": [
                        {"source": "Azure App Service", "target": "Azure Key Vault", "label": "Secrets retrieval"},
                        {"source": "Azure App Service", "target": "Application Insights", "label": "Telemetry"},
                        {"source": "Azure Functions", "target": "Azure Monitor", "label": "Metrics & logs"}
                    ]
                }
            },
            "anti_patterns": [
                "Data layer connecting BACK to edge (reverse flow)",
                "Monitoring connecting TO compute (wrong direction)",
                "Random cross-layer connections that skip layers",
                "Compute connecting directly to Users without gateway",
                "Multiple edge services connecting to same compute without gateway"
            ]
        }
    }
    
    # Service layer mapping for connection validation
    SERVICE_LAYERS = {
        # Layer 0 - Edge (Top) - Entry points
        "users": 0, "user": 0, "client": 0, "client app": 0, "mobile app": 0, "web browser": 0,
        "azure front door": 0, "front door": 0, "azure cdn": 0, "cdn": 0,
        "azure traffic manager": 0, "traffic manager": 0, "waf": 0, "azure waf": 0,
        "azure ddos protection": 0, "ddos protection": 0,
        
        # Layer 1 - Gateway
        "azure application gateway": 1, "application gateway": 1, "app gateway": 1,
        "azure api management": 1, "api management": 1, "apim": 1,
        "azure firewall": 1, "firewall": 1, "azure load balancer": 1, "load balancer": 1,
        "azure bastion": 1, "bastion": 1,
        
        # Layer 2 - Compute & Integration
        "azure app service": 2, "app service": 2, "azure functions": 2, "functions": 2,
        "azure kubernetes service": 2, "aks": 2, "azure container apps": 2, "container apps": 2,
        "azure container instances": 2, "container instances": 2, "aci": 2,
        "azure logic apps": 2, "logic apps": 2, "azure batch": 2, "batch": 2,
        "azure service bus": 2, "service bus": 2, "azure event hubs": 2, "event hubs": 2,
        "azure event grid": 2, "event grid": 2, "azure signalr service": 2, "signalr": 2,
        "virtual machine": 2, "vm": 2, "vmss": 2, "virtual machine scale sets": 2,
        
        # Layer 3 - Data & Storage (Bottom)
        "azure sql database": 3, "sql database": 3, "azure sql": 3,
        "azure cosmos db": 3, "cosmos db": 3, "cosmosdb": 3,
        "azure cache for redis": 3, "redis": 3, "redis cache": 3,
        "azure storage": 3, "storage account": 3, "blob storage": 3,
        "azure data lake": 3, "data lake": 3, "azure synapse": 3, "synapse analytics": 3,
        "azure database for postgresql": 3, "postgresql": 3,
        "azure database for mysql": 3, "mysql": 3,
        "azure table storage": 3, "table storage": 3,
        
        # Cross-cutting (no specific layer - connects horizontally)
        "azure key vault": -1, "key vault": -1,
        "azure active directory": -1, "azure ad": -1, "entra id": -1, "microsoft entra id": -1,
        "azure monitor": -1, "monitor": -1, "application insights": -1, "app insights": -1,
        "azure log analytics": -1, "log analytics": -1,
        "azure defender": -1, "defender for cloud": -1, "microsoft defender": -1,
        "azure sentinel": -1, "sentinel": -1, "microsoft sentinel": -1,
        "azure policy": -1, "policy": -1
    }
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="ArchitectureAgent", openai_client=openai_client, agent_type="architecture")
    
    def _get_learned_patterns_context(self, requirements: str, 
                                       security_services: List = None, 
                                       performance_services: List = None) -> str:
        """Get context from learned patterns extracted from Azure Architecture Center Draw.io files"""
        try:
            learned_patterns = get_learned_patterns()
            if not learned_patterns:
                return ""
            
            # Extract keywords from requirements to find relevant services
            req_lower = requirements.lower()
            mentioned_services = []
            
            # Check which services are mentioned in requirements
            known_services = learned_patterns.get_known_services()
            for service in known_services:
                service_lower = service.lower()
                # Check for service name or key terms
                key_terms = service_lower.replace("azure ", "").replace("microsoft ", "").split()
                for term in key_terms:
                    if len(term) > 3 and term in req_lower:
                        mentioned_services.append(service)
                        break
            
            # Add services from security and performance agents
            if security_services:
                for s in security_services:
                    name = s.get("name", "") if isinstance(s, dict) else str(s)
                    if name and name not in mentioned_services:
                        mentioned_services.append(name)
            
            if performance_services:
                for s in performance_services:
                    name = s.get("name", "") if isinstance(s, dict) else str(s)
                    if name and name not in mentioned_services:
                        mentioned_services.append(name)
            
            if not mentioned_services:
                return ""
            
            # Find similar architectures from Azure Architecture Center
            similar_archs = learned_patterns.find_similar_architecture(mentioned_services, top_n=3)
            
            # Get connection suggestions
            connection_suggestions = {}
            for service in mentioned_services[:10]:  # Limit to avoid too many suggestions
                suggestions = learned_patterns.get_connection_suggestions(service)
                if suggestions:
                    connection_suggestions[service] = suggestions[:5]
            
            # Suggest missing services based on patterns
            missing_services = learned_patterns.suggest_missing_services(mentioned_services)
            
            # Build the context section
            context_parts = []
            
            if similar_archs:
                context_parts.append("â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
                context_parts.append("SIMILAR AZURE ARCHITECTURE CENTER PATTERNS (learned from 64 reference diagrams):")
                context_parts.append("â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
                for arch in similar_archs:
                    context_parts.append(f"ðŸ“ {arch['name']} (similarity: {arch['similarity']*100:.0f}%)")
                    if arch.get('matching'):
                        context_parts.append(f"   Matching services: {', '.join(arch['matching'][:5])}")
                    if arch.get('suggested_additions'):
                        context_parts.append(f"   Consider adding: {', '.join(arch['suggested_additions'][:3])}")
                context_parts.append("")
            
            if connection_suggestions:
                context_parts.append("LEARNED CONNECTION PATTERNS (from Azure Architecture Center):")
                for source, targets in list(connection_suggestions.items())[:5]:
                    context_parts.append(f"  {source} â†’ {', '.join(targets[:4])}")
                context_parts.append("")
            
            if missing_services:
                context_parts.append(f"COMMONLY PAIRED SERVICES YOU MAY WANT TO ADD: {', '.join(missing_services)}")
                context_parts.append("")
            
            if context_parts:
                return "\n".join(context_parts) + "\n"
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error getting learned patterns context: {e}")
            return ""
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyzes requirements with ALL prior agent context and returns a complete
        diagram-ready architecture with services, connections, and containers."""
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Chain-of-Thought reasoning
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        self.think(f"I am the {self.persona.role}. Beginning comprehensive architecture design.", "reasoning")
        self.think("My approach: Match requirements to proven Azure patterns, balance all WAF pillars", "reasoning")
        
        # Check for messages from upstream agents
        messages = self.receive_messages()
        if messages:
            self.think(f"Received {len(messages)} messages from upstream agents", "communication")
            for msg in messages:
                if msg.message_type == "warning":
                    self.think(f"âš ï¸ WARNING from {msg.from_agent}: {msg.content[:150]}", "observation")
                else:
                    self.think(f"From {msg.from_agent}: {msg.content[:100]}", "observation")
        
        if context is None:
            context = {}
        
        # Extract ALL prior agent outputs
        component_data = context.get("component_extraction", {})
        azure_refs = context.get("azure_references", {})
        security_context = context.get("security_analysis", {})
        performance_context = context.get("performance_analysis", {})
        
        security_services = security_context.get("security_services", []) if isinstance(security_context, dict) else []
        performance_services = performance_context.get("performance_services", []) if isinstance(performance_context, dict) else []
        
        # Build component extraction section
        component_section = ""
        if component_data and component_data.get("status") == "completed":
            apis = component_data.get("apis", [])
            nfrs = component_data.get("nfrs", [])
            tech_reqs = component_data.get("technical_requirements", [])
            tech_stack = component_data.get("tech_stack", [])
            data_reqs = component_data.get("data_requirements", [])
            integration_points = component_data.get("integration_points", [])
            business_reqs = component_data.get("business_requirements", [])
            rg_hints = component_data.get("resource_group_hints", [])
            complexity = component_data.get("summary", {}).get("complexity_level", "N/A")
            rec_pattern = component_data.get("summary", {}).get("recommended_architecture_pattern", "N/A")
            rg_hints_section = ""
            if rg_hints:
                rg_hints_section = f"- Resource Group Boundaries: {json.dumps(rg_hints, indent=2)}\n"
            component_section = f"""
EXTRACTED COMPONENTS FROM ComponentExtractionAgent:
- APIs: {json.dumps(apis, indent=2)}
- NFRs: {json.dumps(nfrs, indent=2)}
- Technical Requirements: {json.dumps(tech_reqs, indent=2)}
- Tech Stack: {json.dumps(tech_stack, indent=2)}
- Data Requirements: {json.dumps(data_reqs, indent=2)}
- Integration Points: {json.dumps(integration_points, indent=2)}
- Business Requirements: {json.dumps(business_reqs, indent=2)}
{rg_hints_section}- Complexity Level: {complexity}
- Recommended Pattern: {rec_pattern}
IMPORTANT: Your architecture MUST address ALL of the above components. Every API, NFR, and integration point must be covered by the services you select.
Use the Resource Group Boundaries above to create MULTIPLE separate Resource Groups in your architecture. Each RG must have a clear purpose.
"""

        # Search local docs for architecture-relevant references
        self.think("Using Azure docs search tool for architecture patterns...", "tool_call")
        arch_docs = await self.use_tool(
            AgentTools.SEARCH_AZURE_DOCS,
            {
                "query": requirements,
                "domain_terms": ["architecture", "reference architecture", "microservices", "n-tier",
                               "event-driven", "serverless", "hub-spoke", "web application",
                               "app service", "kubernetes", "containers", "api management",
                               "data warehouse", "iot", "hybrid"],
                "max_results": 8
            }
        )
        
        self.think("Analyzing reference architectures and design patterns to apply...", "reasoning")
        
        # Build reference architecture section from azure_references agent
        ref_architectures = azure_refs.get("matched_reference_architectures", [])[:5] if azure_refs else []
        recommended_svcs = azure_refs.get("recommended_azure_services", []) if azure_refs else []
        design_decisions = azure_refs.get("design_decisions", []) if azure_refs else []
        ref_section = ""
        if ref_architectures:
            ref_section = "\n\nMATCHED REFERENCE ARCHITECTURES (from AzureArchitectureReferenceAgent):\n"
            for r in ref_architectures:
                ref_section += f"  - {r.get('title', 'N/A')}: {r.get('url', 'N/A')}\n"
                if r.get('content_highlights'):
                    ref_section += f"    Guidance: {r.get('content_highlights', '')[:200]}\n"
        if recommended_svcs:
            ref_section += "\nRECOMMENDED AZURE SERVICES (from Reference Agent):\n"
            ref_section += json.dumps(recommended_svcs, indent=2) + "\n"
        if design_decisions:
            ref_section += "\nDESIGN DECISIONS (from Reference Agent):\n"
            ref_section += json.dumps(design_decisions, indent=2) + "\n"
        
        # Get Draw.io reference patterns for better connections and layouts
        drawio_reference_context = self._get_drawio_reference_context(requirements, max_references=5)
        
        # Get learned patterns from Azure Architecture Center Draw.io files
        learned_patterns_section = ""
        if ACCURACY_ENHANCEMENTS_AVAILABLE:
            learned_patterns_section = self._get_learned_patterns_context(requirements, security_services, performance_services)
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # REINFORCEMENT LEARNING: Pattern selection via Q-learning
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        rl_patterns_section = ""
        rl_episode_state = None
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                km = get_knowledge_manager()
                rl = get_rl_learner()
                
                # Start RL episode for this generation
                rl_episode_state = rl.start_episode(requirements, context or {})
                self.think("RL episode started - using Q-learning for pattern selection", "reasoning")
                
                # Get high-confidence architecture patterns from knowledge base
                high_conf_patterns = km.get_high_confidence_patterns(
                    pattern_type=PatternType.ARCHITECTURE,
                    min_confidence=0.5,
                    limit=10
                )
                
                if high_conf_patterns:
                    # Use RL to rank/select patterns
                    pattern_ids = [p.id for p in high_conf_patterns]
                    pattern_confidences = {p.id: p.confidence for p in high_conf_patterns}
                    selected_id = rl.select_pattern(pattern_ids, pattern_confidences)
                    
                    # Build context from top RL-ranked patterns
                    rl_parts = ["REINFORCEMENT-LEARNED ARCHITECTURE PATTERNS (ranked by Q-value + confidence):"]
                    rankings = rl.get_pattern_rankings(pattern_ids)
                    pattern_map = {p.id: p for p in high_conf_patterns}
                    
                    for rank_idx, (pid, qval) in enumerate(rankings[:5]):
                        pat = pattern_map.get(pid)
                        if pat:
                            services = pat.content.get("services", [])
                            connections = pat.content.get("connections", [])
                            rl_parts.append(
                                f"  Pattern #{rank_idx+1}: \"{pat.name}\" "
                                f"(confidence={pat.confidence:.2f}, q_value={qval:.3f}, used={pat.usage_count}x)"
                            )
                            if services:
                                rl_parts.append(f"    Services: {', '.join(services[:12])}")
                            if connections:
                                conn_strs = [f"{c.get('source','?')}â†’{c.get('target','?')}" for c in connections[:6]]
                                rl_parts.append(f"    Connections: {', '.join(conn_strs)}")
                    
                    if len(rl_parts) > 1:
                        rl_patterns_section = "\n".join(rl_parts) + "\n"
                        self.think(f"RL selected {len(rankings[:5])} patterns (exploration_rate={rl.exploration_rate:.3f})", "reasoning")
                
                # Also get KB service suggestions  
                all_services = security_services + performance_services
                if all_services:
                    kb_suggestions = get_suggestions_for_services(all_services[:10])
                    suggested_conns = kb_suggestions.get("suggested_connections", [])
                    if suggested_conns:
                        rl_patterns_section += "\nKNOWLEDGE BASE SUGGESTED CONNECTIONS:\n"
                        for src, tgt, conf in suggested_conns[:8]:
                            rl_patterns_section += f"  {src} â†’ {tgt} (confidence={conf:.2f})\n"
                
                # Track session
                km.start_session(requirements)
                
            except Exception as e:
                logger.warning(f"RL pattern selection failed (non-fatal): {e}")
                rl_patterns_section = ""
        
        # Get few-shot examples for improved accuracy (from accuracy_enhancements module)
        few_shot_section = ""
        if ACCURACY_ENHANCEMENTS_AVAILABLE and FEW_SHOT_ARCHITECTURE_EXAMPLES:
            few_shot_section = f"""

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
FEW-SHOT EXAMPLES - LEARN FROM THESE PATTERNS FOR BETTER ACCURACY:
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{FEW_SHOT_ARCHITECTURE_EXAMPLES}

{FEW_SHOT_CONNECTION_EXAMPLES}
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""
        
        # Single comprehensive prompt - no need for separate extraction step
        architecture_prompt = f"""
You are a Microsoft Certified Azure Solutions Architect Expert.
Design a complete, production-ready Azure architecture based on the requirements below.
{few_shot_section}
{learned_patterns_section}
{rl_patterns_section}
IMPORTANT: Use the LOCAL REFERENCE DOCS and REFERENCE ARCHITECTURE PATTERNS below as your PRIMARY source for architecture patterns, service selection, CONNECTIONS, and LAYOUT.
{arch_docs}
{component_section}
{ref_section}
{drawio_reference_context}

**User Requirements:** "{requirements}"

**Security Agent Recommendations (incorporate these services into the architecture):**
{json.dumps(security_services, indent=2) if security_services else "No specific security services recommended yet."}

**Performance Agent Recommendations (incorporate these services into the architecture):**
{json.dumps(performance_services, indent=2) if performance_services else "No specific performance services recommended yet."}

🔴 **CRITICAL: PRESERVE EXACT NAMES FROM REQUIREMENTS — DO NOT COLLAPSE INDIVIDUAL SERVICES**
- If the requirements specify EXACT resource names (e.g., "func-booking", "func-payment", "rg-test-finnair-fra-sc"), use those EXACT names in your output - do NOT rename them to generic Azure names.
- If requirements specify resource group names like "rg-test-shared-backend-fra-sc", use that exact name in containers and in each service's "resource_group" field.
- If requirements specify subnet names like "snet-shared-apim", use that exact name in containers and in each service's "subnet" field.
- If requirements mention specific VNet names like "vnet-test-shared-backend-fra-sc", use that exact name.
- For named function apps like "func-booking", "func-payment" etc., each should be a SEPARATE service entry with that exact name.
- For named services like "Finnair Portal", "KLM Portal", use those exact display names.
- Only use generic Azure names (like "Azure Functions") when the requirements don't specify a specific name.

🔴 **CRITICAL: NEVER COLLAPSE MULTIPLE NAMED SERVICES INTO ONE GENERIC SERVICE**
- If requirements mention "func-booking, func-payment, func-customer, func-notification, func-analytics, func-integration, func-reporting", you MUST output 7 SEPARATE service entries — one for each.
- Do NOT output a single "Azure Functions" or "Azure Functions (Shared Backend)" entry that groups them all.
- Each individually-named service gets its own {{"name": "func-booking", ...}} entry in the services array.
- This also applies to App Service Plans, Storage Accounts, Portals, or any other resource listed by individual name.
- EXAMPLE — If requirements say "func-booking, func-payment, func-customer" in the shared backend, output:
  {{"name": "func-booking", "category": "compute", "layer": 2, "resource_group": "rg-shared-backend", "subnet": "snet-functions", "description": "Booking function app"}},
  {{"name": "func-payment", "category": "compute", "layer": 2, "resource_group": "rg-shared-backend", "subnet": "snet-functions", "description": "Payment function app"}},
  {{"name": "func-customer", "category": "compute", "layer": 2, "resource_group": "rg-shared-backend", "subnet": "snet-functions", "description": "Customer function app"}}
  NOT: {{"name": "Azure Functions (Shared Backend)", "category": "compute", ...}} ← THIS IS WRONG

IMPORTANT RULES:
1. Use ONLY real Azure service names (e.g., "Azure App Service", "Azure SQL Database", "Azure Front Door")
2. Each service MUST have a "category" from: networking, compute, data, security, monitoring, integration, ai, storage
3. Each service MUST have a "resource_group" field â€” the name of the resource group it belongs to. Use "" or "edge" for edge services (Front Door, CDN, WAF) that sit at the subscription level outside any RG.
4. Each service MUST have a "subnet" field â€” the subnet it belongs to. Use "" for services not in any subnet (e.g., monitoring, DNS zones, certificates). Use "edge" for services outside all RGs.
5. Each connection MUST reference services by their exact "name" field. Use "type": "vnet_peering" for VNet Peering connections between two VNets.
6. Each service MUST have a "layer" field indicating its position in the architecture:
   - layer 0: Edge services (Front Door, CDN, Traffic Manager, Users, WAF)
   - layer 1: Gateways (Application Gateway, API Management, Firewall, Load Balancer)
   - layer 2: Compute & Integration (App Service, Functions, AKS, Service Bus, Event Hub)
   - layer 3: Data & Storage (SQL, Cosmos DB, Redis, Storage, PostgreSQL)
   - layer -1: Cross-cutting (Key Vault, Monitor, Entra ID, Defender - connects horizontally)

ðŸ”— **CRITICAL CONNECTION FLOW RULES (for professional diagrams like Draw.io examples)**:

ðŸ“Œ **MANDATORY: ALWAYS START WITH "Users" NODE**
   - The FIRST service MUST be "Users" (layer 0, category "external")
   - Users is the entry point - ALL architectures start here
   - Users connects to the first Edge service (Front Door, CDN, or Traffic Manager)

ðŸ“Œ **CONNECTIONS MUST FORM A CHAIN (not scattered one-to-one)**:
   Think of connections as a PIPELINE flowing top-to-bottom:
   ```
   Users â†’ Azure Front Door â†’ Application Gateway â†’ Azure App Service â†’ Azure SQL Database
              â†“                                           â†“
           Azure CDN                              Azure Service Bus â†’ Azure Functions
                                                         â†“
                                                  Azure Cosmos DB
   ```

7. **LAYER-BY-LAYER CHAIN FLOW (TOP â†’ BOTTOM)**:
   - Users (Layer 0) connects ONLY to Edge services (Front Door, CDN, Traffic Manager)
   - Edge (Layer 0) connects ONLY to Gateway services (App Gateway, API Management, Firewall)
   - Gateway (Layer 1) connects ONLY to Compute services (App Service, Functions, AKS)
   - Compute (Layer 2) connects to Data (Layer 3) AND other Compute/Integration (Layer 2)
   - Integration (Layer 2) connects to other Compute for event processing
   
8. **CONNECTION DIRECTION RULES**:
   - SOURCE is always the UPSTREAM service (closer to users)
   - TARGET is always the DOWNSTREAM service (closer to data)
   - **PRIMARY CHAIN**: Users â†’ Edge â†’ Gateway â†’ Compute â†’ Data
   - **SECONDARY CHAINS**: Compute â†” Integration â†” Compute (horizontal)
   - Compute â†’ Security/Monitoring (cross-cutting, compute initiates)
   
9. **FORBIDDEN CONNECTION PATTERNS (anti-patterns)**:
   âŒ Data layer connecting back to Edge (reverse flow)
   âŒ Compute connecting directly to Users (missing gateway)
   âŒ Edge connecting directly to Data (skipping layers)
   âŒ Two Edge services connecting to each other randomly
   âŒ Multiple scattered connections without clear chain
   
10. **CORRECT CONNECTION CHAIN EXAMPLES**:
   ```
   PRIMARY CHAIN (must exist):
   {{"source": "Users", "target": "Azure Front Door", "label": "User requests", "flow_type": "entry_point"}}
   {{"source": "Azure Front Door", "target": "Azure Application Gateway", "label": "HTTPS routing", "flow_type": "edge_to_gateway"}}
   {{"source": "Azure Application Gateway", "target": "Azure App Service", "label": "Backend routing", "flow_type": "gateway_to_compute"}}
   {{"source": "Azure App Service", "target": "Azure SQL Database", "label": "SQL queries", "flow_type": "compute_to_data"}}
   
   SECONDARY CHAIN (for async/messaging):
   {{"source": "Azure App Service", "target": "Azure Service Bus", "label": "Message publishing", "flow_type": "compute_to_integration"}}
   {{"source": "Azure Service Bus", "target": "Azure Functions", "label": "Queue trigger", "flow_type": "integration_to_compute"}}
   {{"source": "Azure Functions", "target": "Azure Cosmos DB", "label": "Document writes", "flow_type": "compute_to_data"}}
   
   CROSS-CUTTING (compute initiates):
   {{"source": "Azure App Service", "target": "Azure Key Vault", "label": "Secrets retrieval", "flow_type": "compute_to_crosscutting"}}
   {{"source": "Azure App Service", "target": "Application Insights", "label": "Telemetry", "flow_type": "compute_to_crosscutting"}}
   ```

11. **EVERY service MUST appear in the connection chain.** No orphan services.
12. Design a realistic architecture that addresses ALL extracted components and requirements
13. INCLUDE all security services recommended by SecurityAgent and performance services from PerformanceAgent
14. Every API, NFR, and integration point from ComponentExtractionAgent MUST be addressed
15. Follow the architecture pattern recommended by AzureArchitectureReferenceAgent

CRITICAL LAYOUT RULES (for professional diagrams):
12. **FOLLOW THE LAYOUT GUIDANCE ABOVE**: Place services in appropriate layers:
    - Layer 0 (Top): Edge services (Front Door, CDN, WAF, Traffic Manager, Users)
    - Layer 1: Gateways (Application Gateway, Load Balancer, API Management, Firewall)
    - Layer 2: Compute & Integration (App Service, Functions, Service Bus, Event Hub)
    - Layer 3 (Bottom): Data & Storage (SQL, Cosmos DB, Storage, Redis, PostgreSQL)
    - Security/Monitoring: Distributed across layers, connected to what they protect/monitor

CRITICAL GROUPING RULES (produces multi-RG, real-world Azure architecture diagrams):
13. Create MULTIPLE Resource Groups separated by concern: e.g., one for frontend/tenant UI, one for shared backend services, one for monitoring/security. Each RG has a "purpose" field.
14. Virtual Networks belong to a SPECIFIC Resource Group â€” set "resource_group" on each VNet container.
15. Subnets belong to a SPECIFIC Virtual Network â€” set "virtual_network" on each subnet container.
16. Group related services: frontend-facing services together, backend compute together, databases together, monitoring/security in its own RG without a VNet.
17. If the architecture has separate concerns (e.g., tenant-specific vs shared backend), use separate RGs with separate VNets and VNet Peering between them.
18. Add "annotations" for important architectural notes (e.g., "Shared Backend: Multi-tenant Function Apps + Data Layer").

Return ONLY valid JSON in this exact format:
{{
  "project_name": "<descriptive project name>",
  "architecture_pattern": "<architecture pattern based on analysis>",
  "services": [
    {{"name": "Users", "category": "external", "layer": 0, "resource_group": "", "subnet": "", "description": "End users accessing the application"}},
    {{"name": "<Edge service>", "category": "networking", "layer": 0, "resource_group": "<rg>", "subnet": "", "description": "<description>"}},
    {{"name": "<Gateway service>", "category": "networking", "layer": 1, "resource_group": "<rg>", "subnet": "<subnet>", "description": "<description>"}},
    {{"name": "<Compute service>", "category": "compute", "layer": 2, "resource_group": "<rg>", "subnet": "<subnet>", "description": "<description>"}},
    {{"name": "<Data service>", "category": "data", "layer": 3, "resource_group": "<rg>", "subnet": "<subnet>", "description": "<description>"}}
  ],
  "connections": [
    {{"source": "Users", "target": "<Edge service>", "label": "User requests", "flow_type": "entry_point"}},
    {{"source": "<Edge service>", "target": "<Gateway service>", "label": "HTTPS routing", "flow_type": "edge_to_gateway"}},
    {{"source": "<Gateway service>", "target": "<Compute service>", "label": "Backend routing", "flow_type": "gateway_to_compute"}},
    {{"source": "<Compute service>", "target": "<Data service>", "label": "Data queries", "flow_type": "compute_to_data"}},
    {{"source": "<Compute service>", "target": "<Cross-cutting service>", "label": "Secrets/Telemetry", "flow_type": "compute_to_crosscutting"}}
  ],
  "primary_flow": ["Users", "<Edge>", "<Gateway>", "<Compute>", "<Data>"],
  "containers": [
    {{"name": "<rg-name-1>", "type": "resource_group", "purpose": "<what this RG is for>"}},
    {{"name": "<vnet name>", "type": "virtual_network", "resource_group": "<which rg>"}},
    {{"name": "<subnet name>", "type": "subnet", "virtual_network": "<which vnet>", "cidr": "<CIDR>", "purpose": "<purpose>"}}
  ],
  "annotations": ["<architectural notes>"],
  "architecture_score": 0,
  "design_rationale": "<explanation>",
  "reference_docs_used": [{{"title": "<title>", "url": "<url>", "relevance": "<relevance>"}}]
}}
"""
        
        messages = [
            {"role": "system", "content": """You are a Principal Azure Solutions Architect with:
- 18+ years enterprise architecture experience
- AZ-305, AZ-104, AZ-500 certified, Microsoft Azure MVP
- Designed 500+ production Azure architectures across industries (finance, healthcare, retail, manufacturing)
- Deep expertise in Azure Well-Architected Framework (all 5 pillars)
- Expert in cloud design patterns: microservices, event-driven, serverless, hub-spoke
- Led architecture reviews for Fortune 100 companies

Your design philosophy: "Architecture is the art of balancing trade-offs. Every decision must be intentional, documented, and aligned with business objectives."

Use the REFERENCE ARCHITECTURE PATTERNS and COMMON CONNECTION PATTERNS provided to design professional-quality, production-ready architectures.
Every service must have a purpose, every connection must represent real data flow, and every grouping must reflect operational boundaries.
Return only valid JSON."""},
            {"role": "user", "content": architecture_prompt}
        ]
        
        try:
            self.think("Constructing architecture prompt with security, performance, and reference context. Calling Azure OpenAI...", "tool_call")
            response = await self._call_openai(messages)
            self.think("LLM response received. Parsing JSON architecture specification...", "observation")
            architecture_result = self._parse_architecture_response(response)
            
            # === POST-PROCESSING: Expand collapsed services back to individuals ===
            architecture_result = self._expand_collapsed_services(architecture_result, requirements)
            
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Self-Reflection
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            services_count = len(architecture_result.get("services", []))
            connections_count = len(architecture_result.get("connections", []))
            containers_count = len(architecture_result.get("containers", []))
            pattern = architecture_result.get("architecture_pattern", "Unknown")
            
            # Detailed service breakdown for the thinking panel
            service_names = [s.get("name", s) if isinstance(s, dict) else s for s in architecture_result.get("services", [])[:8]]
            service_categories = {}
            for s in architecture_result.get("services", []):
                cat = s.get("category", "other") if isinstance(s, dict) else "other"
                service_categories[cat] = service_categories.get(cat, 0) + 1
            
            self.think(f"Architecture designed: {pattern} pattern with {services_count} services across {containers_count} resource containers", "decision")
            self.think(f"Key services: {', '.join(service_names[:6])}{'...' if len(service_names) > 6 else ''}", "observation")
            if service_categories:
                cat_summary = ', '.join([f"{v} {k}" for k, v in sorted(service_categories.items(), key=lambda x: -x[1])[:4]])
                self.think(f"Service distribution: {cat_summary}", "observation")
            self.think(f"Connectivity: {connections_count} connections creating {'well-connected' if connections_count >= services_count else 'sparse'} topology", "observation")
            
            reflection = self.reflect(architecture_result, ["completeness", "connectivity", "security_coverage"])
            if reflection.get("improvements_suggested"):
                self.think(f"Design considerations: {', '.join(reflection['improvements_suggested'])}", "reflection")
            
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Inter-Agent Communication
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            self.send_message(
                "ConnectionExpertAgent", "recommendation",
                f"Architecture complete with {services_count} services and {connections_count} connections. Please optimize connection labels and validate flow patterns."
            )
            self.send_message(
                "ValidationAgent", "insight",
                f"Pattern: {pattern}, Services: {services_count}, Connections: {connections_count}, Containers: {containers_count}"
            )
            
            self.think("Architecture design completed successfully", "success")
            architecture_result["thinking_summary"] = self.get_thinking_summary()
            
            return architecture_result
        except Exception as e:
            logger.error(f"Error in ArchitectureAgent.analyze: {e}")
            self.think(f"Architecture design error: {str(e)}", "warning")
            return {
                "agent": "architecture",
                "error": str(e),
                "status": "error",
                "thinking_summary": self.get_thinking_summary()
            }
    
    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse architecture from AI response"""
        default_response = {
            "project_name": "Architecture Generation Failed",
            "architecture_pattern": "Unknown",
            "containers": [],
            "services": [],
            "connections": [],
            "architecture_score": 0,
            "is_fallback": True,
            "error": "AI generation failed"
        }
        
        # Check if this is an error response from _call_openai
        if isinstance(response, str) and response.startswith('{"error"'):
            logger.warning(f"ArchitectureAgent received error response: {response}")
            return default_response
        
        result = self._safe_json_parse(response, default_response)
        
        # Ensure required fields exist
        for key in ["project_name", "architecture_pattern", "services", "connections", "containers"]:
            if key not in result:
                result[key] = default_response[key]
        
        # Ensure annotations list exists
        if "annotations" not in result:
            result["annotations"] = []
        
        # Normalize services to ensure consistent format
        normalized_services = []
        for svc in result.get("services", []):
            if isinstance(svc, dict) and "name" in svc:
                if "category" not in svc:
                    svc["category"] = self._infer_category(svc["name"])
                # Ensure resource_group and subnet fields exist
                if "resource_group" not in svc:
                    svc["resource_group"] = ""
                if "subnet" not in svc:
                    svc["subnet"] = ""
                normalized_services.append(svc)
            elif isinstance(svc, str):
                normalized_services.append({
                    "name": svc,
                    "category": self._infer_category(svc),
                    "resource_group": "",
                    "subnet": "",
                    "description": ""
                })
        result["services"] = normalized_services
        
        # === ENSURE "Users" ENTRY POINT EXISTS ===
        has_users = any(s.get("name", "").lower() == "users" for s in normalized_services)
        if not has_users:
            logger.info("Adding 'Users' entry point node for professional diagram flow")
            normalized_services.insert(0, {
                "name": "Users",
                "category": "external",
                "layer": 0,
                "resource_group": "",
                "subnet": "",
                "description": "End users accessing the application"
            })
            result["services"] = normalized_services
        
        # === BUILD PRIMARY FLOW CHAIN ===
        # Find services by layer to construct the primary flow
        edge_services = [s for s in normalized_services if self._get_service_layer(s["name"]) == 0 and s["name"].lower() != "users"]
        gateway_services = [s for s in normalized_services if self._get_service_layer(s["name"]) == 1]
        compute_services = [s for s in normalized_services if self._get_service_layer(s["name"]) == 2]
        data_services = [s for s in normalized_services if self._get_service_layer(s["name"]) == 3]
        
        # Build primary_flow array
        primary_flow = ["Users"]
        if edge_services:
            primary_flow.append(edge_services[0]["name"])
        if gateway_services:
            primary_flow.append(gateway_services[0]["name"])
        if compute_services:
            primary_flow.append(compute_services[0]["name"])
        if data_services:
            primary_flow.append(data_services[0]["name"])
        result["primary_flow"] = primary_flow
        logger.info(f"Primary flow chain: {' â†’ '.join(primary_flow)}")
        
        # Normalize connections - validate source/target against actual service names
        normalized_connections = []
        service_names = {s["name"] for s in normalized_services}
        # Also collect container names (VNets, subnets, RGs) so VNet Peering connections are not dropped
        container_names = set()
        for c in result.get("containers", []):
            if isinstance(c, dict) and c.get("name"):
                container_names.add(c["name"])
        all_known_names = service_names | container_names
        for conn in result.get("connections", []):
            if isinstance(conn, dict) and conn.get("source") and conn.get("target"):
                conn_type = conn.get("type", "").lower()
                # VNet Peering and network-level connections: pass through without service-name validation
                if (conn_type in ("vnet_peering", "peering", "network")
                        or ("vnet" in conn.get("source", "").lower() and "vnet" in conn.get("target", "").lower())):
                    normalized_connections.append(conn)
                    continue
                # Fuzzy-match source and target against ALL known names (services + containers)
                matched_source = self._match_service_name(conn["source"], all_known_names)
                matched_target = self._match_service_name(conn["target"], all_known_names)
                if matched_source and matched_target:
                    conn["source"] = matched_source
                    conn["target"] = matched_target
                    normalized_connections.append(conn)
                else:
                    logger.warning(f"Dropping connection: '{conn['source']}' -> '{conn['target']}' (no matching services or containers)")
        result["connections"] = normalized_connections
        
        # === INJECT PRIMARY FLOW CHAIN CONNECTIONS (only if missing, preserve existing) ===
        # Build sets for checking existing connections (sourceâ†’target pairs)
        existing_connection_pairs = {(c.get("source", ""), c.get("target", "")) for c in normalized_connections}
        injected_count = 0
        
        # Helper to check if connection already exists (in either direction for some cases)
        def connection_exists(src, tgt):
            return (src, tgt) in existing_connection_pairs
        
        # Helper to add connection only if it doesn't exist
        def add_if_missing(src, tgt, label, flow_type):
            nonlocal injected_count
            if not connection_exists(src, tgt):
                conn = {"source": src, "target": tgt, "label": label, "flow_type": flow_type}
                normalized_connections.append(conn)
                injected_count += 1
                logger.info(f"  Chain link added: {src} â†’ {tgt} ({label})")
                return True
            return False
        
        # 1. Users â†’ Edge (entry point)
        if edge_services:
            add_if_missing("Users", edge_services[0]["name"], "User requests", "entry_point")
        
        # 2. Edge â†’ Gateway
        if edge_services and gateway_services:
            add_if_missing(edge_services[0]["name"], gateway_services[0]["name"], "HTTPS routing", "edge_to_gateway")
        
        # 3. Gateway â†’ Compute
        if gateway_services and compute_services:
            add_if_missing(gateway_services[0]["name"], compute_services[0]["name"], "Backend routing", "gateway_to_compute")
        
        # 4. Compute â†’ Data (for each compute service, ensure at least one data connection)
        if compute_services and data_services:
            # Check if ANY computeâ†’data connection exists
            compute_names = {s["name"] for s in compute_services}
            data_names = {s["name"] for s in data_services}
            has_compute_to_data = any(
                c.get("source", "") in compute_names and c.get("target", "") in data_names
                for c in normalized_connections
            )
            if not has_compute_to_data:
                add_if_missing(compute_services[0]["name"], data_services[0]["name"], "Data queries", "compute_to_data")
        
        if injected_count > 0:
            logger.info(f"  Total chain connections injected: {injected_count} (preserved {len(existing_connection_pairs)} existing)")
        
        result["connections"] = normalized_connections
        
        # Auto-connect orphan services that have no connections
        connected_services = set()
        for conn in normalized_connections:
            connected_services.add(conn.get("source", ""))
            connected_services.add(conn.get("target", ""))
        
        orphan_services = [s for s in normalized_services if s["name"] not in connected_services
                           and s.get("resource_group", "") != "edge" and s.get("subnet", "") != "edge"]
        
        if orphan_services:
            logger.info(f"Auto-connecting {len(orphan_services)} orphan services")
            for orphan in orphan_services:
                cat = orphan.get("category", "").lower()
                # Find a sensible target based on category
                target_name = None
                if cat in ("monitoring", ):
                    # Monitoring services connect to compute services
                    for s in normalized_services:
                        if s.get("category", "").lower() in ("compute",) and s["name"] in connected_services:
                            target_name = s["name"]
                            break
                elif cat in ("security",):
                    # Security services connect to compute or networking
                    for s in normalized_services:
                        if s.get("category", "").lower() in ("compute", "networking") and s["name"] in connected_services:
                            target_name = s["name"]
                            break
                elif cat in ("storage",):
                    # Storage connects to compute
                    for s in normalized_services:
                        if s.get("category", "").lower() in ("compute",) and s["name"] in connected_services:
                            target_name = s["name"]
                            break
                elif cat in ("data",):
                    # Data services connect to compute
                    for s in normalized_services:
                        if s.get("category", "").lower() in ("compute", "integration") and s["name"] in connected_services:
                            target_name = s["name"]
                            break
                else:
                    # Default: connect to the most-connected service in the same RG
                    orphan_rg = orphan.get("resource_group", "")
                    for s in normalized_services:
                        if s.get("resource_group", "") == orphan_rg and s["name"] in connected_services and s["name"] != orphan["name"]:
                            target_name = s["name"]
                            break
                
                if not target_name:
                    # Ultimate fallback: connect to any connected service
                    for s in normalized_services:
                        if s["name"] in connected_services and s["name"] != orphan["name"]:
                            target_name = s["name"]
                            break
                
                if target_name:
                    auto_label = self._get_auto_connection_label(orphan["name"], target_name)
                    normalized_connections.append({
                        "source": target_name,
                        "target": orphan["name"],
                        "label": auto_label
                    })
                    connected_services.add(orphan["name"])
                    logger.info(f"  Auto-connected: {target_name} -> {orphan['name']} ({auto_label})")
        
        # Validate and fix connection flow directions (ensures top-down flow like Draw.io examples)
        logger.info("Validating connection flow directions for professional diagram layout...")
        validated_connections = self._validate_and_fix_connections(normalized_connections, normalized_services)
        result["connections"] = validated_connections
        
        # Add layer information to services if not present
        for svc in normalized_services:
            if "layer" not in svc:
                svc["layer"] = self._get_service_layer(svc["name"])
        
        result["agent"] = "architecture"
        result["status"] = "completed"
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # REINFORCEMENT LEARNING: Learn from this generation
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                km = get_knowledge_manager()
                rl = get_rl_learner()
                
                # Store architecture as a learned pattern
                service_names = [s.get("name", "") for s in result.get("services", []) if isinstance(s, dict)]
                connections_data = result.get("connections", [])
                if service_names:
                    pattern_id = km.store_architecture_pattern(
                        name=f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(service_names)}svc",
                        services=service_names,
                        connections=connections_data,
                        requirements=requirements,
                        tags=["auto_generated", result.get("architecture_pattern", "custom")]
                    )
                    
                    # Track services in session
                    for svc_name in service_names:
                        km.track_service_used(svc_name)
                    km.track_pattern_applied(pattern_id)
                    km.track_output_generated({"services": len(service_names), "connections": len(connections_data)})
                    
                    # End RL episode with neutral reward (will be updated by user feedback)
                    rl.end_episode(final_reward=0.0)
                    
                    result["_knowledge_pattern_id"] = pattern_id
                    logger.info(f"RL: Stored architecture pattern {pattern_id}, {len(service_names)} services")
            except Exception as e:
                logger.warning(f"RL post-generation learning failed (non-fatal): {e}")
        
        return result
    
    # ------------------------------------------------------------------
    # Post-processing: expand collapsed service entries
    # ------------------------------------------------------------------
    def _expand_collapsed_services(self, result: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """Detect when the LLM collapsed individually-named services (e.g. func-booking,
        func-payment) into a single generic entry (e.g. 'Azure Functions') and expand
        them back into separate service entries based on the original requirements text."""
        import re as _re

        # Extract all individually-named resources from requirements
        # Patterns: func-xxx, svc-xxx, app-xxx, api-xxx or any word-dash-word tokens
        req_lower = requirements.lower()
        # Find func-* names
        func_names = set(_re.findall(r'\bfunc-[a-z0-9_-]+', req_lower))
        # Find app-* / svc-* / api-* names
        app_names = set(_re.findall(r'\b(?:app|svc|api)-[a-z0-9_-]+', req_lower))
        named_resources = func_names | app_names

        if not named_resources:
            return result

        services = result.get("services", [])
        existing_names_lower = {s["name"].lower() for s in services}

        # Check which named resources are missing from the output
        missing = {n for n in named_resources if n not in existing_names_lower}
        if not missing:
            return result

        # Find the generic collapsed service to use as a template
        generic_keywords = ["azure functions", "function app", "functions"]
        template_svc = None
        template_idx = None
        for idx, svc in enumerate(services):
            svc_lower = svc["name"].lower()
            if any(kw in svc_lower for kw in generic_keywords):
                template_svc = svc
                template_idx = idx
                break

        if not template_svc:
            # No generic to replace — just add missing ones
            template_svc = {
                "category": "compute",
                "layer": 2,
                "resource_group": "",
                "subnet": "",
                "description": ""
            }
            template_idx = None

        # Build individual service entries from the missing names
        expanded = []
        for name in sorted(missing):
            new_svc = {
                "name": name,
                "category": template_svc.get("category", "compute"),
                "layer": template_svc.get("layer", 2),
                "resource_group": template_svc.get("resource_group", ""),
                "subnet": template_svc.get("subnet", ""),
                "description": f"{name} function app"
            }
            expanded.append(new_svc)

        if expanded:
            # Remove the generic collapsed entry if we found one
            if template_idx is not None:
                removed_name = services[template_idx]["name"]
                services.pop(template_idx)
                logger.info(f"Expanding collapsed '{removed_name}' into {len(expanded)} individual services: {[s['name'] for s in expanded]}")
                # Update any connections that referenced the removed generic name
                for conn in result.get("connections", []):
                    if conn.get("source", "") == removed_name:
                        conn["source"] = expanded[0]["name"]
                    if conn.get("target", "") == removed_name:
                        conn["target"] = expanded[0]["name"]
            else:
                logger.info(f"Adding {len(expanded)} missing named services: {[s['name'] for s in expanded]}")

            # Insert expanded services at the template position (or at end)
            insert_at = template_idx if template_idx is not None else len(services)
            for i, svc in enumerate(expanded):
                services.insert(insert_at + i, svc)

            result["services"] = services

        return result
    
    def _infer_category(self, service_name: str) -> str:
        """Infer service category from name"""
        name_lower = service_name.lower()
        category_keywords = {
            "external": ["user", "internet user", "internet"],
            "networking": ["front door", "cdn", "gateway", "load balancer", "traffic manager", "vnet", "virtual network", "firewall", "dns", "expressroute", "waf", "private endpoint", "private link", "nsg", "peering", "bastion", "ddos", "ssl"],
            "compute": ["app service", "function", "func-", "vm", "virtual machine", "kubernetes", "aks", "container", "batch", "web app", "portal", "asp"],
            "data": ["sql", "cosmos", "database", "redis", "mysql", "postgresql", "table storage", "data factory", "synapse", "data lake"],
            "security": ["key vault", "entra", "active directory", "sentinel", "defender", "certificate", "managed identity"],
            "monitoring": ["monitor", "insights", "log analytics", "diagnostic", "metric", "application insights"],
            "storage": ["storage account", "blob", "file share", "queue storage", "disk", "storage"],
            "integration": ["service bus", "event hub", "event grid", "logic app", "api management", "apim", "app configuration", "notification hub", "signalr"],
            "ai": ["cognitive", "openai", "machine learning", "bot", "search"]
        }
        for category, keywords in category_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return category
        return "compute"
    
    def _match_service_name(self, name: str, service_names: set) -> Optional[str]:
        """Fuzzy-match a connection endpoint name to an actual service name.
        Returns the matched service name, or None if no match found."""
        if not name:
            return None
        # Exact match
        if name in service_names:
            return name
        # Normalized match (case-insensitive, strip Azure/Microsoft prefix)
        name_norm = self._normalize_svc_name(name)
        for svc in service_names:
            if self._normalize_svc_name(svc) == name_norm:
                return svc
        # Substring/contains match (e.g., "App Service" matches "Azure App Service")
        name_lower = name.lower()
        for svc in service_names:
            svc_lower = svc.lower()
            if name_lower in svc_lower or svc_lower in name_lower:
                return svc
        return None
    
    def _normalize_svc_name(self, name: str) -> str:
        """Normalize a service name for fuzzy comparison"""
        n = name.lower().strip()
        for prefix in ["azure ", "microsoft "]:
            if n.startswith(prefix):
                n = n[len(prefix):]
        return n
    
    def _get_auto_connection_label(self, source_name: str, target_name: str) -> str:
        """Generate a meaningful connection label for auto-connected orphan services."""
        target_lower = target_name.lower()
        source_lower = source_name.lower()
        
        # Category-based label generation
        label_map = [
            (["monitor", "insights", "log analytics", "diagnostic"], "Telemetry & diagnostics"),
            (["key vault", "certificate"], "Secrets & certificate management"),
            (["defender", "sentinel", "security"], "Security monitoring"),
            (["firewall", "waf"], "Network security filtering"),
            (["backup", "site recovery"], "Backup & disaster recovery"),
            (["storage", "blob", "file share"], "Data storage"),
            (["redis", "cache"], "Cache-aside pattern"),
            (["sql", "database", "postgresql", "cosmos", "mysql"], "Data queries"),
            (["service bus", "event hub", "event grid"], "Async messaging"),
            (["dns", "private dns"], "DNS resolution"),
            (["front door", "cdn"], "Content delivery"),
            (["api management"], "API gateway routing"),
        ]
        
        for keywords, label in label_map:
            if any(kw in target_lower for kw in keywords):
                return label
            if any(kw in source_lower for kw in keywords):
                return label
        
        return "Service integration"
    
    def _get_service_layer(self, service_name: str) -> int:
        """Get the architectural layer for a service (0=edge, 1=gateway, 2=compute, 3=data, -1=cross-cutting)"""
        name_lower = service_name.lower().strip()
        
        # First check exact match in SERVICE_LAYERS
        if name_lower in self.SERVICE_LAYERS:
            return self.SERVICE_LAYERS[name_lower]
        
        # Check without Azure/Microsoft prefix
        for prefix in ["azure ", "microsoft "]:
            if name_lower.startswith(prefix):
                stripped = name_lower[len(prefix):]
                if stripped in self.SERVICE_LAYERS:
                    return self.SERVICE_LAYERS[stripped]
        
        # Keyword-based fallback
        layer_keywords = {
            0: ["front door", "cdn", "traffic manager", "waf", "ddos", "users", "client", "internet user", "ssl certificate"],
            1: ["gateway", "firewall", "load balancer", "bastion", "api management", "apim"],
            2: ["app service", "function", "func-", "aks", "kubernetes", "container", "vm", "logic app", "service bus", "event hub", "event grid", "batch", "portal"],
            3: ["sql", "cosmos", "database", "redis", "storage", "blob", "data lake", "synapse", "postgresql", "mysql", "table"],
            -1: ["key vault", "monitor", "insights", "log analytics", "entra", "active directory", "defender", "sentinel", "policy"]
        }
        
        for layer, keywords in layer_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return layer
        
        # Default to compute layer
        return 2
    
    def _validate_and_fix_connections(self, connections: List[Dict], services: List[Dict]) -> List[Dict]:
        """Validate connections follow proper layer flow and fix direction issues.
        
        Rules:
        - Connections should flow from lower layer number to higher (top-down)
        - Layer 0 (Edge) â†’ Layer 1 (Gateway) â†’ Layer 2 (Compute) â†’ Layer 3 (Data)
        - Cross-cutting services (-1) can connect bidirectionally with compute (Layer 2)
        """
        # Build service name to layer mapping
        service_layers = {}
        for svc in services:
            name = svc.get("name", "")
            # Use explicit layer if provided, otherwise infer
            layer = svc.get("layer")
            if layer is None:
                layer = self._get_service_layer(name)
            service_layers[name] = layer
        
        validated_connections = []
        fixed_count = 0
        
        for conn in connections:
            source = conn.get("source", "")
            target = conn.get("target", "")
            label = conn.get("label", "")
            conn_type = conn.get("type", "")
            
            # Skip VNet peering and network-level connections
            if conn_type in ("vnet_peering", "peering", "network"):
                validated_connections.append(conn)
                continue
            
            # Get layers for source and target
            source_layer = service_layers.get(source, self._get_service_layer(source))
            target_layer = service_layers.get(target, self._get_service_layer(target))
            
            # Cross-cutting services (-1) - allow connections in either direction to/from compute
            if source_layer == -1 or target_layer == -1:
                # For cross-cutting, prefer compute â†’ cross-cutting direction
                if target_layer == -1:
                    # Already correct: compute â†’ cross-cutting
                    if "flow_type" not in conn:
                        conn["flow_type"] = "compute_to_crosscutting"
                    validated_connections.append(conn)
                else:
                    # Flip: cross-cutting â†’ compute becomes compute â†’ cross-cutting
                    # PRESERVE original label if meaningful, otherwise generate one
                    preserved_label = label if label else self._get_corrected_label(target, source, label)
                    fixed_conn = {
                        "source": target,
                        "target": source,
                        "label": preserved_label,
                        "flow_type": "compute_to_crosscutting"
                    }
                    if conn_type:
                        fixed_conn["type"] = conn_type
                    validated_connections.append(fixed_conn)
                    fixed_count += 1
                    logger.info(f"  Fixed connection direction: {source} â†’ {target} became {target} â†’ {source}")
                continue
            
            # Main flow validation: source should be at equal or lower layer than target
            # Valid: Layer 0 â†’ Layer 1, Layer 1 â†’ Layer 2, Layer 2 â†’ Layer 3, Layer 2 â†’ Layer 2
            if source_layer <= target_layer:
                # Valid direction - preserve everything, just add flow_type if missing
                if "flow_type" not in conn:
                    conn["flow_type"] = self._determine_flow_type(source_layer, target_layer)
                validated_connections.append(conn)
            else:
                # Invalid: flows backward (e.g., data â†’ compute), flip it
                # PRESERVE original label
                preserved_label = label if label else self._get_corrected_label(target, source, label)
                fixed_conn = {
                    "source": target,
                    "target": source,
                    "label": preserved_label,
                    "flow_type": self._determine_flow_type(target_layer, source_layer)
                }
                if conn_type:
                    fixed_conn["type"] = conn_type
                validated_connections.append(fixed_conn)
                fixed_count += 1
                logger.info(f"  Fixed reverse flow: {source} (L{source_layer}) â†’ {target} (L{target_layer}) became {target} â†’ {source}")
        
        if fixed_count > 0:
            logger.info(f"  Connection flow validation: fixed {fixed_count} reverse/incorrect connections")
        
        return validated_connections
    
    def _determine_flow_type(self, source_layer: int, target_layer: int) -> str:
        """Determine the flow type based on source and target layers"""
        flow_types = {
            (0, 1): "edge_to_gateway",
            (0, 2): "edge_to_compute",  # CDN â†’ static web app (valid but uncommon)
            (1, 2): "gateway_to_compute",
            (2, 2): "compute_to_integration",  # Same layer: compute â†” integration
            (2, 3): "compute_to_data",
            (1, 3): "gateway_to_data",  # API Management â†’ backend data (less common)
        }
        return flow_types.get((source_layer, target_layer), "service_integration")
    
    def _get_corrected_label(self, new_source: str, new_target: str, original_label: str) -> str:
        """Generate a corrected label when connection direction is flipped"""
        # Use the auto-connection label logic to generate appropriate label
        return self._get_auto_connection_label(new_source, new_target)


