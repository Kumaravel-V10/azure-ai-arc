"""
Draw.io XML Parser and Generator
Handles parsing .drawio files and extracting architectural components for analysis
Uses DrawioReferenceAnalyzer for intelligent connection labels and layouts
"""

import xml.etree.ElementTree as ET
import json
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
import re
import time
import hashlib
import logging
from config import drawio_config, theme_config

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_reference_analyzer = None

def _get_reference_analyzer():
    """Get the reference analyzer lazily to avoid circular imports"""
    global _reference_analyzer
    if _reference_analyzer is None:
        try:
            from drawio_reference_analyzer import get_reference_analyzer
            _reference_analyzer = get_reference_analyzer()
        except Exception as e:
            logger.warning(f"Could not load reference analyzer: {e}")
            _reference_analyzer = None
    return _reference_analyzer

class DrawioParser:
    """Parse and analyze Draw.io XML files"""
    
    def __init__(self):
        self.azure_service_mappings = {
            # Compute Services
            "Function_Apps.svg": "Azure Functions",
            "App_Services.svg": "App Service",
            "Virtual_Machine.svg": "Virtual Machine",
            "App_Service_Plans.svg": "App Service Plan",
            "Kubernetes_Services.svg": "Azure Kubernetes Service",
            
            # Networking
            "Application_Gateways.svg": "Application Gateway",
            "Front_Doors.svg": "Azure Front Door",
            "Load_Balancers.svg": "Load Balancer",
            "Virtual_Networks.svg": "Virtual Network",
            "Network_Security_Groups.svg": "Network Security Group",
            "Private_Endpoint.svg": "Private Endpoint",
            "DNS_Zones.svg": "DNS Zone",
            
            # Storage & Data
            "Storage_Accounts.svg": "Storage Account",
            "Azure_Database_PostgreSQL_Server.svg": "PostgreSQL Database",
            "Cache_Redis.svg": "Redis Cache",
            "SQL_Database.svg": "SQL Database",
            "Azure_Cosmos_DB.svg": "Cosmos DB",
            
            # Security & Identity
            "Key_Vaults.svg": "Key Vault",
            "Managed_Identities.svg": "Managed Identity",
            "Entra_ID_Protection.svg": "Entra ID",
            "Certificates.svg": "SSL Certificate",
            "Web_Application_Firewall_Policies_WAF.svg": "WAF Policy",
            
            # Monitoring & Management
            "Application_Insights.svg": "Application Insights",
            "Log_Analytics_Workspaces.svg": "Log Analytics",
            "Monitor.svg": "Azure Monitor",
            "API_Management_Services.svg": "API Management",
            "App_Configuration.svg": "App Configuration"
        }
    
    def parse_drawio_file(self, file_content: str) -> Dict[str, Any]:
        """Parse a Draw.io XML file and extract architectural components"""
        try:
            root = ET.fromstring(file_content)
            
            # Find the diagram element
            diagram = root.find('.//diagram')
            if diagram is None:
                raise ValueError("No diagram found in Draw.io file")
            
            # Find the mxGraphModel
            model = diagram.find('.//mxGraphModel')
            if model is None:
                raise ValueError("No mxGraphModel found in diagram")
            
            # Parse components and connections
            components = self._extract_components(model)
            connections = self._extract_connections(model)
            containers = self._extract_containers(model)
            
            return {
                "diagram_name": diagram.get('name', 'Untitled'),
                "diagram_id": diagram.get('id', ''),
                "total_components": len(components),
                "total_connections": len(connections),
                "total_containers": len(containers),
                "components": components,
                "connections": connections,
                "containers": containers,
                "azure_services": self._categorize_azure_services(components),
                "architecture_insights": self._analyze_architecture(components, connections, containers)
            }
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing Draw.io file: {str(e)}")
    
    def _extract_components(self, model: ET.Element) -> List[Dict[str, Any]]:
        """Extract individual components (mxCell with vertex=1)"""
        components = []
        
        for cell in model.findall('.//mxCell[@vertex="1"]'):
            cell_id = cell.get('id', '')
            if cell_id in ['0', '1']:  # Skip root cells
                continue
                
            # Extract geometry
            geometry = cell.find('mxGeometry')
            position = {}
            if geometry is not None:
                position = {
                    "x": float(geometry.get('x', 0)),
                    "y": float(geometry.get('y', 0)),
                    "width": float(geometry.get('width', 64)),
                    "height": float(geometry.get('height', 64))
                }
            
            # Parse style to extract service type
            style = cell.get('style', '')
            service_type = self._extract_service_type_from_style(style)
            
            component = {
                "id": cell_id,
                "label": cell.get('value', ''),
                "service_type": service_type,
                "style": style,
                "position": position,
                "is_container": 'swimlane' in style.lower(),
                "azure_service": self._map_to_azure_service(service_type, style)
            }
            
            components.append(component)
        
        return components
    
    def _extract_connections(self, model: ET.Element) -> List[Dict[str, Any]]:
        """Extract connections (mxCell with edge=1)"""
        connections = []
        
        for cell in model.findall('.//mxCell[@edge="1"]'):
            connection = {
                "id": cell.get('id', ''),
                "label": cell.get('value', ''),
                "source": cell.get('source', ''),
                "target": cell.get('target', ''),
                "style": cell.get('style', ''),
                "connection_type": self._determine_connection_type(cell.get('style', ''))
            }
            
            connections.append(connection)
        
        return connections
    
    def _extract_containers(self, model: ET.Element) -> List[Dict[str, Any]]:
        """Extract containers (Resource Groups, VNets, Subnets)"""
        containers = []
        
        for cell in model.findall('.//mxCell'):
            style = cell.get('style', '')
            if 'swimlane' in style.lower() or 'container' in cell.get('id', '').lower():
                container = {
                    "id": cell.get('id', ''),
                    "label": cell.get('value', ''),
                    "type": self._determine_container_type(cell.get('value', ''), style),
                    "style": style
                }
                containers.append(container)
        
        return containers
    
    def _extract_service_type_from_style(self, style: str) -> str:
        """Extract Azure service type from mxCell style"""
        # Look for image path in style
        image_match = re.search(r'image=([^;]+)', style)
        if image_match:
            image_path = image_match.group(1)
            # Extract filename from path
            filename = image_path.split('/')[-1]
            return filename
        
        # Look for specific style indicators
        if 'Function_Apps' in style:
            return 'Function_Apps.svg'
        elif 'App_Services' in style:
            return 'App_Services.svg'
        elif 'Storage_Accounts' in style:
            return 'Storage_Accounts.svg'
        
        return 'unknown'
    
    def _map_to_azure_service(self, service_type: str, style: str) -> str:
        """Map service type to Azure service name"""
        # Direct mapping from filename
        if service_type in self.azure_service_mappings:
            return self.azure_service_mappings[service_type]
        
        # Fallback mapping based on style content
        style_lower = style.lower()
        for key, service in self.azure_service_mappings.items():
            if key.lower().replace('.svg', '').replace('_', '') in style_lower:
                return service
        
        return "Azure Service"
    
    def _determine_connection_type(self, style: str) -> str:
        """Determine the type of connection based on style"""
        if 'dashed' in style.lower():
            return 'dependency'
        elif 'arrow' in style.lower():
            return 'data_flow'
        else:
            return 'connection'
    
    def _determine_container_type(self, label: str, style: str) -> str:
        """Determine container type from label and style"""
        label_lower = label.lower()
        
        if 'resource group' in label_lower or 'rg-' in label_lower:
            return 'resource_group'
        elif 'vnet' in label_lower or 'virtual network' in label_lower:
            return 'virtual_network'
        elif 'subnet' in label_lower or 'snet-' in label_lower:
            return 'subnet'
        elif 'subscription' in label_lower:
            return 'subscription'
        else:
            return 'container'
    
    def _categorize_azure_services(self, components: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize Azure services by type"""
        categories = {
            "Compute": [],
            "Networking": [],
            "Storage & Data": [],
            "Security & Identity": [],
            "Monitoring & Management": [],
            "Integration": [],
            "Containers": []
        }
        
        for component in components:
            if component['is_container']:
                categories["Containers"].append(component['label'])
                continue
                
            service = component['azure_service']
            service_type = component['service_type']
            
            # Categorize based on service type
            if any(x in service_type for x in ['Function_Apps', 'App_Services', 'Virtual_Machine', 'Kubernetes']):
                categories["Compute"].append(service)
            elif any(x in service_type for x in ['Application_Gateways', 'Front_Doors', 'Load_Balancers', 'Virtual_Networks', 'Network_Security']):
                categories["Networking"].append(service)
            elif any(x in service_type for x in ['Storage_Accounts', 'PostgreSQL', 'Redis', 'SQL_Database', 'Cosmos']):
                categories["Storage & Data"].append(service)
            elif any(x in service_type for x in ['Key_Vaults', 'Managed_Identities', 'Entra_ID', 'Certificates']):
                categories["Security & Identity"].append(service)
            elif any(x in service_type for x in ['Application_Insights', 'Log_Analytics', 'Monitor']):
                categories["Monitoring & Management"].append(service)
            elif any(x in service_type for x in ['API_Management', 'App_Configuration']):
                categories["Integration"].append(service)
            else:
                categories["Integration"].append(service)
        
        # Remove empty categories and duplicates
        return {k: list(set(v)) for k, v in categories.items() if v}
    
    def _analyze_architecture(self, components: List[Dict[str, Any]], 
                            connections: List[Dict[str, Any]], 
                            containers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the architecture and provide insights"""
        
        # Count service types
        service_counts = {}
        for component in components:
            service = component['azure_service']
            service_counts[service] = service_counts.get(service, 0) + 1
        
        # Analyze connections
        connection_analysis = {
            "total_connections": len(connections),
            "connection_types": {},
            "highly_connected_services": []
        }
        
        # Count connection types
        for conn in connections:
            conn_type = conn['connection_type']
            connection_analysis["connection_types"][conn_type] = connection_analysis["connection_types"].get(conn_type, 0) + 1
        
        # Find services with many connections
        service_connections = {}
        for conn in connections:
            source = conn['source']
            target = conn['target']
            service_connections[source] = service_connections.get(source, 0) + 1
            service_connections[target] = service_connections.get(target, 0) + 1
        
        # Get top 3 most connected services
        sorted_connections = sorted(service_connections.items(), key=lambda x: x[1], reverse=True)[:3]
        for service_id, count in sorted_connections:
            # Find the component with this ID
            for component in components:
                if component['id'] == service_id:
                    connection_analysis["highly_connected_services"].append({
                        "service": component['azure_service'],
                        "label": component['label'],
                        "connections": count
                    })
                    break
        
        # Architecture patterns
        architecture_patterns = []
        if any('API Management' in comp['azure_service'] for comp in components):
            architecture_patterns.append("API Gateway Pattern")
        if any('Function' in comp['azure_service'] for comp in components):
            architecture_patterns.append("Serverless Pattern")
        if len([comp for comp in components if 'Database' in comp['azure_service'] or 'SQL' in comp['azure_service']]) > 0:
            architecture_patterns.append("Data Persistence Layer")
        if any('Front Door' in comp['azure_service'] for comp in components):
            architecture_patterns.append("Global Load Balancing")
        
        return {
            "service_counts": service_counts,
            "total_unique_services": len(service_counts),
            "connection_analysis": connection_analysis,
            "architecture_patterns": architecture_patterns,
            "container_structure": {
                "resource_groups": len([c for c in containers if c['type'] == 'resource_group']),
                "virtual_networks": len([c for c in containers if c['type'] == 'virtual_network']),
                "subnets": len([c for c in containers if c['type'] == 'subnet'])
            },
            "complexity_assessment": self._assess_complexity(components, connections, containers)
        }
    
    def _assess_complexity(self, components: List[Dict[str, Any]], 
                          connections: List[Dict[str, Any]], 
                          containers: List[Dict[str, Any]]) -> str:
        """Assess the complexity of the architecture"""
 
        return "Enterprise-scale"

    async def generate_drawio_xml(self, architecture: Dict[str, Any], requirements: str) -> str:
        """Generate a Draw.io XML diagram with MULTIPLE Resource Groups arranged side-by-side.
        Supports the real-world Azure pattern:
          Subscription
            +-- Edge Services (outside all RGs: Front Door, CDN, WAF, Users)
            +-- RG-1 (e.g. Tenant UI) --- VNet-1 --- Subnets --- Services
            +-- RG-2 (e.g. Shared Backend) --- VNet-2 --- Subnets --- Services
            +-- RG-3 (e.g. Monitoring/Security, no VNet) --- Services
            +-- VNet Peering connections between VNets
        Connections use fuzzy name matching so they are never silently dropped.
        Canvas size adapts dynamically."""

        services = architecture.get("services", [])
        connections = architecture.get("connections", [])
        containers = architecture.get("containers", [])
        project_name = str(architecture.get("project_name", "Azure Architecture"))
        annotations = architecture.get("annotations", [])

        # Normalize services to list of dicts
        normalized_services = []
        for svc in services:
            if isinstance(svc, dict) and "name" in svc:
                normalized_services.append(svc)
            elif isinstance(svc, str):
                normalized_services.append({"name": svc, "category": self._infer_category(svc)})

        if not normalized_services:
            return self._generate_empty_diagram(project_name)

        # -- Parse containers --
        resource_groups = [c for c in containers if c.get("type") == "resource_group"]
        virtual_networks = [c for c in containers if c.get("type") == "virtual_network"]
        subnet_list = [c for c in containers if c.get("type") == "subnet"]

        rg_names = {rg["name"] for rg in resource_groups}
        vnet_names = {vn["name"] for vn in virtual_networks}
        subnet_names = {sn["name"] for sn in subnet_list}

        # Map VNet -> RG (explicit or auto-assign to first RG)
        vnet_to_rg = {}
        for vn in virtual_networks:
            rg = vn.get("resource_group", "")
            if rg and rg in rg_names:
                vnet_to_rg[vn["name"]] = rg
            elif resource_groups:
                vnet_to_rg[vn["name"]] = resource_groups[0]["name"]

        # Map subnet -> VNet
        subnet_to_vnet = {}
        for sn in subnet_list:
            vn = sn.get("virtual_network", "")
            if vn and vn in vnet_names:
                subnet_to_vnet[sn["name"]] = vn
            elif virtual_networks:
                subnet_to_vnet[sn["name"]] = virtual_networks[0]["name"]

        # Auto-create defaults if missing
        if not resource_groups:
            slug = project_name.lower().replace(" ", "-")[:20]
            resource_groups = [{"name": f"rg-{slug}", "type": "resource_group", "purpose": "Primary Resources"}]
            rg_names = {resource_groups[0]["name"]}

        # -- Build hierarchy: RG -> VNet -> Subnet -> Services --
        rg_data = {}
        for rg in resource_groups:
            rg_data[rg["name"]] = {"meta": rg, "vnets": {}, "loose": []}

        for vn in virtual_networks:
            rg_name = vnet_to_rg.get(vn["name"], resource_groups[0]["name"])
            if rg_name not in rg_data:
                rg_data[rg_name] = {"meta": {"name": rg_name, "type": "resource_group"}, "vnets": {}, "loose": []}
            rg_data[rg_name]["vnets"][vn["name"]] = {"meta": vn, "subnets": {}, "loose": []}

        for sn in subnet_list:
            vn_name = subnet_to_vnet.get(sn["name"])
            if vn_name:
                rg_name = vnet_to_rg.get(vn_name, resource_groups[0]["name"])
                if rg_name in rg_data and vn_name in rg_data[rg_name]["vnets"]:
                    rg_data[rg_name]["vnets"][vn_name]["subnets"][sn["name"]] = {"meta": sn, "services": []}

        # -- Classify services into the hierarchy --
        edge_keywords = ["front door", "cdn", "waf", "web application firewall",
                         "traffic manager", "ddos", "internet user", "user",
                         "ssl certificate", "ssl", "certificate"]
        edge_services = []
        unassigned = []

        for svc in normalized_services:
            name_lower = svc["name"].lower()
            cat = svc.get("category", "compute")
            svc_rg = svc.get("resource_group", "")
            svc_subnet = svc.get("subnet", "")

            # Edge / subscription level
            is_edge_keyword = any(k in name_lower for k in edge_keywords)
            if svc_rg == "edge" or svc_subnet == "edge" or \
               (not svc_rg and not svc_subnet and cat == "external") or \
               (not svc_rg and is_edge_keyword):
                edge_services.append(svc)
                continue

            # Has explicit RG
            if svc_rg and svc_rg in rg_data:
                if svc_subnet and svc_subnet in subnet_to_vnet:
                    vn = subnet_to_vnet[svc_subnet]
                    if vn in rg_data[svc_rg]["vnets"] and svc_subnet in rg_data[svc_rg]["vnets"][vn]["subnets"]:
                        rg_data[svc_rg]["vnets"][vn]["subnets"][svc_subnet]["services"].append(svc)
                    else:
                        rg_data[svc_rg]["loose"].append(svc)
                elif svc_subnet:
                    placed = False
                    for vn_name_i, vn_d_i in rg_data[svc_rg]["vnets"].items():
                        if svc_subnet in vn_d_i["subnets"]:
                            vn_d_i["subnets"][svc_subnet]["services"].append(svc)
                            placed = True
                            break
                    if not placed:
                        rg_data[svc_rg]["loose"].append(svc)
                else:
                    rg_data[svc_rg]["loose"].append(svc)
                continue

            unassigned.append(svc)

        # -- Smart auto-assignment of unassigned services --
        for svc in unassigned:
            cat = svc.get("category", "compute")
            svc_subnet = svc.get("subnet", "")
            name_lower = svc["name"].lower()
            placed = False

            # If has subnet reference, follow it
            if svc_subnet and svc_subnet in subnet_to_vnet:
                vn = subnet_to_vnet[svc_subnet]
                rg = vnet_to_rg.get(vn, resource_groups[0]["name"])
                if rg in rg_data and vn in rg_data[rg]["vnets"]:
                    if svc_subnet in rg_data[rg]["vnets"][vn]["subnets"]:
                        rg_data[rg]["vnets"][vn]["subnets"][svc_subnet]["services"].append(svc)
                        placed = True

            # Monitoring/security -> dedicated monitoring RG
            if not placed and cat in ("monitoring", "security"):
                monitor_rg = next(
                    (n for n in rg_data if any(k in n.lower() for k in ["monitor", "security", "observ", "mgmt"])),
                    None
                )
                if monitor_rg:
                    rg_data[monitor_rg]["loose"].append(svc)
                    placed = True

            # Compute/data/integration/ai -> first RG with VNets, auto-match subnet
            if not placed and cat in ("compute", "data", "integration", "ai", "networking"):
                rg_with_vnet = next((n for n, d in rg_data.items() if d["vnets"]), None)
                if rg_with_vnet:
                    first_vn = list(rg_data[rg_with_vnet]["vnets"].keys())[0]
                    vn_d = rg_data[rg_with_vnet]["vnets"][first_vn]
                    matched_sn = None
                    for sn_name_i, sn_d_i in vn_d["subnets"].items():
                        purpose = (sn_d_i["meta"].get("purpose", "") + " " + sn_name_i).lower()
                        if cat == "data" and any(k in purpose for k in ["data", "database", "sql", "redis"]):
                            matched_sn = sn_name_i
                            break
                        elif cat == "compute" and any(k in purpose for k in ["backend", "compute", "app", "function"]):
                            matched_sn = sn_name_i
                            break
                        elif cat == "integration" and any(k in purpose for k in ["integration", "apim", "api"]):
                            matched_sn = sn_name_i
                            break
                        elif cat == "ai" and any(k in purpose for k in ["ai", "ml", "cognitive"]):
                            matched_sn = sn_name_i
                            break
                        elif cat == "networking" and any(k in purpose for k in ["frontend", "web", "ingress", "gateway"]):
                            matched_sn = sn_name_i
                            break
                    if matched_sn:
                        vn_d["subnets"][matched_sn]["services"].append(svc)
                    else:
                        vn_d["loose"].append(svc)
                    placed = True

            # Fallback: first RG loose
            if not placed:
                first_rg = list(rg_data.keys())[0]
                rg_data[first_rg]["loose"].append(svc)

        # -- Layout constants (generous spacing for clean orthogonal routing) --
        svc_w, svc_h = 64, 64
        h_gap = 160          # horizontal distance between service centers
        v_gap = 120          # vertical distance between service rows
        pad = 30             # padding inside containers
        header_h = 32
        max_per_row = 4      # max services per row (4 gives professional look)
        rg_spacing = 45      # gap between side-by-side resource groups

        def _zone_dims(svc_list):
            if not svc_list:
                return 0, 0
            rows = (len(svc_list) + max_per_row - 1) // max_per_row
            cols = min(len(svc_list), max_per_row)
            return cols * h_gap + pad, rows * v_gap + pad

        # -- Calculate dimensions bottom-up --
        rg_dims = {}
        for rg_name, rg_d in rg_data.items():
            rg_h = header_h + pad
            rg_w = 0
            vnet_dims_map = {}

            for vn_name, vn_d in rg_d["vnets"].items():
                vn_h = header_h + pad
                vn_w = 0
                sn_dims = {}
                for sn_name, sn_d in vn_d["subnets"].items():
                    sw, sh = _zone_dims(sn_d["services"])
                    sn_total_h = max(sh + 28 + pad, 90)
                    sn_total_w = max(sw + pad * 2, 280)
                    sn_dims[sn_name] = (sn_total_w, sn_total_h)
                    vn_h += sn_total_h + pad
                    vn_w = max(vn_w, sn_total_w)

                if vn_d["loose"]:
                    lw, lh = _zone_dims(vn_d["loose"])
                    vn_h += lh + pad
                    vn_w = max(vn_w, lw)

                vn_w = max(vn_w + pad * 2, 320)
                vnet_dims_map[vn_name] = {"w": vn_w, "h": vn_h, "subnet_dims": sn_dims}
                rg_h += vn_h + pad
                rg_w = max(rg_w, vn_w)

            if rg_d["loose"]:
                lw, lh = _zone_dims(rg_d["loose"])
                rg_h += lh + pad
                rg_w = max(rg_w, lw)

            rg_w = max(rg_w + pad * 2, 260)
            rg_h = max(rg_h, 180)
            rg_dims[rg_name] = {"w": rg_w, "h": rg_h, "vnet_dims": vnet_dims_map}

        # Edge dimensions
        edge_w, edge_h = _zone_dims(edge_services)

        # Subscription dimensions
        total_rg_w = sum(d["w"] for d in rg_dims.values()) + rg_spacing * max(len(rg_dims) - 1, 0)
        max_rg_h = max((d["h"] for d in rg_dims.values()), default=200)
        annotation_w = 300 if annotations else 0  # space for annotation notes on the right
        sub_content_w = max(total_rg_w + annotation_w, edge_w, 600) + pad * 2
        sub_content_h = header_h + pad
        if edge_services:
            sub_content_h += edge_h + pad + 18
        sub_content_h += max_rg_h + pad * 2
        sub_content_h = max(sub_content_h, 400)

        sub_w = sub_content_w + pad * 2
        sub_h = sub_content_h + pad * 2
        canvas_width = max(int(sub_w + 60), drawio_config.MIN_CANVAS_WIDTH)
        canvas_height = max(int(sub_h + 60), drawio_config.MIN_CANVAS_HEIGHT)

        # === BUILD XML CELLS ===
        cells_xml = []
        service_positions = {}
        cell_id = 10

        # --- Subscription container (dashed rectangle, not swimlane) ---
        sub_title = self._xml_escape("Azure Subscription - " + project_name)
        cells_xml.append(
            f'        <mxCell id="2" value="" '
            f'style="rounded=0;whiteSpace=wrap;html=1;dashed=1;" '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="20" y="20" width="{int(sub_w)}" height="{int(sub_h)}" as="geometry"/>\n'
            f'        </mxCell>'
        )
        # Subscription title label (separate text cell)
        cells_xml.append(
            f'        <mxCell id="sub-label" value="{sub_title}" '
            f'style="text;html=1;align=left;verticalAlign=top;resizable=0;points=[];autosize=1;'
            f'strokeColor=none;fillColor=none;fontSize=14;fontStyle=1;" '
            f'vertex="1" parent="2">\n'
            f'          <mxGeometry x="10" y="5" width="{min(len(str(project_name)) * 10 + 200, int(sub_w) - 20)}" height="30" as="geometry"/>\n'
            f'        </mxCell>'
        )

        cur_y = header_h + pad

        # --- Edge / Ingress services (OUTSIDE all RGs, inside subscription) ---
        # Layout edge services in a vertical column on the LEFT for natural left-to-right flow
        if edge_services:
            cur_y += 5
            # Vertical layout for edge services (stacked on the left like reference diagrams)
            edge_col_x = pad + 10
            edge_max_cols = min(len(edge_services), 3)  # up to 3 across for edge services
            
            for i, svc in enumerate(edge_services):
                svc_id = f"svc-{cell_id}"
                row, col = divmod(i, edge_max_cols)
                x = edge_col_x + col * h_gap
                y = cur_y + row * v_gap
                service_positions[svc["name"]] = {"x": x, "y": y, "id": svc_id}
                icon_url = self._get_azure_icon_path(svc["name"])
                # Icon cell (value="")
                cells_xml.append(
                    f'        <mxCell id="{svc_id}" value="" '
                    f'style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon_url};" '
                    f'vertex="1" parent="2">\n'
                    f'          <mxGeometry x="{x}" y="{y}" width="{svc_w}" height="{svc_h}" as="geometry"/>\n'
                    f'        </mxCell>'
                )
                # Separate label cell below icon
                cells_xml.append(
                    f'        <mxCell id="{svc_id}-label" value="{self._xml_escape(svc["name"])}" '
                    f'style="text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;'
                    f'strokeColor=none;fillColor=none;" '
                    f'vertex="1" parent="2">\n'
                    f'          <mxGeometry x="{x - 20}" y="{y + svc_h + 2}" width="{svc_w + 40}" height="30" as="geometry"/>\n'
                    f'        </mxCell>'
                )
                cell_id += 1

            edge_rows = (len(edge_services) + 2) // 3  # using edge_max_cols=3
            cur_y += edge_rows * v_gap + pad

        # --- Resource Groups (arranged SIDE-BY-SIDE horizontally) ---
        rg_start_y = cur_y
        rg_x = pad

        # Reference-style light pastel fills for RG containers
        rg_fill_colors = ["#e6f3ff", "#f0f8f0", "#f5f5f5", "#fff2e6", "#f5f0ff", "#f0ffff"]

        for rg_idx, (rg_name, rg_d) in enumerate(rg_data.items()):
            rg_dim = rg_dims[rg_name]
            rg_w = rg_dim["w"]
            rg_h = max_rg_h

            fill = rg_fill_colors[rg_idx % len(rg_fill_colors)]
            rg_purpose = rg_d["meta"].get("purpose", "")
            rg_display = rg_name
            if rg_purpose:
                rg_display += f" ({rg_purpose})"

            rg_cell_id = f"rg-{rg_idx}"
            # RG container (dashed rounded rectangle, NOT swimlane)
            cells_xml.append(
                f'        <mxCell id="{rg_cell_id}" value="" '
                f'style="rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=8 8;'
                f'shadow=1;arcSize=5;fillColor={fill};" '
                f'vertex="1" parent="2">\n'
                f'          <mxGeometry x="{int(rg_x)}" y="{int(rg_start_y)}" '
                f'width="{int(rg_w)}" height="{int(rg_h)}" as="geometry"/>\n'
                f'        </mxCell>'
            )
            # RG label (separate bold text at top-left)
            cells_xml.append(
                f'        <mxCell id="{rg_cell_id}-label" value="{self._xml_escape(str(rg_display))}" '
                f'style="text;html=1;align=left;verticalAlign=top;resizable=0;points=[];autosize=1;'
                f'strokeColor=none;fillColor=none;fontSize=12;fontStyle=1;" '
                f'vertex="1" parent="{rg_cell_id}">\n'
                f'          <mxGeometry x="10" y="10" width="{min(len(str(rg_display)) * 8, int(rg_w) - 20)}" height="30" as="geometry"/>\n'
                f'        </mxCell>'
            )

            rg_cur_y = header_h + pad

            for vn_name, vn_d in rg_d["vnets"].items():
                vn_dim = rg_dim["vnet_dims"][vn_name]
                vn_w = vn_dim["w"]
                vn_h = vn_dim["h"]
                vn_x = max(pad, int((rg_w - vn_w) / 2))
                vn_cell_id = f"vnet-{rg_idx}-{cell_id}"
                cell_id += 1
                # Register VNet in service_positions so VNet Peering connections can find it
                service_positions[vn_name] = {"x": int(vn_x), "y": int(rg_cur_y), "id": vn_cell_id}

                # VNet container (dashed rectangle, NOT swimlane)
                cells_xml.append(
                    f'        <mxCell id="{vn_cell_id}" value="" '
                    f'style="whiteSpace=wrap;html=1;dashed=1;fillColor={fill};" '
                    f'vertex="1" parent="{rg_cell_id}">\n'
                    f'          <mxGeometry x="{int(vn_x)}" y="{int(rg_cur_y)}" '
                    f'width="{int(vn_w)}" height="{int(vn_h)}" as="geometry"/>\n'
                    f'        </mxCell>'
                )
                # VNet label (separate bold text at top-left)
                cells_xml.append(
                    f'        <mxCell id="{vn_cell_id}-label" value="{self._xml_escape(str(vn_name))}" '
                    f'style="text;html=1;align=left;verticalAlign=top;resizable=0;points=[];autosize=1;'
                    f'strokeColor=none;fillColor=none;fontSize=11;fontStyle=1;" '
                    f'vertex="1" parent="{vn_cell_id}">\n'
                    f'          <mxGeometry x="10" y="5" width="{min(len(str(vn_name)) * 7, int(vn_w) - 20)}" height="30" as="geometry"/>\n'
                    f'        </mxCell>'
                )

                vn_inner_y = header_h + pad
                sn_ci = 0
                for sn_name, sn_d in vn_d["subnets"].items():
                    sn_svcs = sn_d["services"]
                    sn_w, sn_h = vn_dim["subnet_dims"].get(sn_name, (280, 130))
                    if not sn_svcs:
                        sn_w, sn_h = 280, 90  # smaller empty subnet
                    sn_ci += 1
                    sn_meta = sn_d["meta"]
                    sn_cell_id = f"sn-{rg_idx}-{cell_id}"
                    cell_id += 1
                    sn_x = max(pad, int((vn_w - sn_w) / 2))

                    # Subnet container (simple dashed rectangle, NOT swimlane)
                    cells_xml.append(
                        f'        <mxCell id="{sn_cell_id}" value="" '
                        f'style="whiteSpace=wrap;html=1;dashed=1;" '
                        f'vertex="1" parent="{vn_cell_id}">\n'
                        f'          <mxGeometry x="{int(sn_x)}" y="{int(vn_inner_y)}" '
                        f'width="{int(sn_w)}" height="{int(sn_h)}" as="geometry"/>\n'
                        f'        </mxCell>'
                    )
                    # Subnet label (text below the container)
                    cells_xml.append(
                        f'        <mxCell id="{sn_cell_id}-label" value="{self._xml_escape(sn_name)}" '
                        f'style="text;html=1;align=center;verticalAlign=top;resizable=0;points=[];autosize=1;'
                        f'strokeColor=none;fillColor=none;fontSize=10;" '
                        f'vertex="1" parent="{vn_cell_id}">\n'
                        f'          <mxGeometry x="{int(sn_x + sn_w - 160)}" y="{int(vn_inner_y + sn_h)}" '
                        f'width="150" height="25" as="geometry"/>\n'
                        f'        </mxCell>'
                    )
                    # Subnet icon (small subnet logo at bottom-right of container)
                    cells_xml.append(
                        f'        <mxCell id="{sn_cell_id}-icon" value="" '
                        f'style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;'
                        f'image=img/lib/azure2/networking/Subnet.svg;" '
                        f'vertex="1" parent="{vn_cell_id}">\n'
                        f'          <mxGeometry x="{int(sn_x + sn_w - 55)}" y="{int(vn_inner_y + sn_h - 30)}" '
                        f'width="42" height="25" as="geometry"/>\n'
                        f'        </mxCell>'
                    )

                    svc_y = 10
                    if sn_svcs:
                        row_w = min(len(sn_svcs), max_per_row) * h_gap
                        sx = max(pad, int((sn_w - row_w) / 2))
                        for i, svc in enumerate(sn_svcs):
                            sid = f"svc-{cell_id}"
                            r, c = divmod(i, max_per_row)
                            x = sx + c * h_gap
                            y = svc_y + r * v_gap
                            service_positions[svc["name"]] = {"x": x, "y": y, "id": sid, "parent": sn_cell_id}
                            icon = self._get_azure_icon_path(svc["name"])
                            # Icon cell (value="")
                            cells_xml.append(
                                f'        <mxCell id="{sid}" value="" '
                                f'style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon};" '
                                f'vertex="1" parent="{sn_cell_id}">\n'
                                f'          <mxGeometry x="{x}" y="{y}" width="{svc_w}" height="{svc_h}" as="geometry"/>\n'
                                f'        </mxCell>'
                            )
                            # Separate label cell below icon
                            cells_xml.append(
                                f'        <mxCell id="{sid}-label" value="{self._xml_escape(svc["name"])}" '
                                f'style="text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;'
                                f'strokeColor=none;fillColor=none;" '
                                f'vertex="1" parent="{sn_cell_id}">\n'
                                f'          <mxGeometry x="{x - 20}" y="{y + svc_h + 2}" width="{svc_w + 40}" height="30" as="geometry"/>\n'
                                f'        </mxCell>'
                            )
                            cell_id += 1

                    vn_inner_y += int(sn_h) + pad

                # Loose VNet services
                if vn_d["loose"]:
                    row_w = min(len(vn_d["loose"]), max_per_row) * h_gap
                    sx = max(pad, int((vn_w - row_w) / 2))
                    for i, svc in enumerate(vn_d["loose"]):
                        sid = f"svc-{cell_id}"
                        r, c = divmod(i, max_per_row)
                        x = sx + c * h_gap
                        y = vn_inner_y + r * v_gap
                        service_positions[svc["name"]] = {"x": x, "y": y, "id": sid, "parent": vn_cell_id}
                        icon = self._get_azure_icon_path(svc["name"])
                        # Icon cell (value="")
                        cells_xml.append(
                            f'        <mxCell id="{sid}" value="" '
                            f'style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon};" '
                            f'vertex="1" parent="{vn_cell_id}">\n'
                            f'          <mxGeometry x="{x}" y="{y}" width="{svc_w}" height="{svc_h}" as="geometry"/>\n'
                            f'        </mxCell>'
                        )
                        # Separate label cell below icon
                        cells_xml.append(
                            f'        <mxCell id="{sid}-label" value="{self._xml_escape(svc["name"])}" '
                            f'style="text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;'
                            f'strokeColor=none;fillColor=none;" '
                            f'vertex="1" parent="{vn_cell_id}">\n'
                            f'          <mxGeometry x="{x - 20}" y="{y + svc_h + 2}" width="{svc_w + 40}" height="30" as="geometry"/>\n'
                            f'        </mxCell>'
                        )
                        cell_id += 1

                rg_cur_y += int(vn_h) + pad

            # Loose RG services (not in any VNet)
            if rg_d["loose"]:
                row_w = min(len(rg_d["loose"]), max_per_row) * h_gap
                sx = max(pad, int((rg_w - row_w) / 2))
                for i, svc in enumerate(rg_d["loose"]):
                    sid = f"svc-{cell_id}"
                    r, c = divmod(i, max_per_row)
                    x = sx + c * h_gap
                    y = rg_cur_y + r * v_gap
                    service_positions[svc["name"]] = {"x": x, "y": y, "id": sid, "parent": rg_cell_id}
                    icon = self._get_azure_icon_path(svc["name"])
                    # Icon cell (value="")
                    cells_xml.append(
                        f'        <mxCell id="{sid}" value="" '
                        f'style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon};" '
                        f'vertex="1" parent="{rg_cell_id}">\n'
                        f'          <mxGeometry x="{x}" y="{y}" width="{svc_w}" height="{svc_h}" as="geometry"/>\n'
                        f'        </mxCell>'
                    )
                    # Separate label cell below icon
                    cells_xml.append(
                        f'        <mxCell id="{sid}-label" value="{self._xml_escape(svc["name"])}" '
                        f'style="text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;'
                        f'strokeColor=none;fillColor=none;" '
                        f'vertex="1" parent="{rg_cell_id}">\n'
                        f'          <mxGeometry x="{x - 20}" y="{y + svc_h + 2}" width="{svc_w + 40}" height="30" as="geometry"/>\n'
                        f'        </mxCell>'
                    )
                    cell_id += 1

            rg_x += rg_w + rg_spacing

        # --- CONNECTIONS (with labels and professional routing) ---
        conn_id = 200

        for conn_idx, conn in enumerate(connections):
            source_name = conn.get("source", "")
            target_name = conn.get("target", "")
            conn_type = conn.get("type", "")
            conn_label = conn.get("label", "")

            source_pos = self._fuzzy_find_service(source_name, service_positions)
            target_pos = self._fuzzy_find_service(target_name, service_positions)

            if source_pos and target_pos and source_pos["id"] != target_pos["id"]:
                label_escaped = self._xml_escape(conn_label)
                if conn_type == "vnet_peering":
                    # VNet Peering: dashed bidirectional line with label
                    style = ("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
                             "dashed=1;dashPattern=8 4;strokeColor=#00CC00;strokeWidth=2;"
                             "startArrow=diamondThin;startFill=1;endArrow=diamondThin;endFill=1;"
                             "fontSize=10;fontColor=#00CC00;")
                    if not label_escaped:
                        label_escaped = "VNet Peering"
                else:
                    style = ("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
                             "strokeWidth=1;fontSize=10;")

                cells_xml.append(
                    f'        <mxCell id="conn-{conn_id}" value="{label_escaped}" '
                    f'style="{style}" '
                    f'edge="1" parent="1" source="{source_pos["id"]}" target="{target_pos["id"]}">\n'
                    f'          <mxGeometry relative="1" as="geometry"/>\n'
                    f'        </mxCell>'
                )
                conn_id += 1
            else:
                if not source_pos:
                    logger.warning(f"Connection source not found: '{source_name}'")
                if not target_pos:
                    logger.warning(f"Connection target not found: '{target_name}'")

        # --- Annotations (reference-style colored boxes near relevant RGs) ---
        if annotations:
            annotation_colors = ["#fff2cc", "#e6ffe6", "#ffe6e6", "#e6f3ff"]
            # Place annotations to the right of the last RG or below
            note_x = rg_x + pad  # right of last RG
            note_y = rg_start_y + pad
            for ann_idx, note in enumerate(annotations):
                note_text = note.get("text", str(note)) if isinstance(note, dict) else str(note)
                ann_color = annotation_colors[ann_idx % len(annotation_colors)]
                note_w = min(max(len(note_text) * 6, 160), 280)
                note_h = max(50, ((len(note_text) // 30) + 1) * 20 + 20)
                cells_xml.append(
                    f'        <mxCell id="note-{cell_id}" value="{self._xml_escape(note_text)}" '
                    f'style="shape=note;whiteSpace=wrap;html=1;size=14;align=center;verticalAlign=middle;'
                    f'fillColor={ann_color};strokeColor=#d6b656;shadow=1;fontSize=10;fontStyle=2;" '
                    f'vertex="1" parent="2">\n'
                    f'          <mxGeometry x="{int(note_x)}" y="{int(note_y)}" width="{note_w}" height="{note_h}" as="geometry"/>\n'
                    f'        </mxCell>'
                )
                cell_id += 1
                note_y += note_h + 15

        # --- Assemble final XML ---
        cells_content = "\n".join(cells_xml)
        timestamp = str(int(time.time() * 1000))
        etag = hashlib.md5(str(normalized_services).encode()).hexdigest()[:8]

        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="{drawio_config.HOST_APP}" modified="{timestamp}" agent="{drawio_config.GENERATOR_AGENT}" etag="{etag}" version="{drawio_config.VERSION}" type="device">
  <diagram name="{self._xml_escape(project_name)}" id="arch-{etag}">
    <mxGraphModel dx="{drawio_config.MODEL_DX}" dy="{drawio_config.MODEL_DY}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{canvas_width}" pageHeight="{canvas_height}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells_content}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"Generated XML is malformed: {e}")
            xml_content = self._sanitize_xml(xml_content)

        return xml_content

    def _fuzzy_find_service(self, name: str, service_positions: Dict) -> Optional[Dict]:
        """Find a service position using fuzzy name matching.
        Tries exact match, then normalised match, then substring match."""
        if not name:
            return None
        # 1. Exact match
        if name in service_positions:
            return service_positions[name]
        # 2. Normalised match (case-insensitive, strip Azure/Microsoft prefix)
        name_norm = self._normalize_svc_name(name)
        for svc_name, pos in service_positions.items():
            if self._normalize_svc_name(svc_name) == name_norm:
                return pos
        # 3. Substring / contains match
        name_lower = name.lower()
        for svc_name, pos in service_positions.items():
            svc_lower = svc_name.lower()
            if name_lower in svc_lower or svc_lower in name_lower:
                return pos
        return None
    
    def _normalize_svc_name(self, name: str) -> str:
        """Normalize a service name for fuzzy comparison"""
        n = name.lower().strip()
        for prefix in ["azure ", "microsoft "]:
            if n.startswith(prefix):
                n = n[len(prefix):]
        return n
    
    def _sanitize_xml(self, xml_str: str) -> str:
        """Attempt to fix malformed XML by re-escaping problematic characters"""
        import re
        # Fix unescaped & that aren't already part of an entity
        xml_str = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', xml_str)
        return xml_str
    
    def _xml_escape(self, text: str) -> str:
        """Escape ALL special characters for valid XML attributes.
        This prevents 'xmlParseEntityRef: no name' errors in Draw.io."""
        if not text:
            return ""
        text = str(text)
        # & must be escaped FIRST (before other escapes that produce &)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        # Replace special unicode chars that can break XML parsers
        text = text.replace("\u2014", "-")   # em dash
        text = text.replace("\u2013", "-")   # en dash
        text = text.replace("\u2018", "'")   # left single quote
        text = text.replace("\u2019", "'")   # right single quote
        text = text.replace("\u201c", "&quot;")  # left double quote
        text = text.replace("\u201d", "&quot;")  # right double quote
        text = text.replace("\u00a0", " ")   # non-breaking space
        # Remove any remaining control characters
        text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')
        return text
    
    def _infer_category(self, service_name: str) -> str:
        """Infer category from service name"""
        name_lower = service_name.lower()
        mappings = {
            "external": ["user", "internet user", "internet"],
            "networking": ["front door", "cdn", "gateway", "load balancer", "traffic manager", "vnet", "virtual network", "firewall", "dns", "expressroute", "waf", "private endpoint", "private link", "nsg", "peering", "nat", "bastion", "ddos", "ssl"],
            "compute": ["app service", "function", "func-", "vm", "virtual machine", "kubernetes", "aks", "container", "batch", "web app", "portal", "asp"],
            "data": ["sql", "cosmos", "database", "redis", "mysql", "postgresql", "synapse", "data lake", "data factory", "table storage"],
            "security": ["key vault", "entra", "active directory", "sentinel", "defender", "certificate", "managed identity"],
            "monitoring": ["monitor", "insights", "log analytics", "diagnostic", "metric", "application insights"],
            "storage": ["storage account", "blob", "file share", "queue storage", "disk", "storage"],
            "integration": ["service bus", "event hub", "event grid", "logic app", "api management", "apim", "app configuration", "notification hub", "signalr"],
            "ai": ["cognitive", "openai", "machine learning", "bot", "search"]
        }
        for category, keywords in mappings.items():
            if any(kw in name_lower for kw in keywords):
                return category
        return "compute"
    
    def _generate_fallback_connection_label(self, source_name: str, target_name: str) -> str:
        """Generate a meaningful connection label based on service categories when reference analyzer is unavailable"""
        source_cat = self._infer_category(source_name)
        target_cat = self._infer_category(target_name)
        source_lower = source_name.lower()
        target_lower = target_name.lower()
        
        # Category-based label mapping for professional diagrams
        label_map = {
            # Edge/Networking to Gateway
            ("networking", "networking"): "Traffic routing",
            ("networking", "compute"): "Application traffic",
            
            # Compute to Data
            ("compute", "data"): "Data queries",
            ("compute", "storage"): "Data access",
            
            # Compute to Security
            ("compute", "security"): "Secrets & certificates",
            
            # Compute to Monitoring  
            ("compute", "monitoring"): "Telemetry & logs",
            
            # Compute to Integration
            ("compute", "integration"): "Message publishing",
            ("integration", "compute"): "Event processing",
            
            # Compute to AI
            ("compute", "ai"): "AI/ML inference",
            ("ai", "data"): "Model data access",
            
            # Security connections
            ("security", "compute"): "Identity validation",
            ("security", "data"): "Encryption keys",
            
            # Monitoring connections
            ("monitoring", "compute"): "Health monitoring",
            ("monitoring", "data"): "Data diagnostics",
            
            # Data connections
            ("data", "data"): "Data sync",
            ("data", "storage"): "Data replication",
        }
        
        # Check for specific service patterns
        specific_labels = [
            (["key vault", "keyvault"], "Secrets retrieval"),
            (["monitor", "insights"], "Telemetry & diagnostics"),
            (["sql", "database", "cosmos", "postgresql"], "SQL queries"),
            (["redis", "cache"], "Cache lookup"),
            (["service bus", "event hub"], "Async messaging"),
            (["front door", "cdn"], "CDN distribution"),
            (["firewall", "waf"], "Security filtering"),
            (["api management", "apim"], "API routing"),
            (["storage", "blob"], "Blob storage access"),
        ]
        
        for keywords, label in specific_labels:
            if any(kw in target_lower for kw in keywords):
                return label
            if any(kw in source_lower for kw in keywords):
                return label
        
        return label_map.get((source_cat, target_cat), "Service integration")
    
    def _build_component_boxes(self, service_positions: Dict, svc_w: int = 64, svc_h: int = 64) -> List[Dict]:
        """Build bounding boxes for all components for collision detection"""
        boxes = []
        padding = 20  # Extra padding around components
        for name, pos in service_positions.items():
            boxes.append({
                "name": name,
                "id": pos.get("id", ""),
                "x1": pos["x"] - padding,
                "y1": pos["y"] - padding,
                "x2": pos["x"] + svc_w + padding,
                "y2": pos["y"] + svc_h + padding,
                "cx": pos["x"] + svc_w // 2,
                "cy": pos["y"] + svc_h // 2
            })
        return boxes
    
    def _calculate_port_directions(self, source_pos: Dict, target_pos: Dict,
                                     offset_idx: int, svc_w: int = 64, svc_h: int = 64) -> Tuple[str, str]:
        """Calculate clean exit/entry port positions for orthogonal routing.
        
        Returns fixed ports on the nearest sides so Draw.io's built-in
        orthogonal router can produce clean, straight, right-angle paths.
        Parallel connections are offset slightly along the edge to avoid overlap.
        """
        sx = source_pos["x"] + svc_w / 2
        sy = source_pos["y"] + svc_h / 2
        tx = target_pos["x"] + svc_w / 2
        ty = target_pos["y"] + svc_h / 2

        dx = tx - sx
        dy = ty - sy

        # Small parallel-line offset (shift along the edge, not perpendicular)
        parallel_shift = offset_idx * 0.12  # ≤ 0.36 for up to 3 parallel lines

        if abs(dx) >= abs(dy):
            # Primarily horizontal — exit from right/left side of the node
            y_pos = min(0.75, max(0.25, 0.5 + parallel_shift))
            if dx >= 0:
                exit_style  = f"exitX=1;exitY={y_pos};exitDx=0;exitDy=0;"
                entry_style = f"entryX=0;entryY={y_pos};entryDx=0;entryDy=0;"
            else:
                exit_style  = f"exitX=0;exitY={y_pos};exitDx=0;exitDy=0;"
                entry_style = f"entryX=1;entryY={y_pos};entryDx=0;entryDy=0;"
        else:
            # Primarily vertical — exit from top/bottom
            x_pos = min(0.75, max(0.25, 0.5 + parallel_shift))
            if dy >= 0:
                exit_style  = f"exitX={x_pos};exitY=1;exitDx=0;exitDy=0;"
                entry_style = f"entryX={x_pos};entryY=0;entryDx=0;entryDy=0;"
            else:
                exit_style  = f"exitX={x_pos};exitY=0;exitDx=0;exitDy=0;"
                entry_style = f"entryX={x_pos};entryY=1;entryDx=0;entryDy=0;"

        return exit_style, entry_style

    def _generate_empty_diagram(self, project_name: str) -> str:
        """Generate a minimal .drawio diagram when no services are available"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="{drawio_config.HOST_APP}" agent="{drawio_config.GENERATOR_AGENT}" version="{drawio_config.VERSION}" type="device">
  <diagram name="{self._xml_escape(project_name)}" id="empty">
    <mxGraphModel dx="{drawio_config.MODEL_DX}" dy="{drawio_config.MODEL_DY}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{drawio_config.PAGE_WIDTH}" pageHeight="{drawio_config.PAGE_HEIGHT}">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="No services detected. Please provide more specific requirements." 
               style="rounded=1;whiteSpace=wrap;html=1;fillColor={theme_config.WARNING_BG};strokeColor={theme_config.WARNING_STROKE};fontSize=14;" 
               vertex="1" parent="1">
          <mxGeometry x="400" y="350" width="600" height="80" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    
    def _get_azure_icon_path(self, service_name: str) -> str:
        """Get Draw.io built-in Azure icon path for a service.
        Uses img/lib/azure2/... paths which are natively supported by Draw.io.
        """
        service_lower = service_name.lower()
        
        # Draw.io built-in Azure icon library paths (img/lib/azure2/<category>/<icon>.svg)
        icon_mappings = {
            # Compute
            'function app': 'img/lib/azure2/compute/Function_Apps.svg',
            'function': 'img/lib/azure2/compute/Function_Apps.svg',
            'func-': 'img/lib/azure2/compute/Function_Apps.svg',
            'app service plan': 'img/lib/azure2/app_services/App_Service_Plans.svg',
            'service plan': 'img/lib/azure2/app_services/App_Service_Plans.svg',
            'function asp': 'img/lib/azure2/app_services/App_Service_Plans.svg',
            'shared function asp': 'img/lib/azure2/app_services/App_Service_Plans.svg',
            'app service': 'img/lib/azure2/app_services/App_Services.svg',
            'web app': 'img/lib/azure2/app_services/App_Services.svg',
            'portal': 'img/lib/azure2/app_services/App_Services.svg',
            'virtual machine': 'img/lib/azure2/compute/Virtual_Machine.svg',
            'vm scale set': 'img/lib/azure2/compute/VM_Scale_Sets.svg',
            'kubernetes': 'img/lib/azure2/containers/Kubernetes_Services.svg',
            'aks': 'img/lib/azure2/containers/Kubernetes_Services.svg',
            'container instance': 'img/lib/azure2/containers/Container_Instances.svg',
            'container app': 'img/lib/azure2/containers/Container_Apps.svg',
            'batch': 'img/lib/azure2/compute/Batch_Accounts.svg',
            'static web': 'img/lib/azure2/app_services/Static_Apps.svg',
            'cloud service': 'img/lib/azure2/compute/Cloud_Services.svg',
            # Storage
            'storage account': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'storage': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'blob': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'data lake': 'img/lib/azure2/storage/Data_Lake_Storage.svg',
            # Databases
            'sql database': 'img/lib/azure2/databases/SQL_Database.svg',
            'sql server': 'img/lib/azure2/databases/SQL_Server.svg',
            'sql': 'img/lib/azure2/databases/SQL_Database.svg',
            'cosmos db': 'img/lib/azure2/databases/Azure_Cosmos_DB.svg',
            'cosmos': 'img/lib/azure2/databases/Azure_Cosmos_DB.svg',
            'redis cache': 'img/lib/azure2/databases/Cache_Redis.svg',
            'redis': 'img/lib/azure2/databases/Cache_Redis.svg',
            'postgresql': 'img/lib/azure2/databases/Azure_Database_PostgreSQL_Server.svg',
            'postgres': 'img/lib/azure2/databases/Azure_Database_PostgreSQL_Server.svg',
            'mysql': 'img/lib/azure2/databases/Azure_Database_MySQL_Server.svg',
            'mariadb': 'img/lib/azure2/databases/Azure_Database_MariaDB_Server.svg',
            'data factory': 'img/lib/azure2/databases/Data_Factory.svg',
            'synapse': 'img/lib/azure2/databases/Azure_Synapse_Analytics.svg',
            # Networking
            'front door': 'img/lib/azure2/networking/Front_Doors.svg',
            'application gateway': 'img/lib/azure2/networking/Application_Gateways.svg',
            'app gateway': 'img/lib/azure2/networking/Application_Gateways.svg',
            'load balancer': 'img/lib/azure2/networking/Load_Balancers.svg',
            'virtual network': 'img/lib/azure2/networking/Virtual_Networks.svg',
            'vnet': 'img/lib/azure2/networking/Virtual_Networks.svg',
            'subnet': 'img/lib/azure2/networking/Subnet.svg',
            'cdn': 'img/lib/azure2/networking/CDN_Profiles.svg',
            'traffic manager': 'img/lib/azure2/networking/Traffic_Manager_Profiles.svg',
            'dns zone': 'img/lib/azure2/networking/DNS_Zones.svg',
            'dns': 'img/lib/azure2/networking/DNS_Zones.svg',
            'private dns': 'img/lib/mscae/DNS_Private_Zones.svg',
            'expressroute': 'img/lib/azure2/networking/ExpressRoute_Circuits.svg',
            'firewall': 'img/lib/azure2/networking/Firewalls.svg',
            'waf': 'img/lib/azure2/networking/Web_Application_Firewall_Policies_WAF.svg',
            'web application firewall': 'img/lib/azure2/networking/Web_Application_Firewall_Policies_WAF.svg',
            'private endpoint': 'img/lib/azure2/networking/Private_Endpoint.svg',
            'private link': 'img/lib/azure2/networking/Private_Link_Services.svg',
            'nsg': 'img/lib/azure2/networking/Network_Security_Groups.svg',
            'network security group': 'img/lib/azure2/networking/Network_Security_Groups.svg',
            'nat gateway': 'img/lib/azure2/networking/NAT.svg',
            'vpn gateway': 'img/lib/azure2/networking/VPN_Gateways.svg',
            'bastion': 'img/lib/azure2/networking/Bastions.svg',
            'ddos': 'img/lib/azure2/networking/DDoS_Protection_Plans.svg',
            # Security & Identity
            'key vault': 'img/lib/azure2/security/Key_Vaults.svg',
            'entra id': 'img/lib/azure2/identity/Entra_ID_Protection.svg',
            'entra': 'img/lib/azure2/identity/Entra_ID_Protection.svg',
            'active directory': 'img/lib/azure2/identity/Azure_Active_Directory.svg',
            'azure ad': 'img/lib/azure2/identity/Azure_Active_Directory.svg',
            'sentinel': 'img/lib/azure2/security/Microsoft_Sentinel.svg',
            'defender': 'img/lib/azure2/security/MS_Defender_EASM.svg',
            'microsoft defender': 'img/lib/azure2/security/MS_Defender_EASM.svg',
            'managed identity': 'img/lib/azure2/identity/Managed_Identities.svg',
            'certificate': 'img/lib/azure2/security/Certificates.svg',
            'ssl': 'img/lib/azure2/security/Certificates.svg',
            # Monitoring & Management
            'application insights': 'img/lib/azure2/devops/Application_Insights.svg',
            'app insights': 'img/lib/azure2/devops/Application_Insights.svg',
            'monitor': 'img/lib/azure2/management_governance/Monitor.svg',
            'azure monitor': 'img/lib/azure2/management_governance/Monitor.svg',
            'log analytics': 'img/lib/azure2/analytics/Log_Analytics_Workspaces.svg',
            'policy': 'img/lib/azure2/management_governance/Policy.svg',
            'advisor': 'img/lib/azure2/management_governance/Advisor.svg',
            'cost management': 'img/lib/azure2/management_governance/Cost_Management.svg',
            # Integration & Messaging
            'api management': 'img/lib/azure2/app_services/API_Management_Services.svg',
            'apim': 'img/lib/azure2/app_services/API_Management_Services.svg',
            'service bus': 'img/lib/azure2/integration/Service_Bus.svg',
            'event hub': 'img/lib/azure2/analytics/Event_Hubs.svg',
            'event grid': 'img/lib/azure2/integration/Event_Grid_Domains.svg',
            'logic app': 'img/lib/azure2/integration/Logic_Apps.svg',
            'notification hub': 'img/lib/azure2/app_services/Notification_Hubs.svg',
            'app configuration': 'img/lib/azure2/integration/App_Configuration.svg',
            'signalr': 'img/lib/azure2/app_services/SignalR.svg',
            # AI & ML
            'cognitive': 'img/lib/azure2/ai_machine_learning/Cognitive_Services.svg',
            'openai': 'img/lib/azure2/ai_machine_learning/Azure_OpenAI.svg',
            'azure openai': 'img/lib/azure2/ai_machine_learning/Azure_OpenAI.svg',
            'machine learning': 'img/lib/azure2/ai_machine_learning/Machine_Learning.svg',
            'bot service': 'img/lib/azure2/ai_machine_learning/Bot_Services.svg',
            'bot': 'img/lib/azure2/ai_machine_learning/Bot_Services.svg',
            'search': 'img/lib/azure2/general/Search.svg',
            'ai search': 'img/lib/azure2/general/Search.svg',
            # DevOps
            'devops': 'img/lib/azure2/devops/Azure_DevOps.svg',
            'container registry': 'img/lib/azure2/containers/Container_Registries.svg',
            'acr': 'img/lib/azure2/containers/Container_Registries.svg',
            # General
            'resource group': 'img/lib/azure2/general/Resource_Groups.svg',
            'subscription': 'img/lib/azure2/general/Subscriptions.svg',
            'power bi': 'img/lib/azure2/analytics/Power_BI_Embedded.svg',
            'internet user': 'img/lib/azure2/general/User.svg',
            'internet': 'img/lib/azure2/general/User.svg',
            'user': 'img/lib/azure2/general/User.svg',
            'users': 'img/lib/azure2/general/User.svg',
            # VNet Peering visual
            'vnet peering': 'img/lib/azure2/networking/Virtual_Network_Peering.svg',
            'peering': 'img/lib/azure2/networking/Virtual_Network_Peering.svg',
        }
        
        for key, icon_path in icon_mappings.items():
            if key in service_lower:
                return icon_path
        
        # Default - generic Azure resource icon
        return 'img/lib/azure2/general/Resource_Groups.svg'
    
   

# Utility functions for API endpoints (module-level, not indented)
def parse_uploaded_drawio_file(file_content: str) -> Dict[str, Any]:
    """Parse an uploaded Draw.io file and return analysis"""
    parser = DrawioParser()
    return parser.parse_drawio_file(file_content)

async def generate_drawio_from_architecture(architecture: Dict[str, Any], requirements: str) -> str:
    """Generate Draw.io XML from architecture data using AI layout"""
    parser = DrawioParser()
    return await parser.generate_drawio_xml(architecture, requirements)
