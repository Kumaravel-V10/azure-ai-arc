import os
from typing import Dict, List, Any
import json
from config import drawio_config, theme_config, external_url_config

# Azure Portal icon base URL
AZURE_ICON_BASE = external_url_config.AZURE_ICON_BASE_URL

class AzureIconDiagramGenerator:
    def __init__(self):
        self.icons_base_path = "Azure_Public_Service_Icons_V23/Azure_Public_Service_Icons/Icons"
        
        # Azure Portal icon URLs for cloud-based icons
        self.azure_portal_icons = {
            # Compute Services
            "Virtual Machine": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/Computer.svg",
            "App Services": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/AppService.svg",
            "Function Apps": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/FunctionApp.svg",
            "Kubernetes Services": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/KubernetesServices.svg",
            "Container Instances": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/ContainerInstances.svg",
            "Azure Batch": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/Batch.svg",
            
            # Storage Services  
            "Storage Account": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/StorageAccount.svg",
            "Blob Storage": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/BlobStorage.svg",
            "Data Lake Storage": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/DataLakeStorage.svg",
            "File Share": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/FileShare.svg",
            
            # Database Services
            "SQL Database": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/SQLDatabase.svg",
            "Cosmos DB": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/CosmosDB.svg",
            "Azure Database for MySQL": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/MySQL.svg",
            "Azure Database for PostgreSQL": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/PostgreSQL.svg",
            "Redis Cache": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/RedisCache.svg",
            
            # Networking Services
            "Virtual Network": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/VirtualNetwork.svg",
            "Load Balancer": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/LoadBalancer.svg",
            "Application Gateway": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/ApplicationGateway.svg",
            "VPN Gateway": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/VPNGateway.svg",
            "Azure Firewall": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/Firewall.svg",
            
            # Security Services
            "Key Vault": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/KeyVault.svg",
            "Azure Active Directory": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/ActiveDirectory.svg",
            "Microsoft Entra ID": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/ActiveDirectory.svg",
            
            # AI + Machine Learning
            "Azure OpenAI": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/OpenAI.svg",
            "Cognitive Services": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/CognitiveServices.svg",
            "Machine Learning": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/MachineLearning.svg",
            
            # Analytics
            "Event Hubs": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/EventHubs.svg",
            "Stream Analytics": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/StreamAnalytics.svg",
            "Data Factory": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/DataFactory.svg",
            
            # Monitoring
            "Application Insights": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/ApplicationInsights.svg",
            "Azure Monitor": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/Monitor.svg",
            "Log Analytics": "https://portal.azure.com/Content/static/MsPortalFx/Base/Images/Services/LogAnalytics.svg"
        }
        
        # Map Azure services to their actual icon files
        self.azure_service_icons = {
            # Compute Services
            "Virtual Machine": "compute/10021-icon-service-Virtual-Machine.svg",
            "App Services": "compute/10035-icon-service-App-Services.svg",
            "Function Apps": "compute/10029-icon-service-Function-Apps.svg",
            "Kubernetes Services": "compute/10023-icon-service-Kubernetes-Services.svg",
            "Container Instances": "compute/10104-icon-service-Container-Instances.svg",
            "VM Scale Sets": "compute/10034-icon-service-VM-Scale-Sets.svg",
            "Batch Accounts": "compute/10031-icon-service-Batch-Accounts.svg",
            "Service Fabric": "compute/10036-icon-service-Service-Fabric-Clusters.svg",
            
            # Storage Services
            "Storage Account": "storage/10086-icon-service-Storage-Accounts.svg",
            "Blob Storage": "storage/10086-icon-service-Storage-Accounts.svg",
            "File Share": "storage/03549-icon-service-Managed-File-Shares.svg",
            "Data Lake": "storage/10090-icon-service-Data-Lake-Storage-Gen1.svg",
            "NetApp Files": "storage/10096-icon-service-Azure-NetApp-Files.svg",
            "Backup Vault": "storage/00017-icon-service-Recovery-Services-Vaults.svg",
            
            # Database Services
            "SQL Database": "databases/10130-icon-service-SQL-Database.svg",
            "Cosmos DB": "databases/10121-icon-service-Azure-Cosmos-DB.svg",
            "MySQL": "databases/10122-icon-service-Azure-Database-MySQL-Server.svg",
            "PostgreSQL": "databases/10131-icon-service-Azure-Database-PostgreSQL-Server.svg",
            "Redis Cache": "databases/10137-icon-service-Cache-Redis.svg",
            "SQL Managed Instance": "databases/10136-icon-service-SQL-Managed-Instance.svg",
            "Synapse Analytics": "databases/00606-icon-service-Azure-Synapse-Analytics.svg",
            
            # Networking Services
            "Virtual Network": "networking/10061-icon-service-Virtual-Networks.svg",
            "Load Balancer": "networking/10062-icon-service-Load-Balancers.svg",
            "Application Gateway": "networking/10076-icon-service-Application-Gateways.svg",
            "VPN Gateway": "networking/10063-icon-service-Virtual-Network-Gateways.svg",
            "ExpressRoute": "networking/10079-icon-service-ExpressRoute-Circuits.svg",
            "Front Door": "networking/10073-icon-service-Front-Door-and-CDN-Profiles.svg",
            "Traffic Manager": "networking/10065-icon-service-Traffic-Manager-Profiles.svg",
            "Firewall": "networking/10084-icon-service-Firewalls.svg",
            "CDN": "app services/00056-icon-service-CDN-Profiles.svg",
            
            # Security Services
            "Key Vault": "security/10245-icon-service-Key-Vaults.svg",
            "Azure AD": "identity/10230-icon-service-Users.svg",
            "Managed Identity": "identity/10227-icon-service-Managed-Identities.svg",
            "Security Center": "security/10241-icon-service-Microsoft-Defender-for-Cloud.svg",
            "Sentinel": "security/10248-icon-service-Azure-Sentinel.svg",
            
            # Analytics Services
            "Event Hubs": "analytics/00039-icon-service-Event-Hubs.svg",
            "Stream Analytics": "analytics/00042-icon-service-Stream-Analytics-Jobs.svg",
            "Data Factory": "analytics/10126-icon-service-Data-Factories.svg",
            "Databricks": "analytics/10787-icon-service-Azure-Databricks.svg",
            "HDInsight": "analytics/10142-icon-service-HD-Insight-Clusters.svg",
            "Power BI": "analytics/03332-icon-service-Power-BI-Embedded.svg",
            
            # AI + Machine Learning
            "Cognitive Services": "ai + machine learning/10162-icon-service-Cognitive-Services.svg",
            "Machine Learning": "ai + machine learning/10166-icon-service-Machine-Learning.svg",
            "Bot Services": "ai + machine learning/10165-icon-service-Bot-Services.svg",
            "Computer Vision": "ai + machine learning/00792-icon-service-Computer-Vision.svg",
            "Speech Services": "ai + machine learning/00797-icon-service-Speech-Services.svg",
            "Azure OpenAI": "ai + machine learning/03438-icon-service-Azure-OpenAI.svg",
            
            # Monitoring
            "Monitor": "monitor/00001-icon-service-Monitor.svg",
            "Application Insights": "monitor/00012-icon-service-Application-Insights.svg",
            "Log Analytics": "monitor/00009-icon-service-Log-Analytics-Workspaces.svg",
            
            # Integration
            "Logic Apps": "integration/02631-icon-service-Logic-Apps.svg",
            "API Management": "integration/10042-icon-service-API-Management-Services.svg",
            "Service Bus": "integration/10836-icon-service-Azure-Service-Bus.svg",
            "Event Grid": "integration/10206-icon-service-Event-Grid-Topics.svg",
            
            # IoT
            "IoT Hub": "iot/10182-icon-service-IoT-Hub.svg",
            "IoT Central": "iot/10184-icon-service-IoT-Central-Applications.svg",
            "Digital Twins": "iot/01030-icon-service-Digital-Twins.svg",
            
            # Web Services
            "Static Web Apps": "web/01007-icon-service-Static-Apps.svg",
            "SignalR": "web/10052-icon-service-SignalR.svg",
            "API Center": "web/03291-icon-service-API-Center.svg"
        }
        
        # Azure regions
        self.azure_regions = [
            "East US", "West US 2", "Central US", "North Europe", 
            "West Europe", "Southeast Asia", "East Asia"
        ]
        
        # Enhanced service detection keywords for prompt-based generation
        self.service_keywords = {
            # Compute keywords
            "Virtual Machine": ["vm", "virtual machine", "compute", "server", "instance", "ec2"],
            "App Services": ["app service", "web app", "website", "web application", "app"],
            "Function Apps": ["function", "serverless", "lambda", "azure functions", "faas"],
            "Kubernetes Services": ["kubernetes", "k8s", "aks", "container orchestration", "microservices"],
            "Container Instances": ["container", "docker", "containerized", "aci"],
            
            # Storage keywords
            "Storage Account": ["storage", "file storage", "data storage", "blob"],
            "Blob Storage": ["blob", "object storage", "file upload", "media storage"],
            "Data Lake Storage": ["data lake", "big data", "analytics storage", "datalake"],
            "File Share": ["file share", "shared storage", "network storage", "smb"],
            
            # Database keywords
            "SQL Database": ["sql", "database", "relational", "rdbms", "structured data"],
            "Cosmos DB": ["cosmos", "nosql", "document database", "mongodb", "global database"],
            "Azure Database for MySQL": ["mysql", "mariadb"],
            "Azure Database for PostgreSQL": ["postgresql", "postgres"],
            "Redis Cache": ["redis", "cache", "in-memory", "session store"],
            
            # Networking keywords
            "Virtual Network": ["vnet", "network", "vpc", "subnet", "networking"],
            "Load Balancer": ["load balancer", "lb", "traffic distribution", "balancing"],
            "Application Gateway": ["app gateway", "application gateway", "reverse proxy", "waf"],
            "VPN Gateway": ["vpn", "site-to-site", "point-to-site", "hybrid connectivity"],
            "Azure Firewall": ["firewall", "security", "network security", "perimeter"],
            
            # Security keywords
            "Key Vault": ["key vault", "secrets", "certificates", "keys", "credential management"],
            "Azure Active Directory": ["active directory", "ad", "aad", "identity", "authentication"],
            "Microsoft Entra ID": ["entra", "entra id", "identity platform", "sso"],
            
            # AI/ML keywords
            "Azure OpenAI": ["openai", "gpt", "chatgpt", "ai model", "llm", "language model"],
            "Cognitive Services": ["cognitive", "ai services", "computer vision", "speech"],
            "Machine Learning": ["ml", "machine learning", "model training", "ai"],
            
            # Analytics keywords
            "Event Hubs": ["event hub", "streaming", "event streaming", "kafka"],
            "Stream Analytics": ["stream analytics", "real-time analytics", "streaming analytics"],
            "Data Factory": ["data factory", "etl", "data pipeline", "data integration"],
            
            # Monitoring keywords
            "Application Insights": ["application insights", "apm", "monitoring", "telemetry"],
            "Azure Monitor": ["monitor", "monitoring", "metrics", "alerts"],
            "Log Analytics": ["log analytics", "logs", "query", "kusto"]
        }
    
    def generate_drawio_xml(self, architecture: Dict[str, Any]) -> str:
        """Generate Draw.io XML with actual Azure icons and proper formatting"""
        services = architecture.get("services", [])
        # Normalize services to strings (they may be dicts with 'name' key)
        services = [s["name"] if isinstance(s, dict) else s for s in services]
        
        # Add icon paths to services
        services_with_icons = []
        for service in services:
            icon_path = self._get_service_icon_path(service)
            services_with_icons.append({
                "name": service,
                "icon_path": icon_path,
                "full_path": f"{self.icons_base_path}/{icon_path}",
                "svg_content": self._get_azure_icon_svg(service)
            })
        
        architecture["services_with_icons"] = services_with_icons
        
        # Generate proper Azure architecture XML
        xml_template = '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="{timestamp}" agent="azure-architecture-generator" etag="{etag}" version="24.7.17" type="device">
  <diagram name="Azure Architecture Diagram" id="azure-architecture">
    <mxGraphModel dx="{dx}" dy="{dy}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        
        <!-- Azure Cloud Header -->
        <mxCell id="azure-header" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#0078d4;strokeColor=none;fontSize=16;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
          <mxGeometry x="40" y="20" width="1089" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="azure-logo" value="" style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image=img/lib/azure2/general/Resource_Groups.svg;" vertex="1" parent="1">
          <mxGeometry x="50" y="25" width="40" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="azure-title" value="Microsoft Azure Architecture" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=18;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
          <mxGeometry x="100" y="30" width="300" height="30" as="geometry"/>
        </mxCell>
        
        <!-- Azure Subscription Container -->
        <mxCell id="subscription" value="Azure Subscription" style="swimlane;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=14;startSize=30;rounded=1;shadow=1;" vertex="1" parent="1">
          <mxGeometry x="60" y="90" width="1049" height="720" as="geometry"/>
        </mxCell>
        
        <!-- Resource Group Container -->
        <mxCell id="resource-group" value="Resource Group" style="swimlane;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=12;startSize=26;rounded=1;dashed=1;dashPattern=5 5;" vertex="1" parent="subscription">
          <mxGeometry x="30" y="40" width="989" height="650" as="geometry"/>
        </mxCell>
        
        {components}
        {connections}
        {legends}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
        
        components = []
        connections = []
        legends = []
        
        # Categorize services
        categorized_services = self._categorize_services_for_diagram(services)
        
        # Generate components with proper Azure layout
        y_offset = 60
        for category, category_services in categorized_services.items():
            if not category_services:
                continue
                
            # Category header
            category_header = f'''
        <mxCell id="cat-{category.replace(' ', '-').lower()}" value="{self._get_azure_category_icon(category)} {category}" style="swimlane;whiteSpace=wrap;html=1;fillColor={self._get_category_color(category)};strokeColor={self._get_category_border_color(category)};fontSize=12;startSize=26;rounded=1;" vertex="1" parent="resource-group">
          <mxGeometry x="20" y="{y_offset}" width="949" height="{60 + len(category_services) * 80}" as="geometry"/>
        </mxCell>'''
            components.append(category_header)
            
            # Services within category
            for j, service in enumerate(category_services):
                x = 50 + (j % 8) * 110  # 8 services per row
                y = 40 + (j // 8) * 80
                
                icon_path = self._get_drawio_builtin_icon_path(service)
                
                service_cell = f'''
        <mxCell id="service-{service.replace(' ', '-').replace('/', '-').lower()}" value="{service}" style="image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon_path};" vertex="1" parent="cat-{category.replace(' ', '-').lower()}">
          <mxGeometry x="{x}" y="{y}" width="64" height="64" as="geometry"/>
        </mxCell>'''
                components.append(service_cell)
            
            y_offset += 80 + len(category_services) * 80
        
        # Professional single color: Azure Blue for enterprise consistency
        AZURE_BLUE = "#0078D4"
        
        # Generate connections from actual architecture connection data (real data flows)
        arch_connections = architecture.get("connections", [])
        if arch_connections:
            for i, conn in enumerate(arch_connections):
                if isinstance(conn, dict):
                    source = conn.get("source", "")
                    target = conn.get("target", "")
                    label = conn.get("label", conn.get("protocol", ""))
                    source_id = f"service-{source.replace(' ', '-').replace('/', '-').lower()}"
                    target_id = f"service-{target.replace(' ', '-').replace('/', '-').lower()}"
                    
                    # Professional orthogonal routing — clean right-angle paths
                    connection_xml = f'''
        <mxCell id="conn-{i}" value="{label}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=12;html=1;endArrow=blockThin;endFill=1;strokeColor={AZURE_BLUE};strokeWidth=1.5;fontSize=8;fontColor=#444444;labelBackgroundColor=#ffffff;" edge="1" parent="resource-group" source="{source_id}" target="{target_id}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>'''
                    connections.append(connection_xml)
        
        # Add minimal legend
        legend_xml = f'''
        <!-- Architecture Legend -->
        <mxCell id="legend" value="Legend" style="swimlane;whiteSpace=wrap;html=1;fillColor=#fafafa;strokeColor=#e0e0e0;fontSize=10;startSize=20;rounded=1;fontStyle=1;fontColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="1150" y="90" width="140" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="legend-flow" value="" style="endArrow=blockThin;endFill=1;html=1;strokeColor=#0078D4;strokeWidth=1.5;" edge="1" parent="legend">
          <mxGeometry width="40" relative="1" as="geometry">
            <mxPoint x="10" y="35" as="sourcePoint"/>
            <mxPoint x="40" y="35" as="targetPoint"/>
          </mxGeometry>
        </mxCell>
        <mxCell id="legend-flow-label" value="Data Flow" style="text;html=1;fontSize=9;fontColor=#555555;align=left;verticalAlign=middle;" vertex="1" parent="legend">
          <mxGeometry x="45" y="28" width="90" height="14" as="geometry"/>
        </mxCell>'''
        legends.append(legend_xml)
        
        import time
        import hashlib
        
        timestamp = str(int(time.time() * 1000))
        etag = hashlib.md5(str(services).encode()).hexdigest()[:8]
        
        return xml_template.format(
            timestamp=timestamp,
            etag=etag,
            dx=drawio_config.MODEL_DX,
            dy=drawio_config.MODEL_DY,
            page_w=drawio_config.FALLBACK_PAGE_WIDTH,
            page_h=drawio_config.FALLBACK_PAGE_HEIGHT,
            components="".join(components),
            connections="".join(connections),
            legends="".join(legends)
        )
    
    def _get_drawio_builtin_icon_path(self, service_name: str) -> str:
        """Get Draw.io built-in Azure icon path for a service.
        Uses img/lib/azure2/... paths which are natively supported by Draw.io.
        """
        service_lower = service_name.lower()
        
        icon_mappings = {
            # Compute
            'function app': 'img/lib/azure2/compute/Function_Apps.svg',
            'function': 'img/lib/azure2/compute/Function_Apps.svg',
            'azure function': 'img/lib/azure2/compute/Function_Apps.svg',
            'app service plan': 'img/lib/azure2/app_services/App_Service_Plans.svg',
            'app service': 'img/lib/azure2/app_services/App_Services.svg',
            'web app': 'img/lib/azure2/app_services/App_Services.svg',
            'virtual machine': 'img/lib/azure2/compute/Virtual_Machine.svg',
            'vm scale set': 'img/lib/azure2/compute/VM_Scale_Sets.svg',
            'kubernetes': 'img/lib/azure2/containers/Kubernetes_Services.svg',
            'aks': 'img/lib/azure2/containers/Kubernetes_Services.svg',
            'container instance': 'img/lib/azure2/containers/Container_Instances.svg',
            'container app': 'img/lib/azure2/containers/Container_Apps.svg',
            'batch': 'img/lib/azure2/compute/Batch_Accounts.svg',
            'static web': 'img/lib/azure2/app_services/Static_Apps.svg',
            # Storage
            'storage account': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'storage': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'blob': 'img/lib/azure2/storage/Storage_Accounts.svg',
            'data lake': 'img/lib/azure2/storage/Data_Lake_Storage.svg',
            'file share': 'img/lib/azure2/storage/Storage_Accounts.svg',
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
            'dns': 'img/lib/azure2/networking/DNS_Zones.svg',
            'expressroute': 'img/lib/azure2/networking/ExpressRoute_Circuits.svg',
            'firewall': 'img/lib/azure2/networking/Firewalls.svg',
            'waf': 'img/lib/azure2/networking/Web_Application_Firewall_Policies_WAF.svg',
            'private endpoint': 'img/lib/azure2/networking/Private_Endpoint.svg',
            'nsg': 'img/lib/azure2/networking/Network_Security_Groups.svg',
            'network security group': 'img/lib/azure2/networking/Network_Security_Groups.svg',
            'vpn gateway': 'img/lib/azure2/networking/VPN_Gateways.svg',
            'bastion': 'img/lib/azure2/networking/Bastions.svg',
            # Security & Identity
            'key vault': 'img/lib/azure2/security/Key_Vaults.svg',
            'entra': 'img/lib/azure2/identity/Entra_ID_Protection.svg',
            'active directory': 'img/lib/azure2/identity/Azure_Active_Directory.svg',
            'azure ad': 'img/lib/azure2/identity/Azure_Active_Directory.svg',
            'sentinel': 'img/lib/azure2/security/Microsoft_Sentinel.svg',
            'defender': 'img/lib/azure2/security/MS_Defender_EASM.svg',
            'managed identity': 'img/lib/azure2/identity/Managed_Identities.svg',
            'certificate': 'img/lib/azure2/security/Certificates.svg',
            # Monitoring
            'application insights': 'img/lib/azure2/devops/Application_Insights.svg',
            'app insights': 'img/lib/azure2/devops/Application_Insights.svg',
            'monitor': 'img/lib/azure2/management_governance/Monitor.svg',
            'azure monitor': 'img/lib/azure2/management_governance/Monitor.svg',
            'log analytics': 'img/lib/azure2/analytics/Log_Analytics_Workspaces.svg',
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
            'bot': 'img/lib/azure2/ai_machine_learning/Bot_Services.svg',
            'search': 'img/lib/azure2/general/Search.svg',
            'speech': 'img/lib/azure2/ai_machine_learning/Cognitive_Services.svg',
            # IoT
            'iot hub': 'img/lib/azure2/iot/IoT_Hub.svg',
            'iot central': 'img/lib/azure2/iot/IoT_Central_Applications.svg',
            'digital twin': 'img/lib/azure2/iot/Digital_Twins.svg',
            # DevOps
            'devops': 'img/lib/azure2/devops/Azure_DevOps.svg',
            'container registry': 'img/lib/azure2/containers/Container_Registries.svg',
            'power bi': 'img/lib/azure2/analytics/Power_BI_Embedded.svg',
            'stream analytics': 'img/lib/azure2/analytics/Stream_Analytics_Jobs.svg',
        }
        
        for key, icon_path in icon_mappings.items():
            if key in service_lower:
                return icon_path
        
        return 'img/lib/azure2/general/Resource_Groups.svg'

    def _get_azure_icon_svg(self, service_name: str) -> str:
        """Get icon content for Azure service (local SVG or portal URL)"""
        icon_source = self._determine_icon_source(service_name)
        
        if icon_source == 'portal':
            # Use Azure Portal icon URL
            portal_url = self.azure_portal_icons[service_name]
            return self._create_portal_icon_reference(portal_url)
        else:
            # Use local SVG file
            icon_path = self._get_service_icon_path(service_name)
            full_path = f"{self.icons_base_path}/{icon_path}"
            
            try:
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        svg_content = f.read()
                        # URL encode the SVG for use in DrawIO
                        import urllib.parse
                        return urllib.parse.quote(svg_content)
                else:
                    # Return default Azure icon if specific icon not found
                    return self._get_default_azure_icon()
            except Exception:
                return self._get_default_azure_icon()
    
    def _create_portal_icon_reference(self, portal_url: str) -> str:
        """Create a reference to Azure Portal icon"""
        # For portal icons, we can either:
        # 1. Use the URL directly (if Draw.io supports it)
        # 2. Create a placeholder SVG with the service name
        # 3. Fetch and cache the icon (more complex)
        
        # For now, create a styled placeholder that references the portal
        placeholder_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<rect width="64" height="64" rx="8" fill="#0078d4" stroke="#005a9e" stroke-width="2"/>
<text x="32" y="20" text-anchor="middle" fill="white" font-size="8" font-family="Segoe UI">Azure</text>
<text x="32" y="32" text-anchor="middle" fill="white" font-size="7" font-family="Segoe UI">Portal</text>
<text x="32" y="44" text-anchor="middle" fill="white" font-size="6" font-family="Segoe UI">Icon</text>
<text x="32" y="56" text-anchor="middle" fill="#87ceeb" font-size="5" font-family="Segoe UI">Live</text>
</svg>'''
        
        import urllib.parse
        return urllib.parse.quote(placeholder_svg)
    
 
    def _get_default_azure_icon(self) -> str:
        """Return URL-encoded default Azure service icon"""
        default_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">
<defs><linearGradient id="a" x1="8.88" y1="12.21" x2="8.88" y2="0.21" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#0078d4" /><stop offset="0.82" stop-color="#5ea0ef" /></linearGradient></defs>
<rect x="-0.12" y="0.21" width="18" height="12" rx="0.6" fill="url(#a)" />
<polygon points="11.88 4.46 11.88 7.95 8.88 9.71 8.88 6.21 11.88 4.46" fill="#50e6ff" />
<polygon points="11.88 4.46 8.88 6.22 5.88 4.46 8.88 2.71 11.88 4.46" fill="#c3f1ff" />
<polygon points="8.88 6.22 8.88 9.71 5.88 7.95 5.88 4.46 8.88 6.22" fill="#9cebff" />
</svg>'''
        import urllib.parse
        return urllib.parse.quote(default_svg)
    
    def _get_azure_logo_svg(self) -> str:
        """Return URL-encoded Azure logo SVG"""
        azure_logo = '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
<path d="M20 2L38 36H2L20 2z" fill="#0078d4"/>
<text x="20" y="25" text-anchor="middle" fill="white" font-size="8" font-family="Arial">Az</text>
</svg>'''
        import urllib.parse
        return urllib.parse.quote(azure_logo)
    
    def _categorize_services_for_diagram(self, services: List[str]) -> Dict[str, List[str]]:
        """Categorize services for better diagram organization"""
        categories = {
            "Compute": [],
            "Storage": [],
            "Database": [],
            "Networking": [],
            "Security": [],
            "Analytics": [],
            "AI + Machine Learning": [],
            "Integration": [],
            "Other": []
        }
        
        compute_keywords = ["virtual machine", "vm", "app service", "function", "kubernetes", "container", "batch", "fabric"]
        storage_keywords = ["storage", "blob", "file", "data lake", "backup"]
        database_keywords = ["sql", "database", "cosmos", "mysql", "postgresql", "redis", "synapse"]
        networking_keywords = ["network", "load balancer", "gateway", "expressroute", "firewall", "cdn", "front door"]
        security_keywords = ["key vault", "security", "azure ad", "identity", "sentinel"]
        analytics_keywords = ["event hub", "stream analytics", "data factory", "databricks", "hdinsight", "power bi"]
        ai_keywords = ["cognitive", "machine learning", "bot", "vision", "speech", "openai"]
        integration_keywords = ["logic apps", "api management", "service bus", "event grid"]
        
        for service in services:
            service_lower = service.lower()
            categorized = False
            
            for keyword in compute_keywords:
                if keyword in service_lower:
                    categories["Compute"].append(service)
                    categorized = True
                    break
            
            if not categorized:
                for keyword in storage_keywords:
                    if keyword in service_lower:
                        categories["Storage"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in database_keywords:
                    if keyword in service_lower:
                        categories["Database"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in networking_keywords:
                    if keyword in service_lower:
                        categories["Networking"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in security_keywords:
                    if keyword in service_lower:
                        categories["Security"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in analytics_keywords:
                    if keyword in service_lower:
                        categories["Analytics"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in ai_keywords:
                    if keyword in service_lower:
                        categories["AI + Machine Learning"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in integration_keywords:
                    if keyword in service_lower:
                        categories["Integration"].append(service)
                        categorized = True
                        break
            
            if not categorized:
                categories["Other"].append(service)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _get_category_color(self, category: str) -> str:
        """Get background color for service category"""
        colors = {
            "Compute": "#fff3e0",
            "Storage": "#e3f2fd",
            "Database": "#f3e5f5",
            "Networking": "#e8f5e8",
            "Security": "#ffebee",
            "Analytics": "#fafafa",
            "AI + Machine Learning": "#e1f5fe",
            "Integration": "#f9fbe7",
            "Other": "#f5f5f5"
        }
        return colors.get(category, "#f5f5f5")
    
    def _get_category_border_color(self, category: str) -> str:
        """Get border color for service category"""
        colors = {
            "Compute": "#ff9800",
            "Storage": "#2196f3",
            "Database": "#9c27b0",
            "Networking": "#4caf50",
            "Security": "#f44336",
            "Analytics": "#607d8b",
            "AI + Machine Learning": "#00bcd4",
            "Integration": "#8bc34a",
            "Other": "#9e9e9e"
        }
        return colors.get(category, "#9e9e9e")
    
    def detect_services_from_prompt(self, prompt: str) -> List[Dict[str, str]]:
        """Intelligently detect Azure services from user prompt"""
        try:
            if not prompt or not isinstance(prompt, str):
                return []
                
            prompt_lower = prompt.lower().strip()
            if not prompt_lower:
                return []
                
            detected_services = []
            
            # Score-based detection for better accuracy
            service_scores = {}
            
            # Check if service_keywords exists
            if not hasattr(self, 'service_keywords') or not self.service_keywords:
                return []
            
            for service, keywords in self.service_keywords.items():
                if not keywords or not isinstance(keywords, list):
                    continue
                    
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    try:
                        if not keyword or not isinstance(keyword, str):
                            continue
                            
                        keyword_stripped = keyword.strip()
                        if keyword_stripped and keyword_stripped in prompt_lower:
                            # Longer keywords get higher scores - with safe split
                            if keyword_stripped:
                                split_count = len(keyword_stripped.split()) if keyword_stripped else 0
                                score += split_count
                                matched_keywords.append(keyword_stripped)
                    except Exception as e:
                        # Skip this keyword if there's any issue
                        continue
                
                if score > 0:
                    service_scores[service] = {
                        'score': score,
                        'keywords': matched_keywords,
                        'icon_type': self._determine_icon_source(service)
                    }
            
            # Sort by score and return top services
            sorted_services = sorted(service_scores.items(), key=lambda x: x[1]['score'], reverse=True)
            
            for service, data in sorted_services:
                detected_services.append({
                    'name': service,
                    'confidence': min(data['score'] / 5.0, 1.0),  # Normalize to 0-1
                    'keywords_matched': data['keywords'],
                    'icon_source': data['icon_type'],
                    'icon_url': self._get_service_icon_url(service)
                })
            
            return detected_services
            
        except Exception as e:
            # Return empty list if there's any error during detection
            return []
    
    def _determine_icon_source(self, service_name: str) -> str:
        """Determine whether to use local SVG or Azure Portal icon"""
        try:
            if not service_name or not isinstance(service_name, str):
                return 'default'
                
            if hasattr(self, 'azure_portal_icons') and service_name in self.azure_portal_icons:
                return 'portal'
            elif hasattr(self, 'azure_service_icons') and service_name in self.azure_service_icons:
                return 'local'
            else:
                return 'default'
        except Exception:
            return 'default'
    
    def _get_service_icon_url(self, service_name: str) -> str:
        """Get icon URL (portal or local)"""
        try:
            if not service_name or not isinstance(service_name, str):
                return "default://icon"
                
            if hasattr(self, 'azure_portal_icons') and service_name in self.azure_portal_icons:
                return self.azure_portal_icons[service_name]
            else:
                icon_path = self._get_service_icon_path(service_name)
                if icon_path:
                    return f"local://{self.icons_base_path}/{icon_path}"
                else:
                    return "default://icon"
        except Exception:
            return "default://icon"
    
    def _get_service_icon_path(self, service_name: str) -> str:
        """Get the icon path for a service"""
        # Try exact match first
        if service_name in self.azure_service_icons:
            return self.azure_service_icons[service_name]
        
        # Try partial match
        for service, icon_path in self.azure_service_icons.items():
            if service.lower() in service_name.lower() or service_name.lower() in service.lower():
                return icon_path
        
        # Default to Virtual Machine icon
        return self.azure_service_icons["Virtual Machine"]
    
    def generate_mermaid_diagram(self, architecture: Dict[str, Any]) -> str:
        """Generate Mermaid diagram with Azure styling"""
        services = architecture.get("services", [])
        # Normalize services to strings (they may be dicts with 'name' key)
        services = [s["name"] if isinstance(s, dict) else s for s in services]
        
        mermaid = "graph TB\n"
        mermaid += "    subgraph Azure[\"☁️ Microsoft Azure\"]\n"
        mermaid += "        subgraph RG[\"📦 Resource Group\"]\n"
        
        # Categorize services
        categorized = self._categorize_azure_services(services)
        
        for category, service_list in categorized.items():
            if service_list:
                category_icon = self._get_azure_category_icon(category)
                mermaid += f"            subgraph {category.upper().replace(' ', '_')}[\"{category_icon} {category}\"]\n"
                
                for service in service_list:
                    service_id = service.replace(" ", "").replace("-", "")
                    service_icon = self._get_azure_service_emoji(service)
                    mermaid += f"                {service_id}[\"{service_icon} {service}\"]\n"
                
                mermaid += "            end\n"
        
        mermaid += "        end\n"
        mermaid += "    end\n"
        
        # Add connections from actual architecture data (real data flows)
        arch_connections = architecture.get("connections", [])
        if arch_connections:
            mermaid += "\n    %% Architecture Connections\n"
            for conn in arch_connections:
                if isinstance(conn, dict):
                    source = conn.get("source", "")
                    target = conn.get("target", "")
                    label = conn.get("label", conn.get("protocol", ""))
                    source_id = source.replace(" ", "").replace("-", "")
                    target_id = target.replace(" ", "").replace("-", "")
                    if label:
                        mermaid += f"    {source_id} -->|{label}| {target_id}\n"
                    else:
                        mermaid += f"    {source_id} --> {target_id}\n"
        
        # Add Azure styling
        mermaid += "\n    %% Azure Styling\n"
        mermaid += "    classDef azure fill:#0078d4,stroke:#005a9e,stroke-width:2px,color:#fff\n"
        mermaid += "    classDef compute fill:#ff6b35,stroke:#e55100,stroke-width:2px,color:#fff\n"
        mermaid += "    classDef storage fill:#00bcf2,stroke:#0288d1,stroke-width:2px,color:#fff\n"
        mermaid += "    classDef database fill:#ba68c8,stroke:#8e24aa,stroke-width:2px,color:#fff\n"
        mermaid += "    classDef networking fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff\n"
        mermaid += "    classDef security fill:#f44336,stroke:#d32f2f,stroke-width:2px,color:#fff\n"
        
        return mermaid
    
    def _categorize_azure_services(self, services: List[str]) -> Dict[str, List[str]]:
        """Categorize Azure services"""
        categories = {
            "Compute": [],
            "Storage": [],
            "Database": [],
            "Networking": [],
            "Security": [],
            "Analytics": [],
            "AI + ML": [],
            "Integration": [],
            "Monitoring": [],
            "Web": []
        }
        
        category_keywords = {
            "Compute": ["virtual machine", "app service", "function", "kubernetes", "container", "batch"],
            "Storage": ["storage", "blob", "file", "data lake", "backup"],
            "Database": ["sql", "cosmos", "mysql", "postgresql", "redis", "synapse"],
            "Networking": ["network", "load balancer", "gateway", "firewall", "cdn", "front door"],
            "Security": ["key vault", "security", "sentinel", "defender"],
            "Analytics": ["analytics", "databricks", "event hub", "stream", "power bi"],
            "AI + ML": ["cognitive", "machine learning", "bot", "openai", "vision"],
            "Integration": ["logic apps", "api management", "service bus", "event grid"],
            "Monitoring": ["monitor", "insights", "log analytics"],
            "Web": ["web", "static", "signalr", "api center"]
        }
        
        for service in services:
            categorized = False
            for category, keywords in category_keywords.items():
                if any(keyword in service.lower() for keyword in keywords):
                    categories[category].append(service)
                    categorized = True
                    break
            
            if not categorized:
                categories["Compute"].append(service)  # Default category
        
        return {k: v for k, v in categories.items() if v}  # Remove empty categories
    
    def _get_azure_category_icon(self, category: str) -> str:
        """Get emoji for Azure service category"""
        icons = {
            "Compute": "⚡",
            "Storage": "💾",
            "Database": "🗄️",
            "Networking": "🌐",
            "Security": "🔒",
            "Analytics": "📊",
            "AI + ML": "🤖",
            "Integration": "🔗",
            "Monitoring": "📈",
            "Web": "🌍"
        }
        return icons.get(category, "🔧")
    
    def _get_azure_service_emoji(self, service: str) -> str:
        """Get emoji for specific Azure service"""
        service_emojis = {
            "Virtual Machine": "🖥️",
            "App Services": "🌐",
            "Function Apps": "⚡",
            "SQL Database": "🗃️",
            "Cosmos DB": "🌌",
            "Storage Account": "💾",
            "Key Vault": "🔐",
            "Virtual Network": "🏢",
            "Load Balancer": "⚖️",
            "Application Gateway": "🚪"
        }
        
        for azure_service, emoji in service_emojis.items():
            if azure_service.lower() in service.lower():
                return emoji
        return "🔧"
    
    def generate_terraform_template(self, architecture: Dict[str, Any]) -> str:
        """Generate comprehensive Terraform template for Azure resources"""
        services = architecture.get("services", [])
        # Normalize services to strings (they may be dicts with 'name' key)
        services = [s["name"] if isinstance(s, dict) else s for s in services]
        
        terraform = '''# Azure Architecture Terraform Template
# Generated by Azure Architecture Generator

terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "azure-architecture"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "Azure Architecture"
    ManagedBy   = "Terraform"
  }
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Data sources
data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = var.tags
}

# Network Security Group
resource "azurerm_network_security_group" "main" {
  name                = "nsg-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  security_rule {
    name                       = "HTTPS"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

'''
        
        # Add resources based on detected services
        terraform_resources = []
        
        for service in services:
            service_lower = service.lower()
            
            # Virtual Network (add for any networking service)
            if any(keyword in service_lower for keyword in ["network", "vm", "virtual machine", "app service", "function"]):
                if "azurerm_virtual_network" not in terraform:
                    terraform_resources.append(self._get_terraform_vnet())
            
            # Storage Account
            if any(keyword in service_lower for keyword in ["storage", "blob", "file", "data lake"]):
                terraform_resources.append(self._get_terraform_storage(service))
            
            # Virtual Machine
            if any(keyword in service_lower for keyword in ["vm", "virtual machine", "compute"]):
                terraform_resources.extend(self._get_terraform_vm())
            
            # App Service
            if any(keyword in service_lower for keyword in ["app service", "web app"]):
                terraform_resources.extend(self._get_terraform_app_service())
            
            # Function App
            if any(keyword in service_lower for keyword in ["function", "serverless"]):
                terraform_resources.extend(self._get_terraform_function_app())
            
            # SQL Database
            if any(keyword in service_lower for keyword in ["sql", "database"]):
                terraform_resources.extend(self._get_terraform_sql_database())
            
            # Cosmos DB
            if "cosmos" in service_lower:
                terraform_resources.append(self._get_terraform_cosmos_db())
            
            # Key Vault
            if any(keyword in service_lower for keyword in ["key vault", "secret", "certificate"]):
                terraform_resources.append(self._get_terraform_key_vault())
            
            # Application Gateway
            if "gateway" in service_lower:
                terraform_resources.append(self._get_terraform_app_gateway())
            
            # Load Balancer
            if "load balancer" in service_lower:
                terraform_resources.append(self._get_terraform_load_balancer())
            
            # Azure Kubernetes Service
            if any(keyword in service_lower for keyword in ["kubernetes", "aks", "k8s"]):
                terraform_resources.extend(self._get_terraform_aks())
        
        # Add all resources to terraform template
        terraform += "\n".join(set(terraform_resources))  # Use set to avoid duplicates
        
        # Add outputs
        terraform += '''

# Outputs
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    environment      = var.environment
    location        = var.location
    project_name    = var.project_name
    resource_count  = length(azurerm_resource_group.main.tags)
  }
}
'''
        
        return terraform
    
    def _get_terraform_vnet(self) -> str:
        """Generate Terraform for Virtual Network"""
        return '''
# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.project_name}-${var.environment}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_subnet" "internal" {
  name                 = "snet-internal"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}
'''
    
    def _get_terraform_storage(self, service: str) -> str:
        """Generate Terraform for Storage Account"""
        return '''
# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = "st${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.tags
}
'''
    
    def _get_terraform_vm(self) -> List[str]:
        """Generate Terraform for Virtual Machine"""
        return ['''
# Public IP for VM
resource "azurerm_public_ip" "vm" {
  name                = "pip-vm-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Dynamic"
  tags                = var.tags
}

# Network Interface for VM
resource "azurerm_network_interface" "vm" {
  name                = "nic-vm-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.internal.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm.id
  }
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "main" {
  name                = "vm-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = "Standard_B1s"
  admin_username      = "adminuser"
  tags                = var.tags

  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.vm.id,
  ]

  admin_ssh_key {
    username   = "adminuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }
}
''']
    
    def _get_terraform_app_service(self) -> List[str]:
        """Generate Terraform for App Service"""
        return ['''
# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = "sp-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "B1"
  tags                = var.tags
}

# App Service
resource "azurerm_linux_web_app" "main" {
  name                = "app-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  tags                = var.tags

  site_config {
    always_on = false
  }
}
''']
    
    def _get_terraform_function_app(self) -> List[str]:
        """Generate Terraform for Function App"""
        return ['''
# Function App
resource "azurerm_linux_function_app" "main" {
  name                = "func-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  tags                = var.tags

  site_config {}
}
''']
    
    def _get_terraform_sql_database(self) -> List[str]:
        """Generate Terraform for SQL Database"""
        return ['''
# SQL Server
resource "azurerm_mssql_server" "main" {
  name                         = "sql-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_username    # NEVER hardcode credentials
  administrator_login_password = var.sql_admin_password    # Use Key Vault or variable injection
  tags                         = var.tags
}

# SQL Database
resource "azurerm_mssql_database" "main" {
  name      = "sqldb-${var.project_name}-${var.environment}"
  server_id = azurerm_mssql_server.main.id
  sku_name  = "Basic"
  tags      = var.tags
}
''']
    
    def _get_terraform_cosmos_db(self) -> str:
        """Generate Terraform for Cosmos DB"""
        return '''
# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  tags                = var.tags

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }
}
'''
    
    def _get_terraform_key_vault(self) -> str:
        """Generate Terraform for Key Vault"""
        return '''
# Key Vault
resource "azurerm_key_vault" "main" {
  name                        = "kv-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"
  tags                        = var.tags

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get",
    ]

    secret_permissions = [
      "Get",
    ]

    storage_permissions = [
      "Get",
    ]
  }
}
'''
    
    def _get_terraform_app_gateway(self) -> str:
        """Generate Terraform for Application Gateway"""
        return '''
# Public IP for Application Gateway
resource "azurerm_public_ip" "app_gateway" {
  name                = "pip-appgw-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

# Subnet for Application Gateway
resource "azurerm_subnet" "app_gateway" {
  name                 = "snet-appgw"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Application Gateway
resource "azurerm_application_gateway" "main" {
  name                = "appgw-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }

  gateway_ip_configuration {
    name      = "appgw-ip-configuration"
    subnet_id = azurerm_subnet.app_gateway.id
  }

  frontend_port {
    name = "appgw-feport"
    port = 80
  }

  frontend_ip_configuration {
    name                 = "appgw-feip"
    public_ip_address_id = azurerm_public_ip.app_gateway.id
  }

  backend_address_pool {
    name = "appgw-beap"
  }

  backend_http_settings {
    name                  = "appgw-be-htst"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 60
  }

  http_listener {
    name                           = "appgw-httplstn"
    frontend_ip_configuration_name = "appgw-feip"
    frontend_port_name             = "appgw-feport"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "appgw-rqrt"
    rule_type                  = "Basic"
    http_listener_name         = "appgw-httplstn"
    backend_address_pool_name  = "appgw-beap"
    backend_http_settings_name = "appgw-be-htst"
    priority                   = 100
  }
}
'''
    
    def _get_terraform_load_balancer(self) -> str:
        """Generate Terraform for Load Balancer"""
        return '''
# Public IP for Load Balancer
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  tags                = var.tags
}

# Load Balancer
resource "azurerm_lb" "main" {
  name                = "lb-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  frontend_ip_configuration {
    name                 = "PublicIPAddress"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}
'''
    
    def _get_terraform_aks(self) -> List[str]:
        """Generate Terraform for Azure Kubernetes Service"""
        return ['''
# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}-aks"
  tags                = var.tags

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_B2s"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "kubenet"
  }
}
''']
    
    def get_available_icons(self) -> Dict[str, List[str]]:
        """Return available Azure service icons organized by category"""
        return {
            "Compute": [
                "Virtual Machine", "App Services", "Function Apps", 
                "Kubernetes Services", "Container Instances", "VM Scale Sets"
            ],
            "Storage": [
                "Storage Account", "Blob Storage", "File Share", 
                "Data Lake", "NetApp Files", "Backup Vault"
            ],
            "Database": [
                "SQL Database", "Cosmos DB", "MySQL", "PostgreSQL", 
                "Redis Cache", "Synapse Analytics"
            ],
            "Networking": [
                "Virtual Network", "Load Balancer", "Application Gateway", 
                "VPN Gateway", "ExpressRoute", "Front Door"
            ],
            "Security": [
                "Key Vault", "Azure AD", "Managed Identity", 
                "Security Center", "Sentinel"
            ],
            "Analytics": [
                "Event Hubs", "Stream Analytics", "Data Factory", 
                "Databricks", "HDInsight", "Power BI"
            ]
        }