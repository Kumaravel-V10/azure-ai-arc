import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
import logging
from pathlib import Path
from config import azure_openai_config, agent_config

# Import accuracy enhancements for improved service detection
try:
    from accuracy_enhancements import get_service_detector, AZURE_SERVICE_CATALOG
    ACCURACY_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    ACCURACY_ENHANCEMENTS_AVAILABLE = False
    def get_service_detector(): return None
    AZURE_SERVICE_CATALOG = {}

logger = logging.getLogger(__name__)

class AzureOpenAIAnalyzer:
    """Enhanced Azure OpenAI analyzer with full async support"""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=azure_openai_config.API_KEY or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=azure_openai_config.API_VERSION,
            azure_endpoint=azure_openai_config.ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = azure_openai_config.DEPLOYMENT_NAME
        self.icons_base_path = Path("Azure_Public_Service_Icons_V23/Azure_Public_Service_Icons/Icons")
        
        # Initialize enhanced service detector if available
        self.service_detector = get_service_detector() if ACCURACY_ENHANCEMENTS_AVAILABLE else None
        
    async def analyze_requirements_async(self, requirements: str) -> Dict[str, Any]:
        """Async version of requirements analysis"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert Azure solution architect. Analyze requirements and return a JSON response with:
                    {
                        "services": ["list of Azure services"],
                        "architecture_pattern": "pattern name",
                        "connections": [{"source": "service1", "target": "service2", "type": "connection_type"}],
                        "drawio_xml": "complete Draw.io XML diagram",
                        "recommendations": ["list of recommendations"]
                    }
                    
                    Generate complete Draw.io XML that includes Azure service icons and proper positioning."""
                },
                {"role": "user", "content": requirements}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.3,
                max_tokens=agent_config.AGENT_MAX_TOKENS_ARCHITECTURE
            )
            
            content = response.choices[0].message.content
            
            # Check if content is empty or None
            if not content or not isinstance(content, str) or content.strip() == "":
                logger.error(f"Azure OpenAI returned invalid content: {content}")
                return {
                    "services": [],  # Empty - no services detected due to failure
                    "architecture_pattern": "Analysis Failed", 
                    "connections": [],
                    "recommendations": ["AI analysis returned invalid response - manual review required"],
                    "error": "Invalid response from OpenAI",
                    "is_fallback": True
                }
            
            # Try to parse as JSON first
            try:
                # Clean the response similar to agents
                cleaned_content = self._clean_json_response(content)
                if not cleaned_content or cleaned_content == "{}":
                    raise json.JSONDecodeError("Empty cleaned content", content, 0)
                return json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}, Content: {content[:200]}...")
                # If not JSON, check if it's XML
                if "<?xml" in content:
                    return content  # Return raw XML
                else:
                    # Use enhanced service detection if available
                    detected_services = self._extract_services_from_text(content)
                    return {
                        "services": detected_services,
                        "architecture_pattern": "Custom (parsed from text)",
                        "connections": [],
                        "recommendations": [content[:500]],
                        "raw_response": content,
                        "is_fallback": True
                    }
                    
        except Exception as e:
            logger.error(f"Azure OpenAI analysis failed: {str(e)}")
            return {
                "services": [],  # Empty - no services detected due to failure
                "architecture_pattern": "Analysis Failed",
                "connections": [],
                "recommendations": [f"Analysis failed: {str(e)} - please retry or provide more specific requirements"],
                "error": str(e),
                "is_fallback": True
            }
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and prepare JSON response for parsing - similar to agents.py"""
        if not response or not isinstance(response, str) or response.strip() == "":
            return "{}"
        
        cleaned = response.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "").strip()
        elif cleaned.startswith("```"):
            lines = cleaned.split('\n') if cleaned else []
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            cleaned = '\n'.join(lines).strip()
        
        # Remove trailing ```
        if cleaned.endswith("```"):
            cleaned = cleaned.rstrip("```").strip()
        
        # Try to fix common JSON issues
        cleaned = cleaned.replace("'", '"')  # Replace single quotes with double quotes
        
        # Fix trailing commas - this is the main issue causing JSON parsing errors
        import re
        # Remove trailing commas before closing braces or brackets
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        # Remove trailing commas before end of object/array
        cleaned = re.sub(r',(\s*$)', '', cleaned)
        
        # Ensure it starts with opening brace
        if not cleaned.startswith('{'):
            # Try to find the first brace
            brace_idx = cleaned.find('{')
            if brace_idx >= 0:
                cleaned = cleaned[brace_idx:]
            else:
                return "{}"
        
        return cleaned
    
    def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """Sync wrapper for backward compatibility"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.analyze_requirements_async(requirements))
    
    async def analyze_terraform_config_async(self, terraform_config: str) -> Dict[str, Any]:
        """Async analysis of Terraform configuration"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a Terraform and Azure expert. Analyze the Terraform configuration and return JSON with:
                    {
                        "resources": [{"name": "resource_name", "type": "azure_service_type", "properties": {}}],
                        "dependencies": [{"source": "resource1", "target": "resource2"}],
                        "architecture_insights": ["insights about the architecture"],
                        "recommendations": ["optimization recommendations"]
                    }"""
                },
                {"role": "user", "content": f"Terraform Config:\n{terraform_config}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=agent_config.AGENT_TEMPERATURE,
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT
            )
            
            content = response.choices[0].message.content
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "resources": [],
                    "dependencies": [],
                    "architecture_insights": [content[:500]],
                    "recommendations": ["Manual review recommended"],
                    "raw_response": content
                }
                
        except Exception as e:
            logger.error(f"Terraform analysis failed: {str(e)}")
            return {
                "resources": [],
                "dependencies": [],
                "architecture_insights": [],
                "recommendations": [f"Analysis failed: {str(e)}"],
                "error": str(e)
            }
    
    def analyze_terraform_config(self, terraform_config: str) -> Dict[str, Any]:
        """Sync wrapper for Terraform analysis"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.analyze_terraform_config_async(terraform_config))
    
    def get_supported_services(self) -> List[str]:
        """Get list of supported Azure services"""
        return [
            "Azure App Service",
            "Azure Functions", 
            "Azure Kubernetes Service",
            "Azure SQL Database",
            "Azure Cosmos DB",
            "Azure Storage Account",
            "Azure Application Gateway",
            "Azure Load Balancer",
            "Azure API Management",
            "Azure Key Vault",
            "Azure Application Insights",
            "Azure Log Analytics",
            "Azure Virtual Network",
            "Azure Subnet",
            "Azure Service Bus",
            "Azure Event Hub",
            "Azure Data Factory",
            "Azure Databricks",
            "Azure Synapse Analytics",
            "Azure Cognitive Services"
        ]
    
    def get_service_icon_path(self, service_name: str) -> Optional[str]:
        """Get icon path for Azure service"""
        # Mapping of service names to icon paths
        icon_mapping = {
            "Azure App Service": "app services/10035-icon-service-App-Services.svg",
            "Azure Functions": "compute/10029-icon-service-Function-Apps.svg", 
            "Azure Kubernetes Service": "containers/10023-icon-service-Kubernetes-Services.svg",
            "Azure SQL Database": "databases/10130-icon-service-SQL-Database.svg",
            "Azure Cosmos DB": "databases/10121-icon-service-Azure-Cosmos-DB.svg",
            "Azure Storage Account": "storage/10086-icon-service-Storage-Accounts.svg",
            "Azure Application Gateway": "networking/10018-icon-service-Application-Gateways.svg",
            "Azure Load Balancer": "networking/10063-icon-service-Load-Balancers.svg",
            "Azure API Management": "integration/10042-icon-service-API-Management-services.svg",
            "Azure Key Vault": "security/10245-icon-service-Key-Vaults.svg",
            "Azure Application Insights": "devops/10035-icon-service-Application-Insights.svg",
            "Azure Virtual Network": "networking/10080-icon-service-Virtual-Networks.svg"
        }
        
        icon_path = icon_mapping.get(service_name)
        if icon_path:
            full_path = self.icons_base_path / icon_path
            if full_path.exists():
                return str(full_path)
        
        return None
    
    def _extract_services_from_text(self, text: str) -> List[str]:
        """Extract Azure services mentioned in text using enhanced service detection.
        
        Uses the EnhancedServiceDetector from accuracy_enhancements if available,
        which provides fuzzy matching and confidence scoring for more accurate
        service detection.
        """
        if not text or not isinstance(text, str):
            return []  # Return empty list instead of misleading defaults
            
        # Use enhanced service detector if available
        if self.service_detector:
            try:
                detected = self.service_detector.extract_services_from_requirements(text)
                # Return services with confidence > 0.5
                high_confidence_services = [
                    d["service"] for d in detected 
                    if d.get("confidence", 0) > 0.5
                ]
                if high_confidence_services:
                    return high_confidence_services[:10]
            except Exception as e:
                logger.warning(f"Enhanced service detection failed: {e}, falling back to basic detection")
        
        # Fallback to basic detection
        services = []
        supported_services = self.get_supported_services()
        text_lower = text.lower().strip()
        
        for service in supported_services:
            if service and service.lower() in text_lower:
                services.append(service)
        
        # Return empty list if no services found (don't add misleading defaults)
        return services[:10]  # Limit to 10 services