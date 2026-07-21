import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent, AgentTools

logger = logging.getLogger(__name__)


class ComponentExtractionAgent(BaseAgent):
    """First agent in the pipeline - extracts all components from user requirements text.
    Identifies: APIs, NFRs, Technical Requirements, Tech Stack, Business Requirements.
    Uses local azure-docs to identify Azure-specific patterns and services implied by requirements."""
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="ComponentExtractionAgent", openai_client=openai_client, agent_type="components")

    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract structured components from free-form user requirements text."""
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Chain-of-Thought reasoning
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        self.think(f"I am the {self.persona.role}. Starting deep requirements decomposition.", "reasoning")
        
        # Step 1: Initial analysis with context-aware summary
        words = requirements.split()
        key_terms = [w for w in words if w.lower() in ["api", "database", "auth", "scale", "security", "microservice", "event", "queue", "cache", "monitor", "gateway", "kubernetes", "aks", "container", "serverless", "function", "storage", "sql", "cosmos", "redis"]]
        self.think(f"Analyzing {len(requirements)} chars ({len(words)} words). Domain terms spotted: {', '.join(set(key_terms[:8])) if key_terms else 'inferring from context'}", "reasoning")
        self.think("Goal: Extract APIs, NFRs, tech stack, business requirements, data needs, and integration points", "reasoning")
        
        # Step 2: Tool usage - search Azure docs
        self.think("Searching local Azure Architecture Center docs for matching reference patterns...", "tool_call")
        component_docs = await self.use_tool(
            AgentTools.SEARCH_AZURE_DOCS,
            {
                "query": requirements,
                "domain_terms": ["architecture", "pattern", "service", "api", "database",
                               "authentication", "messaging", "integration"],
                "max_results": 5
            }
        )
        
        # Step 3: Decision making
        self.think("Structuring extraction prompt with Azure reference context. Will identify: REST APIs, GraphQL endpoints, NFRs (SLA, throughput, latency), tech stack, compliance needs...", "decision")
        
        extraction_prompt = f"""
You are an expert Requirements Analyst and Solution Architect.
Your task is to carefully read the user's requirements text and extract ALL components into structured categories.

IMPORTANT: Use the LOCAL REFERENCE DOCS below to identify Azure-specific services, patterns, and architecture styles that match the user's requirements. This helps you recommend the correct Azure services and architecture patterns.
{component_docs}

USER REQUIREMENTS TEXT:
\"\"\"{requirements}\"\"\"

Extract the following categories thoroughly:

1. **APIs**: Any REST APIs, GraphQL endpoints, webhooks, gRPC services, API integrations mentioned or implied.
2. **Non-Functional Requirements (NFRs)**: Scalability, availability, latency, throughput, SLA targets, compliance (GDPR, HIPAA, SOC2), disaster recovery RPO/RTO, data residency.
3. **Technical Requirements**: Authentication methods, database needs, messaging/queuing, caching, CI/CD, logging, monitoring, containerization, orchestration.
4. **Tech Stack**: Programming languages, frameworks, cloud services, third-party tools, SDK/libraries explicitly mentioned.
5. **Business Requirements**: Core business goals, user stories, feature requirements, workflows.
6. **Data Requirements**: Data stores, data flow patterns, data volume estimates, data formats.
7. **Integration Points**: External systems, third-party services, legacy system integrations.
8. **Resource Group Boundaries**: Identify logical separation of concerns that should map to distinct Azure Resource Groups. Look for: multi-tenant isolation, shared vs tenant-specific, frontend vs backend separation, monitoring/security as a separate concern, environment boundaries.

IMPORTANT: Extract ONLY what is in the user's requirements. Do NOT invent requirements that are not stated or implied.

Return ONLY valid JSON:
{{
  "apis": [
    {{"name": "<exact API name from requirements>", "type": "<REST|GraphQL|gRPC|WebSocket>", "description": "<what it does>", "methods": ["<HTTP methods>"]}}
  ],
  "nfrs": [
    {{"category": "<Availability|Scalability|Performance|Security|Compliance|Reliability>", "requirement": "<exact NFR from requirements>", "priority": "<Critical|High|Medium|Low>"}}
  ],
  "technical_requirements": [
    {{"area": "<Authentication|Database|Messaging|Caching|CI/CD|Monitoring|Containerization|Networking>", "requirement": "<exact tech requirement>", "details": "<specifics>"}}
  ],
  "tech_stack": [
    {{"technology": "<exact technology name>", "category": "<language|framework|cloud_service|tool|library>", "purpose": "<why it is used>"}}
  ],
  "business_requirements": [
    {{"requirement": "<business goal from requirements>", "priority": "<High|Medium|Low>", "user_story": "<user story if applicable>"}}
  ],
  "data_requirements": [
    {{"type": "<Relational|NoSQL|Graph|TimeSeries|Blob|Queue>", "volume": "<High|Medium|Low>", "description": "<data description>"}}
  ],
  "integration_points": [
    {{"system": "<external system name>", "type": "<External API|Legacy System|Third-party SaaS|On-premises>", "protocol": "<REST|SOAP|gRPC|AMQP|HTTPS>"}}
  ],
  "resource_group_hints": [
    {{"name": "<suggested rg name, e.g. rg-frontend, rg-shared-backend, rg-monitoring>", "purpose": "<what goes here>", "services_hint": ["<service categories or names that belong>"]}}
  ],
  "summary": {{
    "total_apis": 0,
    "total_nfrs": 0,
    "total_technical_reqs": 0,
    "complexity_level": "<High|Medium|Low>",
    "recommended_architecture_pattern": "<pattern based on actual requirements>",
    "matched_azure_patterns": ["<patterns from local docs that match>"],
    "suggested_rg_count": 0
  }}
}}
"""

        messages = [
            {"role": "system", "content": "You are an expert Requirements Analyst with deep Azure Architecture Center knowledge. Extract ALL components from user requirements text. Use the LOCAL REFERENCE DOCS to identify matching Azure services and architecture patterns. Be thorough - do not miss any implied requirements. Return only valid JSON."},
            {"role": "user", "content": extraction_prompt}
        ]

        try:
            self.think("Sending requirements to Azure OpenAI for deep component extraction (APIs, NFRs, tech stack, integrations)...", "tool_call")
            response = await self._call_openai(messages)
            self.think("LLM response received. Parsing structured JSON into component categories...", "observation")
            result = self._parse_component_response(response)
            
            # Add detailed thinking about what was found
            apis = result.get("apis", [])
            nfrs = result.get("nfrs", [])
            tech_stack = result.get("tech_stack", [])
            integration_points = result.get("integration_points", [])
            complexity = result.get("summary", {}).get("complexity_level", "N/A")
            pattern = result.get("summary", {}).get("recommended_architecture_pattern", "N/A")
            
            if apis:
                api_names = [a.get("name", "unnamed") for a in apis[:4]]
                self.think(f"Identified {len(apis)} API endpoints: {', '.join(api_names)}{'...' if len(apis) > 4 else ''}", "observation")
            if nfrs:
                critical_nfrs = [n.get("category", "?") for n in nfrs if n.get("priority") in ("Critical", "High")][:3]
                self.think(f"Found {len(nfrs)} NFRs. Critical/High priority: {', '.join(critical_nfrs) if critical_nfrs else 'none'}", "observation")
            if tech_stack:
                techs = [t.get("technology", "?") for t in tech_stack[:4]]
                self.think(f"Tech stack detected: {', '.join(techs)}", "observation")
            if integration_points:
                self.think(f"External integrations: {len(integration_points)} systems to connect with", "observation")
            self.think(f"Complexity assessment: {complexity}. Recommending {pattern} architecture pattern.", "decision")
            
            # Log extracted components summary
            logger.info("=" * 70)
            logger.info("ðŸ“‹ COMPONENT EXTRACTION AGENT - RESULTS SUMMARY")
            logger.info("=" * 70)
            logger.info(f"  APIs identified:              {len(result.get('apis', []))}")
            logger.info(f"  NFRs identified:              {len(result.get('nfrs', []))}")
            logger.info(f"  Technical Requirements:       {len(result.get('technical_requirements', []))}")
            logger.info(f"  Tech Stack items:             {len(result.get('tech_stack', []))}")
            logger.info(f"  Business Requirements:        {len(result.get('business_requirements', []))}")
            logger.info(f"  Data Requirements:            {len(result.get('data_requirements', []))}")
            logger.info(f"  Integration Points:           {len(result.get('integration_points', []))}")
            logger.info(f"  Complexity Level:              {result.get('summary', {}).get('complexity_level', 'N/A')}")
            logger.info(f"  Recommended Pattern:           {result.get('summary', {}).get('recommended_architecture_pattern', 'N/A')}")
            logger.info("=" * 70)

            # Also print to console for visibility
            print("\n" + "=" * 70)
            print("ðŸ“‹ COMPONENT EXTRACTION AGENT - RESULTS")
            print("=" * 70)
            for api in result.get("apis", []):
                print(f"  ðŸ”Œ API: {api.get('name', 'Unknown')} ({api.get('type', 'REST')}) - {api.get('description', '')}")
            for nfr in result.get("nfrs", []):
                print(f"  ðŸ“Š NFR [{nfr.get('priority', 'Normal')}]: {nfr.get('category', '')} - {nfr.get('requirement', '')}")
            for tr in result.get("technical_requirements", []):
                print(f"  âš™ï¸  Tech Req: {tr.get('area', '')} - {tr.get('requirement', '')}")
            for ts in result.get("tech_stack", []):
                print(f"  ðŸ› ï¸  Tech Stack: {ts.get('technology', '')} ({ts.get('category', '')}) - {ts.get('purpose', '')}")
            for bp in result.get("integration_points", []):
                print(f"  ðŸ”— Integration: {bp.get('system', '')} ({bp.get('type', '')}) - {bp.get('protocol', '')}")
            print("=" * 70 + "\n")

            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Self-Reflection
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            reflection = self.reflect(result, ["completeness", "api_coverage", "nfr_coverage"])
            if reflection.get("improvements_suggested"):
                self.think(f"Reflection notes: {', '.join(reflection['improvements_suggested'])}", "reflection")
            
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # AGENTIC BEHAVIOR: Inter-Agent Communication
            # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
            # Send insights to downstream agents
            api_count = len(result.get("apis", []))
            nfr_count = len(result.get("nfrs", []))
            complexity = result.get("summary", {}).get("complexity_level", "Medium")
            
            self.send_message(
                "SecurityAgent", "insight",
                f"Extracted {api_count} APIs and {nfr_count} NFRs. Complexity: {complexity}. Pay attention to authentication NFRs."
            )
            self.send_message(
                "ArchitectureAgent", "recommendation",
                f"Recommended pattern: {result.get('summary', {}).get('recommended_architecture_pattern', 'N/A')}. Consider {api_count} APIs for service design."
            )
            
            self.think(f"Completed extraction: {api_count} APIs, {nfr_count} NFRs, complexity={complexity}", "success")
            
            # Add thinking summary to result for frontend display
            result["thinking_summary"] = self.get_thinking_summary()

            return result
        except Exception as e:
            logger.error(f"Error in ComponentExtractionAgent.analyze: {e}")
            self.think(f"Error during extraction: {str(e)}", "warning")
            return {
                "agent": "component_extraction",
                "error": str(e),
                "status": "error",
                "apis": [], "nfrs": [], "technical_requirements": [],
                "tech_stack": [], "business_requirements": [],
                "data_requirements": [], "integration_points": [],
                "summary": {},
                "thinking_summary": self.get_thinking_summary()
            }

    def _parse_component_response(self, response: str) -> Dict[str, Any]:
        """Parse component extraction from AI response"""
        default_response = {
            "apis": [], "nfrs": [], "technical_requirements": [],
            "tech_stack": [], "business_requirements": [],
            "data_requirements": [], "integration_points": [],
            "summary": {}, "is_fallback": True
        }
        parsed = self._safe_json_parse(response, default_response)
        parsed["agent"] = "component_extraction"
        parsed["status"] = "completed"
        return parsed


