import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AzureArchitectureReviewAgent(BaseAgent):
    """
    Expert Azure Architecture Review Agent with comprehensive knowledge of Azure services and best practices.
    This agent acts as a FINAL QUALITY GATE before returning the architecture to the user.
    
    Responsibilities:
    1. Deep review of generated architecture against Azure Well-Architected Framework
    2. Validate service selection, connections, and data flow
    3. Identify issues and create specific correction tasks
    4. Route corrections back to appropriate agents (Security, Performance, Architecture)
    5. Ensure enterprise-grade quality before final output
    """
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="AzureArchitectureReviewAgent", openai_client=openai_client, agent_type="review")
    
    # Azure Well-Architected Framework pillars for validation
    WAF_PILLARS = {
        "reliability": {
            "description": "Ensuring a workload performs its intended function correctly and consistently",
            "checklist": [
                "High availability patterns (zone redundancy, multi-region)",
                "Disaster recovery (backup, geo-replication, failover)",
                "Health monitoring and self-healing",
                "Graceful degradation patterns",
                "Circuit breaker pattern for dependent services"
            ]
        },
        "security": {
            "description": "Protecting applications and data from threats",
            "checklist": [
                "Identity and access management (Entra ID, Managed Identity)",
                "Network security (Private endpoints, NSG, WAF, Firewall)",
                "Data protection (encryption at rest, in transit, Key Vault)",
                "Security monitoring (Defender, Sentinel)",
                "Zero-trust architecture principles"
            ]
        },
        "cost_optimization": {
            "description": "Managing costs to maximize value delivered",
            "checklist": [
                "Right-sizing resources",
                "Reserved instances for predictable workloads",
                "Autoscaling to match demand",
                "Cost monitoring and budgets",
                "Storage tier optimization"
            ]
        },
        "operational_excellence": {
            "description": "Operations processes that keep a system running in production",
            "checklist": [
                "Infrastructure as Code (IaC)",
                "CI/CD pipelines",
                "Monitoring and alerting (Azure Monitor, Log Analytics)",
                "Incident response procedures",
                "Documentation and runbooks"
            ]
        },
        "performance_efficiency": {
            "description": "The ability of a workload to scale and meet demands",
            "checklist": [
                "Horizontal scaling patterns",
                "Caching strategies (Redis, CDN)",
                "Async processing (Service Bus, Event Hubs)",
                "Database optimization (indexing, read replicas)",
                "Load balancing and traffic distribution"
            ]
        }
    }
    
    # Azure service compatibility matrix for common patterns
    SERVICE_COMPATIBILITY = {
        "Azure App Service": {
            "recommended_connections": ["Azure SQL Database", "Azure Key Vault", "Azure Cache for Redis", "Application Insights", "Azure Storage"],
            "security_requirements": ["Managed Identity", "Private Endpoint or VNet Integration"],
            "common_issues": ["Missing monitoring", "No caching for DB-heavy apps", "Plain HTTP endpoints"]
        },
        "Azure Kubernetes Service": {
            "recommended_connections": ["Azure Container Registry", "Azure Key Vault", "Azure Monitor", "Azure Application Gateway"],
            "security_requirements": ["Pod Identity/Workload Identity", "Network Policies", "Private Cluster"],
            "common_issues": ["Missing ingress controller", "No secrets management", "Insufficient monitoring"]
        },
        "Azure Functions": {
            "recommended_connections": ["Azure Storage", "Azure Key Vault", "Application Insights", "Azure Service Bus"],
            "security_requirements": ["Managed Identity", "Private Endpoints for Premium"],
            "common_issues": ["Cold start issues without Premium", "Missing connection to message broker"]
        },
        "Azure SQL Database": {
            "recommended_connections": ["Azure Key Vault", "Azure Monitor", "Backup/Geo-Replication"],
            "security_requirements": ["Private Endpoint", "TDE Encryption", "Entra ID Auth"],
            "common_issues": ["Missing backup strategy", "No read replica for read-heavy workloads"]
        },
        "Azure Cosmos DB": {
            "recommended_connections": ["Azure Key Vault", "Azure Monitor", "Azure Functions"],
            "security_requirements": ["Private Endpoint", "RBAC", "Customer-managed keys"],
            "common_issues": ["Suboptimal partition key", "Missing consistency level consideration"]
        },
        "Azure Front Door": {
            "recommended_connections": ["Azure App Service", "Azure Kubernetes Service", "Azure WAF", "Azure CDN"],
            "security_requirements": ["WAF Policy", "HTTPS Only", "DDoS Protection"],
            "common_issues": ["Missing WAF rules", "No health probes configured"]
        }
    }
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform comprehensive architecture review with Azure expertise.
        Returns review results with correction tasks if issues are found.
        """
        if context is None:
            context = {}
        
        # Extract all previous agent results
        component_extraction = context.get("component_extraction", {})
        azure_references = context.get("azure_references", {})
        security_analysis = context.get("security_analysis", {})
        performance_analysis = context.get("performance_analysis", {})
        architecture_analysis = context.get("architecture_analysis", {})
        cost_analysis = context.get("cost_analysis", {})
        validation_result = context.get("validation_result", {})
        
        # Get the generated architecture
        services = architecture_analysis.get("services", [])
        connections = architecture_analysis.get("connections", [])
        containers = architecture_analysis.get("containers", [])
        
        # Search local docs for review-relevant references
        review_docs = self._search_local_docs(
            requirements,
            domain_terms=["well-architected", "best practice", "anti-pattern", "review",
                         "checklist", "architecture decision", "reliability", "security",
                         "operational", "performance", "cost", "compliance"],
            max_results=6
        )
        
        # Build service list for validation
        service_names = [s.get("name", s) if isinstance(s, dict) else s for s in services]
        connection_list = [(c.get("source", ""), c.get("target", ""), c.get("label", "")) 
                          for c in connections if isinstance(c, dict)]
        
        review_prompt = f"""
You are a Principal Azure Solutions Architect with 15+ years of enterprise architecture experience.
You have DEEP expertise in Azure Well-Architected Framework and have reviewed 500+ production architectures.

Your role is to perform a FINAL COMPREHENSIVE REVIEW of this generated architecture before it's delivered to the user.
You must identify ANY issues that would prevent this from being a production-ready, enterprise-grade architecture.

IMPORTANT: Use the LOCAL REFERENCE DOCS below to validate against Azure best practices and identify anti-patterns.
{review_docs}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
AZURE WELL-ARCHITECTED FRAMEWORK PILLARS (Use these for validation):
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{json.dumps(self.WAF_PILLARS, indent=2)}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
SERVICE COMPATIBILITY PATTERNS (Use these for connection validation):
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{json.dumps(self.SERVICE_COMPATIBILITY, indent=2)}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ORIGINAL USER REQUIREMENTS:
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
\"\"\"{requirements}\"\"\"

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
EXTRACTED COMPONENTS (What user needs):
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
- APIs: {json.dumps(component_extraction.get('apis', []), indent=2)}
- NFRs: {json.dumps(component_extraction.get('nfrs', []), indent=2)}
- Technical Requirements: {json.dumps(component_extraction.get('technical_requirements', []), indent=2)}
- Integration Points: {json.dumps(component_extraction.get('integration_points', []), indent=2)}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
GENERATED ARCHITECTURE (What was built - VALIDATE THIS):
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
- Services: {json.dumps(services, indent=2)}
- Connections: {json.dumps(connections, indent=2)}
- Containers/Subnets: {json.dumps(containers, indent=2)}
- Architecture Pattern: {architecture_analysis.get('architecture_pattern', 'N/A')}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
PREVIOUS VALIDATION RESULT:
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
- Validation Score: {validation_result.get('overall_validation_score', 'N/A')}
- Status: {validation_result.get('overall_status', 'N/A')}
- Missing Components: {json.dumps(validation_result.get('missing_components', []), indent=2)}
- Connection Issues: {json.dumps(validation_result.get('connection_validation', {}).get('issues', []), indent=2)}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
YOUR REVIEW TASKS:
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

1. **SERVICE SELECTION REVIEW**: 
   - Are all required Azure services present for the user's requirements?
   - Are there redundant or unnecessary services?
   - Are enterprise-grade services used (not basic/free tiers for production)?

2. **CONNECTION INTEGRITY REVIEW**:
   - Do all services have correct connections (using SERVICE_COMPATIBILITY patterns)?
   - Are there orphan services with no connections?
   - Are connection labels meaningful and accurate?
   - Is the data flow logical (ingress â†’ compute â†’ data â†’ egress)?

3. **WELL-ARCHITECTED FRAMEWORK REVIEW** (Check EACH pillar):
   - RELIABILITY: HA patterns, DR, redundancy, health checks
   - SECURITY: Identity, network isolation, encryption, monitoring
   - COST: Right-sizing, optimization opportunities
   - OPERATIONAL EXCELLENCE: Monitoring, logging, IaC readiness
   - PERFORMANCE: Caching, scaling, load balancing

4. **FLOW VALIDATION**:
   - Is there a clear entry point (Front Door, API Gateway, Load Balancer)?
   - Does data flow make sense end-to-end?
   - Are there bottlenecks or single points of failure?

5. **CRITICAL ISSUES IDENTIFICATION**:
   - Security vulnerabilities (exposed endpoints, missing encryption)
   - Reliability gaps (no redundancy for critical services)
   - Missing essential connections

For ANY issue found, provide a SPECIFIC correction task that routes to the appropriate agent.

Return ONLY valid JSON:
{{
  "review_status": "<APPROVED|NEEDS_CORRECTION|CRITICAL_ISSUES>",
  "overall_score": 0,
  "waf_pillar_scores": {{
    "reliability": {{"score": 0, "issues": [], "recommendations": []}},
    "security": {{"score": 0, "issues": [], "recommendations": []}},
    "cost_optimization": {{"score": 0, "issues": [], "recommendations": []}},
    "operational_excellence": {{"score": 0, "issues": [], "recommendations": []}},
    "performance_efficiency": {{"score": 0, "issues": [], "recommendations": []}}
  }},
  "service_review": {{
    "total_services": 0,
    "appropriate_services": 0,
    "missing_services": [
      {{"service": "<missing Azure service>", "reason": "<why needed>", "priority": "<Critical|High|Medium>"}}
    ],
    "redundant_services": [
      {{"service": "<redundant service>", "reason": "<why redundant>", "action": "<remove or consolidate>"}}
    ]
  }},
  "connection_review": {{
    "total_connections": 0,
    "valid_connections": 0,
    "missing_connections": [
      {{"source": "<service>", "target": "<service>", "label": "<connection type>", "reason": "<why needed>"}}
    ],
    "invalid_connections": [
      {{"source": "<service>", "target": "<service>", "issue": "<what is wrong>", "fix": "<how to fix>"}}
    ],
    "orphan_services": ["<services with no connections>"]
  }},
  "flow_review": {{
    "has_clear_entry_point": true,
    "entry_points": ["<entry point services>"],
    "data_flow_valid": true,
    "flow_description": "<request flow path>",
    "bottlenecks": [],
    "single_points_of_failure": []
  }},
  "critical_issues": [
    {{
      "issue": "<critical issue description>",
      "category": "<Security|Reliability|Performance|Compliance>",
      "severity": "<Critical|High|Medium>",
      "affected_services": ["<services affected>"],
      "impact": "<business impact if not fixed>",
      "resolution": "<specific fix required>"
    }}
  ],
  "correction_tasks": [
    {{
      "task_id": "<unique task id like CT-001>",
      "task_type": "<add_service|add_connection|modify_service|remove_service|add_container>",
      "target_agent": "<ArchitectureAgent|SecurityAgent|PerformanceAgent>",
      "priority": "<Critical|High|Medium|Low>",
      "description": "<what needs to be done>",
      "details": {{
        "service_name": "<if adding/modifying service>",
        "source": "<if adding connection>",
        "target": "<if adding connection>",
        "label": "<connection label>",
        "category": "<service category>",
        "subnet": "<target subnet>",
        "reason": "<why this correction is needed>"
      }},
      "affected_requirement": "<which user requirement this fixes>",
      "waf_pillar": "<which pillar this improves>"
    }}
  ],
  "improvement_suggestions": [
    {{
      "area": "<area>",
      "suggestion": "<improvement suggestion>",
      "priority": "<High|Medium|Low>",
      "effort": "<Low|Medium|High>"
    }}
  ],
  "final_verdict": {{
    "ready_for_production": true,
    "confidence_level": "<High|Medium|Low>",
    "summary": "<brief summary of architecture quality>",
    "key_strengths": ["<strength 1>", "<strength 2>"],
    "key_concerns": ["<concern 1>", "<concern 2>"]
  }}
}}
"""

        messages = [
            {"role": "system", "content": """You are a Principal Azure Solutions Architect performing the FINAL REVIEW of a generated architecture.
You have deep expertise in Azure Well-Architected Framework and have reviewed hundreds of enterprise architectures.
Your review must be THOROUGH and CRITICAL. If there are issues, identify them clearly with specific correction tasks.
The architecture will be corrected through your correction_tasks before being delivered to the user.
Return only valid JSON."""},
            {"role": "user", "content": review_prompt}
        ]

        try:
            response = await self._call_openai(messages)
            result = self._parse_review_response(response)
            
            # Log review results
            self._log_review_results(result)
            
            return result
        except Exception as e:
            logger.error(f"Error in AzureArchitectureReviewAgent.analyze: {e}")
            return {
                "agent": "architecture_review",
                "error": str(e),
                "status": "error",
                "review_status": "ERROR",
                "overall_score": 0,
                "correction_tasks": []
            }

    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse review response from AI"""
        default_response = {
            "review_status": "ERROR",
            "overall_score": 0,
            "waf_pillar_scores": {},
            "service_review": {},
            "connection_review": {},
            "flow_review": {},
            "critical_issues": [],
            "correction_tasks": [],
            "improvement_suggestions": [],
            "final_verdict": {
                "ready_for_production": False,
                "confidence_level": "Low",
                "summary": "Review could not be completed"
            },
            "is_fallback": True
        }
        
        parsed = self._safe_json_parse(response, default_response)
        parsed["agent"] = "architecture_review"
        parsed["status"] = "completed"
        
        return parsed

    def _log_review_results(self, result: Dict):
        """Log the architecture review results prominently."""
        review_status = result.get("review_status", "UNKNOWN")
        overall_score = result.get("overall_score", 0)
        
        status_icon = "âœ…" if review_status == "APPROVED" else "âš ï¸" if review_status == "NEEDS_CORRECTION" else "âŒ"
        score_icon = "ðŸŸ¢" if overall_score >= 80 else "ðŸŸ¡" if overall_score >= 60 else "ðŸ”´"
        
        logger.info("\n" + "=" * 80)
        logger.info("ðŸ” AZURE ARCHITECTURE REVIEW AGENT - FINAL REVIEW REPORT")
        logger.info("=" * 80)
        logger.info(f"  {status_icon} Review Status: {review_status}")
        logger.info(f"  {score_icon} Overall Score: {overall_score}/100")
        
        print("\n" + "=" * 80)
        print("ðŸ” AZURE ARCHITECTURE REVIEW AGENT - FINAL REVIEW REPORT")
        print("=" * 80)
        print(f"  {status_icon} Review Status: {review_status}")
        print(f"  {score_icon} Overall Score: {overall_score}/100")
        
        # WAF Pillar Scores
        waf_scores = result.get("waf_pillar_scores", {})
        if waf_scores:
            logger.info("\n  ðŸ“Š Well-Architected Framework Pillar Scores:")
            print("\n  ðŸ“Š Well-Architected Framework Pillar Scores:")
            for pillar, data in waf_scores.items():
                if isinstance(data, dict):
                    score = data.get("score", 0)
                    p_icon = "ðŸŸ¢" if score >= 80 else "ðŸŸ¡" if score >= 60 else "ðŸ”´"
                    logger.info(f"    {p_icon} {pillar.title()}: {score}/100")
                    print(f"    {p_icon} {pillar.title()}: {score}/100")
        
        # Critical Issues
        critical_issues = result.get("critical_issues", [])
        if critical_issues:
            logger.info(f"\n  âŒ Critical Issues ({len(critical_issues)}):")
            print(f"\n  âŒ Critical Issues ({len(critical_issues)}):")
            for issue in critical_issues:
                severity = issue.get("severity", "Unknown")
                s_icon = "ðŸ”´" if severity == "Critical" else "ðŸŸ " if severity == "High" else "ðŸŸ¡"
                logger.info(f"    {s_icon} [{severity}] {issue.get('issue', 'Unknown issue')}")
                logger.info(f"       Impact: {issue.get('impact', 'N/A')}")
                logger.info(f"       Resolution: {issue.get('resolution', 'N/A')}")
                print(f"    {s_icon} [{severity}] {issue.get('issue', 'Unknown issue')}")
                print(f"       Impact: {issue.get('impact', 'N/A')}")
                print(f"       Resolution: {issue.get('resolution', 'N/A')}")
        
        # Correction Tasks
        correction_tasks = result.get("correction_tasks", [])
        if correction_tasks:
            logger.info(f"\n  ðŸ”§ Correction Tasks ({len(correction_tasks)}):")
            print(f"\n  ðŸ”§ Correction Tasks ({len(correction_tasks)}):")
            for task in correction_tasks:
                task_id = task.get("task_id", "N/A")
                task_type = task.get("task_type", "unknown")
                target = task.get("target_agent", "ArchitectureAgent")
                priority = task.get("priority", "Medium")
                p_icon = "ðŸ”´" if priority == "Critical" else "ðŸŸ " if priority == "High" else "ðŸŸ¡"
                logger.info(f"    {p_icon} [{task_id}] {task_type} â†’ {target}")
                logger.info(f"       {task.get('description', 'No description')}")
                print(f"    {p_icon} [{task_id}] {task_type} â†’ {target}")
                print(f"       {task.get('description', 'No description')}")
        
        # Final Verdict
        verdict = result.get("final_verdict", {})
        if verdict:
            ready = verdict.get("ready_for_production", False)
            ready_icon = "âœ…" if ready else "âŒ"
            logger.info(f"\n  {ready_icon} Ready for Production: {'YES' if ready else 'NO'}")
            logger.info(f"  ðŸ“Š Confidence Level: {verdict.get('confidence_level', 'N/A')}")
            logger.info(f"  ðŸ“ Summary: {verdict.get('summary', 'N/A')}")
            print(f"\n  {ready_icon} Ready for Production: {'YES' if ready else 'NO'}")
            print(f"  ðŸ“Š Confidence Level: {verdict.get('confidence_level', 'N/A')}")
            print(f"  ðŸ“ Summary: {verdict.get('summary', 'N/A')}")
            
            strengths = verdict.get("key_strengths", [])
            if strengths:
                logger.info("  ðŸ’ª Key Strengths:")
                print("  ðŸ’ª Key Strengths:")
                for s in strengths[:3]:
                    logger.info(f"    âœ“ {s}")
                    print(f"    âœ“ {s}")
            
            concerns = verdict.get("key_concerns", [])
            if concerns:
                logger.info("  âš ï¸ Key Concerns:")
                print("  âš ï¸ Key Concerns:")
                for c in concerns[:3]:
                    logger.info(f"    âš¡ {c}")
                    print(f"    âš¡ {c}")
        
        logger.info("=" * 80 + "\n")
        print("=" * 80 + "\n")

    def get_agents_for_correction(self, correction_tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group correction tasks by target agent for routing.
        Returns dict mapping agent name to list of tasks for that agent.
        """
        agent_tasks = {}
        for task in correction_tasks:
            target_agent = task.get("target_agent", "ArchitectureAgent")
            if target_agent not in agent_tasks:
                agent_tasks[target_agent] = []
            agent_tasks[target_agent].append(task)
        return agent_tasks

    def create_correction_context(self, original_context: Dict, correction_tasks: List[Dict]) -> Dict:
        """
        Create a modified context for correction agents that includes the correction tasks.
        """
        correction_context = original_context.copy()
        correction_context["review_correction_tasks"] = correction_tasks
        correction_context["is_correction_pass"] = True
        return correction_context


