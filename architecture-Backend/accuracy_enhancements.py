"""
Accuracy Enhancement Module for AI Architecture Generator
=========================================================

This module provides enhanced accuracy for:
1. Azure service detection and recognition
2. Connection analysis and flow detection  
3. Validation scoring with meaningful metrics
4. Few-shot examples for better LLM prompts
5. Pattern matching for reference architectures

Author: GitHub Copilot
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
from config import content_config


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED AZURE SERVICE RECOGNITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AzureServiceInfo:
    """Comprehensive Azure service information for accurate detection"""
    canonical_name: str
    display_name: str
    category: str
    layer: int  # 0=Edge, 1=Gateway, 2=Compute, 3=Data, -1=Cross-cutting
    aliases: List[str] = field(default_factory=list)
    typical_connections: List[str] = field(default_factory=list)
    well_architected_pillar: str = ""  # Primary WAF pillar
    icon_path: str = ""


# Comprehensive Azure Service Catalog with accurate metadata
AZURE_SERVICE_CATALOG: Dict[str, AzureServiceInfo] = {
    # ═══════════════ LAYER 0: EDGE SERVICES ═══════════════
    "azure_front_door": AzureServiceInfo(
        canonical_name="azure_front_door",
        display_name="Azure Front Door",
        category="networking",
        layer=0,
        aliases=["front door", "frontdoor", "afd", "azure front door premium", "azure front door standard"],
        typical_connections=["application_gateway", "app_service", "storage_static_website", "api_management"],
        well_architected_pillar="performance",
        icon_path="networking/10037-icon-service-Front-Doors.svg"
    ),
    "azure_cdn": AzureServiceInfo(
        canonical_name="azure_cdn",
        display_name="Azure CDN",
        category="networking",
        layer=0,
        aliases=["cdn", "content delivery network", "akamai", "verizon cdn"],
        typical_connections=["storage_account", "app_service", "static_web_app"],
        well_architected_pillar="performance",
        icon_path="networking/10151-icon-service-CDN-Profiles.svg"
    ),
    "azure_traffic_manager": AzureServiceInfo(
        canonical_name="azure_traffic_manager",
        display_name="Azure Traffic Manager",
        category="networking",
        layer=0,
        aliases=["traffic manager", "tm", "dns load balancer"],
        typical_connections=["app_service", "load_balancer", "application_gateway"],
        well_architected_pillar="reliability",
        icon_path="networking/10068-icon-service-Traffic-Manager-Profiles.svg"
    ),
    "azure_waf": AzureServiceInfo(
        canonical_name="azure_waf",
        display_name="Azure Web Application Firewall",
        category="security",
        layer=0,
        aliases=["waf", "web application firewall", "waf policy"],
        typical_connections=["front_door", "application_gateway"],
        well_architected_pillar="security",
        icon_path="security/10279-icon-Web-Application-Firewall-Policies(WAF).svg"
    ),
    
    # ═══════════════ LAYER 1: GATEWAY SERVICES ═══════════════
    "application_gateway": AzureServiceInfo(
        canonical_name="application_gateway",
        display_name="Azure Application Gateway",
        category="networking",
        layer=1,
        aliases=["app gateway", "appgw", "azure application gateway", "layer 7 load balancer"],
        typical_connections=["app_service", "aks", "vm_scale_set", "container_apps"],
        well_architected_pillar="reliability",
        icon_path="networking/10018-icon-service-Application-Gateways.svg"
    ),
    "api_management": AzureServiceInfo(
        canonical_name="api_management",
        display_name="Azure API Management",
        category="integration",
        layer=1,
        aliases=["apim", "api gateway", "azure api management", "api mgmt"],
        typical_connections=["app_service", "functions", "aks", "logic_apps"],
        well_architected_pillar="operational_excellence",
        icon_path="integration/10042-icon-service-API-Management-Services.svg"
    ),
    "azure_firewall": AzureServiceInfo(
        canonical_name="azure_firewall",
        display_name="Azure Firewall",
        category="security",
        layer=1,
        aliases=["firewall", "azure firewall premium", "azure firewall standard"],
        typical_connections=["virtual_network", "route_table", "aks"],
        well_architected_pillar="security",
        icon_path="networking/10072-icon-service-Firewalls.svg"
    ),
    "load_balancer": AzureServiceInfo(
        canonical_name="load_balancer",
        display_name="Azure Load Balancer",
        category="networking",
        layer=1,
        aliases=["lb", "azure load balancer", "internal load balancer", "public load balancer"],
        typical_connections=["vm", "vm_scale_set", "aks"],
        well_architected_pillar="reliability",
        icon_path="networking/10063-icon-service-Load-Balancers.svg"
    ),
    "azure_bastion": AzureServiceInfo(
        canonical_name="azure_bastion",
        display_name="Azure Bastion",
        category="security",
        layer=1,
        aliases=["bastion", "jump host", "jumpbox"],
        typical_connections=["vm", "aks"],
        well_architected_pillar="security",
        icon_path="networking/10073-icon-service-Bastions.svg"
    ),
    
    # ═══════════════ LAYER 2: COMPUTE & INTEGRATION ═══════════════
    "app_service": AzureServiceInfo(
        canonical_name="app_service",
        display_name="Azure App Service",
        category="compute",
        layer=2,
        aliases=["web app", "azure app service", "app service plan", "webapp"],
        typical_connections=["sql_database", "cosmos_db", "redis", "key_vault", "storage_account", "service_bus"],
        well_architected_pillar="operational_excellence",
        icon_path="compute/10035-icon-service-App-Services.svg"
    ),
    "azure_functions": AzureServiceInfo(
        canonical_name="azure_functions",
        display_name="Azure Functions",
        category="compute",
        layer=2,
        aliases=["functions", "function app", "serverless", "azure functions premium"],
        typical_connections=["cosmos_db", "storage_account", "service_bus", "event_hub", "event_grid", "key_vault"],
        well_architected_pillar="cost_optimization",
        icon_path="compute/10029-icon-service-Function-Apps.svg"
    ),
    "aks": AzureServiceInfo(
        canonical_name="aks",
        display_name="Azure Kubernetes Service",
        category="compute",
        layer=2,
        aliases=["kubernetes", "azure kubernetes service", "k8s", "aks cluster"],
        typical_connections=["container_registry", "sql_database", "cosmos_db", "redis", "key_vault", "service_bus"],
        well_architected_pillar="operational_excellence",
        icon_path="containers/10023-icon-service-Kubernetes-Services.svg"
    ),
    "container_apps": AzureServiceInfo(
        canonical_name="container_apps",
        display_name="Azure Container Apps",
        category="compute",
        layer=2,
        aliases=["aca", "container apps", "azure container apps"],
        typical_connections=["container_registry", "cosmos_db", "redis", "key_vault", "service_bus"],
        well_architected_pillar="cost_optimization",
        icon_path="containers/10104-icon-service-Container-Apps.svg"
    ),
    "service_bus": AzureServiceInfo(
        canonical_name="service_bus",
        display_name="Azure Service Bus",
        category="integration",
        layer=2,
        aliases=["asb", "azure service bus", "message queue", "topic", "subscription"],
        typical_connections=["functions", "app_service", "logic_apps"],
        well_architected_pillar="reliability",
        icon_path="integration/10070-icon-service-Service-Bus.svg"
    ),
    "event_hub": AzureServiceInfo(
        canonical_name="event_hub",
        display_name="Azure Event Hubs",
        category="integration",
        layer=2,
        aliases=["event hubs", "eventhub", "kafka", "streaming"],
        typical_connections=["functions", "stream_analytics", "databricks"],
        well_architected_pillar="performance",
        icon_path="integration/10052-icon-service-Event-Hubs.svg"
    ),
    "event_grid": AzureServiceInfo(
        canonical_name="event_grid",
        display_name="Azure Event Grid",
        category="integration",
        layer=2,
        aliases=["eventgrid", "event grid topics", "event subscriptions"],
        typical_connections=["functions", "logic_apps", "storage_account"],
        well_architected_pillar="reliability",
        icon_path="integration/10053-icon-service-Event-Grid-Domains.svg"
    ),
    "logic_apps": AzureServiceInfo(
        canonical_name="logic_apps",
        display_name="Azure Logic Apps",
        category="integration",
        layer=2,
        aliases=["logic app", "workflow", "azure logic apps"],
        typical_connections=["service_bus", "sql_database", "storage_account", "office_365"],
        well_architected_pillar="operational_excellence",
        icon_path="integration/10058-icon-service-Logic-Apps.svg"
    ),
    
    # ═══════════════ LAYER 3: DATA & STORAGE ═══════════════
    "sql_database": AzureServiceInfo(
        canonical_name="sql_database",
        display_name="Azure SQL Database",
        category="data",
        layer=3,
        aliases=["azure sql", "sql server", "sql db", "azure sql database", "sql managed instance"],
        typical_connections=["app_service", "functions", "aks"],
        well_architected_pillar="reliability",
        icon_path="databases/10130-icon-service-SQL-Database.svg"
    ),
    "cosmos_db": AzureServiceInfo(
        canonical_name="cosmos_db",
        display_name="Azure Cosmos DB",
        category="data",
        layer=3,
        aliases=["cosmosdb", "cosmos", "documentdb", "azure cosmos db"],
        typical_connections=["functions", "app_service", "aks"],
        well_architected_pillar="reliability",
        icon_path="databases/10121-icon-service-Azure-Cosmos-DB.svg"
    ),
    "redis": AzureServiceInfo(
        canonical_name="redis",
        display_name="Azure Cache for Redis",
        category="data",
        layer=3,
        aliases=["azure redis", "redis cache", "azure cache for redis"],
        typical_connections=["app_service", "functions", "aks"],
        well_architected_pillar="performance",
        icon_path="databases/10136-icon-service-Cache-Redis.svg"
    ),
    "postgresql": AzureServiceInfo(
        canonical_name="postgresql",
        display_name="Azure Database for PostgreSQL",
        category="data",
        layer=3,
        aliases=["postgres", "azure postgresql", "postgresql flexible server", "azure database for postgresql"],
        typical_connections=["app_service", "functions", "aks"],
        well_architected_pillar="reliability",
        icon_path="databases/10129-icon-service-Azure-Database-PostgreSQL-Server.svg"
    ),
    "storage_account": AzureServiceInfo(
        canonical_name="storage_account",
        display_name="Azure Storage Account",
        category="storage",
        layer=3,
        aliases=["storage", "blob storage", "azure storage", "blob", "file share", "queue storage", "table storage"],
        typical_connections=["functions", "app_service", "data_factory"],
        well_architected_pillar="cost_optimization",
        icon_path="storage/10086-icon-service-Storage-Accounts.svg"
    ),
    "data_lake": AzureServiceInfo(
        canonical_name="data_lake",
        display_name="Azure Data Lake Storage",
        category="storage",
        layer=3,
        aliases=["adls", "data lake", "adls gen2", "azure data lake storage"],
        typical_connections=["databricks", "synapse", "data_factory"],
        well_architected_pillar="performance",
        icon_path="storage/10086-icon-service-Storage-Accounts.svg"
    ),
    
    # ═══════════════ CROSS-CUTTING SERVICES (LAYER -1) ═══════════════
    "key_vault": AzureServiceInfo(
        canonical_name="key_vault",
        display_name="Azure Key Vault",
        category="security",
        layer=-1,
        aliases=["keyvault", "azure key vault", "secrets", "certificates"],
        typical_connections=["app_service", "functions", "aks", "api_management"],
        well_architected_pillar="security",
        icon_path="security/10245-icon-service-Key-Vaults.svg"
    ),
    "application_insights": AzureServiceInfo(
        canonical_name="application_insights",
        display_name="Application Insights",
        category="monitoring",
        layer=-1,
        aliases=["appinsights", "app insights", "azure application insights"],
        typical_connections=["app_service", "functions", "aks"],
        well_architected_pillar="operational_excellence",
        icon_path="devops/00012-icon-service-Application-Insights.svg"
    ),
    "azure_monitor": AzureServiceInfo(
        canonical_name="azure_monitor",
        display_name="Azure Monitor",
        category="monitoring",
        layer=-1,
        aliases=["monitor", "azure monitor", "monitoring"],
        typical_connections=["log_analytics", "application_insights"],
        well_architected_pillar="operational_excellence",
        icon_path="management governance/00001-icon-service-Monitor.svg"
    ),
    "log_analytics": AzureServiceInfo(
        canonical_name="log_analytics",
        display_name="Log Analytics Workspace",
        category="monitoring",
        layer=-1,
        aliases=["log analytics", "oms", "workspace", "azure log analytics"],
        typical_connections=["azure_monitor", "application_insights", "sentinel"],
        well_architected_pillar="operational_excellence",
        icon_path="management governance/00003-icon-service-Log-Analytics-Workspaces.svg"
    ),
    "entra_id": AzureServiceInfo(
        canonical_name="entra_id",
        display_name="Microsoft Entra ID",
        category="security",
        layer=-1,
        aliases=["azure ad", "active directory", "aad", "entra", "microsoft entra id"],
        typical_connections=["app_service", "api_management", "functions"],
        well_architected_pillar="security",
        icon_path="identity/10221-icon-service-Azure-Active-Directory.svg"
    ),
    "defender_for_cloud": AzureServiceInfo(
        canonical_name="defender_for_cloud",
        display_name="Microsoft Defender for Cloud",
        category="security",
        layer=-1,
        aliases=["defender", "security center", "azure security center", "microsoft defender"],
        typical_connections=["log_analytics", "sentinel"],
        well_architected_pillar="security",
        icon_path="security/10241-icon-service-Security-Center.svg"
    ),
}


class EnhancedServiceDetector:
    """Enhanced Azure service detection with fuzzy matching and confidence scoring"""
    
    def __init__(self):
        self.catalog = AZURE_SERVICE_CATALOG
        self._build_alias_index()
    
    def _build_alias_index(self):
        """Build reverse index from aliases to canonical names"""
        self.alias_index: Dict[str, str] = {}
        for canonical, info in self.catalog.items():
            # Add canonical name
            self.alias_index[canonical.lower()] = canonical
            self.alias_index[info.display_name.lower()] = canonical
            # Add all aliases
            for alias in info.aliases:
                self.alias_index[alias.lower()] = canonical
    
    def detect_service(self, text: str) -> Tuple[Optional[AzureServiceInfo], float]:
        """
        Detect Azure service from text with confidence score.
        
        Returns:
            Tuple of (AzureServiceInfo or None, confidence_score 0.0-1.0)
        """
        if not text:
            return None, 0.0
        
        text_lower = text.lower().strip()
        
        # Exact match - highest confidence
        if text_lower in self.alias_index:
            canonical = self.alias_index[text_lower]
            return self.catalog[canonical], 1.0
        
        # Remove common prefixes and try again
        for prefix in ["azure ", "microsoft ", "ms "]:
            if text_lower.startswith(prefix):
                stripped = text_lower[len(prefix):]
                if stripped in self.alias_index:
                    canonical = self.alias_index[stripped]
                    return self.catalog[canonical], 0.95
        
        # Fuzzy match - find best substring match
        best_match = None
        best_confidence = 0.0
        
        for alias, canonical in self.alias_index.items():
            # Check if alias is contained in text
            if alias in text_lower:
                confidence = len(alias) / len(text_lower) * 0.8
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = canonical
            # Check if text is contained in alias
            elif text_lower in alias:
                confidence = len(text_lower) / len(alias) * 0.7
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = canonical
        
        if best_match and best_confidence > 0.4:
            return self.catalog[best_match], best_confidence
        
        return None, 0.0
    
    def extract_services_from_requirements(self, requirements: str) -> List[Dict[str, Any]]:
        """
        Extract Azure services mentioned in requirements text.
        
        Returns list of detected services with confidence scores.
        """
        detected = []
        requirements_lower = requirements.lower()
        
        # Check each service's aliases against requirements
        for canonical, info in self.catalog.items():
            all_names = [info.display_name.lower()] + [a.lower() for a in info.aliases]
            
            for name in all_names:
                if name in requirements_lower:
                    # Calculate confidence based on match quality
                    confidence = min(1.0, len(name) / 20)  # Longer names = higher confidence
                    detected.append({
                        "service": info.display_name,
                        "canonical_name": canonical,
                        "category": info.category,
                        "layer": info.layer,
                        "confidence": confidence,
                        "matched_text": name
                    })
                    break  # Avoid duplicate detections for same service
        
        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        
        return detected


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED VALIDATION SCORING
# ═══════════════════════════════════════════════════════════════════════════════

class AccuracyScorer:
    """
    Calculates meaningful accuracy scores based on actual architecture analysis.
    Replaces arbitrary fallback scores with computed metrics.
    """
    
    # Weights for each Well-Architected Framework pillar
    WAF_WEIGHTS = {
        "security": 0.25,
        "reliability": 0.20,
        "performance": 0.20,
        "cost_optimization": 0.15,
        "operational_excellence": 0.20
    }
    
    def calculate_architecture_score(
        self,
        services: List[Dict],
        connections: List[Dict],
        requirements: str,
        security_analysis: Dict = None,
        performance_analysis: Dict = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive architecture score based on actual analysis.
        
        Returns:
            Dict containing scores for each pillar and overall score with explanations.
        """
        scores = {
            "security": self._score_security(services, connections, security_analysis),
            "reliability": self._score_reliability(services, connections),
            "performance": self._score_performance(services, connections, performance_analysis),
            "cost_optimization": self._score_cost(services),
            "operational_excellence": self._score_operations(services, connections)
        }
        
        # Calculate weighted overall score
        overall = sum(
            scores[pillar]["score"] * weight
            for pillar, weight in self.WAF_WEIGHTS.items()
        )
        
        return {
            "overall_score": round(overall, 1),
            "pillar_scores": scores,
            "scoring_methodology": "Calculated based on architecture composition analysis",
            "improvements": self._generate_improvements(scores)
        }
    
    def _score_security(self, services: List[Dict], connections: List[Dict], security_analysis: Dict = None) -> Dict:
        """Score security pillar based on actual security controls"""
        score = 40  # Base score
        details = []
        
        service_names = [s.get("name", "").lower() for s in services]
        
        # Check for identity management
        if any("entra" in n or "active directory" in n or "identity" in n for n in service_names):
            score += 15
            details.append("Identity management present")
        else:
            details.append("Missing: Identity management (Entra ID)")
        
        # Check for secrets management
        if any("key vault" in n for n in service_names):
            score += 15
            details.append("Secrets management with Key Vault")
        else:
            details.append("Missing: Azure Key Vault for secrets")
        
        # Check for network security
        if any("firewall" in n or "waf" in n or "nsg" in n for n in service_names):
            score += 10
            details.append("Network security controls present")
        else:
            details.append("Missing: Network security (Firewall/WAF)")
        
        # Check for private endpoints in connections
        if any("private" in c.get("label", "").lower() for c in connections):
            score += 10
            details.append("Private endpoint connectivity")
        
        # Check for threat detection
        if any("defender" in n or "sentinel" in n for n in service_names):
            score += 10
            details.append("Threat detection configured")
        
        return {
            "score": min(100, score),
            "details": details,
            "pillar": "security"
        }
    
    def _score_reliability(self, services: List[Dict], connections: List[Dict]) -> Dict:
        """Score reliability pillar"""
        score = 50  # Base score
        details = []
        
        service_names = [s.get("name", "").lower() for s in services]
        
        # Check for load balancing
        if any("load balancer" in n or "front door" in n or "traffic manager" in n for n in service_names):
            score += 15
            details.append("Load balancing configured")
        else:
            details.append("Missing: Load balancing for HA")
        
        # Check for redundant data stores
        data_services = [s for s in services if s.get("category") == "data"]
        if len(data_services) >= 2 or any("geo" in s.get("description", "").lower() for s in data_services):
            score += 15
            details.append("Redundant data tier")
        
        # Check for async patterns (resilience)
        if any("service bus" in n or "event" in n or "queue" in n for n in service_names):
            score += 10
            details.append("Async messaging for resilience")
        
        # Check for monitoring
        if any("monitor" in n or "insights" in n for n in service_names):
            score += 10
            details.append("Monitoring configured")
        
        return {
            "score": min(100, score),
            "details": details,
            "pillar": "reliability"
        }
    
    def _score_performance(self, services: List[Dict], connections: List[Dict], performance_analysis: Dict = None) -> Dict:
        """Score performance pillar"""
        score = 50  # Base score
        details = []
        
        service_names = [s.get("name", "").lower() for s in services]
        
        # Check for caching
        if any("redis" in n or "cache" in n for n in service_names):
            score += 20
            details.append("Caching layer present")
        else:
            details.append("Consider: Adding caching (Redis)")
        
        # Check for CDN
        if any("cdn" in n or "front door" in n for n in service_names):
            score += 15
            details.append("Content delivery/CDN configured")
        
        # Check for auto-scaling capable services
        scalable_services = ["app service", "functions", "aks", "container apps"]
        if any(ss in n for n in service_names for ss in scalable_services):
            score += 15
            details.append("Auto-scaling capable compute")
        
        return {
            "score": min(100, score),
            "details": details,
            "pillar": "performance"
        }
    
    def _score_cost(self, services: List[Dict]) -> Dict:
        """Score cost optimization pillar"""
        score = 60  # Base score
        details = []
        
        categories = [s.get("category", "") for s in services]
        
        # Check for serverless (cost-efficient)
        service_names = [s.get("name", "").lower() for s in services]
        if any("functions" in n or "logic app" in n for n in service_names):
            score += 15
            details.append("Serverless compute for cost efficiency")
        
        # Check if architecture is not over-engineered
        if len(services) <= content_config.MAX_SERVICES_THRESHOLD:
            score += 10
            details.append("Right-sized architecture")
        else:
            details.append("Consider: Simplifying architecture")
        
        # Check for storage tiering
        if any("storage" in n for n in service_names):
            score += 10
            details.append("Storage services for tiering options")
        
        return {
            "score": min(100, score),
            "details": details,
            "pillar": "cost_optimization"
        }
    
    def _score_operations(self, services: List[Dict], connections: List[Dict]) -> Dict:
        """Score operational excellence pillar"""
        score = 50  # Base score
        details = []
        
        service_names = [s.get("name", "").lower() for s in services]
        
        # Check for monitoring
        if any("application insights" in n for n in service_names):
            score += 15
            details.append("Application monitoring (App Insights)")
        else:
            details.append("Missing: Application Insights")
        
        if any("log analytics" in n or "monitor" in n for n in service_names):
            score += 10
            details.append("Centralized logging")
        
        # Check for API management
        if any("api management" in n for n in service_names):
            score += 10
            details.append("API governance (APIM)")
        
        # Check for infrastructure as code readiness
        if any("container" in n or "kubernetes" in n or "aks" in n for n in service_names):
            score += 10
            details.append("Container-based (IaC friendly)")
        
        return {
            "score": min(100, score),
            "details": details,
            "pillar": "operational_excellence"
        }
    
    def _generate_improvements(self, scores: Dict) -> List[Dict]:
        """Generate improvement recommendations based on low-scoring pillars"""
        improvements = []
        
        for pillar, data in scores.items():
            if data["score"] < 70:
                missing = [d for d in data["details"] if d.startswith("Missing:") or d.startswith("Consider:")]
                for item in missing:
                    improvements.append({
                        "pillar": pillar,
                        "recommendation": item,
                        "priority": "High" if data["score"] < 50 else "Medium"
                    })
        
        return improvements


# ═══════════════════════════════════════════════════════════════════════════════
# FEW-SHOT EXAMPLES FOR IMPROVED LLM ACCURACY
# ═══════════════════════════════════════════════════════════════════════════════

FEW_SHOT_ARCHITECTURE_EXAMPLES = """
<example_1>
REQUIREMENTS: "Build a web application with user authentication and a PostgreSQL database"
ARCHITECTURE:
{
  "services": [
    {"name": "Users", "category": "external", "layer": 0},
    {"name": "Azure Front Door", "category": "networking", "layer": 0},
    {"name": "Azure Application Gateway", "category": "networking", "layer": 1},
    {"name": "Azure App Service", "category": "compute", "layer": 2},
    {"name": "Azure Database for PostgreSQL", "category": "data", "layer": 3},
    {"name": "Azure Key Vault", "category": "security", "layer": -1},
    {"name": "Application Insights", "category": "monitoring", "layer": -1},
    {"name": "Microsoft Entra ID", "category": "security", "layer": -1}
  ],
  "connections": [
    {"source": "Users", "target": "Azure Front Door", "label": "HTTPS requests", "flow_type": "entry_point"},
    {"source": "Azure Front Door", "target": "Azure Application Gateway", "label": "WAF inspection & routing", "flow_type": "edge_to_gateway"},
    {"source": "Azure Application Gateway", "target": "Azure App Service", "label": "Load balanced traffic", "flow_type": "gateway_to_compute"},
    {"source": "Azure App Service", "target": "Azure Database for PostgreSQL", "label": "SQL queries via Private Endpoint", "flow_type": "compute_to_data"},
    {"source": "Azure App Service", "target": "Azure Key Vault", "label": "Connection string retrieval", "flow_type": "compute_to_crosscutting"},
    {"source": "Azure App Service", "target": "Application Insights", "label": "Telemetry & traces", "flow_type": "compute_to_crosscutting"},
    {"source": "Azure App Service", "target": "Microsoft Entra ID", "label": "OAuth 2.0 authentication", "flow_type": "compute_to_crosscutting"}
  ],
  "architecture_pattern": "Web Application with Authentication"
}
</example_1>

<example_2>
REQUIREMENTS: "Create an event-driven microservices architecture for order processing"
ARCHITECTURE:
{
  "services": [
    {"name": "Users", "category": "external", "layer": 0},
    {"name": "Azure Front Door", "category": "networking", "layer": 0},
    {"name": "Azure API Management", "category": "integration", "layer": 1},
    {"name": "Azure Kubernetes Service", "category": "compute", "layer": 2},
    {"name": "Azure Service Bus", "category": "integration", "layer": 2},
    {"name": "Azure Functions", "category": "compute", "layer": 2},
    {"name": "Azure Cosmos DB", "category": "data", "layer": 3},
    {"name": "Azure Cache for Redis", "category": "data", "layer": 3},
    {"name": "Azure Key Vault", "category": "security", "layer": -1},
    {"name": "Application Insights", "category": "monitoring", "layer": -1}
  ],
  "connections": [
    {"source": "Users", "target": "Azure Front Door", "label": "API requests", "flow_type": "entry_point"},
    {"source": "Azure Front Door", "target": "Azure API Management", "label": "API routing & policies", "flow_type": "edge_to_gateway"},
    {"source": "Azure API Management", "target": "Azure Kubernetes Service", "label": "Microservice routing", "flow_type": "gateway_to_compute"},
    {"source": "Azure Kubernetes Service", "target": "Azure Service Bus", "label": "Order events published", "flow_type": "compute_to_integration"},
    {"source": "Azure Service Bus", "target": "Azure Functions", "label": "Queue-triggered processing", "flow_type": "integration_to_compute"},
    {"source": "Azure Functions", "target": "Azure Cosmos DB", "label": "Document persistence", "flow_type": "compute_to_data"},
    {"source": "Azure Kubernetes Service", "target": "Azure Cache for Redis", "label": "Session cache", "flow_type": "compute_to_data"},
    {"source": "Azure Kubernetes Service", "target": "Azure Key Vault", "label": "Secrets via Managed Identity", "flow_type": "compute_to_crosscutting"}
  ],
  "architecture_pattern": "Event-Driven Microservices"
}
</example_2>

<example_3>
REQUIREMENTS: "Real-time analytics dashboard with streaming data"
ARCHITECTURE:
{
  "services": [
    {"name": "IoT Devices", "category": "external", "layer": 0},
    {"name": "Azure Event Hubs", "category": "integration", "layer": 1},
    {"name": "Azure Stream Analytics", "category": "compute", "layer": 2},
    {"name": "Azure Functions", "category": "compute", "layer": 2},
    {"name": "Azure Cosmos DB", "category": "data", "layer": 3},
    {"name": "Azure Synapse Analytics", "category": "data", "layer": 3},
    {"name": "Power BI", "category": "external", "layer": 0}
  ],
  "connections": [
    {"source": "IoT Devices", "target": "Azure Event Hubs", "label": "Streaming telemetry", "flow_type": "entry_point"},
    {"source": "Azure Event Hubs", "target": "Azure Stream Analytics", "label": "Real-time processing", "flow_type": "integration_to_compute"},
    {"source": "Azure Stream Analytics", "target": "Azure Cosmos DB", "label": "Hot path storage", "flow_type": "compute_to_data"},
    {"source": "Azure Event Hubs", "target": "Azure Functions", "label": "Archive processing", "flow_type": "integration_to_compute"},
    {"source": "Azure Functions", "target": "Azure Synapse Analytics", "label": "Cold path analytics", "flow_type": "compute_to_data"},
    {"source": "Azure Cosmos DB", "target": "Power BI", "label": "Dashboard queries", "flow_type": "data_to_visualization"}
  ],
  "architecture_pattern": "Lambda Architecture (Hot/Cold Path)"
}
</example_3>
"""

FEW_SHOT_CONNECTION_EXAMPLES = """
<connection_patterns>
CORRECT CONNECTION LABELING BY SERVICE TYPE:

1. Edge → Gateway:
   - "Azure Front Door" → "Azure Application Gateway": "WAF inspection & TLS termination"
   - "Azure Traffic Manager" → "Azure Application Gateway": "Geographic routing"
   - "Azure CDN" → "Azure App Service": "Static content delivery"

2. Gateway → Compute:
   - "Azure Application Gateway" → "Azure App Service": "Load-balanced HTTP traffic"
   - "Azure API Management" → "Azure Functions": "API gateway routing"
   - "Azure Load Balancer" → "Azure VM Scale Set": "Layer 4 load balancing"

3. Compute → Data:
   - "Azure App Service" → "Azure SQL Database": "SQL queries via Private Endpoint"
   - "Azure Functions" → "Azure Cosmos DB": "Document CRUD operations"
   - "Azure AKS" → "Azure Cache for Redis": "Session state & caching"

4. Compute → Integration:
   - "Azure App Service" → "Azure Service Bus": "Message queue publishing"
   - "Azure Functions" → "Azure Event Grid": "Event publishing"
   - "Azure Logic Apps" → "Azure Service Bus": "Workflow orchestration"

5. Integration → Compute:
   - "Azure Service Bus" → "Azure Functions": "Queue-triggered processing"
   - "Azure Event Hubs" → "Azure Stream Analytics": "Stream processing"
   - "Azure Event Grid" → "Azure Functions": "Event-driven triggers"

6. Compute → Cross-cutting:
   - "Azure App Service" → "Azure Key Vault": "Secret retrieval via Managed Identity"
   - "Azure Functions" → "Application Insights": "Telemetry & distributed tracing"
   - "Azure AKS" → "Microsoft Entra ID": "Workload identity authentication"
</connection_patterns>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedPromptBuilder:
    """Build enhanced prompts with few-shot examples and chain-of-thought instructions"""
    
    @staticmethod
    def build_architecture_prompt(requirements: str, context: Dict = None) -> str:
        """Build enhanced architecture generation prompt"""
        
        chain_of_thought = """
CHAIN-OF-THOUGHT REASONING INSTRUCTIONS:
Before generating the architecture, think through these steps:

Step 1: REQUIREMENTS ANALYSIS
- What are the functional requirements?
- What are the non-functional requirements (performance, security, scale)?
- What is the expected user load and data volume?

Step 2: PATTERN SELECTION
- Which Azure reference architecture pattern best fits?
- Is this a web app, microservices, data processing, or hybrid scenario?

Step 3: SERVICE SELECTION
- For each requirement, which Azure service is the best fit?
- Consider: managed vs. self-managed, serverless vs. always-on, cost implications

Step 4: CONNECTION FLOW
- What is the primary data flow from users to data storage?
- What secondary flows exist (async processing, events, caching)?
- Ensure connections follow layer hierarchy: Edge → Gateway → Compute → Data

Step 5: CROSS-CUTTING CONCERNS
- Security: Identity, secrets, network security
- Monitoring: Application insights, log analytics
- Operations: Alerting, diagnostics

Step 6: VALIDATION
- Does every service have at least one connection?
- Does every requirement have a corresponding service?
- Is the flow direction correct (top-down)?
"""
        
        prompt = f"""
{chain_of_thought}

FEW-SHOT EXAMPLES (learn from these patterns):
{FEW_SHOT_ARCHITECTURE_EXAMPLES}

NOW GENERATE ARCHITECTURE FOR:
REQUIREMENTS: {requirements}

CONTEXT FROM PREVIOUS AGENTS:
{json.dumps(context, indent=2) if context else "No additional context"}

Remember:
1. Always start with "Users" entry point
2. Follow layer hierarchy strictly
3. Include cross-cutting services (Key Vault, Application Insights)
4. Use specific, meaningful connection labels
5. Every service must have at least one connection

Return ONLY valid JSON following the exact structure shown in examples.
"""
        return prompt
    
    @staticmethod
    def build_connection_optimization_prompt(services: List[Dict], connections: List[Dict]) -> str:
        """Build enhanced connection optimization prompt"""
        
        return f"""
{FEW_SHOT_CONNECTION_EXAMPLES}

OPTIMIZE THESE CONNECTIONS:
Services: {json.dumps(services, indent=2)}
Current Connections: {json.dumps(connections, indent=2)}

VALIDATION RULES:
1. Every service must have at least one connection (no orphans)
2. Connection flow should be top-down (lower layer → higher layer)
3. Labels must be specific and meaningful (not generic like "connects to")
4. Cross-cutting services connect FROM compute services (compute → Key Vault, not reverse)
5. Remove duplicate connections
6. Connection types must be realistic (HTTPS, Private Endpoint, Message Queue, etc.)

Return optimized connections with improved labels and fixed flow directions.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# LEARNED PATTERNS INTEGRATION (from Azure Architecture Center Draw.io files)
# ═══════════════════════════════════════════════════════════════════════════════

class LearnedPatternsIntegration:
    """Integrates learned patterns from extracted Draw.io training data"""
    
    _instance = None
    _training_data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_training_data()
        return cls._instance
    
    @classmethod
    def _load_training_data(cls):
        """Load training data from extracted JSON file"""
        import os
        training_data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "azure_architecture_training_data.json"
        )
        
        if os.path.exists(training_data_path):
            with open(training_data_path, 'r', encoding='utf-8') as f:
                cls._training_data = json.load(f)
        else:
            cls._training_data = {
                "services": [],
                "connection_patterns": {},
                "service_co_occurrence": {},
                "architecture_patterns": []
            }
    
    @property
    def training_data(self) -> Dict:
        """Get loaded training data"""
        if self._training_data is None:
            self._load_training_data()
        return self._training_data
    
    def get_known_services(self) -> List[str]:
        """Get list of all known Azure services from training data"""
        return self.training_data.get("services", [])
    
    def get_connection_suggestions(self, service_name: str) -> List[str]:
        """Get suggested downstream connections for a service"""
        patterns = self.training_data.get("connection_patterns", {})
        return patterns.get(service_name, [])
    
    def get_co_occurring_services(self, service_name: str) -> List[str]:
        """Get services that commonly appear together with given service"""
        co_occurrence = self.training_data.get("service_co_occurrence", {})
        return co_occurrence.get(service_name, [])
    
    def find_similar_architecture(self, services: List[str], top_n: int = 3) -> List[Dict]:
        """Find architecture patterns similar to given services"""
        service_set = set(services)
        patterns = self.training_data.get("architecture_patterns", [])
        
        scored = []
        for pattern in patterns:
            pattern_services = set(pattern.get("services", []))
            intersection = len(service_set & pattern_services)
            union = len(service_set | pattern_services)
            
            if union > 0:
                similarity = intersection / union
                scored.append({
                    "name": pattern.get("name", "Unknown"),
                    "source": pattern.get("source_file", ""),
                    "similarity": round(similarity, 3),
                    "matching": list(service_set & pattern_services),
                    "suggested_additions": list(pattern_services - service_set)[:5]
                })
        
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_n]
    
    def suggest_missing_services(self, current_services: List[str], 
                                 architecture_type: str = None) -> List[str]:
        """Suggest services that are commonly used but missing from current list"""
        patterns = self.training_data.get("architecture_patterns", [])
        
        # Find patterns that match architecture type or current services
        relevant_patterns = []
        for pattern in patterns:
            pattern_name = pattern.get("name", "").lower()
            pattern_services = set(pattern.get("services", []))
            
            # Check if architecture type matches
            if architecture_type and architecture_type.lower() in pattern_name:
                relevant_patterns.append(pattern_services)
                continue
            
            # Check overlap with current services
            current_set = set(current_services)
            overlap = len(current_set & pattern_services)
            if overlap >= 2:  # At least 2 services in common
                relevant_patterns.append(pattern_services)
        
        # Find commonly used services in relevant patterns
        if not relevant_patterns:
            return []
        
        from collections import Counter
        service_counts = Counter()
        for pattern_services in relevant_patterns:
            service_counts.update(pattern_services)
        
        # Return top suggestions not in current list
        current_set = set(current_services)
        suggestions = [
            service for service, count in service_counts.most_common(10)
            if service not in current_set and count >= 2
        ]
        
        return suggestions[:5]
    
    def validate_connections(self, connections: List[Tuple[str, str]]) -> List[Dict]:
        """Validate if connections are commonly seen in reference architectures"""
        patterns = self.training_data.get("connection_patterns", {})
        
        results = []
        for source, target in connections:
            known_targets = patterns.get(source, [])
            is_common = target in known_targets
            
            results.append({
                "source": source,
                "target": target,
                "is_common_pattern": is_common,
                "confidence": 0.9 if is_common else 0.5,
                "alternative_targets": known_targets[:3] if not is_common else []
            })
        
        return results
    
    def get_architecture_template(self, architecture_type: str) -> Optional[Dict]:
        """Get a template architecture based on type"""
        patterns = self.training_data.get("architecture_patterns", [])
        
        type_lower = architecture_type.lower()
        best_match = None
        best_relevance = 0
        
        for pattern in patterns:
            pattern_name = pattern.get("name", "").lower()
            
            # Check for keyword matches
            keywords = type_lower.split()
            matches = sum(1 for kw in keywords if kw in pattern_name)
            
            if matches > best_relevance:
                best_relevance = matches
                best_match = pattern
        
        return best_match


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_service_detector() -> EnhancedServiceDetector:
    """Get singleton service detector instance"""
    return EnhancedServiceDetector()


def get_accuracy_scorer() -> AccuracyScorer:
    """Get singleton accuracy scorer instance"""
    return AccuracyScorer()


def get_prompt_builder() -> EnhancedPromptBuilder:
    """Get prompt builder instance"""
    return EnhancedPromptBuilder()


def get_learned_patterns() -> LearnedPatternsIntegration:
    """Get learned patterns integration instance"""
    return LearnedPatternsIntegration()
