import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AzureArchitectureReferenceAgent(BaseAgent):
    """Principal Azure Architecture Center Expert - Maps requirements to proven Azure reference architectures.
    Uses the local azure-docs folder as the primary knowledge source with a built-in catalog fallback.
    References: https://learn.microsoft.com/en-us/azure/architecture/browse/
    Identifies applicable reference architectures, design patterns, and best-practice diagrams.
    
    EXPERTISE DOMAINS:
    - Azure Architecture Center (100+ reference architectures)
    - Cloud Design Patterns (Reliability, Performance, Security)
    - Industry-Specific Patterns (Healthcare, Finance, Retail, Manufacturing)
    - Well-Architected Framework Assessment & Implementation
    - Technology Workloads (Web, AI/ML, IoT, Data, DevOps)
    - Hybrid & Multi-cloud Integration Patterns
    """

    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="AzureArchitectureReferenceAgent", openai_client=openai_client, agent_type="references")
        logger.info(f"AzureArchitectureReferenceAgent initialized with {len(self.scanner._index)} local doc entries")

    # Comprehensive catalog of Azure Architecture Center reference architectures
    AZURE_REFERENCE_ARCHITECTURES = {
        # Web Applications
        "basic-web-app": {
            "title": "Basic web application",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/web-apps/app-service/architectures/basic-web-app",
            "tags": ["web", "app service", "sql", "cdn", "basic"],
            "services": ["Azure App Service", "Azure SQL Database", "Azure CDN", "Azure DNS"]
        },
        "scalable-web-app": {
            "title": "Baseline highly available zone-redundant web application",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/web-apps/app-service/architectures/baseline-zone-redundant",
            "tags": ["web", "scalable", "redis", "autoscaling", "zone-redundant", "high availability"],
            "services": ["Azure App Service", "Azure SQL Database", "Azure Cache for Redis", "Azure CDN", "Azure Front Door"]
        },
        "multi-region-web-app": {
            "title": "Reliable Web App pattern - multi-region deployment",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/web-apps/guides/enterprise-app-patterns/reliable-web-app/dotnet/guidance",
            "tags": ["web", "multi-region", "high availability", "traffic manager", "geo-redundancy", "reliable"],
            "services": ["Azure Traffic Manager", "Azure App Service", "Azure SQL Database", "Azure Front Door"]
        },

        # Microservices
        "microservices-aks": {
            "title": "Microservices architecture on AKS",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-microservices/aks-microservices",
            "tags": ["microservices", "kubernetes", "aks", "containers", "docker"],
            "services": ["Azure Kubernetes Service", "Azure Container Registry", "Azure Monitor", "Azure Key Vault"]
        },
        "microservices-service-fabric": {
            "title": "Microservices architecture design",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/microservices/design/index",
            "tags": ["microservices", "service fabric", "stateful", "design"],
            "services": ["Azure Service Fabric", "Azure SQL Database", "Azure API Management"]
        },

        # Serverless
        "serverless-web-app": {
            "title": "Serverless computing on Azure",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/serverless/guide/serverless-start-here",
            "tags": ["serverless", "functions", "static", "api", "spa", "logic apps"],
            "services": ["Azure Functions", "Azure Blob Storage", "Azure CDN", "Azure Cosmos DB", "Azure Logic Apps"]
        },
        "serverless-event-processing": {
            "title": "Event-driven architecture style",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven",
            "tags": ["serverless", "event-driven", "event hub", "functions", "stream", "messaging"],
            "services": ["Azure Functions", "Azure Event Hubs", "Azure Cosmos DB", "Azure Stream Analytics"]
        },

        # Data & Analytics
        "modern-data-warehouse": {
            "title": "Data warehousing and analytics",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/example-scenario/data/data-warehouse",
            "tags": ["data warehouse", "synapse", "analytics", "etl", "data lake", "big data"],
            "services": ["Azure Synapse Analytics", "Azure Data Lake Storage", "Azure Data Factory", "Power BI"]
        },
        "real-time-analytics": {
            "title": "Real-time analytics on big data",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/databases/architecture/real-time-analytics",
            "tags": ["real-time", "streaming", "analytics", "event hub", "big data"],
            "services": ["Azure Event Hubs", "Azure Stream Analytics", "Azure Cosmos DB", "Power BI"]
        },
        "lambda-architecture": {
            "title": "Big data analytics with Azure Data Explorer",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/solution-ideas/articles/big-data-azure-data-explorer",
            "tags": ["lambda", "big data", "batch", "speed", "data explorer"],
            "services": ["Azure Data Explorer", "Azure Event Hubs", "Azure Data Lake Storage"]
        },

        # IoT
        "iot-reference-architecture": {
            "title": "Azure IoT architecture",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/iot/iot-architecture-iot-edge-vision",
            "tags": ["iot", "devices", "telemetry", "edge", "hub"],
            "services": ["Azure IoT Hub", "Azure IoT Edge", "Azure Stream Analytics", "Azure Cosmos DB"]
        },
        "iot-edge": {
            "title": "IoT Edge architecture",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/iot/iot-architecture-iot-edge-vision",
            "tags": ["iot", "edge", "ai", "ml", "vision"],
            "services": ["Azure IoT Edge", "Azure IoT Hub", "Azure Machine Learning", "Azure Storage"]
        },

        # AI & ML
        "ml-operations": {
            "title": "MLOps with Azure Machine Learning",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/mlops-technical-paper",
            "tags": ["ml", "mlops", "machine learning", "ai", "training", "model"],
            "services": ["Azure Machine Learning", "Azure DevOps", "Azure Container Registry", "Azure Kubernetes Service"]
        },
        "conversational-bot": {
            "title": "Enterprise-grade conversational bot",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/conversational-bot",
            "tags": ["bot", "conversational", "ai", "nlp", "chatbot", "openai"],
            "services": ["Azure Bot Service", "Azure OpenAI Service", "Azure Cognitive Services", "Azure Cosmos DB"]
        },
        "openai-chat": {
            "title": "Baseline OpenAI end-to-end chat reference architecture",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-openai-e2e-chat",
            "tags": ["openai", "chat", "gpt", "rag", "ai", "generative"],
            "services": ["Azure OpenAI Service", "Azure AI Search", "Azure Cosmos DB", "Azure App Service"]
        },

        # Networking & Security
        "hub-spoke-network": {
            "title": "Hub-spoke network topology",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/networking/architecture/hub-spoke",
            "tags": ["hub", "spoke", "network", "vnet", "peering", "firewall"],
            "services": ["Azure Virtual Network", "Azure Firewall", "Azure VPN Gateway", "Azure Bastion"]
        },
        "dmz-between-azure-onpremises": {
            "title": "Network DMZ between Azure and on-premises",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/networking/guide/nva-ha",
            "tags": ["dmz", "hybrid", "on-premises", "nva", "firewall", "vpn"],
            "services": ["Azure Firewall", "Azure VPN Gateway", "Azure ExpressRoute", "Network Security Groups"]
        },
        "zero-trust-network": {
            "title": "Zero Trust network for web applications",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/example-scenario/gateway/application-gateway-before-azure-firewall",
            "tags": ["zero trust", "security", "waf", "firewall", "network", "identity"],
            "services": ["Azure Application Gateway", "Azure Firewall", "Azure Active Directory", "Azure Front Door"]
        },

        # Identity
        "identity-management": {
            "title": "Azure AD identity management",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/identity/",
            "tags": ["identity", "azure ad", "sso", "authentication", "authorization", "entra"],
            "services": ["Azure Active Directory", "Azure AD B2C", "Azure Key Vault"]
        },
        "hybrid-identity": {
            "title": "Hybrid identity with Azure AD",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/identity/azure-ad",
            "tags": ["hybrid", "identity", "on-premises", "ad connect", "sync"],
            "services": ["Azure Active Directory", "Azure AD Connect", "Azure AD DS"]
        },

        # DevOps & CI/CD
        "ci-cd-pipeline": {
            "title": "CI/CD for Azure Web Apps with Azure Pipelines",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/guide/devops/devops-start-here",
            "tags": ["ci/cd", "devops", "pipeline", "deployment", "automation"],
            "services": ["Azure DevOps", "Azure App Service", "Azure Container Registry", "Azure Key Vault"]
        },
        "gitops-aks": {
            "title": "GitOps for AKS",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/example-scenario/gitops-aks/gitops-blueprint-aks",
            "tags": ["gitops", "aks", "kubernetes", "flux", "ci/cd"],
            "services": ["Azure Kubernetes Service", "Azure Container Registry", "Azure DevOps", "Azure Policy"]
        },

        # E-Commerce
        "ecommerce-architecture": {
            "title": "E-commerce website running in secured App Service Environment",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/web-apps/idea/ecommerce-website-running-in-secured-ase",
            "tags": ["ecommerce", "commerce", "shopping", "cart", "payment", "retail"],
            "services": ["Azure App Service", "Azure SQL Database", "Azure Cache for Redis", "Azure Search"]
        },

        # Healthcare
        "health-data-architecture": {
            "title": "Health data solutions on Azure",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/healthcare",
            "tags": ["health", "healthcare", "hipaa", "fhir", "medical", "hl7"],
            "services": ["Azure Health Data Services", "Azure Data Lake", "Azure Synapse Analytics", "Power BI"]
        },

        # Event-Driven
        "event-driven-architecture": {
            "title": "Event-driven architecture",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven",
            "tags": ["event-driven", "event grid", "service bus", "messaging", "async", "queue"],
            "services": ["Azure Event Grid", "Azure Service Bus", "Azure Functions", "Azure Logic Apps"]
        },
        "cqrs-pattern": {
            "title": "CQRS pattern",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs",
            "tags": ["cqrs", "command query", "event sourcing", "read write", "separation"],
            "services": ["Azure Cosmos DB", "Azure Service Bus", "Azure Functions", "Azure SQL Database"]
        },

        # API Management
        "api-management-architecture": {
            "title": "API Management landing zone accelerator",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/example-scenario/integration/app-gateway-internal-api-management-function",
            "tags": ["api", "api management", "gateway", "rest", "graphql", "apim"],
            "services": ["Azure API Management", "Azure Application Gateway", "Azure Functions", "Azure Key Vault"]
        },

        # Disaster Recovery
        "disaster-recovery": {
            "title": "Disaster recovery for Azure applications",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/guide/disaster-recovery/disaster-recovery-overview",
            "tags": ["disaster recovery", "dr", "backup", "site recovery", "bcdr", "rpo", "rto"],
            "services": ["Azure Site Recovery", "Azure Backup", "Azure Traffic Manager", "Azure Storage"]
        },

        # Monitoring
        "monitoring-architecture": {
            "title": "Monitoring best practices for cloud applications",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/best-practices/monitoring",
            "tags": ["monitoring", "observability", "logging", "alerts", "metrics", "traces"],
            "services": ["Azure Monitor", "Azure Application Insights", "Azure Log Analytics", "Azure Alerts"]
        },

        # Multi-tenant / SaaS
        "multitenant-saas": {
            "title": "Multitenant SaaS on Azure",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/overview",
            "tags": ["multi-tenant", "saas", "tenant", "isolation", "shared"],
            "services": ["Azure App Service", "Azure SQL Database", "Azure Active Directory", "Azure Front Door"]
        },

        # Hybrid
        "hybrid-architecture": {
            "title": "Azure hybrid architecture design",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/hybrid/hybrid-start-here",
            "tags": ["hybrid", "on-premises", "arc", "expressroute", "vpn"],
            "services": ["Azure Arc", "Azure ExpressRoute", "Azure VPN Gateway", "Azure Stack"]
        },
        
        # Financial Services
        "financial-services-architecture": {
            "title": "Azure for Financial Services",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/finance",
            "tags": ["finance", "banking", "payment", "trading", "fintech", "pci-dss", "sox"],
            "services": ["Azure Kubernetes Service", "Azure SQL Database", "Azure Key Vault", "Azure Front Door", "Azure DDoS Protection"]
        },
        "payment-processing": {
            "title": "Payment processing architecture",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/finance",
            "tags": ["payment", "pci", "secure", "transaction", "fintech", "card"],
            "services": ["Azure API Management", "Azure Functions", "Azure SQL Database", "Azure Key Vault", "Azure DDoS Protection"]
        },
        
        # Retail & E-commerce
        "retail-architecture": {
            "title": "Azure for Retail industry",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/retail",
            "tags": ["retail", "ecommerce", "inventory", "pos", "omnichannel", "customer"],
            "services": ["Azure Cosmos DB", "Azure Cognitive Search", "Azure Functions", "Azure Cache for Redis", "Power BI"]
        },
        "recommendation-engine": {
            "title": "Personalization and recommendations",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/solution-ideas/articles/personalization-using-cosmos-db",
            "tags": ["recommendation", "personalization", "ai", "retail", "ecommerce", "ml"],
            "services": ["Azure Machine Learning", "Azure Cosmos DB", "Azure Databricks", "Azure Functions"]
        },
        
        # Manufacturing & IoT
        "manufacturing-architecture": {
            "title": "Azure for Manufacturing",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/manufacturing",
            "tags": ["manufacturing", "industry 4.0", "iot", "predictive maintenance", "scada", "opc-ua"],
            "services": ["Azure IoT Hub", "Azure Digital Twins", "Azure Time Series Insights", "Azure Machine Learning", "Power BI"]
        },
        "predictive-maintenance": {
            "title": "Predictive maintenance solution",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/solution-ideas/articles/predictive-maintenance",
            "tags": ["predictive", "maintenance", "iot", "ml", "manufacturing", "sensor"],
            "services": ["Azure IoT Hub", "Azure Machine Learning", "Azure Stream Analytics", "Azure Cosmos DB"]
        },
        
        # Gaming
        "gaming-architecture": {
            "title": "Gaming using Azure Cosmos DB",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/gaming/",
            "tags": ["gaming", "game", "leaderboard", "multiplayer", "matchmaking", "real-time"],
            "services": ["Azure PlayFab", "Azure Cosmos DB", "Azure SignalR Service", "Azure Functions", "Azure CDN"]
        },
        
        # Media & Entertainment
        "media-streaming": {
            "title": "Media streaming using Azure Media Services",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/media/",
            "tags": ["media", "streaming", "video", "transcoding", "cdn", "vod"],
            "services": ["Azure Media Services", "Azure CDN", "Azure Blob Storage", "Azure Front Door"]
        },
        
        # Government & Public Sector
        "government-architecture": {
            "title": "Azure for Government",
            "url": "https://learn.microsoft.com/en-us/azure/azure-government/",
            "tags": ["government", "fedramp", "dod", "compliance", "public sector", "sovereign"],
            "services": ["Azure Government", "Azure Policy", "Azure Blueprints", "Azure Key Vault", "Azure Monitor"]
        },
        
        # Energy & Utilities
        "energy-architecture": {
            "title": "Azure for Energy & Utilities",
            "url": "https://learn.microsoft.com/en-us/azure/architecture/industries/energy",
            "tags": ["energy", "utilities", "smart grid", "renewable", "scada", "oil gas"],
            "services": ["Azure IoT Hub", "Azure Digital Twins", "Azure Time Series Insights", "Azure Maps", "Power BI"]
        },
    }

    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Map extracted components to Azure Architecture Center reference architectures.
        Uses the local azure-docs folder as the primary source, with built-in catalog fallback."""
        if context is None:
            context = {}

        components = context.get("component_extraction", {})

        # â”€â”€ Step 1: Search local azure-docs for relevant reference architectures â”€â”€
        local_results = self.scanner.search_by_components(components, max_results=15)
        # Also search by the raw requirements text for broader coverage
        text_results = self.scanner.search(requirements, max_results=10)
        
        # Merge and deduplicate results (prefer higher score)
        seen_paths = {}
        for entry in local_results + text_results:
            path = entry.get("doc_path", "")
            if path not in seen_paths or entry.get("_score", 0) > seen_paths[path].get("_score", 0):
                seen_paths[path] = entry
        
        merged_results = sorted(seen_paths.values(), key=lambda x: x.get("_score", 0), reverse=True)[:12]

        # â”€â”€ Step 2: Build rich context from top local doc matches â”€â”€
        local_docs_context = []
        for entry in merged_results[:8]:
            prompt_entry = self.scanner.get_entry_for_prompt(entry, include_content=True)
            local_docs_context.append(prompt_entry)

        # â”€â”€ Step 3: Build the LLM prompt with local docs context â”€â”€
        local_docs_section = ""
        if local_docs_context:
            local_docs_section = "\n\nLOCAL AZURE ARCHITECTURE CENTER REFERENCE DOCS (from azure-docs folder):\n"
            for i, doc in enumerate(local_docs_context, 1):
                diagrams_info = f" | Diagrams: {len(doc.get('diagrams', []))} available" if doc.get('diagrams') else ""
                local_docs_section += f"\n--- Reference {i} ---\n"
                local_docs_section += f"Title: {doc.get('title', 'N/A')}\n"
                local_docs_section += f"URL: {doc.get('url', 'N/A')}\n"
                local_docs_section += f"Category: {doc.get('category', 'N/A')}\n"
                local_docs_section += f"Products: {', '.join(doc.get('products', []))}\n"
                local_docs_section += f"Summary: {doc.get('summary', 'N/A')}\n"
                local_docs_section += f"Local Path: {doc.get('local_path', 'N/A')}{diagrams_info}\n"
                if doc.get("content_excerpt"):
                    # Truncate content for the prompt
                    excerpt = doc["content_excerpt"][:1500]
                    local_docs_section += f"Content Excerpt:\n{excerpt}\n"

        # â”€â”€ Step 4: Also include static catalog entries for fallback â”€â”€
        static_catalog_section = "\n\nSTATIC REFERENCE CATALOG (built-in):\n"
        for ref_id, ref_data in list(self.AZURE_REFERENCE_ARCHITECTURES.items())[:15]:
            static_catalog_section += f"  - {ref_id}: {ref_data['title']} â†’ {ref_data['url']}\n"
            static_catalog_section += f"    Tags: {', '.join(ref_data['tags'])} | Services: {', '.join(ref_data['services'])}\n"

        # â”€â”€ Step 5: Get Draw.io reference patterns for connection guidance â”€â”€
        drawio_patterns = self._get_drawio_reference_context(requirements, max_references=3)

        reference_prompt = f"""
You are an Azure Architecture Center Expert. Your job is to analyze the extracted components and map them to the most relevant Azure Architecture Center reference architectures.

IMPORTANT: Use the LOCAL REFERENCE DOCS and DRAWIO REFERENCE PATTERNS provided below as your PRIMARY sources. These contain actual Azure Architecture Center content, diagrams, connection patterns, and layout guidance.

EXTRACTED COMPONENTS:
- APIs: {json.dumps(components.get('apis', []), indent=2)}
- NFRs: {json.dumps(components.get('nfrs', []), indent=2)}
- Technical Requirements: {json.dumps(components.get('technical_requirements', []), indent=2)}
- Tech Stack: {json.dumps(components.get('tech_stack', []), indent=2)}
- Business Requirements: {json.dumps(components.get('business_requirements', []), indent=2)}
- Data Requirements: {json.dumps(components.get('data_requirements', []), indent=2)}
- Integration Points: {json.dumps(components.get('integration_points', []), indent=2)}

ORIGINAL USER REQUIREMENTS: {requirements}
{local_docs_section}
{drawio_patterns}
{static_catalog_section}

Based on these components AND the local reference docs, identify the MOST RELEVANT Azure Architecture Center reference architectures.
For each reference architecture, explain WHY it is relevant to the user's specific components.
PRIORITIZE references from the LOCAL REFERENCE DOCS since they contain verified content and diagrams.
Include the local_path and diagram information when available.

Return ONLY valid JSON:
{{
  "matched_reference_architectures": [
    {{
      "id": "reference-id",
      "title": "Reference Architecture Title",
      "url": "https://learn.microsoft.com/en-us/azure/architecture/...",
      "local_path": "path/to/doc.yml",
      "diagrams": ["path/to/diagram.svg"],
      "relevance_score": 95,
      "why_relevant": "Matches user's requirement for X because...",
      "applicable_components": ["Component A", "Component B"],
      "content_highlights": "Key architectural guidance from this reference..."
    }}
  ],
  "recommended_architecture_pattern": "Microservices with Event-Driven",
  "recommended_azure_services": [
    {{"service": "Azure Kubernetes Service", "purpose": "Container orchestration for microservices", "reference_architecture": "microservices-aks"}}
  ],
  "design_decisions": [
    {{"decision": "Use AKS for container orchestration", "rationale": "User requires Kubernetes-based deployment", "reference": "microservices-aks"}}
  ],
  "architecture_guidance": {{
    "primary_pattern": "Microservices",
    "secondary_patterns": ["Event-Driven", "CQRS"],
    "key_principles": ["Loose coupling", "Independent deployability", "Resilience"]
  }}
}}
"""

        messages = [
            {"role": "system", "content": """You are a Principal Azure Architecture Center Expert with:
- 15+ years enterprise architecture experience across industries
- AZ-305, AZ-104 certified, Microsoft Azure MVP, Cloud Solution Architect Partner
- Author of 50+ Azure Architecture Center reference architecture contributions
- Deep expertise mapping business requirements to proven Azure patterns
- Specialized in: Healthcare (HIPAA/FHIR), Finance (PCI-DSS/SOX), Retail, Manufacturing, Government (FedRAMP)

Your methodology:
1. Analyze extracted components thoroughly
2. Match to PROVEN reference architectures (prefer local azure-docs, they're verified)
3. Explain WHY each reference is relevant to the specific requirements
4. Recommend Azure services with clear purpose for each

You have access to LOCAL azure-docs content â€” prioritize these verified references over generic suggestions.
Return only valid JSON."""},
            {"role": "user", "content": reference_prompt}
        ]

        try:
            response = await self._call_openai(messages)
            result = self._parse_reference_response(response, components)

            # Cross-reference with both our built-in catalog AND local docs
            result = self._cross_reference_catalog(result, components)

            # Enrich result with local docs metadata
            result["local_docs_indexed"] = len(self.scanner._index)
            result["local_docs_matched"] = len(merged_results)
            result["local_docs_with_diagrams"] = sum(1 for r in merged_results if r.get("diagrams"))

            # LOG all referenced diagrams prominently
            self._log_referenced_architectures(result)

            return result
        except Exception as e:
            logger.error(f"Error in AzureArchitectureReferenceAgent.analyze: {e}")
            return {
                "agent": "azure_architecture_reference",
                "error": str(e),
                "status": "error",
                "matched_reference_architectures": [],
                "recommended_azure_services": [],
                "design_decisions": [],
                "local_docs_indexed": len(self.scanner._index),
                "local_docs_matched": 0
            }

    def _parse_reference_response(self, response: str, components: Dict) -> Dict[str, Any]:
        """Parse reference architecture matching from AI response"""
        default_response = {
            "matched_reference_architectures": [],
            "recommended_azure_services": [],
            "design_decisions": [],
            "architecture_guidance": {},
            "is_fallback": True
        }
        parsed = self._safe_json_parse(response, default_response)
        parsed["agent"] = "azure_architecture_reference"
        parsed["status"] = "completed"
        return parsed

    def _cross_reference_catalog(self, ai_result: Dict, components: Dict) -> Dict:
        """Cross-reference AI suggestions with both the built-in catalog AND local azure-docs scanner.
        Adds matching entries the AI might have missed from either source."""
        
        # Build a full text blob from all components for phrase matching
        all_text_parts = []
        component_sections = ["apis", "nfrs", "technical_requirements", "tech_stack", 
                            "business_requirements", "data_requirements", "integration_points"]
        
        for section in component_sections:
            items = components.get(section, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        for val in item.values():
                            if isinstance(val, str):
                                all_text_parts.append(val.lower())
                    elif isinstance(item, str):
                        all_text_parts.append(item.lower())
            elif isinstance(items, str):
                all_text_parts.append(items.lower())
        
        full_text = " ".join(all_text_parts)

        # â”€â”€ Part A: Cross-reference with static catalog â”€â”€
        existing_urls = {ref.get("url", "") for ref in ai_result.get("matched_reference_architectures", [])}
        existing_ids = {ref.get("id", "") for ref in ai_result.get("matched_reference_architectures", [])}
        catalog_matches = []

        for ref_id, ref_data in self.AZURE_REFERENCE_ARCHITECTURES.items():
            if ref_id in existing_ids or ref_data["url"] in existing_urls:
                continue
            matched_tags = [tag for tag in ref_data["tags"] if tag in full_text]
            matched_services = [svc for svc in ref_data["services"] if svc.lower() in full_text]
            
            tag_matches = len(matched_tags) + len(matched_services)
            if tag_matches >= 2:
                match_details = matched_tags + [s for s in matched_services]
                catalog_matches.append({
                    "id": ref_id,
                    "title": ref_data["title"],
                    "url": ref_data["url"],
                    "relevance_score": min(tag_matches * 20, 80),
                    "why_relevant": f"Matched {tag_matches} component phrases: {', '.join(match_details[:6])}",
                    "applicable_components": ref_data["services"],
                    "source": "static_catalog"
                })

        catalog_matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # â”€â”€ Part B: Cross-reference with local docs scanner â”€â”€
        local_matches = self.scanner.search_by_components(components, max_results=8)
        local_additions = []
        
        for entry in local_matches:
            url = entry.get("url", "")
            doc_path = entry.get("doc_path", "")
            # Skip if already in AI results (match by URL or path)
            if url in existing_urls:
                continue
            already_present = False
            for ref in ai_result.get("matched_reference_architectures", []):
                if ref.get("local_path") == doc_path:
                    already_present = True
                    break
            if already_present:
                continue
                
            local_additions.append({
                "id": doc_path.replace("/", "-").replace(".yml", "").replace(".md", ""),
                "title": entry.get("title", ""),
                "url": url,
                "local_path": doc_path,
                "diagrams": entry.get("diagrams", []),
                "relevance_score": min(int(entry.get("_score", 0)), 90),
                "why_relevant": f"Local docs match â€” Category: {entry.get('category', 'N/A')}, Products: {', '.join(entry.get('products', [])[:5])}",
                "applicable_components": entry.get("products", []),
                "content_highlights": entry.get("summary", ""),
                "source": "local_azure_docs"
            })

        # Merge: add up to 3 static catalog + 4 local doc matches
        ai_result.setdefault("matched_reference_architectures", []).extend(catalog_matches[:3])
        ai_result["matched_reference_architectures"].extend(local_additions[:4])
        ai_result["catalog_matches_added"] = len(catalog_matches[:3])
        ai_result["local_docs_matches_added"] = len(local_additions[:4])

        return ai_result

    def _log_referenced_architectures(self, result: Dict):
        """Log all referenced Azure Architecture Center diagrams prominently, including local docs info."""
        refs = result.get("matched_reference_architectures", [])
        local_indexed = result.get("local_docs_indexed", 0)
        local_matched = result.get("local_docs_matched", 0)
        local_with_diagrams = result.get("local_docs_with_diagrams", 0)
        
        logger.info("\n" + "=" * 80)
        logger.info("ðŸ›ï¸  AZURE ARCHITECTURE CENTER - REFERENCED DIAGRAMS")
        logger.info("=" * 80)
        logger.info(f"  Source: https://learn.microsoft.com/en-us/azure/architecture/browse/")
        logger.info(f"  Local Docs Index: {local_indexed} entries | Matched: {local_matched} | With Diagrams: {local_with_diagrams}")
        logger.info(f"  Total reference architectures matched: {len(refs)}")
        logger.info("-" * 80)
        
        print("\n" + "=" * 80)
        print("ðŸ›ï¸  AZURE ARCHITECTURE CENTER - REFERENCED DIAGRAMS")
        print("=" * 80)
        print(f"  Source: https://learn.microsoft.com/en-us/azure/architecture/browse/")
        print(f"  Local Docs Index: {local_indexed} entries | Matched: {local_matched} | With Diagrams: {local_with_diagrams}")
        print(f"  Total reference architectures matched: {len(refs)}")
        print("-" * 80)

        for i, ref in enumerate(refs, 1):
            title = ref.get("title", "Unknown")
            url = ref.get("url", "N/A")
            score = ref.get("relevance_score", 0)
            why = ref.get("why_relevant", "")
            source = ref.get("source", "ai_analysis")
            local_path = ref.get("local_path", "")
            diagrams = ref.get("diagrams", [])
            content_highlights = ref.get("content_highlights", "")
            
            log_line = f"  [{i}] {title}"
            logger.info(log_line)
            logger.info(f"      URL:       {url}")
            logger.info(f"      Relevance: {score}%  |  Source: {source}")
            if local_path:
                logger.info(f"      Local:     {local_path}")
            if diagrams:
                logger.info(f"      Diagrams:  {len(diagrams)} - {', '.join(diagrams[:3])}")
            logger.info(f"      Reason:    {why}")
            if content_highlights:
                logger.info(f"      Guidance:  {content_highlights[:150]}")
            logger.info("")
            
            print(f"  [{i}] ðŸ“ {title}")
            print(f"      ðŸ”— URL:       {url}")
            print(f"      ðŸ“Š Relevance: {score}%  |  Source: {source}")
            if local_path:
                print(f"      ðŸ“ Local:     {local_path}")
            if diagrams:
                print(f"      ðŸ–¼ï¸  Diagrams:  {len(diagrams)} available â€” {', '.join(diagrams[:3])}")
            print(f"      ðŸ’¡ Reason:    {why}")
            if content_highlights:
                print(f"      ðŸ“– Guidance:  {content_highlights[:150]}")
            print()

        # Log recommended services from reference architectures
        recommended = result.get("recommended_azure_services", [])
        if recommended:
            logger.info("-" * 80)
            logger.info("  RECOMMENDED AZURE SERVICES (from reference architectures):")
            print("-" * 80)
            print("  RECOMMENDED AZURE SERVICES (from reference architectures):")
            for svc in recommended:
                svc_name = svc.get("service", "Unknown")
                purpose = svc.get("purpose", "")
                ref_arch = svc.get("reference_architecture", "")
                logger.info(f"    â€¢ {svc_name}: {purpose} (ref: {ref_arch})")
                print(f"    â€¢ {svc_name}: {purpose} (ref: {ref_arch})")

        # Log design decisions
        decisions = result.get("design_decisions", [])
        if decisions:
            logger.info("-" * 80)
            logger.info("  KEY DESIGN DECISIONS:")
            print("-" * 80)
            print("  KEY DESIGN DECISIONS:")
            for dec in decisions:
                logger.info(f"    âœ“ {dec.get('decision', '')} â€” {dec.get('rationale', '')}")
                print(f"    âœ“ {dec.get('decision', '')} â€” {dec.get('rationale', '')}")

        logger.info("=" * 80 + "\n")
        print("=" * 80 + "\n")


