import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class CostOptimizationAgent(BaseAgent):
    """Expert Azure FinOps Architect following Azure Architecture Center cost optimization patterns and FinOps Foundation principles.
    Uses local azure-docs for verified cost optimization guidance and FinOps patterns.
    
    EXPERTISE DOMAINS:
    - Azure Well-Architected Framework (Cost Optimization Pillar)
    - FinOps Foundation Principles (Inform, Optimize, Operate)
    - Azure Cost Management & Billing
    - Reserved Instances, Savings Plans, Spot VMs
    - Azure Hybrid Benefit & License Optimization
    - Storage Tiering & Lifecycle Management
    - Right-sizing & Resource Optimization
    """
    
    # FinOps knowledge base
    COST_KNOWLEDGE_BASE = {
        "pricing_models": {
            "pay_as_you_go": {
                "description": "Standard on-demand pricing",
                "best_for": "Variable workloads, dev/test, unpredictable demand",
                "flexibility": "Maximum flexibility, no commitment"
            },
            "reserved_instances": {
                "description": "1 or 3-year commitment for significant discount",
                "savings": "Up to 72% vs PAYG",
                "best_for": "Steady-state workloads, production databases",
                "azure_services": ["VMs", "SQL Database", "Cosmos DB", "App Service", "Redis", "Synapse"]
            },
            "savings_plans": {
                "description": "Flexible compute commitment across VM families",
                "savings": "Up to 65% vs PAYG",
                "best_for": "Organizations with diverse VM usage"
            },
            "spot_instances": {
                "description": "Spare capacity at up to 90% discount",
                "best_for": "Batch processing, CI/CD, fault-tolerant workloads",
                "risk": "Can be evicted with 30 seconds notice",
                "azure_services": ["VMSS", "AKS node pools", "Azure Batch"]
            },
            "dev_test_pricing": {
                "description": "Reduced rates for dev/test workloads",
                "savings": "Up to 55% on VMs, free Windows licensing",
                "requirements": "Enterprise Agreement or Visual Studio subscription"
            }
        },
        "license_optimization": {
            "azure_hybrid_benefit": {
                "windows_server": "Use existing Windows Server licenses with SA",
                "sql_server": "Use existing SQL Server licenses with SA",
                "savings": "Up to 40% on Windows VMs, 55% on SQL"
            },
            "byol": {
                "description": "Bring Your Own License",
                "applies_to": ["Oracle", "SAP", "Red Hat", "SUSE"]
            },
            "license_included": {
                "description": "License included in Azure pricing",
                "when_to_use": "No existing licenses, short-term workloads"
            }
        },
        "storage_optimization": {
            "blob_tiers": {
                "hot": "Frequently accessed data, highest storage cost, lowest access cost",
                "cool": "Infrequently accessed (30+ days), lower storage, higher access",
                "cold": "Rarely accessed (90+ days), lower than cool",
                "archive": "Rarely accessed (180+ days), lowest storage, highest access/retrieval time"
            },
            "lifecycle_management": {
                "description": "Automatically tier data based on age/access patterns",
                "benefits": "Reduces storage costs without manual intervention"
            },
            "reserved_capacity": {
                "description": "1 or 3-year commitment for storage",
                "savings": "Up to 38% for hot tier"
            }
        },
        "compute_optimization": {
            "rightsizing": {
                "description": "Match VM size to actual workload requirements",
                "tools": ["Azure Advisor", "Azure Monitor", "Cost Management"],
                "savings_potential": "Typically 30-50% on over-provisioned VMs"
            },
            "auto_shutdown": {
                "description": "Automatically shut down dev/test VMs outside business hours",
                "savings": "Up to 70% for 10hr/day usage"
            },
            "b_series_burstable": {
                "description": "Cost-effective for variable CPU workloads",
                "best_for": "Dev/test, small web apps, microservices"
            },
            "container_optimization": {
                "aks_node_pools": "Use multiple node pools with different VM sizes",
                "spot_node_pools": "Use spot VMs for fault-tolerant workloads",
                "virtual_nodes": "Burst to ACI for temporary scale"
            }
        },
        "database_optimization": {
            "elastic_pools": {
                "description": "Share resources across multiple databases",
                "best_for": "SaaS with variable per-tenant usage"
            },
            "serverless": {
                "description": "Auto-pause when idle, auto-scale when active",
                "best_for": "Intermittent, unpredictable workloads",
                "azure_services": ["Azure SQL Serverless", "Cosmos DB Serverless"]
            },
            "reserved_capacity": {
                "description": "1 or 3-year commitment for vCores/DTUs",
                "savings": "Up to 65% on SQL Database"
            }
        },
        "finops_practices": {
            "inform": {
                "description": "Visibility and allocation of cloud costs",
                "practices": ["Tagging strategy", "Cost allocation", "Showback/chargeback"]
            },
            "optimize": {
                "description": "Reduce waste and improve efficiency",
                "practices": ["Rightsizing", "Reserved instances", "Spot instances", "Storage tiering"]
            },
            "operate": {
                "description": "Continuous cost management process",
                "practices": ["Budgets", "Alerts", "Anomaly detection", "Governance"]
            }
        },
        "governance": {
            "azure_budgets": "Set spending limits with alerts",
            "azure_policy": "Enforce cost-related policies (VM sizes, regions, tags)",
            "management_groups": "Apply policies across subscriptions",
            "cost_anomaly_detection": "AI-powered detection of unusual spending"
        }
    }
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyzes requirements and returns cost optimization recommendations backed by local azure-docs.
        Uses context from ALL previous agents to provide accurate cost analysis for the actual architecture."""
        if context is None:
            context = {}

        # Extract data from previous agents
        component_data = context.get("component_extraction", {})
        azure_refs = context.get("azure_references", {})
        security_data = context.get("security_analysis", {})
        performance_data = context.get("performance_analysis", {})
        architecture_data = context.get("architecture_analysis", {})

        # Build dynamic context sections from previous agents
        component_context = ""
        if component_data and component_data.get("status") == "completed":
            nfrs = component_data.get("nfrs", [])
            tech_stack = component_data.get("tech_stack", [])
            component_context = f"""
EXTRACTED COMPONENTS FROM ComponentExtractionAgent:
- Non-Functional Requirements: {json.dumps(nfrs, indent=2)}
- Tech Stack: {json.dumps(tech_stack, indent=2)}
- Complexity Level: {component_data.get('summary', {}).get('complexity_level', 'N/A')}
"""

        architecture_context = ""
        if architecture_data and architecture_data.get("status") == "completed":
            arch_services = architecture_data.get("services", [])
            arch_pattern = architecture_data.get("architecture_pattern", "N/A")
            architecture_context = f"""
ARCHITECTURE DESIGN FROM ArchitectureAgent (THESE ARE THE SERVICES TO OPTIMIZE COST FOR):
- Architecture Pattern: {arch_pattern}
- Services: {json.dumps(arch_services, indent=2)}
"""

        security_perf_context = ""
        security_services = security_data.get("security_services", []) if isinstance(security_data, dict) else []
        performance_services = performance_data.get("performance_services", []) if isinstance(performance_data, dict) else []
        if security_services or performance_services:
            security_perf_context = f"""
SECURITY SERVICES (from SecurityAgent): {json.dumps(security_services, indent=2)}
PERFORMANCE SERVICES (from PerformanceAgent): {json.dumps(performance_services, indent=2)}
NOTE: Cost optimizations must NOT compromise security or required performance. Optimize within constraints.
"""

        # Search local docs for cost-relevant references
        cost_docs = self._search_local_docs(
            requirements,
            domain_terms=["cost", "optimization", "reserved instance", "spot", "pricing",
                         "finops", "budget", "savings", "rightsizing", "hybrid benefit",
                         "storage tier", "auto-shutdown", "scale down", "serverless",
                         "elastic pool", "savings plan", "dev test", "b-series"],
            max_results=8
        )

        enhanced_cost_prompt = f"""
You are a Principal Azure FinOps Architect with 12+ years of experience in cloud cost optimization and financial operations.
You are FinOps Certified Practitioner and hold AZ-104, AZ-305 certifications.
You have saved enterprises $50M+ through strategic cost optimization initiatives.

YOUR FINOPS PHILOSOPHY:
- "Cost is a first-class architectural concern" - Optimize from day one
- "Visibility drives accountability" - Tag everything, allocate costs to teams
- "Right-size first, reserve second" - Don't commit to oversized resources
- "Waste is never acceptable" - Continuously hunt for idle resources

IMPORTANT: Use the LOCAL REFERENCE DOCS below as your PRIMARY source for cost optimization patterns and best practices.
{cost_docs}
{component_context}
{architecture_context}
{security_perf_context}

YOUR DEEP EXPERTISE:
{json.dumps(self.COST_KNOWLEDGE_BASE, indent=2)}

ðŸ’° **AZURE ARCHITECTURE CENTER COST OPTIMIZATION PATTERNS**:
- Cost Optimization Pillar: https://learn.microsoft.com/en-us/azure/architecture/framework/cost/
- Azure Pricing Calculator: https://azure.microsoft.com/pricing/calculator/
- Azure Hybrid Benefit: https://azure.microsoft.com/pricing/hybrid-benefit/
- Reserved Instances: https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/
- Spot VMs: https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms

USER REQUIREMENTS: {requirements}

ANALYSIS TASKS:
1. **Service-by-Service Cost Analysis**: Analyze each service in the architecture for cost optimization
2. **Commitment Strategy**: Identify services suitable for reserved instances or savings plans
3. **Right-sizing Analysis**: Identify over-provisioned resources
4. **License Optimization**: Apply Azure Hybrid Benefit where applicable
5. **Storage Tiering**: Recommend appropriate storage tiers for each data type
6. **Serverless Opportunities**: Identify workloads suitable for serverless/consumption pricing
7. **Governance Recommendations**: Budget alerts, policies, tagging strategy

Return ONLY valid JSON:
{{
  "cost_optimization_services": [
    {{"service": "<actual service from architecture>", "current_pricing": "<current model>", "recommended_pricing": "<optimized model>", "commitment_term": "<1yr|3yr|none>", "monthly_savings": "<estimated $>", "savings_percentage": "<percentage>"}}
  ],
  "rightsizing_opportunities": [
    {{"resource": "<actual resource>", "current_sku": "<current SKU>", "recommended_sku": "<optimized SKU>", "utilization": "<current utilization %>", "monthly_savings": "<estimated $>"}}
  ],
  "license_optimization": [
    {{"service": "<service>", "current_licensing": "<current>", "optimized_licensing": "<AHUB/BYOL/etc>", "annual_savings": "<estimated $>"}}
  ],
  "storage_optimization": [
    {{"storage_account": "<storage service>", "data_type": "<type of data>", "current_tier": "<current>", "recommended_tier": "<optimized>", "lifecycle_policy": "<policy recommendation>"}}
  ],
  "serverless_opportunities": [
    {{"workload": "<workload>", "current_service": "<current>", "serverless_alternative": "<serverless option>", "cost_model": "<consumption-based>"}}
  ],
  "spot_opportunities": [
    {{"workload": "<workload>", "fault_tolerance": "<High|Medium|Low>", "recommended_implementation": "<how to use spot>"}}
  ],
  "governance_recommendations": [
    {{"category": "<budgets|policies|tags>", "recommendation": "<specific recommendation>", "implementation": "<how to implement>"}}
  ],
  "cost_score": 0,
  "total_cost_analysis": {{
    "estimated_monthly_unoptimized": "<$ amount>",
    "estimated_monthly_optimized": "<$ amount>",
    "monthly_savings": "<$ amount>",
    "annual_savings": "<$ amount>",
    "savings_percentage": "<percentage>"
  }},
  "critical_cost_issues": [
    {{"issue": "<specific cost issue>", "monthly_waste": "<estimated waste>", "priority": "<P1|P2|P3>"}}
  ],
  "quick_cost_wins": [
    {{"optimization": "<specific quick win>", "implementation_effort": "<Low|Medium|High>", "monthly_savings": "<amount>"}}
  ],
  "finops_maturity_recommendations": [
    {{"phase": "<Crawl|Walk|Run>", "recommendation": "<maturity recommendation>"}}
  ],
  "reference_docs_used": [
    {{"title": "<doc title>", "url": "<url>", "relevance": "<how it was applied>"}}
  ]
}}
"""
        
        messages = [
            {"role": "system", "content": """You are a Principal Azure FinOps Architect with:
- 12+ years cloud cost optimization experience
- FinOps Certified Practitioner, AZ-104, AZ-305 certified
- Led FinOps transformations saving $50M+ for Fortune 500 companies
- Deep expertise in Azure pricing models, reserved instances, spot VMs, hybrid benefit
- Creator of enterprise FinOps frameworks and showback/chargeback models

Your FinOps philosophy: "Cost is a first-class architectural concern. Optimize from day one, not after the bill arrives."

Use the LOCAL REFERENCE DOCS provided to ground your recommendations in verified Azure guidance. Return only valid JSON."""},
            {"role": "user", "content": enhanced_cost_prompt}
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_cost_response(response)
        except Exception as e:
            logger.error(f"Error in CostOptimizationAgent.analyze: {e}")
            return {
                "agent": "cost_optimization",
                "error": str(e),
                "status": "error"
            }
    
    def _parse_cost_response(self, response: str) -> Dict[str, Any]:
        """Parse cost recommendations from AI response"""
        default_response = {
            "cost_optimization_services": [],
            "recommendations": [],
            "cost_score": 0,
            "is_fallback": True
        }
        
        parsed = self._safe_json_parse(response, default_response)
        
        return {
            "agent": "cost_optimization",
            "cost_optimization_services": parsed.get("cost_optimization_services", []),
            "rightsizing_opportunities": parsed.get("rightsizing_opportunities", []),
            "license_optimization": parsed.get("license_optimization", []),
            "storage_optimization": parsed.get("storage_optimization", []),
            "serverless_opportunities": parsed.get("serverless_opportunities", []),
            "spot_opportunities": parsed.get("spot_opportunities", []),
            "governance_recommendations": parsed.get("governance_recommendations", []),
            "cost_score": parsed.get("cost_score", 0),
            "total_cost_analysis": parsed.get("total_cost_analysis", {}),
            "critical_cost_issues": parsed.get("critical_cost_issues", []),
            "quick_wins": parsed.get("quick_cost_wins", []),
            "finops_maturity_recommendations": parsed.get("finops_maturity_recommendations", []),
            "reference_docs_used": parsed.get("reference_docs_used", []),
            "status": "completed"
        }

