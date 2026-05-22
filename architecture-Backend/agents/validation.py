import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class RequirementsValidationAgent(BaseAgent):
    """Final agent in the pipeline - validates that ALL user requirements are accurately
    implemented in the generated architecture, connections are correct, and flow is valid.
    Uses local azure-docs to verify architecture against best practices and reference patterns."""
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="RequirementsValidationAgent", openai_client=openai_client, agent_type="validation")

    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate the final architecture against original user requirements and azure-docs best practices."""
        if context is None:
            context = {}

        extracted_components = context.get("component_extraction", {})
        reference_architectures = context.get("azure_references", {})
        security_result = context.get("security_analysis", {})
        performance_result = context.get("performance_analysis", {})
        architecture_result = context.get("architecture_analysis", {})
        cost_result = context.get("cost_analysis", {})

        # Search local docs for validation-relevant references (best practices, anti-patterns)
        validation_docs = self._search_local_docs(
            requirements,
            domain_terms=["best practice", "anti-pattern", "design principle", "reliability",
                         "validation", "well-architected", "review checklist",
                         "disaster recovery", "resilience", "monitoring"],
            max_results=5
        )

        validation_prompt = f"""
You are a Senior Azure Solutions Architect performing a FINAL VALIDATION of a generated architecture.
Your job is to verify that ALL user requirements are accurately implemented, all connections are correct, and the architecture flow is valid.
When you find gaps, provide SPECIFIC remediation actions so the architecture can be automatically fixed.

IMPORTANT: Use the LOCAL REFERENCE DOCS below to validate the architecture against Azure best practices, design principles, and anti-patterns.
{validation_docs}

ORIGINAL USER REQUIREMENTS:
\"\"\"{requirements}\"\"\"

EXTRACTED COMPONENTS (what user asked for):
- APIs: {json.dumps(extracted_components.get('apis', []), indent=2)}
- NFRs: {json.dumps(extracted_components.get('nfrs', []), indent=2)}
- Technical Requirements: {json.dumps(extracted_components.get('technical_requirements', []), indent=2)}
- Tech Stack: {json.dumps(extracted_components.get('tech_stack', []), indent=2)}
- Business Requirements: {json.dumps(extracted_components.get('business_requirements', []), indent=2)}
- Data Requirements: {json.dumps(extracted_components.get('data_requirements', []), indent=2)}
- Integration Points: {json.dumps(extracted_components.get('integration_points', []), indent=2)}

REFERENCE ARCHITECTURES USED:
{json.dumps(reference_architectures.get('matched_reference_architectures', [])[:5], indent=2)}

GENERATED ARCHITECTURE (what was built):
- Services: {json.dumps(architecture_result.get('services', []), indent=2)}
- Connections: {json.dumps(architecture_result.get('connections', []), indent=2)}
- Containers: {json.dumps(architecture_result.get('containers', []), indent=2)}
- Architecture Pattern: {architecture_result.get('architecture_pattern', 'N/A')}

SECURITY ANALYSIS:
- Security Services: {json.dumps(security_result.get('security_services', [])[:5], indent=2)}
- Compliance Score: {security_result.get('compliance_score', 'N/A')}

PERFORMANCE ANALYSIS:
- Performance Services: {json.dumps(performance_result.get('performance_services', [])[:5], indent=2)}
- Performance Score: {performance_result.get('performance_score', 'N/A')}

COST ANALYSIS:
- Cost Score: {cost_result.get('cost_score', 'N/A') if cost_result else 'N/A'}
- Cost Optimizations: {json.dumps(cost_result.get('cost_optimization_services', [])[:3], indent=2) if cost_result else '[]'}

Perform a thorough validation:

1. **Requirements Coverage**: For EACH extracted component (API, NFR, tech requirement, integration point), check if the architecture addresses it. If not, flag it as MISSING.
2. **Connection Validation**: Are all connections between services correct? Are there missing connections that should exist (e.g., app â†’ database, app â†’ cache)?
3. **Flow Validation**: Does the end-to-end data/request flow make sense? Is there a clear path from user â†’ frontend â†’ backend â†’ data?
4. **NFR Compliance**: Are the non-functional requirements (availability, scalability, security, latency) properly addressed by the services chosen?
5. **Missing Components**: List ANY requirement that has NO corresponding service. For each, specify which Azure service should be added.
6. **Security Completeness**: Are identity, network security, data protection, and encryption properly implemented?
7. **Integration Completeness**: Are all external integration points covered?
8. **Multi-RG Grouping Validation**: Are services properly separated into distinct Resource Groups by concern? Does each RG have a clear purpose? Are VNets assigned to specific RGs? Are subnets inside specific VNets? Are monitoring/security services in their own RG? Is VNet Peering defined where needed between separate VNets?

CRITICAL: For every gap found, provide a specific remediation_action with the exact service to add and connection to create.

Return ONLY valid JSON:
{{
  "overall_validation_score": 0,
  "overall_status": "<PASSED|PASSED_WITH_WARNINGS|FAILED>",
  "requirements_coverage": {{
    "total_requirements": 0,
    "implemented": 0,
    "partially_implemented": 0,
    "missing": 0,
    "coverage_percentage": 0
  }},
  "requirement_checks": [
    {{
      "requirement": "<exact requirement text from extracted components>",
      "source_category": "<api|nfr|technical_requirement|integration_point|business_requirement|data_requirement>",
      "status": "<IMPLEMENTED|PARTIALLY_IMPLEMENTED|MISSING>",
      "implemented_by": "<service name or null>",
      "notes": "<explanation>",
      "recommendation": "<action if not fully implemented>"
    }}
  ],
  "connection_validation": {{
    "total_connections": 0,
    "valid_connections": 0,
    "invalid_connections": 0,
    "missing_connections": [
      {{"source": "<service>", "target": "<service>", "reason": "<why needed>", "label": "<protocol>"}}
    ],
    "issues": [
      {{"source": "<service>", "target": "<service>", "issue": "<problem>"}}
    ]
  }},
  "flow_validation": {{
    "is_valid": true,
    "flow_description": "<end-to-end request flow>",
    "issues": [],
    "recommendations": []
  }},
  "nfr_compliance": [
    {{"nfr": "<exact NFR text>", "status": "<COMPLIANT|PARTIALLY_COMPLIANT|NON_COMPLIANT>", "evidence": "<which services address this>", "gap": "<what is missing if any>"}}
  ],
  "missing_components": [
    {{"component": "<what is missing>", "source_requirement": "<which requirement needs it>", "reason": "<why it is needed>", "recommendation": "<specific Azure service to add>", "category": "<service category>", "subnet": "<which subnet>"}}
  ],
  "security_validation": {{
    "identity_check": "<PASS|FAIL|WARNING>",
    "network_security_check": "<PASS|FAIL|WARNING>",
    "data_protection_check": "<PASS|FAIL|WARNING>",
    "issues": []
  }},
  "remediation_actions": [
    {{
      "action_type": "<add_service|add_connection|modify_service|add_container>",
      "priority": "<Critical|High|Medium|Low>",
      "target_agent": "<ArchitectureAgent|SecurityAgent|PerformanceAgent>",
      "details": {{
        "service_name": "<Azure service to add if add_service>",
        "category": "<service category>",
        "subnet": "<target subnet>",
        "description": "<why needed>",
        "source": "<connection source if add_connection>",
        "target": "<connection target if add_connection>",
        "label": "<connection label if add_connection>"
      }},
      "reason": "<which requirement this fixes>"
    }}
  ],
  "recommendations": [
    {{"priority": "<High|Medium|Low>", "area": "<area>", "recommendation": "<specific action>"}}
  ],
  "best_practice_violations": [
    {{"practice": "<best practice>", "reference_doc": "<doc title>", "status": "<VIOLATED|COMPLIANT>", "recommendation": "<fix>"}}
  ]
}}
"""

        messages = [
            {"role": "system", "content": "You are a Senior Azure Solutions Architect performing final validation. Use the LOCAL REFERENCE DOCS to verify the architecture against Azure best practices, anti-patterns, and design principles. Be thorough and critical. Check every requirement against the actual architecture. Return only valid JSON."},
            {"role": "user", "content": validation_prompt}
        ]

        try:
            response = await self._call_openai(messages)
            result = self._parse_validation_response(response)

            # Log validation results
            self._log_validation_results(result)

            return result
        except Exception as e:
            logger.error(f"Error in RequirementsValidationAgent.analyze: {e}")
            return {
                "agent": "requirements_validation",
                "error": str(e),
                "status": "error",
                "overall_validation_score": 0,
                "overall_status": "ERROR"
            }

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse validation response from AI"""
        default_response = {
            "overall_validation_score": 0,
            "overall_status": "UNKNOWN",
            "requirements_coverage": {},
            "requirement_checks": [],
            "connection_validation": {},
            "flow_validation": {},
            "nfr_compliance": [],
            "missing_components": [],
            "security_validation": {},
            "remediation_actions": [],
            "recommendations": [],
            "best_practice_violations": [],
            "is_fallback": True
        }
        parsed = self._safe_json_parse(response, default_response)
        parsed["agent"] = "requirements_validation"
        parsed["status"] = "completed"
        
        # Auto-generate remediation_actions from missing_components if not provided by LLM
        if not parsed.get("remediation_actions") and parsed.get("missing_components"):
            remediation = []
            for mc in parsed["missing_components"]:
                rec = mc.get("recommendation", "")
                if rec:
                    remediation.append({
                        "action_type": "add_service",
                        "priority": "High",
                        "target_agent": "ArchitectureAgent",
                        "details": {
                            "service_name": rec.split("Add ")[-1] if "Add " in rec else rec,
                            "category": mc.get("category", "compute"),
                            "subnet": mc.get("subnet", "backend-subnet"),
                            "description": mc.get("reason", "")
                        },
                        "reason": mc.get("source_requirement", mc.get("component", ""))
                    })
            # Also add missing connections
            conn_val = parsed.get("connection_validation", {})
            for mc in conn_val.get("missing_connections", []):
                remediation.append({
                    "action_type": "add_connection",
                    "priority": "High",
                    "target_agent": "ArchitectureAgent",
                    "details": {
                        "source": mc.get("source", ""),
                        "target": mc.get("target", ""),
                        "label": mc.get("label", mc.get("reason", "")),
                    },
                    "reason": mc.get("reason", "")
                })
            parsed["remediation_actions"] = remediation
        
        return parsed

    def _log_validation_results(self, result: Dict):
        """Log the final validation results prominently."""
        score = result.get("overall_validation_score", 0)
        status = result.get("overall_status", "UNKNOWN")
        coverage = result.get("requirements_coverage", {})

        logger.info("\n" + "=" * 80)
        logger.info("âœ… REQUIREMENTS VALIDATION AGENT - FINAL REPORT")
        logger.info("=" * 80)
        
        print("\n" + "=" * 80)
        print("âœ… REQUIREMENTS VALIDATION AGENT - FINAL REPORT")
        print("=" * 80)

        # Overall score
        score_icon = "ðŸŸ¢" if score >= 80 else "ðŸŸ¡" if score >= 60 else "ðŸ”´"
        logger.info(f"  {score_icon} Overall Validation Score: {score}/100")
        logger.info(f"  Status: {status}")
        print(f"  {score_icon} Overall Validation Score: {score}/100")
        print(f"  Status: {status}")

        # Requirements coverage
        if coverage:
            total = coverage.get("total_requirements", 0)
            implemented = coverage.get("implemented", 0)
            missing = coverage.get("missing", 0)
            pct = coverage.get("coverage_percentage", 0)
            logger.info(f"\n  ðŸ“‹ Requirements Coverage: {pct}% ({implemented}/{total} implemented, {missing} missing)")
            print(f"\n  ðŸ“‹ Requirements Coverage: {pct}% ({implemented}/{total} implemented, {missing} missing)")

        # Individual requirement checks
        checks = result.get("requirement_checks", [])
        if checks:
            print("\n  Individual Requirement Checks:")
            logger.info("\n  Individual Requirement Checks:")
            for chk in checks:
                req = chk.get("requirement", "")
                st = chk.get("status", "UNKNOWN")
                icon = "âœ…" if st == "IMPLEMENTED" else "âš ï¸" if st == "PARTIALLY_IMPLEMENTED" else "âŒ"
                impl = chk.get("implemented_by", "N/A")
                logger.info(f"    {icon} {req} â†’ {st} (by: {impl})")
                print(f"    {icon} {req} â†’ {st} (by: {impl})")
                if chk.get("recommendation"):
                    logger.info(f"       ðŸ’¡ Recommendation: {chk['recommendation']}")
                    print(f"       ðŸ’¡ Recommendation: {chk['recommendation']}")

        # Connection validation
        conn_val = result.get("connection_validation", {})
        if conn_val:
            total_conn = conn_val.get("total_connections", 0)
            valid_conn = conn_val.get("valid_connections", 0)
            logger.info(f"\n  ðŸ”— Connection Validation: {valid_conn}/{total_conn} valid")
            print(f"\n  ðŸ”— Connection Validation: {valid_conn}/{total_conn} valid")
            for issue in conn_val.get("issues", []):
                logger.info(f"    âš ï¸  {issue.get('source', '')} â†’ {issue.get('target', '')}: {issue.get('issue', '')}")
                print(f"    âš ï¸  {issue.get('source', '')} â†’ {issue.get('target', '')}: {issue.get('issue', '')}")

        # Flow validation
        flow_val = result.get("flow_validation", {})
        if flow_val:
            flow_valid = flow_val.get("is_valid", False)
            flow_icon = "âœ…" if flow_valid else "âŒ"
            logger.info(f"\n  {flow_icon} Flow Validation: {'VALID' if flow_valid else 'INVALID'}")
            logger.info(f"    Flow: {flow_val.get('flow_description', 'N/A')}")
            print(f"\n  {flow_icon} Flow Validation: {'VALID' if flow_valid else 'INVALID'}")
            print(f"    Flow: {flow_val.get('flow_description', 'N/A')}")

        # Missing components
        missing = result.get("missing_components", [])
        if missing:
            logger.info(f"\n  âŒ Missing Components ({len(missing)}):")
            print(f"\n  âŒ Missing Components ({len(missing)}):")
            for mc in missing:
                logger.info(f"    â€¢ {mc.get('component', '')}: {mc.get('reason', '')} â†’ {mc.get('recommendation', '')}")
                print(f"    â€¢ {mc.get('component', '')}: {mc.get('reason', '')} â†’ {mc.get('recommendation', '')}")

        # NFR compliance
        nfr_compliance = result.get("nfr_compliance", [])
        if nfr_compliance:
            logger.info(f"\n  ðŸ“Š NFR Compliance:")
            print(f"\n  ðŸ“Š NFR Compliance:")
            for nfr in nfr_compliance:
                nfr_status = nfr.get("status", "UNKNOWN")
                nfr_icon = "âœ…" if nfr_status == "COMPLIANT" else "âš ï¸" if "PARTIAL" in nfr_status else "âŒ"
                logger.info(f"    {nfr_icon} {nfr.get('nfr', '')} â†’ {nfr_status}")
                print(f"    {nfr_icon} {nfr.get('nfr', '')} â†’ {nfr_status}")

        # Final recommendations
        recs = result.get("recommendations", [])
        if recs:
            logger.info(f"\n  ðŸ’¡ Recommendations ({len(recs)}):")
            print(f"\n  ðŸ’¡ Recommendations ({len(recs)}):")
            for rec in recs:
                priority = rec.get("priority", "Medium")
                p_icon = "ðŸ”´" if priority == "High" else "ðŸŸ¡" if priority == "Medium" else "ðŸŸ¢"
                logger.info(f"    {p_icon} [{priority}] {rec.get('area', '')}: {rec.get('recommendation', '')}")
                print(f"    {p_icon} [{priority}] {rec.get('area', '')}: {rec.get('recommendation', '')}")

        logger.info("=" * 80 + "\n")
        print("=" * 80 + "\n")


