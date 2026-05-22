"""
Reverse Engineering Module
==========================
Full reverse engineering of architecture diagrams from multiple sources:
- Draw.io XML files
- Visio (.vsdx) files
- Architecture images (PNG, JPG) via GPT-4o Vision
- Terraform files

Extracts services, connections, patterns, and generates requirements from diagrams.
"""

import os
import io
import json
import base64
import zipfile
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from config import agent_config, content_config

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
_ai_validator = None
_drawio_parser = None
_visio_parser = None


def _get_ai_validator():
    global _ai_validator
    if _ai_validator is None:
        from ai_validator import AIArchitectureValidator
        _ai_validator = AIArchitectureValidator()
    return _ai_validator


def _get_drawio_parser():
    global _drawio_parser
    if _drawio_parser is None:
        from drawio_parser import DrawioParser
        _drawio_parser = DrawioParser()
    return _drawio_parser


def _get_visio_parser_class():
    global _visio_parser
    if _visio_parser is None:
        from visio_to_drawio_converter import VisioParser
        _visio_parser = VisioParser
    return _visio_parser


# ═══════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ExtractedService:
    """A service extracted from a diagram"""
    name: str
    type: str = ""
    category: str = ""  # compute, data, networking, security, monitoring, integration, ai, storage
    confidence: float = 1.0
    source: str = ""  # "drawio", "visio", "image", "terraform"
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedConnection:
    """A connection extracted from a diagram"""
    source: str
    target: str
    connection_type: str = "https"
    label: str = ""
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedArchitecture:
    """Complete architecture extracted via reverse engineering"""
    services: List[ExtractedService] = field(default_factory=list)
    connections: List[ExtractedConnection] = field(default_factory=list)
    architecture_pattern: str = ""
    resource_groups: List[str] = field(default_factory=list)
    network_design: str = ""
    security_features: List[str] = field(default_factory=list)
    complexity: str = "Medium"
    source_type: str = ""  # "drawio", "visio", "image", "terraform"
    source_filename: str = ""
    requirements_inferred: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "services": [s.to_dict() for s in self.services],
            "connections": [c.to_dict() for c in self.connections],
            "architecture_pattern": self.architecture_pattern,
            "resource_groups": self.resource_groups,
            "network_design": self.network_design,
            "security_features": self.security_features,
            "complexity": self.complexity,
            "source_type": self.source_type,
            "source_filename": self.source_filename,
            "requirements_inferred": self.requirements_inferred,
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════════════
# AZURE SERVICE CATEGORIZER
# ═══════════════════════════════════════════════════════════════════

AZURE_CATEGORY_MAP = {
    "compute": [
        "app service", "azure functions", "virtual machine", "vm", "aks",
        "kubernetes", "container apps", "container instances", "batch",
        "cloud services", "service fabric", "spring apps", "web app"
    ],
    "data": [
        "sql database", "cosmos db", "postgresql", "mysql", "redis",
        "cache", "sql server", "mariadb", "table storage"
    ],
    "storage": [
        "storage account", "blob storage", "file storage", "data lake",
        "queue storage", "disk storage"
    ],
    "networking": [
        "virtual network", "vnet", "load balancer", "application gateway",
        "front door", "cdn", "traffic manager", "dns", "expressroute",
        "vpn gateway", "firewall", "bastion", "private endpoint", "nat gateway",
        "nsg", "network security group", "waf", "private link"
    ],
    "security": [
        "key vault", "managed identity", "entra id", "active directory",
        "sentinel", "defender", "security center", "ddos protection"
    ],
    "monitoring": [
        "application insights", "monitor", "log analytics", "alerts",
        "diagnostic", "dashboard"
    ],
    "integration": [
        "api management", "service bus", "event grid", "event hubs",
        "logic apps", "data factory", "synapse", "stream analytics"
    ],
    "ai": [
        "openai", "cognitive services", "bot service", "machine learning",
        "ai search", "form recognizer", "computer vision", "speech"
    ]
}


def categorize_service(service_name: str) -> str:
    """Categorize a service based on its name"""
    name_lower = service_name.lower()
    for category, keywords in AZURE_CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return "compute"  # default


# ═══════════════════════════════════════════════════════════════════
# REVERSE ENGINEER: DRAW.IO
# ═══════════════════════════════════════════════════════════════════

class DrawioReverseEngineer:
    """Reverse engineer architecture from Draw.io XML files"""

    def __init__(self):
        self.parser = _get_drawio_parser()

    async def reverse_engineer(self, xml_content: str, filename: str = "diagram.drawio") -> ExtractedArchitecture:
        """Extract full architecture from Draw.io XML"""
        logger.info(f"🔍 Reverse engineering Draw.io file: {filename}")

        try:
            parsed = self.parser.parse_drawio_file(xml_content)
        except Exception as e:
            logger.error(f"Draw.io parsing failed: {e}")
            raise ValueError(f"Failed to parse Draw.io file: {e}")

        # Extract services
        services = []
        seen_names = set()
        for component in parsed.get("components", []):
            label = component.get("label", "").strip()
            azure_service = component.get("azure_service", "")
            service_name = azure_service if azure_service else label
            if not service_name or service_name in seen_names:
                continue
            seen_names.add(service_name)

            services.append(ExtractedService(
                name=service_name,
                type=component.get("service_type", ""),
                category=categorize_service(service_name),
                confidence=0.9 if azure_service else 0.6,
                source="drawio",
                properties={
                    "id": component.get("id", ""),
                    "position": component.get("position", {}),
                    "is_container": component.get("is_container", False),
                }
            ))

        # Extract connections
        connections = []
        id_to_name = {}
        for component in parsed.get("components", []):
            cid = component.get("id", "")
            name = component.get("azure_service", "") or component.get("label", "")
            if cid and name:
                id_to_name[cid] = name

        for conn in parsed.get("connections", []):
            source_id = conn.get("source_id", conn.get("source", ""))
            target_id = conn.get("target_id", conn.get("target", ""))
            source_name = id_to_name.get(source_id, conn.get("source_label", source_id))
            target_name = id_to_name.get(target_id, conn.get("target_label", target_id))

            if source_name and target_name:
                connections.append(ExtractedConnection(
                    source=source_name,
                    target=target_name,
                    label=conn.get("label", ""),
                    connection_type=conn.get("type", "https"),
                    confidence=0.85,
                ))

        # Detect patterns from insights
        insights = parsed.get("architecture_insights", {})
        pattern = insights.get("architecture_patterns", ["Unknown"])[0] if insights.get("architecture_patterns") else "Unknown"

        # Detect resource groups from containers
        resource_groups = []
        for container in parsed.get("containers", []):
            label = container.get("label", "")
            if label:
                resource_groups.append(label)

        # Infer requirements from extracted information
        requirements = self._infer_requirements(services, connections, pattern)

        arch = ExtractedArchitecture(
            services=services,
            connections=connections,
            architecture_pattern=pattern,
            resource_groups=resource_groups,
            complexity=insights.get("complexity_assessment", "Medium"),
            source_type="drawio",
            source_filename=filename,
            requirements_inferred=requirements,
            metadata={
                "diagram_name": parsed.get("diagram_name", ""),
                "total_components": parsed.get("total_components", 0),
                "total_connections": parsed.get("total_connections", 0),
                "total_containers": parsed.get("total_containers", 0),
            }
        )

        logger.info(f"✅ Extracted {len(services)} services, {len(connections)} connections from Draw.io")
        return arch

    def _infer_requirements(self, services: List[ExtractedService], connections: List[ExtractedConnection], pattern: str) -> str:
        """Infer requirements text from extracted architecture"""
        service_names = [s.name for s in services]
        categories = set(s.category for s in services)

        parts = []
        parts.append(f"Architecture with {len(services)} Azure services using {pattern} pattern.")

        if "data" in categories:
            data_services = [s.name for s in services if s.category == "data"]
            parts.append(f"Data tier: {', '.join(data_services)}.")
        if "networking" in categories:
            parts.append("Network layer with VNet and security groups.")
        if "security" in categories:
            sec_services = [s.name for s in services if s.category == "security"]
            parts.append(f"Security: {', '.join(sec_services)}.")
        if "monitoring" in categories:
            parts.append("Monitoring and observability configured.")

        parts.append(f"Services: {', '.join(service_names[:15])}.")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════
# REVERSE ENGINEER: VISIO
# ═══════════════════════════════════════════════════════════════════

class VisioReverseEngineer:
    """Reverse engineer architecture from Visio (.vsdx) files"""

    async def reverse_engineer(self, file_bytes: bytes, filename: str = "diagram.vsdx") -> ExtractedArchitecture:
        """Extract architecture from Visio file"""
        logger.info(f"🔍 Reverse engineering Visio file: {filename}")

        import tempfile
        VisioParser = _get_visio_parser_class()

        # Write bytes to temp file for VisioParser
        with tempfile.NamedTemporaryFile(suffix=".vsdx", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            parser = VisioParser(tmp_path)
            parsed = parser.parse()
        except Exception as e:
            logger.error(f"Visio parsing failed: {e}")
            raise ValueError(f"Failed to parse Visio file: {e}")
        finally:
            os.unlink(tmp_path)

        # Extract services from shapes
        services = []
        seen_names = set()
        for shape in parsed.get("shapes", []):
            name = shape.text.strip() if hasattr(shape, "text") else (shape.get("text", "") or "").strip()
            master = shape.master_name if hasattr(shape, "master_name") else shape.get("master_name", "")
            shape_name = shape.name if hasattr(shape, "name") else shape.get("name", "")

            service_name = name or shape_name or master
            if not service_name or service_name in seen_names:
                continue
            seen_names.add(service_name)

            services.append(ExtractedService(
                name=service_name,
                type=master,
                category=categorize_service(service_name),
                confidence=0.7,
                source="visio",
                properties={
                    "shape_id": shape.id if hasattr(shape, "id") else shape.get("id", ""),
                    "shape_type": shape.shape_type if hasattr(shape, "shape_type") else shape.get("shape_type", ""),
                }
            ))

        # Extract connections
        connections = []
        shape_id_map = {}
        for shape in parsed.get("shapes", []):
            sid = shape.id if hasattr(shape, "id") else shape.get("id", "")
            sname = shape.text.strip() if hasattr(shape, "text") else (shape.get("text", "") or "").strip()
            shape_id_map[str(sid)] = sname or str(sid)

        for conn in parsed.get("connections", []):
            from_id = conn.from_shape_id if hasattr(conn, "from_shape_id") else conn.get("from_shape_id", "")
            to_id = conn.to_shape_id if hasattr(conn, "to_shape_id") else conn.get("to_shape_id", "")
            label = conn.label if hasattr(conn, "label") else conn.get("label", "")

            source_name = shape_id_map.get(str(from_id), str(from_id))
            target_name = shape_id_map.get(str(to_id), str(to_id))

            if source_name and target_name:
                connections.append(ExtractedConnection(
                    source=source_name,
                    target=target_name,
                    label=label,
                    connection_type="https",
                    confidence=0.7,
                ))

        arch = ExtractedArchitecture(
            services=services,
            connections=connections,
            architecture_pattern="Detected from Visio",
            source_type="visio",
            source_filename=filename,
            requirements_inferred=f"Visio architecture with {len(services)} services and {len(connections)} connections.",
            metadata={
                "pages": parsed.get("pages", []),
                "total_shapes": len(parsed.get("shapes", [])),
            }
        )

        logger.info(f"✅ Extracted {len(services)} services, {len(connections)} connections from Visio")
        return arch


# ═══════════════════════════════════════════════════════════════════
# REVERSE ENGINEER: IMAGE (GPT-4o Vision)
# ═══════════════════════════════════════════════════════════════════

class ImageReverseEngineer:
    """Reverse engineer architecture from images using GPT-4o Vision"""

    async def reverse_engineer(self, image_b64: str, content_type: str, filename: str = "diagram.png") -> ExtractedArchitecture:
        """Extract architecture from an image using GPT-4o Vision"""
        logger.info(f"🔍 Reverse engineering image: {filename}")

        validator = _get_ai_validator()

        try:
            analysis = await validator.analyze_diagram_image(image_b64, content_type, "Reverse engineer this architecture diagram")
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise ValueError(f"Failed to analyze image: {e}")

        # Build services
        services = []
        for svc_name in analysis.get("detected_services", []):
            services.append(ExtractedService(
                name=svc_name,
                category=categorize_service(svc_name),
                confidence=0.75,
                source="image",
            ))

        # Build connections
        connections = []
        for conn in analysis.get("connections", []):
            connections.append(ExtractedConnection(
                source=conn.get("source", ""),
                target=conn.get("target", ""),
                connection_type=conn.get("type", "https"),
                label=conn.get("label", ""),
                confidence=0.65,
            ))

        arch = ExtractedArchitecture(
            services=services,
            connections=connections,
            architecture_pattern=analysis.get("architecture_pattern", "Detected from Image"),
            resource_groups=analysis.get("resource_groups", []),
            network_design=analysis.get("network_design", ""),
            security_features=analysis.get("security_features", []),
            complexity=analysis.get("complexity_level", "Medium"),
            source_type="image",
            source_filename=filename,
            requirements_inferred=self._build_requirements(analysis),
            metadata={
                "compliance_assessment": analysis.get("compliance_assessment", {}),
                "critical_issues": analysis.get("critical_issues", []),
                "recommendations": analysis.get("recommendations", []),
            }
        )

        logger.info(f"✅ Extracted {len(services)} services, {len(connections)} connections from image")
        return arch

    def _build_requirements(self, analysis: Dict[str, Any]) -> str:
        """Build requirements text from image analysis"""
        parts = []
        pattern = analysis.get("architecture_pattern", "")
        services = analysis.get("detected_services", [])
        complexity = analysis.get("complexity_level", "Medium")

        if pattern:
            parts.append(f"{pattern} architecture pattern.")
        if services:
            parts.append(f"Uses {len(services)} services: {', '.join(services[:10])}.")
        if complexity:
            parts.append(f"Complexity: {complexity}.")
        if analysis.get("security_features"):
            parts.append(f"Security: {', '.join(analysis['security_features'][:5])}.")

        return " ".join(parts) or "Architecture detected from image."


# ═══════════════════════════════════════════════════════════════════
# REVERSE ENGINEER: TERRAFORM
# ═══════════════════════════════════════════════════════════════════

class TerraformReverseEngineer:
    """Reverse engineer architecture from Terraform files"""

    # Map Terraform resource types to Azure service names
    TF_RESOURCE_MAP = {
        "azurerm_resource_group": ("Resource Group", "networking"),
        "azurerm_virtual_network": ("Virtual Network", "networking"),
        "azurerm_subnet": ("Subnet", "networking"),
        "azurerm_network_security_group": ("Network Security Group", "networking"),
        "azurerm_public_ip": ("Public IP", "networking"),
        "azurerm_application_gateway": ("Application Gateway", "networking"),
        "azurerm_frontdoor": ("Azure Front Door", "networking"),
        "azurerm_cdn_profile": ("Azure CDN", "networking"),
        "azurerm_lb": ("Load Balancer", "networking"),
        "azurerm_private_endpoint": ("Private Endpoint", "networking"),
        "azurerm_dns_zone": ("DNS Zone", "networking"),
        "azurerm_firewall": ("Azure Firewall", "networking"),
        "azurerm_nat_gateway": ("NAT Gateway", "networking"),
        "azurerm_bastion_host": ("Azure Bastion", "networking"),
        "azurerm_app_service": ("App Service", "compute"),
        "azurerm_linux_web_app": ("App Service (Linux)", "compute"),
        "azurerm_windows_web_app": ("App Service (Windows)", "compute"),
        "azurerm_function_app": ("Azure Functions", "compute"),
        "azurerm_linux_function_app": ("Azure Functions (Linux)", "compute"),
        "azurerm_service_plan": ("App Service Plan", "compute"),
        "azurerm_kubernetes_cluster": ("Azure Kubernetes Service", "compute"),
        "azurerm_container_app": ("Container Apps", "compute"),
        "azurerm_container_group": ("Container Instances", "compute"),
        "azurerm_virtual_machine": ("Virtual Machine", "compute"),
        "azurerm_linux_virtual_machine": ("Virtual Machine (Linux)", "compute"),
        "azurerm_windows_virtual_machine": ("Virtual Machine (Windows)", "compute"),
        "azurerm_mssql_server": ("SQL Server", "data"),
        "azurerm_mssql_database": ("SQL Database", "data"),
        "azurerm_postgresql_server": ("PostgreSQL Database", "data"),
        "azurerm_postgresql_flexible_server": ("PostgreSQL Flexible Server", "data"),
        "azurerm_mysql_server": ("MySQL Database", "data"),
        "azurerm_cosmosdb_account": ("Cosmos DB", "data"),
        "azurerm_redis_cache": ("Azure Cache for Redis", "data"),
        "azurerm_storage_account": ("Storage Account", "storage"),
        "azurerm_storage_container": ("Blob Container", "storage"),
        "azurerm_key_vault": ("Key Vault", "security"),
        "azurerm_user_assigned_identity": ("Managed Identity", "security"),
        "azurerm_api_management": ("API Management", "integration"),
        "azurerm_servicebus_namespace": ("Service Bus", "integration"),
        "azurerm_eventhub_namespace": ("Event Hubs", "integration"),
        "azurerm_eventgrid_topic": ("Event Grid", "integration"),
        "azurerm_logic_app_workflow": ("Logic Apps", "integration"),
        "azurerm_data_factory": ("Data Factory", "integration"),
        "azurerm_application_insights": ("Application Insights", "monitoring"),
        "azurerm_log_analytics_workspace": ("Log Analytics", "monitoring"),
        "azurerm_monitor_action_group": ("Azure Monitor", "monitoring"),
        "azurerm_cognitive_account": ("Cognitive Services", "ai"),
    }

    async def reverse_engineer(self, zip_bytes: bytes, filename: str = "terraform.zip") -> ExtractedArchitecture:
        """Extract architecture from Terraform ZIP file"""
        logger.info(f"🔍 Reverse engineering Terraform: {filename}")

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                tf_files = [f for f in zf.namelist() if f.endswith('.tf') or f.endswith('.tf.json')]
                if not tf_files:
                    raise ValueError("No .tf files found in ZIP")

                all_content = ""
                for tf_file in tf_files:
                    with zf.open(tf_file) as f:
                        all_content += f.read().decode('utf-8', errors='replace') + "\n"
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")

        # Parse resources
        import re
        resource_pattern = re.compile(r'resource\s+"(\w+)"\s+"(\w+)"')
        found_resources = resource_pattern.findall(all_content)

        services = []
        seen = set()
        for resource_type, resource_name in found_resources:
            mapped = self.TF_RESOURCE_MAP.get(resource_type)
            if mapped:
                service_name, category = mapped
                display_name = f"{service_name} ({resource_name})"
                if display_name not in seen:
                    seen.add(display_name)
                    services.append(ExtractedService(
                        name=display_name,
                        type=resource_type,
                        category=category,
                        confidence=0.95,
                        source="terraform",
                        properties={"resource_name": resource_name}
                    ))
            else:
                if resource_type not in seen:
                    seen.add(resource_type)
                    services.append(ExtractedService(
                        name=resource_type,
                        type=resource_type,
                        category="compute",
                        confidence=0.5,
                        source="terraform",
                    ))

        # Infer connections from references
        connections = self._infer_connections(all_content, services)

        arch = ExtractedArchitecture(
            services=services,
            connections=connections,
            architecture_pattern="Infrastructure as Code",
            source_type="terraform",
            source_filename=filename,
            complexity="Medium" if len(services) <= content_config.COMPLEXITY_THRESHOLD else "High",
            requirements_inferred=f"Terraform deployment with {len(services)} resources across {len(tf_files)} files.",
            metadata={
                "terraform_files": tf_files,
                "total_resources": len(found_resources),
            }
        )

        logger.info(f"✅ Extracted {len(services)} services, {len(connections)} connections from Terraform")
        return arch

    def _infer_connections(self, content: str, services: List[ExtractedService]) -> List[ExtractedConnection]:
        """Infer connections from Terraform resource references"""
        import re
        connections = []
        seen = set()

        # Look for resource references like azurerm_xxx.name.id
        ref_pattern = re.compile(r'(\w+)\.(\w+)\.id')
        refs = ref_pattern.findall(content)

        # Build resource type -> service name map
        type_map = {}
        for svc in services:
            if svc.properties.get("resource_name"):
                type_map[svc.properties["resource_name"]] = svc.name

        for ref_type, ref_name in refs:
            target = type_map.get(ref_name, ref_name)
            # Find current resource context (simplified)
            for svc in services:
                if svc.properties.get("resource_name") and svc.name != target:
                    key = (svc.name, target)
                    if key not in seen:
                        seen.add(key)
                        connections.append(ExtractedConnection(
                            source=svc.name,
                            target=target,
                            connection_type="reference",
                            confidence=0.6,
                        ))

        return connections[:50]  # Limit


# ═══════════════════════════════════════════════════════════════════
# AI-ENHANCED ANALYSIS (uses GPT-4o for deeper insights)
# ═══════════════════════════════════════════════════════════════════

class AIArchitectureAnalyzer:
    """Use GPT-4o to provide deeper analysis of extracted architecture"""

    async def enhance_extraction(self, architecture: ExtractedArchitecture) -> Dict[str, Any]:
        """Enhance extracted architecture with AI-powered analysis"""
        validator = _get_ai_validator()

        service_names = [s.name for s in architecture.services]
        connection_list = [{"from": c.source, "to": c.target, "label": c.label} for c in architecture.connections]

        prompt = f"""Analyze this extracted Azure architecture and provide a thorough enhancement assessment.

SERVICES DETECTED ({len(service_names)} total): {json.dumps(service_names, indent=2)}
CONNECTIONS ({len(connection_list)} total): {json.dumps(connection_list, indent=2)}
SOURCE FORMAT: {architecture.source_type}
DETECTED PATTERN: {architecture.architecture_pattern}

Your task:
1. Identify the architecture pattern (e.g. microservices, hub-spoke, n-tier, event-driven, serverless)
2. Find MISSING services that a production-grade architecture like this should have (monitoring, security, caching, etc.)
3. Find MISSING connections between existing services
4. Assess security posture (identity, network, data protection, compliance readiness)
5. Assess performance characteristics (caching, scaling, async patterns, bottlenecks)
6. Infer the complete business requirements this architecture was built to serve
7. Score each Well-Architected Framework pillar from 0-100 based on the services present:
   - Security: identity services? firewalls? WAF? key vault? private endpoints? managed identity?
   - Reliability: redundancy? multi-region? health probes? retry patterns? backups?
   - Performance: caching? CDN? auto-scaling? load balancing? async processing?
   - Cost Optimization: right-sized tiers? serverless? reserved instances? lifecycle policies?
   - Operational Excellence: monitoring? logging? CI/CD? IaC? alerting? dashboards?

Be SPECIFIC and REALISTIC with scores — don't default everything to 0. If the architecture has App Service + SQL + Key Vault, security is at least 40-50. If it has Application Gateway, performance is at least 50-60. Even a basic architecture should get at least 20-30 in most pillars.

Return JSON:
{{
    "architecture_pattern": "identified pattern name",
    "missing_services": ["services that should be present but are missing"],
    "missing_connections": [{{"from": "A", "to": "B", "label": "reason"}}],
    "security_assessment": "2-3 sentence security evaluation with specific findings",
    "performance_assessment": "2-3 sentence performance evaluation with specific findings",
    "inferred_requirements": "Detailed requirements text (3-5 sentences) inferred from the diagram",
    "recommendations": ["specific, actionable improvements — at least 5"],
    "well_architected_scores": {{
        "security": <realistic 0-100 score>,
        "reliability": <realistic 0-100 score>,
        "performance": <realistic 0-100 score>,
        "cost_optimization": <realistic 0-100 score>,
        "operational_excellence": <realistic 0-100 score>
    }}
}}"""

        try:
            response = validator.client.chat.completions.create(
                model=validator.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a Principal Azure Solutions Architect with 15+ years experience. Analyze architectures thoroughly and provide REALISTIC scores (not all zeros). Base scores on what services are actually present. Respond with valid JSON only. No markdown."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,
                temperature=agent_config.AGENT_TEMPERATURE
            )
            content = response.choices[0].message.content
            cleaned = validator._clean_json_response(content)
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
            return {
                "architecture_pattern": architecture.architecture_pattern,
                "missing_services": [],
                "missing_connections": [],
                "inferred_requirements": architecture.requirements_inferred,
                "recommendations": [],
                "error": str(e)
            }


# ═══════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

class ReverseEngineerOrchestrator:
    """Orchestrates reverse engineering from any source"""

    def __init__(self):
        self.drawio_re = DrawioReverseEngineer()
        self.visio_re = VisioReverseEngineer()
        self.image_re = ImageReverseEngineer()
        self.terraform_re = TerraformReverseEngineer()
        self.ai_analyzer = AIArchitectureAnalyzer()

    async def reverse_engineer_drawio(self, xml_content: str, filename: str = "diagram.drawio", enhance_with_ai: bool = True) -> Dict[str, Any]:
        """Reverse engineer a Draw.io file"""
        architecture = await self.drawio_re.reverse_engineer(xml_content, filename)
        return await self._build_response(architecture, enhance_with_ai)

    async def reverse_engineer_visio(self, file_bytes: bytes, filename: str = "diagram.vsdx", enhance_with_ai: bool = True) -> Dict[str, Any]:
        """Reverse engineer a Visio file"""
        architecture = await self.visio_re.reverse_engineer(file_bytes, filename)
        return await self._build_response(architecture, enhance_with_ai)

    async def reverse_engineer_image(self, image_b64: str, content_type: str, filename: str = "diagram.png", enhance_with_ai: bool = True) -> Dict[str, Any]:
        """Reverse engineer an image"""
        architecture = await self.image_re.reverse_engineer(image_b64, content_type, filename)
        return await self._build_response(architecture, enhance_with_ai)

    async def reverse_engineer_terraform(self, zip_bytes: bytes, filename: str = "terraform.zip", enhance_with_ai: bool = True) -> Dict[str, Any]:
        """Reverse engineer Terraform files"""
        architecture = await self.terraform_re.reverse_engineer(zip_bytes, filename)
        return await self._build_response(architecture, enhance_with_ai)

    async def _build_response(self, architecture: ExtractedArchitecture, enhance_with_ai: bool) -> Dict[str, Any]:
        """Build standardized response from extracted architecture"""
        # Optionally enhance with AI
        ai_enhancement = {}
        if enhance_with_ai:
            try:
                ai_enhancement = await self.ai_analyzer.enhance_extraction(architecture)
                # Update inferred requirements if AI provided better ones
                if ai_enhancement.get("inferred_requirements"):
                    architecture.requirements_inferred = ai_enhancement["inferred_requirements"]
                if ai_enhancement.get("architecture_pattern"):
                    architecture.architecture_pattern = ai_enhancement["architecture_pattern"]
            except Exception as e:
                logger.warning(f"AI enhancement skipped: {e}")

        # Build Draw.io XML from extracted architecture
        drawio_xml = None
        try:
            from drawio_parser import generate_drawio_from_architecture
            arch_dict = {
                "services": [{"name": s.name, "type": s.type, "category": s.category} for s in architecture.services],
                "connections": [{"source": c.source, "target": c.target, "type": c.connection_type, "label": c.label} for c in architecture.connections],
                "architecture_pattern": architecture.architecture_pattern,
            }
            drawio_xml = await generate_drawio_from_architecture(arch_dict, architecture.requirements_inferred or "Reverse engineered architecture")
        except Exception as e:
            logger.warning(f"Draw.io generation failed: {e}")

        return {
            "status": "success",
            "source_type": architecture.source_type,
            "source_filename": architecture.source_filename,
            "architecture": architecture.to_dict(),
            "drawio_xml": drawio_xml,
            "ai_enhancement": ai_enhancement,
            "summary": {
                "total_services": len(architecture.services),
                "total_connections": len(architecture.connections),
                "architecture_pattern": architecture.architecture_pattern,
                "complexity": architecture.complexity,
                "inferred_requirements": architecture.requirements_inferred,
                "categories": self._count_categories(architecture.services),
            },
            "timestamp": datetime.now().isoformat()
        }

    def _count_categories(self, services: List[ExtractedService]) -> Dict[str, int]:
        """Count services by category"""
        counts = {}
        for s in services:
            counts[s.category] = counts.get(s.category, 0) + 1
        return counts
