import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class PerformanceAgent(BaseAgent):
    """Expert Azure Performance Architect following Azure Architecture Center performance patterns and optimization reference architectures.
    Uses local azure-docs for verified performance guidance, scalability patterns, and caching strategies.
    
    EXPERTISE DOMAINS:
    - Azure Well-Architected Framework (Performance Efficiency Pillar)
    - Horizontal & Vertical Scaling Patterns
    - Caching Strategies (Cache-Aside, Read-Through, Write-Behind)
    - CQRS & Event Sourcing Patterns
    - Load Balancing & Traffic Distribution
    - Database Performance Optimization
    - CDN & Edge Computing Strategies
    - Async Processing & Message-Based Architectures
    """
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="PerformanceAgent", openai_client=openai_client, agent_type="performance")
    
    # Performance optimization knowledge base
    PERFORMANCE_KNOWLEDGE_BASE = {
        "scalability_patterns": {
            "horizontal_scaling": {
                "description": "Scale out by adding more instances",
                "azure_services": ["Azure App Service Auto-scale", "VMSS", "AKS HPA/VPA", "Azure Functions Consumption"],
                "when_to_use": "Stateless workloads, web frontends, APIs",
                "metrics": ["CPU utilization", "Request count", "Queue length", "Custom metrics"]
            },
            "vertical_scaling": {
                "description": "Scale up by increasing resource capacity",
                "azure_services": ["VM resize", "SQL DTU/vCore scaling", "Redis tier upgrade"],
                "when_to_use": "Stateful workloads, databases, legacy applications",
                "limitations": ["Upper limits on instance size", "Downtime during resize"]
            },
            "partitioning": {
                "description": "Distribute data/workload across multiple partitions",
                "patterns": ["Horizontal partitioning (sharding)", "Vertical partitioning", "Functional partitioning"],
                "azure_services": ["Cosmos DB partitioning", "SQL elastic pools", "Event Hubs partitions"]
            }
        },
        "caching_strategies": {
            "cache_aside": {
                "pattern": "Application manages cache reads/writes",
                "azure_service": "Azure Cache for Redis",
                "best_for": "Read-heavy workloads with infrequent updates"
            },
            "read_through": {
                "pattern": "Cache automatically loads from data store",
                "best_for": "Simplifying application code"
            },
            "write_through": {
                "pattern": "Writes go to cache and data store synchronously",
                "best_for": "Data consistency requirements"
            },
            "write_behind": {
                "pattern": "Writes queued and persisted asynchronously",
                "best_for": "Write-heavy workloads accepting eventual consistency"
            },
            "cdn_caching": {
                "pattern": "Edge caching for static content",
                "azure_services": ["Azure CDN", "Azure Front Door"],
                "best_for": "Static assets, API responses with long TTL"
            }
        },
        "database_optimization": {
            "read_replicas": {
                "pattern": "Offload read traffic to replicas",
                "azure_services": ["Azure SQL read replicas", "Cosmos DB multi-region", "PostgreSQL read replicas"],
                "benefits": ["Reduced primary load", "Geographic distribution", "Failover capability"]
            },
            "connection_pooling": {
                "pattern": "Reuse database connections",
                "importance": "Reduces connection overhead, improves throughput"
            },
            "indexing": {
                "best_practices": ["Index frequently queried columns", "Avoid over-indexing", "Use covering indexes", "Monitor query plans"]
            },
            "cqrs": {
                "pattern": "Separate read and write models",
                "benefits": ["Optimized read performance", "Independent scaling", "Eventual consistency"],
                "azure_services": ["Cosmos DB", "Azure SQL", "Event Grid", "Service Bus"]
            }
        },
        "async_patterns": {
            "message_queues": {
                "pattern": "Decouple components with async messaging",
                "azure_services": ["Azure Service Bus", "Azure Queue Storage", "Azure Event Hubs"],
                "benefits": ["Load leveling", "Resilience", "Scalability"]
            },
            "event_driven": {
                "pattern": "React to events asynchronously",
                "azure_services": ["Azure Event Grid", "Azure Functions", "Logic Apps"],
                "benefits": ["Loose coupling", "Real-time processing", "Scalability"]
            }
        },
        "load_balancing": {
            "global": {
                "azure_services": ["Azure Front Door", "Azure Traffic Manager"],
                "features": ["Geographic routing", "Failover", "SSL offloading", "WAF"]
            },
            "regional": {
                "azure_services": ["Azure Application Gateway", "Azure Load Balancer"],
                "features": ["Layer 7 routing", "SSL termination", "Session affinity"]
            }
        },
        "performance_targets": {
            "latency_tiers": {
                "real_time": "<100ms for interactive applications",
                "near_real_time": "<1s for dashboard/analytics",
                "batch": "Minutes to hours for background processing"
            },
            "availability_targets": {
                "99.9%": "8.76 hours downtime/year - standard web apps",
                "99.95%": "4.38 hours downtime/year - business critical",
                "99.99%": "52.56 minutes downtime/year - mission critical"
            }
        }
    }
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyzes requirements and returns performance recommendations backed by local azure-docs.
        Uses context from previous agents (component_extraction, azure_references, security_analysis) to ground recommendations."""
        if context is None:
            context = {}

        # Extract data from previous agents
        component_data = context.get("component_extraction", {})
        azure_refs = context.get("azure_references", {})
        security_data = context.get("security_analysis", {})

        # Build dynamic context sections from previous agents
        component_context = ""
        if component_data and component_data.get("status") == "completed":
            apis = component_data.get("apis", [])
            nfrs = component_data.get("nfrs", [])
            tech_reqs = component_data.get("technical_requirements", [])
            tech_stack = component_data.get("tech_stack", [])
            data_reqs = component_data.get("data_requirements", [])
            component_context = f"""
EXTRACTED COMPONENTS FROM PREVIOUS AGENT (ComponentExtractionAgent):
- APIs: {json.dumps(apis, indent=2)}
- Non-Functional Requirements: {json.dumps(nfrs, indent=2)}
- Technical Requirements: {json.dumps(tech_reqs, indent=2)}
- Tech Stack: {json.dumps(tech_stack, indent=2)}
- Data Requirements: {json.dumps(data_reqs, indent=2)}
"""

        reference_context = ""
        if azure_refs and azure_refs.get("status") == "completed":
            matched_archs = azure_refs.get("matched_reference_architectures", [])[:5]
            recommended_svcs = azure_refs.get("recommended_azure_services", [])
            reference_context = f"""
AZURE ARCHITECTURE REFERENCES FROM PREVIOUS AGENT (AzureArchitectureReferenceAgent):
- Matched Reference Architectures: {json.dumps(matched_archs, indent=2)}
- Recommended Azure Services: {json.dumps(recommended_svcs, indent=2)}
"""

        security_context = ""
        if security_data and security_data.get("status") == "completed":
            security_services = security_data.get("security_services", [])
            security_context = f"""
SECURITY ANALYSIS FROM PREVIOUS AGENT (SecurityAgent):
- Security Services Already Selected: {json.dumps(security_services, indent=2)}
- Compliance Score: {security_data.get('compliance_score', 'N/A')}
NOTE: Your performance recommendations must be COMPATIBLE with these security services. Do not recommend removing or weakening security measures.
"""

        # Search local docs for performance-relevant references
        performance_docs = self._search_local_docs(
            requirements,
            domain_terms=["performance", "scalability", "autoscaling", "cache", "cqrs",
                         "load balancer", "front door", "cdn", "redis", "event driven",
                         "throughput", "latency", "availability zone", "high availability",
                         "async", "queue", "partition", "read replica", "connection pool"],
            max_results=8
        )

        enhanced_performance_prompt = f"""
You are a Principal Azure Performance Architect with 15+ years of experience optimizing enterprise-scale cloud applications.
You hold AZ-305 certification and have led performance engineering for applications serving 100M+ users.

YOUR PERFORMANCE PHILOSOPHY:
- "Measure First" - Profile before optimizing, use data-driven decisions
- "Cache Everything Cacheable" - Reduce database hits, leverage Redis and CDN
- "Async by Default" - Decouple components, use message queues for resilience
- "Scale Horizontally" - Design for stateless scale-out, not scale-up

IMPORTANT: Use the LOCAL REFERENCE DOCS below as your PRIMARY source for performance patterns and best practices.
{performance_docs}
{component_context}
{reference_context}
{security_context}

YOUR DEEP EXPERTISE:
{json.dumps(self.PERFORMANCE_KNOWLEDGE_BASE, indent=2)}

ðŸš€ **AZURE ARCHITECTURE CENTER PERFORMANCE PATTERNS**:
- Performance Efficiency Pillar: https://learn.microsoft.com/en-us/azure/architecture/framework/scalability/
- Cache-Aside Pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside
- CQRS Pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs
- Throttling Pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/throttling
- Priority Queue Pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/priority-queue
- Competing Consumers Pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/competing-consumers

USER REQUIREMENTS: {requirements}

ANALYSIS TASKS:
1. **Workload Analysis**: Identify workload characteristics (CPU-bound, I/O-bound, memory-bound)
2. **Latency Requirements**: Map NFRs to specific latency targets (P50, P95, P99)
3. **Scaling Strategy**: Design horizontal/vertical scaling approach
4. **Caching Strategy**: Identify cache candidates and invalidation strategy
5. **Database Optimization**: Read replicas, connection pooling, indexing
6. **Async Processing**: Identify components that should be async/event-driven
7. **Load Balancing**: Global vs regional traffic distribution

Return ONLY valid JSON:
{{
  "performance_services": [
    {{"service": "<specific Azure service>", "optimization": "<specific optimization>", "expected_improvement": "<quantified improvement>"}}
  ],
  "caching_strategy": [
    {{"cache_target": "<what to cache>", "cache_service": "<Redis/CDN/etc>", "ttl": "<TTL recommendation>", "invalidation": "<invalidation strategy>"}}
  ],
  "scaling_strategy": [
    {{"component": "<component name>", "scaling_type": "<horizontal|vertical|hybrid>", "trigger_metrics": ["<metrics>"], "min_max_instances": "<range>"}}
  ],
  "database_optimization": [
    {{"database": "<database service>", "optimization": "<optimization type>", "implementation": "<how to implement>"}}
  ],
  "async_recommendations": [
    {{"component": "<component>", "pattern": "<queue|event|saga>", "azure_service": "<service>", "benefit": "<expected benefit>"}}
  ],
  "load_balancing": [
    {{"tier": "<global|regional>", "service": "<Azure service>", "routing_method": "<routing strategy>"}}
  ],
  "monitoring_optimization": [
    {{"service": "<monitoring service>", "metrics": ["<key metrics>"], "alerts": ["<alert conditions>"]}}
  ],
  "performance_score": 0,
  "latency_targets": {{
    "p50": "<target ms>",
    "p95": "<target ms>",
    "p99": "<target ms>"
  }},
  "throughput_targets": {{
    "requests_per_second": "<target>",
    "concurrent_users": "<target>"
  }},
  "bottleneck_analysis": [
    {{"bottleneck": "<identified bottleneck>", "impact": "<performance impact>", "resolution": "<how to resolve>"}}
  ],
  "quick_performance_wins": [
    {{"improvement": "<specific improvement>", "impact": "<expected improvement>", "effort": "<Low|Medium|High>"}}
  ],
  "anti_patterns_detected": [
    {{"anti_pattern": "<performance anti-pattern>", "location": "<where detected>", "fix": "<how to fix>"}}
  ],
  "reference_docs_used": [
    {{"title": "<doc title>", "url": "<url>", "relevance": "<how it was applied>"}}
  ]
}}
"""
        
        messages = [
            {"role": "system", "content": """You are a Principal Azure Performance Architect with:
- 15+ years performance engineering experience
- AZ-305 certified, specialized in large-scale distributed systems
- Experience optimizing applications serving 100M+ users
- Deep expertise in caching (Redis, CDN), CQRS, event-driven architectures
- Led performance engineering at Fortune 100 companies

Your performance philosophy: "Measure first, cache aggressively, scale horizontally, embrace async."

Use the LOCAL REFERENCE DOCS provided to ground your recommendations in verified Azure Architecture Center guidance. Return only valid JSON."""},
            {"role": "user", "content": enhanced_performance_prompt}
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_performance_response(response)
        except Exception as e:
            logger.error(f"Error in PerformanceAgent.analyze: {e}")
            return {
                "agent": "performance",
                "error": str(e),
                "status": "error"
            }
    
    def _parse_performance_response(self, response: str) -> Dict[str, Any]:
        """Parse performance recommendations from AI response"""
        default_response = {
            "performance_services": [],
            "recommendations": [],
            "performance_score": 0,
            "is_fallback": True
        }
        
        parsed = self._safe_json_parse(response, default_response)

        return {
            "agent": "performance",
            "performance_services": parsed.get("performance_services", []),
            "caching_strategy": parsed.get("caching_strategy", []),
            "scaling_strategy": parsed.get("scaling_strategy", []),
            "database_optimization": parsed.get("database_optimization", []),
            "async_recommendations": parsed.get("async_recommendations", []),
            "load_balancing": parsed.get("load_balancing", []),
            "monitoring_optimization": parsed.get("monitoring_optimization", []),
            "optimization_strategies": parsed.get("optimization_strategies", []),
            "performance_score": parsed.get("performance_score", 0),
            "latency_targets": parsed.get("latency_targets", {}),
            "throughput_targets": parsed.get("throughput_targets", {}),
            "bottleneck_analysis": parsed.get("bottleneck_analysis", []),
            "quick_wins": parsed.get("quick_performance_wins", []),
            "anti_patterns_detected": parsed.get("anti_patterns_detected", []),
            "reference_docs_used": parsed.get("reference_docs_used", []),
            "status": "completed"
        }

