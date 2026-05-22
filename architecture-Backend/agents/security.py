import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent, AgentTools

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """Expert Azure Security Architect following Azure Architecture Center security patterns and Zero Trust reference architectures.
    Uses local azure-docs for verified security guidance, patterns, and reference architectures.
    
    EXPERTISE DOMAINS:
    - Zero Trust Architecture & Principles
    - Azure Well-Architected Framework (Security Pillar)
    - Identity & Access Management (RBAC, PIM, Conditional Access)
    - Network Security (NSG, Firewall, Private Link, Service Endpoints)
    - Data Protection (Encryption, Key Vault, CMK, DPK)
    - Compliance Frameworks (SOC2, HIPAA, GDPR, PCI-DSS, ISO 27001, FedRAMP)
    - Threat Modeling & Security Posture Management
    - Microsoft Defender for Cloud & Sentinel
    """
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="SecurityAgent", openai_client=openai_client, agent_type="security")
    
    # Security service categories and their Azure implementations
    SECURITY_KNOWLEDGE_BASE = {
        "zero_trust_principles": {
            "description": "Never trust, always verify - assume breach",
            "pillars": ["Verify explicitly", "Use least privilege access", "Assume breach"],
            "azure_services": ["Microsoft Entra ID", "Conditional Access", "PIM", "Azure AD B2C"]
        },
        "identity_protection": {
            "services": {
                "Microsoft Entra ID": "Primary identity provider for all Azure workloads",
                "Conditional Access": "Context-aware access policies based on user, device, location, risk",
                "Privileged Identity Management": "Just-in-time privileged access with approval workflows",
                "Azure AD B2C": "Customer-facing identity for consumer applications",
                "Managed Identity": "System/User-assigned identities eliminating credential management"
            },
            "best_practices": [
                "Use Managed Identities instead of service principals where possible",
                "Enable MFA for all users, especially privileged accounts",
                "Implement Conditional Access with risk-based policies",
                "Use PIM for all administrative access",
                "Separate workload identities from user identities"
            ]
        },
        "network_security": {
            "services": {
                "Azure Firewall Premium": "Enterprise-grade firewall with TLS inspection and IDPS",
                "Azure WAF": "Web Application Firewall protecting against OWASP Top 10",
                "Network Security Groups": "Stateful packet filtering for subnets and NICs",
                "Azure DDoS Protection": "Layer 3/4 DDoS mitigation",
                "Private Link": "Private connectivity to Azure PaaS services",
                "Azure Bastion": "Secure RDP/SSH without public IP exposure"
            },
            "patterns": {
                "hub_spoke": "Centralized network security with shared services",
                "zero_trust_network": "Microsegmentation with identity-based access",
                "private_endpoints": "Eliminate public internet exposure for PaaS services"
            }
        },
        "data_protection": {
            "services": {
                "Azure Key Vault": "Centralized secrets, keys, and certificate management",
                "Azure Information Protection": "Data classification and labeling",
                "Transparent Data Encryption": "At-rest encryption for Azure SQL",
                "Always Encrypted": "Client-side encryption for sensitive columns",
                "Customer Managed Keys": "BYOK encryption for compliance requirements"
            },
            "encryption_standards": {
                "at_rest": "AES-256 with platform or customer-managed keys",
                "in_transit": "TLS 1.2+ for all communications",
                "in_use": "Confidential Computing with SGX enclaves"
            }
        },
        "threat_detection": {
            "services": {
                "Microsoft Defender for Cloud": "Cloud Security Posture Management (CSPM)",
                "Microsoft Sentinel": "Cloud-native SIEM and SOAR",
                "Azure Security Center": "Unified security management",
                "Microsoft Defender for Identity": "On-premises AD threat detection"
            },
            "capabilities": [
                "Continuous vulnerability assessment",
                "Just-in-time VM access",
                "Adaptive application controls",
                "File integrity monitoring",
                "Threat intelligence integration"
            ]
        },
        "compliance_frameworks": {
            "SOC2": {"focus": "Security, Availability, Confidentiality, Processing Integrity, Privacy", 
                    "azure_tools": ["Compliance Manager", "Azure Policy", "Azure Blueprints"]},
            "HIPAA": {"focus": "Protected Health Information (PHI)", 
                     "azure_tools": ["Azure Health Data Services", "Private Link", "CMK encryption"]},
            "GDPR": {"focus": "Personal data protection for EU residents", 
                    "azure_tools": ["Data residency controls", "Azure Information Protection", "Right to erasure"]},
            "PCI_DSS": {"focus": "Payment card data security", 
                       "azure_tools": ["Azure Firewall", "NSG", "Key Vault", "Activity logging"]},
            "ISO_27001": {"focus": "Information security management", 
                         "azure_tools": ["Azure Security Center", "Policy compliance", "Audit logs"]},
            "FedRAMP": {"focus": "US government cloud security", 
                       "azure_tools": ["Azure Government", "IL4/IL5 compliance", "Encryption controls"]}
        }
    }
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyzes requirements and returns security recommendations backed by local azure-docs.
        Uses context from previous agents (component_extraction, azure_references) to ground recommendations."""
        if context is None:
            context = {}

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Chain-of-Thought reasoning
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        self.think(f"I am the {self.persona.role}. Analyzing security requirements.", "reasoning")
        self.think("My approach: Defense in Depth, Zero Trust, Least Privilege", "reasoning")
        
        # Check for messages from upstream agents
        messages = self.receive_messages()
        if messages:
            self.think(f"Received {len(messages)} insights from upstream agents", "communication")
            for msg in messages:
                self.think(f"Insight from {msg.from_agent}: {msg.content[:100]}", "observation")

        # Extract data from previous agents
        component_data = context.get("component_extraction", {})
        azure_refs = context.get("azure_references", {})

        # Build dynamic context sections from previous agents
        component_context = ""
        if component_data and component_data.get("status") == "completed":
            apis = component_data.get("apis", [])
            nfrs = component_data.get("nfrs", [])
            tech_reqs = component_data.get("technical_requirements", [])
            tech_stack = component_data.get("tech_stack", [])
            integration_points = component_data.get("integration_points", [])
            component_context = f"""
EXTRACTED COMPONENTS FROM PREVIOUS AGENT (ComponentExtractionAgent):
- APIs: {json.dumps(apis, indent=2)}
- Non-Functional Requirements: {json.dumps(nfrs, indent=2)}
- Technical Requirements: {json.dumps(tech_reqs, indent=2)}
- Tech Stack: {json.dumps(tech_stack, indent=2)}
- Integration Points: {json.dumps(integration_points, indent=2)}
"""

        reference_context = ""
        if azure_refs and azure_refs.get("status") == "completed":
            matched_archs = azure_refs.get("matched_reference_architectures", [])[:5]
            recommended_svcs = azure_refs.get("recommended_azure_services", [])
            design_decisions = azure_refs.get("design_decisions", [])
            reference_context = f"""
AZURE ARCHITECTURE REFERENCES FROM PREVIOUS AGENT (AzureArchitectureReferenceAgent):
- Matched Reference Architectures: {json.dumps(matched_archs, indent=2)}
- Recommended Azure Services: {json.dumps(recommended_svcs, indent=2)}
- Design Decisions: {json.dumps(design_decisions, indent=2)}
"""

        # Search local docs for security-relevant references
        self.think("Using Azure docs search tool for security patterns...", "tool_call")
        security_docs = await self.use_tool(
            AgentTools.SEARCH_AZURE_DOCS,
            {
                "query": requirements,
                "domain_terms": ["security", "zero trust", "firewall", "identity", "network security",
                               "key vault", "waf", "private endpoint", "nsg", "defender",
                               "conditional access", "encryption", "compliance", "sentinel",
                               "managed identity", "rbac", "pim", "bastion", "ddos"],
                "max_results": 8
            }
        )
        
        self.think("Analyzing Zero Trust principles, network security, and compliance requirements...", "reasoning")

        enhanced_security_prompt = f"""
You are a Principal Azure Security Architect with 15+ years of enterprise security experience.
You hold the following certifications: AZ-500, SC-100, SC-200, CISSP, and CCSP.
You have designed Zero Trust architectures for Fortune 500 companies and led security audits for SOC2, HIPAA, and PCI-DSS compliance.

YOUR SECURITY PHILOSOPHY:
- "Defense in Depth" - Multiple layers of security controls
- "Zero Trust" - Never trust, always verify, assume breach
- "Least Privilege" - Minimum required access for every identity
- "Security by Design" - Security built into architecture, not bolted on

IMPORTANT: Use the LOCAL REFERENCE DOCS below as your PRIMARY source for security patterns and best practices.
{security_docs}
{component_context}
{reference_context}

YOUR DEEP EXPERTISE AREAS:

ðŸ” **ZERO TRUST ARCHITECTURE**:
- Verify explicitly using all available data points (user identity, location, device health, service/workload, data classification, anomalies)
- Use least privilege access with Just-In-Time (JIT) and Just-Enough-Access (JEA)
- Assume breach - minimize blast radius using micro-segmentation and real-time threat detection

ðŸ›¡ï¸ **AZURE SECURITY SERVICES EXPERTISE**:
{json.dumps(self.SECURITY_KNOWLEDGE_BASE, indent=2)}

ðŸ›ï¸ **AZURE ARCHITECTURE CENTER SECURITY PATTERNS**:
- Zero Trust Reference Architecture: https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/identity/
- Network Security Patterns: https://learn.microsoft.com/en-us/azure/architecture/framework/security/design-network
- Identity & Access Management: https://learn.microsoft.com/en-us/azure/architecture/framework/security/design-identity
- Data Protection Patterns: https://learn.microsoft.com/en-us/azure/architecture/framework/security/design-storage
- Application Security: https://learn.microsoft.com/en-us/azure/architecture/framework/security/design-apps-services
- Security Operations: https://learn.microsoft.com/en-us/azure/architecture/framework/security/security-operations

USER REQUIREMENTS: {requirements}

ANALYSIS TASKS:
1. **Threat Modeling**: Identify potential threats (STRIDE model) based on the architecture
2. **Identity Strategy**: Design identity architecture with Zero Trust principles
3. **Network Security**: Plan network segmentation, private endpoints, and perimeter security
4. **Data Protection**: Specify encryption requirements and key management
5. **Compliance Mapping**: Map requirements to relevant compliance frameworks
6. **Detection & Response**: Plan security monitoring and incident response

Return ONLY valid JSON:
{{
  "security_services": [
    {{"service": "<specific Azure security service>", "tier": "<recommended tier>", "purpose": "<why this service is needed for THIS architecture>", "zero_trust_pillar": "<which ZT pillar this addresses>"}}
  ],
  "network_security": [
    {{"component": "<network security component>", "configuration": "<specific configuration>", "protection_scope": "<what it protects>"}}
  ],
  "identity_management": [
    {{"capability": "<identity capability>", "configuration": "<specific configuration>", "rbac_scope": "<access scope>"}}
  ],
  "data_protection": [
    {{"data_type": "<type of data>", "encryption_method": "<encryption approach>", "key_management": "<KV/CMK/PMK>"}}
  ],
  "threat_model": [
    {{"threat_category": "<STRIDE category>", "threat": "<specific threat>", "mitigation": "<security control>", "severity": "<Critical|High|Medium|Low>"}}
  ],
  "compliance_requirements": [
    {{"framework": "<compliance framework>", "controls": ["<relevant controls>"], "azure_implementation": "<how to implement>"}}
  ],
  "compliance_score": 0,
  "zero_trust_score": 0,
  "critical_issues": [
    {{"issue": "<specific security gap>", "severity": "Critical|High|Medium", "remediation": "<specific fix>", "cve_reference": "<if applicable>"}}
  ],
  "quick_wins": [
    {{"improvement": "<specific quick security improvement>", "impact": "<expected impact>", "effort": "<Low|Medium|High>"}}
  ],
  "security_baseline": {{
    "identity": {{"score": 0, "gaps": []}},
    "network": {{"score": 0, "gaps": []}},
    "data": {{"score": 0, "gaps": []}},
    "compute": {{"score": 0, "gaps": []}}
  }},
  "reference_docs_used": [
    {{"title": "<doc title>", "url": "<url>", "relevance": "<how it was applied>"}}
  ]
}}
"""
        
        messages = [
            {"role": "system", "content": """You are a Principal Azure Security Architect with:
- 15+ years enterprise security experience
- Certifications: AZ-500, SC-100, SC-200, CISSP, CCSP
- Expertise in Zero Trust Architecture, Threat Modeling (STRIDE/DREAD), and Compliance (SOC2/HIPAA/PCI-DSS/GDPR)
- Deep knowledge of Microsoft Defender, Sentinel, and Azure Security Center
- Experience designing security for Fortune 500 companies

Your security philosophy: "Defense in Depth with Zero Trust principles - assume breach, verify explicitly, enforce least privilege."

Use the LOCAL REFERENCE DOCS provided to ground your recommendations in verified Azure Architecture Center guidance. Return only valid JSON."""},
            {"role": "user", "content": enhanced_security_prompt}
        ]
        
        try:
            self.think("Calling LLM to generate security recommendations...", "tool_call")
            response = await self._call_openai(messages)
            self.think("LLM response received. Analyzing security posture...", "observation")
            result = self._parse_security_response(response)
            
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Self-Reflection
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            services_count = len(result.get("security_services", []))
            compliance_score = result.get("compliance_score", 0)
            zero_trust_score = result.get("zero_trust_score", 0)
            
            self.think(f"Security analysis complete: {services_count} security services recommended", "observation")
            self.think(f"Compliance Score: {compliance_score}%, Zero Trust Score: {zero_trust_score}%", "observation")
            
            reflection = self.reflect(result, ["zero_trust_coverage", "compliance_completeness"])
            if reflection.get("improvements_suggested"):
                self.think(f"Security concerns: {', '.join(reflection['improvements_suggested'])}", "reflection")
            
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Inter-Agent Communication
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            critical_issues = result.get("critical_issues", [])
            if critical_issues:
                self.send_message(
                    "ArchitectureAgent", "warning",
                    f"SECURITY CRITICAL: {len(critical_issues)} critical security issues identified. Ensure architecture addresses: {', '.join([i.get('issue', str(i))[:50] if isinstance(i, dict) else str(i)[:50] for i in critical_issues[:3]])}"
                )
            
            self.send_message(
                "ValidationAgent", "insight",
                f"Security posture: Compliance={compliance_score}%, ZeroTrust={zero_trust_score}%. {services_count} security services recommended."
            )
            
            self.think("Security analysis completed successfully", "success")
            result["thinking_summary"] = self.get_thinking_summary()
            
            return result
        except Exception as e:
            logger.error(f"Error in SecurityAgent.analyze: {e}")
            self.think(f"Security analysis error: {str(e)}", "warning")
            return {
                "agent": "security",
                "error": str(e),
                "status": "error",
                "thinking_summary": self.get_thinking_summary()
            }
    
    def _parse_security_response(self, response: str) -> Dict[str, Any]:
        """Parse security recommendations from AI response"""
        default_response = {
            "security_services": [],
            "recommendations": [],
            "compliance_score": 0,
            "is_fallback": True
        }
        
        parsed = self._safe_json_parse(response, default_response)
        
        return {
            "agent": "security",
            "security_services": parsed.get("security_services", []),
            "network_security": parsed.get("network_security", []),
            "identity_management": parsed.get("identity_management", []),
            "data_protection": parsed.get("data_protection", []),
            "threat_model": parsed.get("threat_model", []),
            "compliance_requirements": parsed.get("compliance_requirements", []),
            "compliance_score": parsed.get("compliance_score", 0),
            "zero_trust_score": parsed.get("zero_trust_score", 0),
            "critical_issues": parsed.get("critical_issues", []),
            "quick_wins": parsed.get("quick_wins", []),
            "security_baseline": parsed.get("security_baseline", {}),
            "reference_docs_used": parsed.get("reference_docs_used", []),
            "status": "completed"
        }

