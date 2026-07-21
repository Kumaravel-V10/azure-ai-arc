from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import asyncio
import csv
import zipfile
import io
import base64
import os
import re
import html
import logging
import json
import glob
import uuid
from datetime import datetime
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from azure_analyzer import AzureOpenAIAnalyzer
from azure_icon_generator import AzureIconDiagramGenerator
from multi_agent_workflow import MultiAgentWorkflowPipeline, run_multi_agent_workflow
from agents import AgentOrchestrator, FeatureImpactAnalyzerAgent, ArchitectureAgent
from ai_validator import AIArchitectureValidator
from drawio_parser import DrawioParser, generate_drawio_from_architecture
from config import api_config, agent_config, validation_config, path_config, workflow_config, content_config, azure_openai_config
from reverse_engineer import ReverseEngineerOrchestrator
from diff_analyzer import ArchitectureDiffAnalyzer, AIEnhancedDiffAnalyzer, DiffReportGenerator
from diagram_modification_agent import DiagramModificationAgent, ModificationStrategy
from extras.architecture_modifier import (
    _build_baseline_services_and_connections,
    _dynamic_edge_stitching,
    _filter_enhanced_connections,
    _build_service_lookup,
    _generate_highlighted_preview_xml,
    _inject_nodes_and_edges_into_xml,
    _parse_drawio_xml_to_dict,
    _remove_generated_artifacts_from_xml,
)

# LangGraph import (optional - falls back gracefully)
try:
    from langgraph_workflow import run_langgraph_workflow, get_langgraph_workflow, LANGGRAPH_AVAILABLE
except ImportError:
    LANGGRAPH_AVAILABLE = False
    run_langgraph_workflow = None
    get_langgraph_workflow = None

# Load environment variables
load_dotenv()

# Global progress tracking store with TTL cleanup
agent_progress_store = {}
PROGRESS_STORE_TTL_SECONDS = 3600  # 1 hour

# Human-in-the-loop interaction store
# Stores pending interaction requests from agents waiting for user decisions
agent_interaction_store = {}  # session_id -> interaction data


def cleanup_expired_sessions():
    """Remove progress entries older than TTL to prevent memory leaks."""
    now = datetime.now()
    expired = [
        sid for sid, data in agent_progress_store.items()
        if (now - datetime.fromisoformat(data.get("created_at", now.isoformat()))).total_seconds() > PROGRESS_STORE_TTL_SECONDS
    ]
    for sid in expired:
        del agent_progress_store[sid]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired progress sessions")

# Enhanced Pydantic Models
class GenerateRequest(BaseModel):
    requirements: str = Field(..., description="Architecture requirements description", min_length=10)
    project_name: Optional[str] = Field(None, description="Optional project name")
    environment: Optional[str] = Field("production", description="Target environment")
    include_terraform: Optional[bool] = Field(True, description="Generate Terraform templates")
    include_mermaid: Optional[bool] = Field(True, description="Generate Mermaid diagrams")
    use_professional_style: Optional[bool] = Field(True, description="Use professional Microsoft-style diagrams")
    use_langgraph: Optional[bool] = Field(True, description="Use LangGraph for improved agent accuracy")

class ValidationRequest(BaseModel):
    actual_diagram: Optional[str] = None
    expected_diagram: Optional[str] = None
    requirements: str = Field("", description="Architecture requirements")
    validation_type: Optional[str] = Field("full", description="Type of validation to perform")

class ServiceDetectionRequest(BaseModel):
    prompt: str = Field(..., description="User prompt for service detection", min_length=5)
    confidence_threshold: Optional[float] = Field(content_config.CONFIDENCE_THRESHOLD, description="Minimum confidence for service detection")

class ArchitectureAnalysisRequest(BaseModel):
    services: List[str] = Field(..., description="List of Azure services to analyze")
    requirements: str = Field(..., description="Architecture requirements")
    architecture_pattern: Optional[str] = Field(None, description="Preferred architecture pattern")

class FeatureImpactAnalyzeRequest(BaseModel):
    application_name: str = Field(..., min_length=2, description="Application name")
    feature_name: str = Field(..., min_length=2, description="Feature name")
    feature_description: str = Field(..., min_length=10, description="Feature description")
    business_capability: Optional[str] = Field("General", description="Business capability")
    change_type: Optional[str] = Field("New Feature", description="Change type")
    priority: Optional[str] = Field("Medium", description="Priority")
    target_release: Optional[str] = Field(None, description="Target release")
    architecture_layer: Optional[List[str]] = Field(default_factory=list, description="Scoped architecture layers")
    impact_type: Optional[List[str]] = Field(default_factory=list, description="Scoped impact types")
    environment: Optional[str] = Field("Prod", description="Target environment")
    view_mode: Optional[str] = Field("Technical View", description="View mode")
    confidence_threshold: Optional[str] = Field("All", description="Confidence threshold")


def _build_feature_impact_requirements_text(request: FeatureImpactAnalyzeRequest) -> str:
    """Build a normalized text requirement block consumed by the impact agent."""
    return (
        f"Application: {request.application_name}\n"
        f"Feature: {request.feature_name}\n"
        f"Description: {request.feature_description}\n"
        f"Business Capability: {request.business_capability}\n"
        f"Change Type: {request.change_type}\n"
        f"Priority: {request.priority}\n"
        f"Target Release: {request.target_release}\n"
        f"Architecture Layer Scope: {', '.join(request.architecture_layer or [])}\n"
        f"Impact Type Scope: {', '.join(request.impact_type or [])}\n"
        f"Environment: {request.environment}\n"
        f"View Mode: {request.view_mode}\n"
    )


def _lookup_application_diagram(application_name: str) -> Dict[str, Any]:
    """Lookup application architecture diagram from Knowledgebase/applications.csv."""
    if not application_name:
        return {"found": False}

    workspace_root = Path(__file__).resolve().parents[1]
    csv_path = workspace_root / "Knowledgebase" / "applications.csv"
    if not csv_path.exists():
        return {"found": False}

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_name = (row.get("application_name") or row.get("application") or "").strip().lower()
                if row_name != application_name.strip().lower():
                    continue

                diagram_path = (row.get("architecture_diagram") or row.get("diagram_path") or row.get("location") or "").strip()
                diagram_title = (row.get("diagram_title") or row.get("title") or application_name).strip()

                resolved_path = None
                diagram_xml = None
                if diagram_path:
                    candidate_paths = [
                        workspace_root / diagram_path,
                        workspace_root / "Knowledgebase" / Path(diagram_path).name,
                    ]
                    for candidate in candidate_paths:
                        if candidate.exists():
                            resolved_path = candidate
                            break
                    if resolved_path and resolved_path.suffix.lower() == ".drawio":
                        diagram_xml = resolved_path.read_text(encoding="utf-8")

                return {
                    "found": True,
                    "application_name": application_name,
                    "diagram_title": diagram_title,
                    "diagram_path": diagram_path,
                    "diagram_xml": diagram_xml,
                    "resolved_path": str(resolved_path) if resolved_path else None,
                }
    except Exception as exc:
        logger.warning(f"Application diagram lookup failed: {exc}")

    return {"found": False}


def _build_feature_impact_analysis_payload(request: FeatureImpactAnalyzeRequest) -> Dict[str, Any]:
    """Build a pragmatic architecture impact analysis payload for UI rendering."""
    capability = (request.business_capability or "General").lower()
    feature_name = request.feature_name.strip()
    feature_description = request.feature_description.strip()

    existing_components = [
        {
            "id": "ui-agent",
            "name": "Agent UI",
            "layer": "UI",
            "purpose": "Agent-facing servicing workflows",
            "status": "Active",
            "changeStatus": "Impacted",
            "impactSummary": f"Add {feature_name} workflow section"
        },
        {
            "id": "api-gateway",
            "name": "API Gateway",
            "layer": "API",
            "purpose": "Single entry point for application APIs",
            "status": "Active",
            "changeStatus": "Impacted",
            "impactSummary": "Route new feature endpoint and policies"
        },
        {
            "id": "svc-core",
            "name": "Core Business Service",
            "layer": "Service",
            "purpose": "Orchestrates domain business operations",
            "status": "Active",
            "changeStatus": "Impacted",
            "impactSummary": "Add orchestration for new feature path"
        },
        {
            "id": "db-main",
            "name": "Operational Database",
            "layer": "Data",
            "purpose": "Stores transactional records",
            "status": "Active",
            "changeStatus": "Impacted",
            "impactSummary": "Persist feature-related state"
        },
        {
            "id": "obs-appinsights",
            "name": "Application Insights",
            "layer": "Observability",
            "purpose": "Tracing, metrics, and logs",
            "status": "Active",
            "changeStatus": "Impacted",
            "impactSummary": "Add telemetry for feature execution"
        },
    ]

    if capability in {"payment", "refund"}:
        existing_components.append(
            {
                "id": "int-payment",
                "name": "Payment Gateway Integration",
                "layer": "Integration",
                "purpose": "External payment provider integration",
                "status": "Active",
                "changeStatus": "Impacted",
                "impactSummary": "Contract and payload updates"
            }
        )

    proposed_components = [c.copy() for c in existing_components]
    new_component = {
        "id": "svc-feature-impact",
        "name": f"{feature_name} Service",
        "layer": "Service",
        "purpose": f"Executes {feature_name} domain logic",
        "status": "Planned",
        "changeStatus": "New",
        "impactSummary": feature_description,
        "discussionRequired": True,
        "reasonNeeded": "Isolates feature logic from existing orchestration to reduce coupling",
        "ownerNeeded": "Yes",
        "deploymentRequired": "Yes",
    }
    proposed_components.append(new_component)

    detailed_impacts = [
        {
            "component": "Agent UI",
            "layer": "UI",
            "currentRole": "Agent servicing screen",
            "impact": f"Expose {feature_name} workflow",
            "changeNeeded": "UI enhancement",
            "risk": "Medium",
            "discussionRequired": "No",
        },
        {
            "component": "API Gateway",
            "layer": "API",
            "currentRole": "API routing and policy enforcement",
            "impact": "Add new route and policy checks",
            "changeNeeded": "API route + policy update",
            "risk": "Medium",
            "discussionRequired": "No",
        },
        {
            "component": "Core Business Service",
            "layer": "Service",
            "currentRole": "Core orchestration",
            "impact": f"Invoke {feature_name} Service",
            "changeNeeded": "Service orchestration change",
            "risk": "High",
            "discussionRequired": "Yes",
        },
        {
            "component": "Operational Database",
            "layer": "Data",
            "currentRole": "Transactional persistence",
            "impact": "Store feature state and outcomes",
            "changeNeeded": "Schema extension",
            "risk": "High",
            "discussionRequired": "Yes",
        },
        {
            "component": f"{feature_name} Service",
            "layer": "Service",
            "currentRole": "New service",
            "impact": "New deployable unit",
            "changeNeeded": "Build + deploy",
            "risk": "Medium",
            "discussionRequired": "Yes",
        },
    ]

    decision_items = [
        {
            "decision": "Build vs Reuse",
            "question": f"Should {feature_name} logic be embedded in Core Business Service or isolated in a new service?",
            "participants": ["Architect", "Service Owner", "Product Owner"],
            "priority": "High",
        },
        {
            "decision": "API Design",
            "question": "Should feature execution be synchronous or asynchronous?",
            "participants": ["Architect", "API Owner"],
            "priority": "High",
        },
        {
            "decision": "Data Storage",
            "question": "What data retention and migration strategy is required?",
            "participants": ["Architect", "DBA", "Compliance Owner"],
            "priority": "Medium",
        },
    ]

    discussion_items = [
        {
            "topic": f"{feature_name} ownership and deployment boundary",
            "reason": "A new service is introduced and ownership/SLO must be defined",
            "requiredParticipants": ["Architect", "Product Owner", "Service Owner"],
            "priority": "High",
        },
        {
            "topic": "Database schema update",
            "reason": "Schema changes require migration and rollback strategy",
            "requiredParticipants": ["Architect", "DBA", "Platform Owner"],
            "priority": "High",
        },
    ]

    impacted_count = len([c for c in proposed_components if c.get("changeStatus") == "Impacted"])
    new_count = len([c for c in proposed_components if c.get("changeStatus") == "New"])
    discussion_required = any(item.get("priority") == "High" for item in discussion_items)

    return {
        "application": {
            "name": request.application_name,
            "environment": request.environment,
            "viewMode": request.view_mode,
        },
        "feature": {
            "name": feature_name,
            "description": feature_description,
            "changeType": request.change_type,
            "priority": request.priority,
            "targetRelease": request.target_release,
            "businessCapability": request.business_capability,
        },
        "existingArchitecture": {
            "components": existing_components,
        },
        "proposedArchitecture": {
            "components": proposed_components,
        },
        "architectureDiff": {
            "added": [new_component["name"]],
            "modified": [c["name"] for c in proposed_components if c.get("changeStatus") == "Impacted"],
            "unchanged": [],
            "removed": [],
        },
        "impactSummary": {
            "impactLevel": "High" if impacted_count >= 4 else "Medium",
            "impactedComponentCount": impacted_count,
            "newComponentCount": new_count,
            "apiChangeRequired": True,
            "dataChangeRequired": True,
            "securityReviewRequired": True,
            "discussionRequired": discussion_required,
        },
        "detailedImpactTable": detailed_impacts,
        "newComponentRecommendations": [
            {
                "componentName": new_component["name"],
                "componentType": "Service",
                "purpose": new_component["purpose"],
                "reasonNeeded": new_component["reasonNeeded"],
                "ownerNeeded": new_component["ownerNeeded"],
                "deploymentRequired": new_component["deploymentRequired"],
                "discussionRequired": "Yes",
            }
        ],
        "decisionPanel": decision_items,
        "minimalExplanation": {
            "whyImpacted": f"Core API, service orchestration, and persistence layers are impacted to support {feature_name}.",
            "whatChanges": f"Introduce {feature_name} Service, update API routes, extend database schema, and add telemetry.",
            "discussionRequired": "Yes - ownership, schema migration, and API contract updates require architecture review.",
        },
        "aiConfidence": {
            "confidence": "Medium",
            "assumptions": [
                "Existing architecture has API gateway, core service, and transactional database.",
                f"{feature_name} requires persistent state and observability updates.",
            ],
            "missingInformation": [
                "Current API contract details",
                "Data retention policy",
                "Throughput and latency targets",
            ],
            "sourceUsed": ["user_input", "feature_impact_rules"],
        },
        "discussionItems": discussion_items,
        "legend": {
            "unchanged": "Grey",
            "impacted": "Orange",
            "new": "Green",
            "removed": "Red",
            "discussionRequired": "Purple",
        },
        "requestedScope": {
            "architectureLayer": request.architecture_layer,
            "impactType": request.impact_type,
            "confidenceThreshold": request.confidence_threshold,
        },
        "timestamp": datetime.now().isoformat(),
    }


def _slugify_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", (value or "").strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or fallback


def _layer_to_category(layer: str) -> str:
    layer_key = (layer or "").strip().lower()
    mapping = {
        "ui": "networking",
        "api": "integration",
        "service": "compute",
        "data": "data",
        "integration": "integration",
        "security": "security",
        "observability": "monitoring",
    }
    return mapping.get(layer_key, "compute")


def _get_icon_path_for_component(component: Dict[str, Any]) -> str:
    """Determine the appropriate Azure icon path for a component.
    
    Priority:
    1. Use resourceType field if available
    2. Match component name against keyword patterns
    3. Fall back to generic resource icon
    """
    parser = DrawioParser()
    
    # Try resourceType first (if LLM provided it)
    resource_type = component.get("resourceType", "").strip().lower()
    if resource_type:
        # Map resourceType to service name for icon lookup
        type_to_service_name = {
            # Compute
            "function_app": "Function Apps",
            "function app": "Function Apps",
            "func": "Function Apps",
            "app_service": "App Services",
            "app service": "App Services",
            "web app": "App Services",
            "container_instance": "Container Instances",
            "container app": "Container Apps",
            "virtual_machine": "Virtual Machine",
            "vm": "Virtual Machine",
            "kubernetes": "Kubernetes Services",
            "aks": "Kubernetes Services",
            # Storage
            "storage_account": "Storage Account",
            "storage account": "Storage Account",
            "blob": "Blob Storage",
            "data_lake": "Data Lake",
            # Database
            "database": "SQL Database",
            "sql_database": "SQL Database",
            "sql database": "SQL Database",
            "cosmos_db": "Cosmos DB",
            "cosmosdb": "Cosmos DB",
            "cache": "Redis Cache",
            "redis": "Redis Cache",
            "postgresql": "PostgreSQL",
            "postgres": "PostgreSQL",
            "mysql": "MySQL",
            # Networking
            "virtual_network": "Virtual Network",
            "vnet": "Virtual Network",
            "load_balancer": "Load Balancer",
            "application_gateway": "Application Gateway",
            "app gateway": "Application Gateway",
            "vpn_gateway": "VPN Gateway",
            "firewall": "Firewall",
            "cdn": "CDN",
            "front_door": "Front Door",
            # Integration
            "api_management": "API Management",
            "apim": "API Management",
            "event_hub": "Event Hubs",
            "event hubs": "Event Hubs",
            "service_bus": "Service Bus",
            "logic_app": "Logic Apps",
            "event_grid": "Event Grid",
            # Security & Identity
            "keyvault": "Key Vault",
            "key_vault": "Key Vault",
            "active_directory": "Active Directory",
            "entra_id": "Entra ID",
            "sentinel": "Sentinel",
            "managed_identity": "Managed Identity",
            # Monitoring & Analytics
            "log_analytics": "Log Analytics",
            "log_analytics_workspace": "Log Analytics",
            "application_insights": "Application Insights",
            "app insights": "Application Insights",
            "monitor": "Monitor",
            "azure monitor": "Azure Monitor",
            # AI & ML
            "cognitive_services": "Cognitive Services",
            "cognitive": "Cognitive Services",
            "openai": "Azure OpenAI",
            "azure_openai": "Azure OpenAI",
            "machine_learning": "Machine Learning",
            "bot_service": "Bot Services",
            "ai_search": "Search",
            "ai search": "Search",
            # DevOps
            "container_registry": "Container Registry",
            "acr": "Container Registry",
            "devops": "DevOps",
        }
        service_name = type_to_service_name.get(resource_type)
        if service_name:
            return parser._get_azure_icon_path(service_name)
    
    # Fallback: use component name for keyword matching
    comp_name = component.get("name", "")
    if comp_name:
        return parser._get_azure_icon_path(comp_name)
    
    # Final fallback to generic resource
    return parser._get_azure_icon_path("")


def _build_feature_impact_drawio_architecture(payload: Dict[str, Any], request: FeatureImpactAnalyzeRequest) -> Dict[str, Any]:
    proposed_arch = payload.get("proposedArchitecture", {}) if isinstance(payload.get("proposedArchitecture"), dict) else {}
    components = proposed_arch.get("components", []) if isinstance(proposed_arch.get("components"), list) else []
    connections = proposed_arch.get("connections", []) if isinstance(proposed_arch.get("connections"), list) else []

    components_by_id = {}
    services = []
    impacted_names = []
    new_names = []

    for comp in components:
        if not isinstance(comp, dict):
            continue
        comp_id = str(comp.get("id") or "").strip()
        name = str(comp.get("name") or "").strip()
        if not name:
            continue
        if comp_id:
            components_by_id[comp_id] = name

        change_status = str(comp.get("changeStatus") or "").strip()
        if change_status == "Impacted":
            impacted_names.append(name)
        elif change_status == "New":
            new_names.append(name)

        services.append(
            {
                "name": name,
                "category": _layer_to_category(str(comp.get("layer") or "")),
            }
        )

    normalized_connections = []
    for conn in connections:
        if not isinstance(conn, dict):
            continue
        source = str(conn.get("source") or "").strip()
        target = str(conn.get("target") or "").strip()
        if not source or not target:
            continue

        source_name = components_by_id.get(source, source)
        target_name = components_by_id.get(target, target)
        if not source_name or not target_name:
            continue

        normalized_connections.append(
            {
                "source": source_name,
                "target": target_name,
                "label": str(conn.get("label") or ""),
            }
        )

    annotations = []
    if impacted_names:
        annotations.append({"text": f"Impacted: {', '.join(impacted_names[:6])}"})
    if new_names:
        annotations.append({"text": f"New: {', '.join(new_names[:6])}"})

    return {
        "project_name": f"{request.application_name} - {request.feature_name} (Proposed)",
        "services": services,
        "connections": normalized_connections,
        "annotations": annotations,
        "_impacted_names": impacted_names,
        "_new_names": new_names,
    }


def _normalize_drawio_text(value: str) -> str:
    decoded = html.unescape(value or "")
    decoded = decoded.replace("&#xa;", "\n").replace("&nbsp;", " ")
    decoded = decoded.replace("\n", " ")
    decoded = re.sub(r"\s+", " ", decoded)
    return decoded.strip().lower()


def _append_style_once(style: str, extra: str) -> str:
    style = style or ""
    if extra in style:
        return style
    if style and not style.endswith(";"):
        style += ";"
    return style + extra


def _find_existing_drawio_label_matches(root: ET.Element, names: List[str]) -> Dict[str, ET.Element]:
    matches: Dict[str, ET.Element] = {}
    wanted = {name.strip().lower(): name for name in names if name}
    if not wanted:
        return matches

    for cell in root.findall(".//mxCell"):
        value = cell.get("value") or ""
        if not value:
            continue
        normalized = _normalize_drawio_text(value)
        for lookup in wanted:
            if lookup and lookup in normalized and lookup not in matches:
                matches[lookup] = cell
    return matches


def _highlight_existing_drawio_copy(drawio_xml: str, impacted_names: List[str], new_names: List[str]) -> str:
    if not drawio_xml:
        return drawio_xml

    try:
        root = ET.fromstring(drawio_xml)
    except ET.ParseError:
        return drawio_xml

    impacted_matches = _find_existing_drawio_label_matches(root, impacted_names)
    new_matches = _find_existing_drawio_label_matches(root, new_names)

    for lookup, cell in impacted_matches.items():
        style = cell.get("style") or ""
        cell.set("style", _append_style_once(style, "fontStyle=1;fontColor=#b45309;labelBackgroundColor=#fef3c7;rounded=1;spacing=4;"))
        value = cell.get("value") or ""
        if "(Impacted)" not in html.unescape(value):
            cell.set("value", f"{value}&#xa;(Impacted)")

    for lookup, cell in new_matches.items():
        style = cell.get("style") or ""
        cell.set("style", _append_style_once(style, "fontStyle=1;fontColor=#166534;labelBackgroundColor=#dcfce7;rounded=1;spacing=4;"))
        value = cell.get("value") or ""
        if "(New)" not in html.unescape(value):
            cell.set("value", f"{value}&#xa;(New)")

    return ET.tostring(root, encoding="unicode")


def _next_numeric_cell_id(root: ET.Element) -> int:
    max_id = 1000
    for cell in root.findall(".//mxCell"):
        cell_id = cell.get("id") or ""
        if cell_id.isdigit():
            max_id = max(max_id, int(cell_id))
    return max_id + 1


def _add_new_components_to_existing_drawio(drawio_xml: str, payload: Dict[str, Any]) -> str:
    if not drawio_xml:
        return drawio_xml

    proposed_arch = payload.get("proposedArchitecture", {}) if isinstance(payload.get("proposedArchitecture"), dict) else {}
    new_components = [
        component for component in (proposed_arch.get("components") or [])
        if isinstance(component, dict) and component.get("changeStatus") == "New"
    ]
    if not new_components:
        return drawio_xml

    try:
        root = ET.fromstring(drawio_xml)
    except ET.ParseError:
        return drawio_xml

    graph_root = root.find(".//root")
    func_group = root.find(".//mxCell[@id='11']")
    func_section = root.find(".//mxCell[@id='func-section']")
    if graph_root is None:
        return drawio_xml

    parent_id = "11" if func_group is not None else "1"
    icon_parent = func_group if func_group is not None else graph_root.find(".//mxCell[@id='1']")

    existing_icons = [
        cell for cell in root.findall(f".//mxCell[@parent='{parent_id}']")
        if "Function_Apps.svg" in (cell.get("style") or "")
    ]

    xs = []
    ys = []
    for cell in existing_icons:
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue
        xs.append(float(geometry.get("x", 0)))
        ys.append(float(geometry.get("y", 0)))

    base_x = (max(xs) + 110) if xs else 30
    base_y = min(ys) if ys else 50
    row_limit = 1680 if parent_id == "11" else 1800
    width_expand = 0
    next_id = _next_numeric_cell_id(root)

    for index, component in enumerate(new_components):
        comp_name = str(component.get("name") or f"New Component {index + 1}")
        icon_id = f"proposed-new-icon-{index + 1}"
        label_id = f"proposed-new-label-{index + 1}"
        x = base_x + (index * 110)
        y = base_y
        if x > row_limit:
            x = 30 + ((index % 4) * 110)
            y = base_y + 130

        # Get the appropriate icon for this component
        icon_url = _get_icon_path_for_component(component)
        logger.debug(f"[NewNode] {comp_name}: resourceType={component.get('resourceType')}, icon={icon_url}")
        
        icon_cell = ET.Element("mxCell", {
            "id": icon_id,
            "value": "",
            "style": f"image;aspect=fixed;html=1;points=[];align=center;image={icon_url};strokeColor=#166534;strokeWidth=2;fillColor=#dcfce7;rounded=1;",
            "parent": parent_id,
            "vertex": "1",
        })
        ET.SubElement(icon_cell, "mxGeometry", {
            "x": str(int(x)),
            "y": str(int(y)),
            "width": "44",
            "height": "44",
            "as": "geometry",
        })
        graph_root.append(icon_cell)

        label_text = html.escape(comp_name).replace("\n", "&#xa;") + "&#xa;(New)"
        label_cell = ET.Element("mxCell", {
            "id": label_id,
            "value": label_text,
            "style": "text;html=1;align=center;verticalAlign=top;fontSize=9;fontStyle=1;strokeColor=#166534;fillColor=#dcfce7;rounded=1;whiteSpace=wrap;",
            "parent": parent_id,
            "vertex": "1",
        })
        ET.SubElement(label_cell, "mxGeometry", {
            "x": str(int(x - 15)),
            "y": str(int(y + 48)),
            "width": "90",
            "height": "44",
            "as": "geometry",
        })
        graph_root.append(label_cell)

        width_expand = max(width_expand, int(x + 110))
        next_id += 2

    if func_group is not None:
        group_geometry = func_group.find("mxGeometry")
        if group_geometry is not None and width_expand:
            current_width = float(group_geometry.get("width", 1760))
            if width_expand > current_width:
                group_geometry.set("width", str(width_expand))
        if func_section is not None:
            section_geometry = func_section.find("mxGeometry")
            if section_geometry is not None and width_expand:
                current_width = float(section_geometry.get("width", 1760))
                if width_expand > current_width:
                    section_geometry.set("width", str(width_expand))
            title = html.unescape(func_section.get("value") or "Azure Functions")
            count_match = re.search(r"\((\d+) apps\)", title)
            if count_match:
                current_count = int(count_match.group(1))
                func_section.set("value", re.sub(r"\(\d+ apps\)", f"({current_count + len(new_components)} apps)", func_section.get("value") or title, count=1))

    return ET.tostring(root, encoding="unicode")


def _highlight_drawio_labels(drawio_xml: str, impacted_names: List[str], new_names: List[str]) -> str:
    if not drawio_xml:
        return drawio_xml

    impacted_lookup = {name.strip().lower() for name in impacted_names if name}
    new_lookup = {name.strip().lower() for name in new_names if name}
    if not impacted_lookup and not new_lookup:
        return drawio_xml

    try:
        root = ET.fromstring(drawio_xml)
    except ET.ParseError:
        return drawio_xml

    def append_style(style: str, extra: str) -> str:
        style = style or ""
        if style and not style.endswith(";"):
            style += ";"
        return style + extra

    for cell in root.findall(".//mxCell"):
        value = (cell.get("value") or "").strip()
        if not value:
            continue
        value_key = value.lower()
        style = cell.get("style") or ""

        if value_key in impacted_lookup:
            cell.set("style", append_style(style, "fontStyle=1;fontColor=#b45309;labelBackgroundColor=#fef3c7;rounded=1;spacing=4;"))
            if "(Impacted)" not in value:
                cell.set("value", f"{value} (Impacted)")
        elif value_key in new_lookup:
            cell.set("style", append_style(style, "fontStyle=1;fontColor=#166534;labelBackgroundColor=#dcfce7;rounded=1;spacing=4;"))
            if "(New)" not in value:
                cell.set("value", f"{value} (New)")

    return ET.tostring(root, encoding="unicode")


async def _generate_and_save_feature_impact_drawio(payload: Dict[str, Any], request: FeatureImpactAnalyzeRequest) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    architecture = _build_feature_impact_drawio_architecture(payload, request)
    if not architecture.get("services"):
        return payload

    impacted_names = architecture.pop("_impacted_names", [])
    new_names = architecture.pop("_new_names", [])

    try:
        existing_drawio_xml = payload.get("architectureDiagramXml") or payload.get("applicationReference", {}).get("diagram_xml")

        # Resolve baseline diagram XML robustly so updates are applied in-place on the real architecture.
        if not existing_drawio_xml:
            app_ref = _lookup_application_diagram(request.application_name)
            existing_drawio_xml = app_ref.get("diagram_xml") if isinstance(app_ref, dict) else None
            if existing_drawio_xml:
                logger.info("Feature impact diagram update: using baseline XML from application lookup")

        if not existing_drawio_xml:
            workspace_root = Path(__file__).resolve().parents[1]
            architecture_dir = workspace_root / "Arc-frontend" / "public" / "Architecture"
            if architecture_dir.exists():
                wanted = (request.application_name or "").strip().lower()
                for candidate in architecture_dir.glob("*.drawio"):
                    stem = candidate.stem.strip().lower()
                    if stem == wanted:
                        existing_drawio_xml = candidate.read_text(encoding="utf-8", errors="replace")
                        logger.info(f"Feature impact diagram update: using baseline XML from {candidate}")
                        break

        preview_drawio_xml = None

        if existing_drawio_xml:
            original_drawio_xml = existing_drawio_xml
            proposed_arch = payload.get("proposedArchitecture", {}) if isinstance(payload.get("proposedArchitecture"), dict) else {}
            proposed_components = proposed_arch.get("components", []) if isinstance(proposed_arch.get("components"), list) else []

            def _layer_to_numeric(layer: Any) -> int:
                key = str(layer or "").strip().lower()
                if key in {"ui", "edge"}:
                    return 0
                if key in {"api", "gateway"}:
                    return 1
                if key in {"data", "database"}:
                    return 3
                if key in {"security", "observability", "monitoring"}:
                    return -1
                return 2

            services_to_add: List[Dict[str, Any]] = []
            for comp in proposed_components:
                if not isinstance(comp, dict):
                    continue
                if str(comp.get("changeStatus") or "").strip() != "New":
                    continue
                name = str(comp.get("name") or "").strip()
                if not name:
                    continue
                services_to_add.append(
                    {
                        "name": name,
                        "layer": _layer_to_numeric(comp.get("layer")),
                        "category": _layer_to_category(str(comp.get("layer") or "")),
                        "resourceType": comp.get("resourceType", ""),  # Add resourceType for icon selection
                    }
                )

            sanitized_xml = _remove_generated_artifacts_from_xml(existing_drawio_xml)
            baseline_architecture = _parse_drawio_xml_to_dict(sanitized_xml)

            # Align new services with modifier behavior: avoid re-adding existing baseline services.
            baseline_lookup = _build_service_lookup(baseline_architecture)
            filtered_services_to_add: List[Dict[str, Any]] = []
            seen_new_names = set()
            for svc in services_to_add:
                name = str(svc.get("name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen_new_names or key in baseline_lookup:
                    continue
                seen_new_names.add(key)
                filtered_services_to_add.append(svc)

            # Use full modifier connection update logic to preserve baseline-oriented stitching.
            feature_prompt_text = (
                f"Feature: {request.feature_name}\n"
                f"Description: {request.feature_description}\n"
                f"Business capability: {request.business_capability}"
            )
            arch_agent = ArchitectureAgent()
            initial_connections = _dynamic_edge_stitching(
                baseline_architecture=baseline_architecture,
                services_to_add=filtered_services_to_add,
                arch_agent=arch_agent,
                modification_prompt=feature_prompt_text,
                csv_context_summary="",
            )
            validated_connections = _filter_enhanced_connections(
                enhanced_connections=initial_connections,
                baseline_architecture=baseline_architecture,
                services_to_add=filtered_services_to_add,
                modification_prompt=feature_prompt_text,
                csv_context_summary="",
            )
            if not validated_connections:
                validated_connections = initial_connections

            # Include explicit proposed links touching newly inserted services.
            proposed_connections = proposed_arch.get("connections", []) if isinstance(proposed_arch.get("connections"), list) else []
            component_name_by_id: Dict[str, str] = {}
            for comp in proposed_components:
                if not isinstance(comp, dict):
                    continue
                comp_id = str(comp.get("id") or "").strip()
                comp_name = str(comp.get("name") or "").strip()
                if comp_id and comp_name:
                    component_name_by_id[comp_id] = comp_name
            new_names_set = {str(s.get("name") or "").strip().lower() for s in filtered_services_to_add if s.get("name")}
            seen_conn_sig = {
                (
                    str(c.get("source") or "").strip().lower(),
                    str(c.get("target") or "").strip().lower(),
                    str(c.get("label") or "").strip().lower(),
                )
                for c in validated_connections
                if isinstance(c, dict)
            }
            for conn in proposed_connections:
                if not isinstance(conn, dict):
                    continue
                source_raw = str(conn.get("source") or "").strip()
                target_raw = str(conn.get("target") or "").strip()
                if not source_raw or not target_raw:
                    continue
                source_name = component_name_by_id.get(source_raw, source_raw)
                target_name = component_name_by_id.get(target_raw, target_raw)
                if not source_name or not target_name or source_name == target_name:
                    continue
                if source_name.lower() not in new_names_set and target_name.lower() not in new_names_set:
                    continue
                sig = (source_name.lower(), target_name.lower(), str(conn.get("label") or "").strip().lower())
                if sig in seen_conn_sig:
                    continue
                seen_conn_sig.add(sig)
                validated_connections.append(
                    {
                        "source": source_name,
                        "target": target_name,
                        "label": str(conn.get("label") or ""),
                        "type": "service_integration",
                    }
                )

            drawio_xml, _, _ = _inject_nodes_and_edges_into_xml(
                xml_content=sanitized_xml,
                current_architecture=baseline_architecture,
                services_to_add=filtered_services_to_add,
                validated_connections=validated_connections,
            )
            preview_drawio_xml = _generate_highlighted_preview_xml(original_drawio_xml, drawio_xml)
            logger.info("Feature impact diagram update: modifier in-place injection path applied")
        else:
            logger.warning("Feature impact diagram update: baseline XML unavailable; using fallback diagram generation")
            requirements = _build_feature_impact_requirements_text(request)
            drawio_xml = await generate_drawio_from_architecture(architecture, requirements)
            preview_drawio_xml = _highlight_drawio_labels(drawio_xml, impacted_names, new_names)

        workspace_root = Path(__file__).resolve().parents[1]
        output_dir = workspace_root / "Arc-frontend" / "public" / "Architecture"
        output_dir.mkdir(parents=True, exist_ok=True)

        app_slug = _slugify_filename(request.application_name, "application")
        feature_slug = _slugify_filename(request.feature_name, "feature")
        filename = f"{app_slug}-{feature_slug}-proposed.drawio"
        file_path = output_dir / filename
        file_path.write_text(drawio_xml, encoding="utf-8")

        payload["proposedArchitectureDiagramPath"] = f"/Architecture/{filename}"
        payload["proposedArchitectureDiagramXml"] = drawio_xml
        if preview_drawio_xml:
            payload["proposedArchitectureDiagramPreviewXml"] = preview_drawio_xml
    except Exception as exc:
        logger.warning(f"Failed to generate proposed drawio for feature impact: {exc}")

    return payload

class InteractionResponse(BaseModel):
    """User response to an agent interaction request."""
    decision: str = Field(..., description="User decision: 'approve', 'reject', 'modify'")
    feedback: Optional[str] = Field(None, description="Optional user feedback or modification instructions")
    selected_items: Optional[List[str]] = Field(None, description="Optional list of selected recommendation IDs")

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

app = FastAPI(
    title="Architecture Diagram Generator API",
    description="AI-powered Azure architecture diagram generation and validation API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


@app.on_event("startup")
async def startup_event():
    """Build expensive indexes once at startup instead of per-agent."""
    from shared_services import ensure_docs_index
    ensure_docs_index()
    logger.info("Startup complete: docs index built, shared services ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    agent_progress_store.clear()


async def run_drawio_generation_background(session_id: str, request: GenerateRequest):
    """Background task for Draw.io generation with human-in-the-loop support."""
    agent_progress_store[session_id]["status"] = "running"
    agent_progress_store[session_id]["agent_logs"] = []
    
    # Track completed agent results for interaction summaries
    completed_agents_data = {}
    
    def progress_callback(agent_name: str, status: str, percentage: int, output_summary: dict = None):
        logger.info(f"Progress update: {agent_name} is {status} ({percentage}%)")
        if output_summary and output_summary.get("message"):
            logger.info(f"  Message: {output_summary.get('message')}")
        
        agent_progress_store[session_id]["current_agent"] = agent_name
        if status != "completed":
            agent_progress_store[session_id]["status"] = status
        agent_progress_store[session_id]["progress_percentage"] = percentage
        
        # Track completed agent data for interaction summaries
        if status == "completed" and output_summary:
            completed_agents_data[agent_name] = output_summary
        
        # Handle real-time thinking updates (percentage=-1 signals a thought update)
        if percentage == -1 and status == "thinking" and output_summary:
            # Append thought to a dedicated live_thoughts array for the UI
            thought_entry = {
                "agent": agent_name,
                "type": output_summary.get("thought_type", "reasoning"),
                "content": output_summary.get("thought", ""),
                "emoji": output_summary.get("emoji", "🧠"),
                "agent_emoji": output_summary.get("agent_emoji", "🤖"),
                "agent_persona": output_summary.get("agent_persona", ""),
                "timestamp": datetime.now().isoformat(),
            }
            if "live_thoughts" not in agent_progress_store[session_id]:
                agent_progress_store[session_id]["live_thoughts"] = []
            agent_progress_store[session_id]["live_thoughts"].append(thought_entry)
            # Keep only last 50 thoughts to avoid memory bloat
            if len(agent_progress_store[session_id]["live_thoughts"]) > 50:
                agent_progress_store[session_id]["live_thoughts"] = agent_progress_store[session_id]["live_thoughts"][-50:]
            return  # Don't update agent_logs for thinking updates
        
        log_entry = {
            "agent": agent_name,
            "status": status,
            "percentage": percentage,
            "timestamp": datetime.now().isoformat(),
            "output_summary": output_summary or {}
        }
        
        if status == "running":
            existing_idx = None
            for i, log in enumerate(agent_progress_store[session_id]["agent_logs"]):
                if log["agent"] == agent_name and log["status"] == "running":
                    existing_idx = i
                    break
            if existing_idx is not None:
                agent_progress_store[session_id]["agent_logs"][existing_idx] = log_entry
            else:
                agent_progress_store[session_id]["agent_logs"].append(log_entry)
        else:
            # For completed status, always append
            agent_progress_store[session_id]["agent_logs"].append(log_entry)

    async def interaction_callback(checkpoint: str, agent_name: str, summary: dict) -> dict:
        """
        Human-in-the-loop callback: pause workflow and wait for user decision.
        Sets an interaction request in the progress store and waits for user response.
        """
        if session_id not in agent_interaction_store:
            return {"decision": "approve"}  # Auto-approve if no interaction store
        
        interaction_request = {
            "checkpoint": checkpoint,
            "agent": agent_name,
            "title": summary.get("title", "Agent needs your input"),
            "description": summary.get("description", ""),
            "findings": summary.get("findings"),
            "architecture": summary.get("architecture"),
            "recommendations": summary.get("recommendations", []),
            "requested_at": datetime.now().isoformat(),
        }
        
        # Set the pending interaction
        agent_interaction_store[session_id]["pending"] = interaction_request
        agent_interaction_store[session_id]["response"] = None
        agent_interaction_store[session_id]["event"].clear()
        
        # Update progress store to show interaction is pending
        agent_progress_store[session_id]["interaction"] = interaction_request
        agent_progress_store[session_id]["status"] = "waiting_for_input"
        
        if progress_callback:
            progress_callback(agent_name, "waiting", agent_progress_store[session_id]["progress_percentage"], {
                "message": f"🤝 Waiting for your review and approval...",
                "interaction": True,
                "checkpoint": checkpoint,
            })
        
        logger.info(f"🤝 Interaction requested at checkpoint '{checkpoint}' for agent '{agent_name}'")
        
        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(
                agent_interaction_store[session_id]["event"].wait(),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Interaction timeout at checkpoint '{checkpoint}' - auto-approving")
            agent_progress_store[session_id]["interaction"] = None
            agent_progress_store[session_id]["status"] = "running"
            return {"decision": "approve", "feedback": None}
        
        # Get user response
        user_response = agent_interaction_store[session_id].get("response", {})
        agent_interaction_store[session_id]["pending"] = None
        agent_progress_store[session_id]["interaction"] = None
        agent_progress_store[session_id]["status"] = "running"
        
        logger.info(f"🤝 User responded: {user_response.get('decision', 'unknown')}")
        return user_response or {"decision": "approve"}

    try:
        # Use multi-agent workflow to generate comprehensive architecture
        workflow = MultiAgentWorkflowPipeline()
        
        workflow_result = await workflow.execute_workflow(
            user_prompt=request.requirements,
            project_name=request.project_name,
            include_connection_agent=True,
            progress_callback=progress_callback,
            interaction_callback=interaction_callback
        )
        
        agent_progress_store[session_id]["progress_percentage"] = 95
        agent_progress_store[session_id]["current_agent"] = "Finalizing"


        # The workflow already generates Draw.io XML
        drawio_xml = workflow_result.get("drawio_xml")
        drawio_filename = workflow_result.get("drawio_filename")
        
        if not drawio_xml:
            raise ValueError("Failed to generate Draw.io XML")

        # Generate Mermaid and Terraform from the architecture
        final_architecture = workflow_result.get("final_architecture", {})
        mermaid_diagram = None
        terraform_template = None
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            mermaid_diagram = azure_generator.generate_mermaid_diagram(final_architecture)
            logger.info("✅ Mermaid diagram generated")
        except Exception as e:
            logger.error(f"Mermaid generation failed: {e}")
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            terraform_template = azure_generator.generate_terraform_template(final_architecture)
            logger.info("✅ Terraform template generated")
        except Exception as e:
            logger.error(f"Terraform generation failed: {e}")

        result = {
            "status": "success",
            "drawio_xml": drawio_xml,
            "filename": drawio_filename,
            "final_architecture": final_architecture,
            "diagrams": {
                "drawio_xml": drawio_xml,
                "mermaid": mermaid_diagram,
                "terraform": terraform_template,
            },
            "processing_timeline": workflow_result.get("processing_timeline", []),
            "total_duration": workflow_result.get("total_duration", 0),
            "agents_executed": workflow_result.get("agents_executed", []),
            "timestamp": datetime.now().isoformat()
        }
        
        agent_progress_store[session_id]["status"] = "completed"
        agent_progress_store[session_id]["progress_percentage"] = 100
        agent_progress_store[session_id]["result"] = result

    except Exception as e:
        logger.error(f"Error generating Draw.io architecture in background: {str(e)}")
        agent_progress_store[session_id]["status"] = "error"
        agent_progress_store[session_id]["error"] = str(e)


async def run_feature_impact_background(session_id: str, request: FeatureImpactAnalyzeRequest):
    """Background task for feature impact analysis with live agent thinking."""
    agent_progress_store[session_id]["status"] = "running"
    agent_progress_store[session_id]["agent_logs"] = []

    def progress_callback(agent_name: str, status: str, percentage: int, output_summary: dict = None):
        agent_progress_store[session_id]["current_agent"] = agent_name
        if status != "completed":
            agent_progress_store[session_id]["status"] = status
        agent_progress_store[session_id]["progress_percentage"] = percentage

        if percentage == -1 and status == "thinking" and output_summary:
            thought_entry = {
                "agent": agent_name,
                "type": output_summary.get("thought_type", "reasoning"),
                "content": output_summary.get("thought", ""),
                "emoji": output_summary.get("emoji", "🧠"),
                "agent_emoji": output_summary.get("agent_emoji", "🤖"),
                "agent_persona": output_summary.get("agent_persona", ""),
                "timestamp": datetime.now().isoformat(),
            }
            if "live_thoughts" not in agent_progress_store[session_id]:
                agent_progress_store[session_id]["live_thoughts"] = []
            agent_progress_store[session_id]["live_thoughts"].append(thought_entry)
            if len(agent_progress_store[session_id]["live_thoughts"]) > 50:
                agent_progress_store[session_id]["live_thoughts"] = agent_progress_store[session_id]["live_thoughts"][-50:]
            return

        log_entry = {
            "agent": agent_name,
            "status": status,
            "percentage": percentage,
            "timestamp": datetime.now().isoformat(),
            "output_summary": output_summary or {},
        }

        if status == "running":
            existing_idx = None
            for i, log in enumerate(agent_progress_store[session_id]["agent_logs"]):
                if log["agent"] == agent_name and log["status"] == "running":
                    existing_idx = i
                    break
            if existing_idx is not None:
                agent_progress_store[session_id]["agent_logs"][existing_idx] = log_entry
            else:
                agent_progress_store[session_id]["agent_logs"].append(log_entry)
        else:
            agent_progress_store[session_id]["agent_logs"].append(log_entry)

    try:
        agent = FeatureImpactAnalyzerAgent()
        if hasattr(agent, "set_progress_callback"):
            agent.set_progress_callback(progress_callback)

        progress_callback("FeatureImpactAnalyzerAgent", "running", 10, {
            "message": "Analyzing feature impact with architecture context...",
        })

        requirements = _build_feature_impact_requirements_text(request)

        payload = await agent.analyze(
            requirements,
            context={"feature_request": request.dict()}
        )
        payload = await _generate_and_save_feature_impact_drawio(payload, request)

        summary = payload.get("impactSummary", {}) if isinstance(payload, dict) else {}
        progress_callback("FeatureImpactAnalyzerAgent", "completed", 95, {
            "message": "Feature impact analysis completed.",
            "impact_level": summary.get("impactLevel"),
            "impacted_components": summary.get("impactedComponentCount", 0),
            "new_components": summary.get("newComponentCount", 0),
            "thinking_summary": payload.get("thinking_summary") if isinstance(payload, dict) else None,
        })

        agent_progress_store[session_id]["status"] = "completed"
        agent_progress_store[session_id]["progress_percentage"] = 100
        agent_progress_store[session_id]["result"] = {
            "status": "success",
            "result": payload,
        }
    except Exception as e:
        logger.exception("Feature impact background workflow failed")
        agent_progress_store[session_id]["status"] = "error"
        agent_progress_store[session_id]["error"] = str(e)

 
  
@app.post("/api/analyze-architecture")
async def analyze_architecture(request: ArchitectureAnalysisRequest):
    """Analyze a specific set of services for architecture recommendations"""
    try:
        # Create architecture analysis object from services
        architecture = {
            "services": request.services,
            "architecture_pattern": request.architecture_pattern or "Custom",
            "requirements": request.requirements
        }
        
        # Get AI recommendations
        analyzer = AzureOpenAIAnalyzer()
        analysis = await analyzer.analyze_requirements_async(request.requirements)
        
        # Enhance with service-specific recommendations
        azure_generator = AzureIconDiagramGenerator()
        service_details = []
        
        for service in request.services:
            icon_info = {
                "name": service,
                "icon_source": azure_generator._determine_icon_source(service),
                "icon_url": azure_generator._get_service_icon_url(service),
                "category": azure_generator._get_service_category(service)
            }
            service_details.append(icon_info)
        
        return {
            "services": service_details,
            "analysis": analysis,
            "recommendations": {
                "security": "Implement Azure Security Center recommendations",
                "scalability": "Consider auto-scaling groups and load balancing",
                "cost_optimization": "Use Azure Cost Management tools",
                "monitoring": "Implement Azure Monitor and Application Insights"
            },
            "architecture_patterns": [
                "Microservices",
                "Event-driven",
                "Layered architecture", 
                "Clean architecture"
            ]
        }
    except Exception as e:
        logger.error(f"Architecture analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/feature-impact/analyze")
async def analyze_feature_impact(request: FeatureImpactAnalyzeRequest):
    """Analyze the impact of a new feature on an existing architecture."""
    try:
        agent = FeatureImpactAnalyzerAgent()
        payload = await agent.analyze(
            _build_feature_impact_requirements_text(request),
            context={"feature_request": request.dict()}
        )
        payload = await _generate_and_save_feature_impact_drawio(payload, request)
        return {
            "status": "success",
            "result": payload,
        }
    except Exception as e:
        logger.exception("Feature impact analysis failed")
        raise HTTPException(status_code=500, detail=f"Feature impact analysis failed: {str(e)}")


@app.post("/api/feature-impact/stream")
async def analyze_feature_impact_stream(request: FeatureImpactAnalyzeRequest, background_tasks: BackgroundTasks):
    """Start feature impact analysis as a background task and return session_id for progress polling."""
    if not request.application_name.strip() or not request.feature_name.strip() or not request.feature_description.strip():
        raise HTTPException(status_code=400, detail="application_name, feature_name and feature_description are required")

    session_id = f"impact_{uuid.uuid4().hex[:workflow_config.SESSION_ID_LENGTH]}_{int(time.time())}"

    agent_progress_store[session_id] = {
        "status": "queued",
        "current_agent": None,
        "progress_percentage": 0,
        "agent_logs": [],
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "requirements": request.feature_description[:200],
        "interaction": None,
        "live_thoughts": [],
    }

    background_tasks.add_task(run_feature_impact_background, session_id, request)

    return {
        "session_id": session_id,
        "status": "queued",
        "message": "Feature impact workflow started. Poll /api/progress/{session_id} for real-time updates.",
    }

@app.get("/api/recent-diagrams")
async def get_recent_diagrams(limit: int = Query(10, description="Number of recent diagrams to return")):
    """Get recently generated diagrams"""
    try:
        responses_dir = os.path.join(os.path.dirname(__file__), path_config.SAVED_DIAGRAMS_DIR, 'responses')
        
        if not os.path.exists(responses_dir):
            return {"diagrams": [], "total": 0}
        
        # Get all response files
        response_files = glob.glob(os.path.join(responses_dir, "response-*.json"))
        response_files.sort(key=os.path.getmtime, reverse=True)
        
        recent_diagrams = []
        for file_path in response_files[:limit]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)
                    
                recent_diagrams.append({
                    "id": os.path.basename(file_path).replace('response-', '').replace('.json', ''),
                    "timestamp": response_data.get("timestamp"),
                    "requirements": response_data.get("requirements", "")[:100] + "..." if len(response_data.get("requirements", "")) > 100 else response_data.get("requirements", ""),
                    "services_count": len(response_data.get("architecture", {}).get("services", [])),
                    "diagram_url": response_data.get("diagram_url"),
                    "file_path": file_path
                })
            except Exception as e:
                logger.error(f"Error reading diagram file {file_path}: {str(e)}")
                continue
        
        return {
            "diagrams": recent_diagrams,
            "total": len(recent_diagrams),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching recent diagrams: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch diagrams: {str(e)}")

@app.get("/api/diagram/{diagram_id}")
async def get_diagram_details(diagram_id: str):
    """Get detailed information about a specific diagram"""
    try:
        responses_dir = os.path.join(os.path.dirname(__file__), path_config.SAVED_DIAGRAMS_DIR, 'responses')
        response_file = os.path.join(responses_dir, f"response-{diagram_id}.json")
        
        if not os.path.exists(response_file):
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        with open(response_file, 'r', encoding='utf-8') as f:
            diagram_data = json.load(f)
        
        return diagram_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Diagram not found")
    except Exception as e:
        logger.error(f"Error fetching diagram {diagram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch diagram: {str(e)}")

@app.delete("/api/diagram/{diagram_id}")
async def delete_diagram(diagram_id: str):
    
    try:
        base_dir = os.path.dirname(__file__)
        
        # Files to delete
        files_to_delete = [
            os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses', f"response-{diagram_id}.json"),
            os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', f"drawio-{diagram_id}.drawio"),
            os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', f"drawio-{diagram_id}.xml"),  # legacy
            os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', f"mermaid-{diagram_id}.mmd"),
            os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', f"terraform-{diagram_id}.tf"),
            os.path.join(base_dir, path_config.FRONTEND_DIAGRAMS_DIR, f"generated-{diagram_id}.png")
        ]
        
        deleted_files = []
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(os.path.basename(file_path))
        
        if not deleted_files:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        return {
            "message": f"Diagram {diagram_id} deleted successfully",
            "deleted_files": deleted_files
        }
    except Exception as e:
        logger.error(f"Error deleting diagram {diagram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete diagram: {str(e)}")

 
@app.get("/api/agents/status")
async def get_agents_status():
    orchestrator = AgentOrchestrator()
    return {
        "agents": [{
            "name": agent.name,
            "status": agent.status,
            "specialization": agent.__class__.__name__.replace("Agent", "")
        } for agent in orchestrator.agents]
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config.get_cors_origins(),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=("*" not in api_config.get_cors_origins()),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health and Status endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Architecture Diagram Generator API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "health": "/api/health"
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if essential services are available
        azure_generator = AzureIconDiagramGenerator()
        orchestrator = AgentOrchestrator()
        
        services_status = {
            "azure_generator": "healthy",
            "agent_orchestrator": "healthy", 
            "ai_validator": "healthy",
            "langgraph": "available" if LANGGRAPH_AVAILABLE else "not_installed"
        }
        
        # Test Azure OpenAI connection
        try:
            analyzer = AzureOpenAIAnalyzer()
            services_status["azure_openai"] = "healthy"
        except Exception as e:
            services_status["azure_openai"] = f"unhealthy: {str(e)}"
        
        # Test LangGraph if available
        if LANGGRAPH_AVAILABLE:
            try:
                workflow = get_langgraph_workflow()
                services_status["langgraph"] = "healthy" if workflow else "available_but_not_initialized"
            except Exception as e:
                services_status["langgraph"] = f"error: {str(e)}"
            
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version="1.0.0",
            services=services_status
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            services={"error": str(e)}
        )


@app.post("/api/multi-agent-workflow")
async def multi_agent_workflow_architecture(request: GenerateRequest):
    """
    Multi-Agent Workflow Pipeline for comprehensive Azure architecture design.
    Same flow as /api/generate but returns additional workflow metadata.
    
    Pipeline: SecurityAgent → PerformanceAgent → ArchitectureAgent → CostAgent
    → Compile Architecture → Generate Draw.io XML
    """
    try:
        if not request.requirements or not isinstance(request.requirements, str) or not request.requirements.strip():
            raise HTTPException(status_code=400, detail="Multi-agent workflow requires detailed requirements (minimum 10 characters)")
        
        if len(request.requirements.strip()) < 30:
            raise HTTPException(
                status_code=400, 
                detail="Multi-agent workflow needs detailed requirements.\n\nInclude:\n• Application type and business domain\n• Specific Azure services or patterns\n• Security, performance, and cost considerations\n• Scale and geographic requirements"
            )
        
        logger.info("🚀 Starting Multi-Agent Workflow Pipeline...")
        
        # Execute multi-agent workflow
        workflow_pipeline = MultiAgentWorkflowPipeline()
        
        try:
            workflow_results = await workflow_pipeline.execute_workflow(
                user_prompt=request.requirements,
                project_name=request.project_name,
                include_connection_agent=True
            )
            
            if workflow_results.get("workflow_status") == "failed":
                raise Exception(workflow_results.get("error", "Workflow failed"))
                
        except Exception as e:
            logger.error(f"❌ Multi-agent workflow failed: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Unable to generate architecture from requirements. Please provide more specific details.\n\n• Specify Azure services\n• Mention architectural patterns\n• Include non-functional requirements"
            )
        
        # Extract results
        architecture = workflow_results.get("final_architecture", {})
        drawio_xml = workflow_results.get("drawio_xml", "")
        
        # Save files
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        xml_dir = path_config.SAVED_XML_DIR
        responses_dir = path_config.SAVED_RESPONSES_DIR
        os.makedirs(xml_dir, exist_ok=True)
        os.makedirs(responses_dir, exist_ok=True)
        
        saved_files = {}
        
        drawio_filename = f"multi-agent-drawio-{timestamp}.drawio"
        drawio_path = os.path.join(xml_dir, drawio_filename)
        with open(drawio_path, 'w', encoding='utf-8') as f:
            f.write(drawio_xml)
        saved_files["drawio_path"] = drawio_path
        
        # Generate additional formats
        mermaid_diagram = None
        terraform_template = None
        
        if request.include_mermaid:
            try:
                azure_generator = AzureIconDiagramGenerator()
                mermaid_diagram = azure_generator.generate_mermaid_diagram(architecture)
            except Exception as e:
                logger.error(f"Mermaid generation failed: {e}")
        
        if request.include_terraform:
            try:
                azure_generator = AzureIconDiagramGenerator()
                terraform_template = azure_generator.generate_terraform_template(architecture)
            except Exception as e:
                logger.error(f"Terraform generation failed: {e}")
        
        # Build response
        response = {
            "architecture": architecture,
            "workflow_results": workflow_results,
            "multi_agent_features": {
                "component_extraction": "ComponentExtractionAgent" in workflow_results.get("agents_executed", []),
                "azure_reference_mapping": "AzureArchitectureReferenceAgent" in workflow_results.get("agents_executed", []),
                "security_analysis": "SecurityAgent" in workflow_results.get("agents_executed", []),
                "performance_optimization": "PerformanceAgent" in workflow_results.get("agents_executed", []),
                "architecture_design": "ArchitectureAgent" in workflow_results.get("agents_executed", []),
                "cost_optimization": "CostOptimizationAgent" in workflow_results.get("agents_executed", []),
                "requirements_validation": "RequirementsValidationAgent" in workflow_results.get("agents_executed", []),
            },
            "agents_insights": {
                "component_extraction": architecture.get("component_extraction", {}),
                "azure_references": architecture.get("azure_references", {}),
                "security_insights": architecture.get("security_insights", {}),
                "performance_insights": architecture.get("performance_insights", {}),
                "architecture_insights": architecture.get("architecture_insights", {}),
                "cost_insights": architecture.get("cost_insights", {}),
                "validation": architecture.get("validation", {}),
            },
            "workflow_timeline": workflow_results.get("processing_timeline", []),
            "agents_executed": workflow_results.get("agents_executed", []),
            "total_processing_time": workflow_results.get("total_duration", 0),
            "diagrams": {
                "drawio_xml": drawio_xml,
                "mermaid": mermaid_diagram,
                "terraform": terraform_template,
            },
            "saved_files": saved_files,
            "timestamp": timestamp,
            "requirements": request.requirements,
            "project_name": request.project_name,
            "environment": request.environment,
            "agent_type": "multi_agent_workflow",
            "workflow_status": workflow_results.get("workflow_status", "unknown")
        }
        
        # Save response
        response_filename = f"multi-agent-response-{timestamp}.json"
        response_path = os.path.join(responses_dir, response_filename)
        with open(response_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        
        logger.info(f"🎉 Multi-Agent Workflow completed! {len(architecture.get('services', []))} services")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"❌ Multi-agent workflow error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Multi-agent workflow failed: {str(e)}")



@app.post("/api/generate")
async def generate_diagram(request: GenerateRequest):
    """
    Generate Azure architecture diagram using Multi-Agent AI pipeline.
    
    Flow: Requirements → SecurityAgent → PerformanceAgent → ArchitectureAgent → CostAgent
          → Compile Architecture → Generate Draw.io XML (algorithmic layout)
          
    When use_langgraph=True (default): Uses LangGraph for improved accuracy with:
    - Structured state management
    - Conditional routing based on quality
    - Retry logic for low-quality outputs
    - Checkpointing support
    """
    try:
        if not request.requirements or not isinstance(request.requirements, str) or not request.requirements.strip():
            raise HTTPException(status_code=400, detail="Valid requirements text is required (minimum 10 characters)")
        
        # Determine workflow mode
        use_langgraph = request.use_langgraph and LANGGRAPH_AVAILABLE
        workflow_mode = "LangGraph" if use_langgraph else "Standard"
        
        logger.info(f"🚀 Starting architecture generation ({workflow_mode} mode) for: {request.requirements[:100]}...")
        
        # ── Step 1: Run Multi-Agent Workflow ──────────────────────────────
        try:
            if use_langgraph:
                # Use LangGraph workflow for improved accuracy
                logger.info("🧠 Using LangGraph workflow with structured state and quality validation")
                workflow_results = await run_langgraph_workflow(
                    requirements=request.requirements,
                    project_name=request.project_name,
                    include_connection_agent=True
                )
            else:
                # Fall back to standard workflow
                workflow_pipeline = MultiAgentWorkflowPipeline()
                workflow_results = await workflow_pipeline.execute_workflow(
                    user_prompt=request.requirements,
                    project_name=request.project_name,
                    include_connection_agent=True
                )
            
            if workflow_results.get("workflow_status") in ["failed", "error"]:
                raise Exception(workflow_results.get("error_message", workflow_results.get("error", "Workflow failed")))
            
            architecture = workflow_results.get("final_architecture", workflow_results.get("combined_architecture", {}))
            drawio_xml = workflow_results.get("drawio_xml", "")
            
            # If no drawio_xml yet, generate it from architecture
            if not drawio_xml and architecture.get("services"):
                drawio_xml = generate_drawio_from_architecture(architecture)
            
            if not architecture.get("services"):
                raise Exception("No services detected in architecture")
            
            quality_score = workflow_results.get("overall_quality_score", 0)
            logger.info(f"✅ Workflow completed ({workflow_mode}): {len(architecture.get('services', []))} services, {len(architecture.get('connections', []))} connections")
            if use_langgraph:
                logger.info(f"   Quality Score: {quality_score:.0%}")
            
        except Exception as e:
            logger.error(f"❌ Multi-agent workflow failed: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Unable to generate architecture. Please provide more specific requirements.\n\nTips:\n• Name specific Azure services\n• Describe the application type\n• Include scale and security requirements"
            )
        
        # ── Step 2: Save files ────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        xml_dir = path_config.SAVED_XML_DIR
        responses_dir = path_config.SAVED_RESPONSES_DIR
        os.makedirs(xml_dir, exist_ok=True)
        os.makedirs(responses_dir, exist_ok=True)
        
        saved_files = {}
        
        # Save Draw.io file
        drawio_filename = f"multi-agent-drawio-{timestamp}.drawio"
        drawio_path = os.path.join(xml_dir, drawio_filename)
        with open(drawio_path, 'w', encoding='utf-8') as f:
            f.write(drawio_xml)
        saved_files["drawio_path"] = drawio_path
        
        # ── Step 3: Generate additional formats if requested ──────────────
        mermaid_diagram = None
        terraform_template = None
        
        if request.include_mermaid:
            try:
                azure_generator = AzureIconDiagramGenerator()
                mermaid_diagram = azure_generator.generate_mermaid_diagram(architecture)
            except Exception as e:
                logger.error(f"Mermaid generation failed: {e}")
        
        if request.include_terraform:
            try:
                azure_generator = AzureIconDiagramGenerator()
                terraform_template = azure_generator.generate_terraform_template(architecture)
            except Exception as e:
                logger.error(f"Terraform generation failed: {e}")
        
        # Save additional formats
        if mermaid_diagram:
            mermaid_path = os.path.join(xml_dir, f"multi-agent-mermaid-{timestamp}.mmd")
            with open(mermaid_path, 'w', encoding='utf-8') as f:
                f.write(mermaid_diagram)
            saved_files["mermaid_path"] = mermaid_path
        
        if terraform_template:
            terraform_path = os.path.join(xml_dir, f"multi-agent-terraform-{timestamp}.tf")
            with open(terraform_path, 'w', encoding='utf-8') as f:
                f.write(terraform_template)
            saved_files["terraform_path"] = terraform_path
        
        # ── Step 4: AI validation ────────────────────────────────────────
        validation_result = None
        try:
            ai_validator = AIArchitectureValidator()
            validation_result = await ai_validator.generate_validation_report(
                drawio_xml, "", request.requirements
            )
        except Exception as e:
            logger.error(f"Validation failed: {e}")
        
        # ── Step 5: Build response ───────────────────────────────────────
        response = {
            "architecture": architecture,
            "diagrams": {
                "drawio_xml": drawio_xml,
                "mermaid": mermaid_diagram,
                "terraform": terraform_template,
            },
            "validation": validation_result,
            "workflow_insights": {
                "agents_executed": workflow_results.get("agents_executed", []),
                "processing_timeline": workflow_results.get("processing_timeline", []),
                "total_processing_time": workflow_results.get("total_duration", 0),
                "workflow_status": workflow_results.get("workflow_status", "unknown"),
                "langgraph_mode": use_langgraph,
                "quality_score": workflow_results.get("overall_quality_score", None) if use_langgraph else None
            },
            "multi_agent_features": {
                "security_analysis": "SecurityAgent" in workflow_results.get("agents_executed", []),
                "performance_optimization": "PerformanceAgent" in workflow_results.get("agents_executed", []),
                "architecture_design": "ArchitectureAgent" in workflow_results.get("agents_executed", []),
                "cost_optimization": "CostOptimizationAgent" in workflow_results.get("agents_executed", []),
                "langgraph_enabled": use_langgraph,
            },
            "service_detection": {
                "total_services": len(architecture.get("services", [])),
                "services": architecture.get("all_services", [])
            },
            "saved_files": saved_files,
            "timestamp": timestamp,
            "requirements": request.requirements,
            "project_name": request.project_name,
            "environment": request.environment,
            "generation_method": "langgraph_multi_agent" if use_langgraph else "multi_agent_drawio",
        }
        
        # Save response JSON
        response_filename = f"multi-agent-response-{timestamp}.json"
        response_path = os.path.join(responses_dir, response_filename)
        with open(response_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        
        logger.info(f"🎉 Generation complete! {len(architecture.get('services', []))} services, saved to {drawio_path}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error generating diagram: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {str(e)}")

@app.post("/api/reverse-engineer")
async def reverse_engineer(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(400, "Only ZIP files are supported")
    
    content = await file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
            terraform_files = [f for f in zip_file.namelist() if f.endswith('.tf')]
    except:
        raise HTTPException(400, "Invalid ZIP file")
    
    # Generate dynamic analysis based on terraform files
    ai_validator = AIArchitectureValidator()
    analysis_result = await ai_validator._analyze_terraform_files(
        terraform_files, content
    )
    
    return {
        "diagram_url": "/diagrams/azure-architecture-eastus.png",
        "terraform_files": terraform_files,
        "analysis": analysis_result.get("analysis", {
            "implemented": ["Microservices Architecture", "API Gateway Pattern", "Layered Architecture"],
            "missing": ["Security", "High Availability", "Performance Optimization"]
        })
    }

@app.post("/api/parse-diagram")
async def parse_diagram_xml(drawio_xml: str = Form(...)):
    """
    📊 Parse DrawIO XML and extract architecture information
    - Extracts all Azure services and components
    - Analyzes connections and relationships
    - Categorizes services by type
    - Provides architecture insights and patterns
    """
    try:
        logger.info("🔍 Starting DrawIO XML parsing...")
        
        from drawio_parser import DrawioParser
        parser = DrawioParser()
        
        # Parse the DrawIO XML
        parsed_data = parser.parse_drawio_file(drawio_xml)
        
        logger.info(f"✅ Parsing completed: {parsed_data['total_components']} components found")
        
        return {
            "status": "success",
            "diagram_info": {
                "name": parsed_data["diagram_name"],
                "total_components": parsed_data["total_components"],
                "total_connections": parsed_data["total_connections"],
                "total_containers": parsed_data["total_containers"]
            },
            "azure_services": parsed_data["azure_services"],
            "components": parsed_data["components"],
            "connections": parsed_data["connections"],
            "containers": parsed_data["containers"],
            "architecture_insights": parsed_data["architecture_insights"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ DrawIO parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to parse diagram: {str(e)}")

@app.post("/api/generate-terraform-from-drawio")
async def generate_terraform_from_drawio(drawio_xml: str = Form(...)):
    """
    🏗️ Generate Terraform from Draw.io Diagram
    - Parses Draw.io XML to extract Azure services
    - Generates production-ready Terraform templates
    - Includes all detected services with best practice configurations
    """
    try:
        logger.info("🏗️ Starting Terraform generation from Draw.io diagram...")
        
        # Parse the Draw.io XML to extract services
        from drawio_parser import DrawioParser
        parser = DrawioParser()
        parsed_data = parser.parse_drawio_file(drawio_xml)
        
        # Extract services from parsed data
        azure_services = parsed_data.get("azure_services", [])
        services = [s.get("service_name", s.get("name", "")) for s in azure_services if isinstance(s, dict)]
        if not services:
            services = [s for s in azure_services if isinstance(s, str)]
        
        logger.info(f"📋 Found {len(services)} Azure services to generate Terraform for")
        
        # Build architecture dict for Terraform generator
        architecture = {
            "services": services,
            "project_name": parsed_data.get("diagram_name", "architecture"),
            "connections": parsed_data.get("connections", []),
            "environment": "production"
        }
        
        # Generate Terraform using existing generator
        azure_generator = AzureIconDiagramGenerator()
        terraform_template = azure_generator.generate_terraform_template(architecture)
        
        # Save the Terraform file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        terraform_dir = path_config.SAVED_TERRAFORM_DIR
        os.makedirs(terraform_dir, exist_ok=True)
        
        terraform_filename = f"terraform-from-drawio-{timestamp}.tf"
        terraform_path = os.path.join(terraform_dir, terraform_filename)
        with open(terraform_path, 'w', encoding='utf-8') as f:
            f.write(terraform_template)
        
        logger.info(f"✅ Terraform generated: {terraform_path}")
        
        return {
            "status": "success",
            "terraform": terraform_template,
            "services_detected": services,
            "service_count": len(services),
            "saved_path": terraform_path,
            "timestamp": timestamp,
            "diagram_name": parsed_data.get("diagram_name", "Untitled")
        }
        
    except Exception as e:
        logger.error(f"❌ Terraform generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Terraform: {str(e)}")


@app.post("/api/validate")
async def validate_architecture(request: ValidationRequest):
    """
    ✅ Comprehensive Architecture Validation with Multi-Component Analysis
    - 🤖 Multi-Agent Workflow validation (Security → Performance → Architecture → Cost)
    - 🎨 Professional diagram style validation
    - 🧠 Intelligent design pattern validation
    - 📊 Architecture compliance scoring
    - 🔍 Best practices analysis
    """
    try:
        # Create unique validation ID for tracking
        validation_id = f"validation_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        logger.info(f"🔍 Starting comprehensive architecture validation - ID: {validation_id}")
        logger.info(f"📋 Validation request:")
        logger.info(f"  - Requirements length: {len(request.requirements)} characters")
        logger.info(f"  - Has actual diagram: {bool(request.actual_diagram)}")
        logger.info(f"  - Has expected diagram: {bool(request.expected_diagram)}")
        logger.info(f"  - Validation type: {request.validation_type}")
        
        # Initialize validation components
        logger.info("🔧 Initializing validation components...")
        ai_validator = AIArchitectureValidator()
        azure_generator = AzureIconDiagramGenerator()
        orchestrator = AgentOrchestrator()
        
        start_time = time.time()
        
        # Step 1: Initial Requirements Analysis
        logger.info("📊 Step 1: Analyzing requirements and detecting services...")
        try:
            if not request.requirements or not request.requirements.strip():
                logger.warning("⚠️ No requirements provided, using default validation")
                request.requirements = "General Azure architecture validation"
            
            # Detect services from requirements
            detected_services = azure_generator.detect_services_from_prompt(request.requirements)
            logger.info(f"🔍 Detected {len(detected_services)} services from requirements")
            for service in detected_services[:5]:  # Log first 5
                logger.info(f"   - {service.get('name', 'Unknown')} (confidence: {service.get('confidence', 0):.2f})")
            
            # Get AI analysis of requirements
            analyzer = AzureOpenAIAnalyzer()
            requirements_analysis = await analyzer.analyze_requirements_async(request.requirements)
            logger.info("✅ Requirements analysis completed")
            
        except Exception as e:
            logger.error(f"❌ Requirements analysis failed: {str(e)}")
            detected_services = []
            requirements_analysis = {
                "services": ["Azure App Service", "Azure SQL Database"],
                "architecture_pattern": "Standard Web Application",
                "recommendations": [f"Requirements analysis failed: {str(e)}"]
            }
        
        # Step 2: Multi-Agent Validation Pipeline
        logger.info("🤖 Step 2: Running Multi-Agent validation pipeline...")
        agent_results = {}
        
        try:
            # Security Agent Validation
            logger.info("🛡️  Running Security Agent validation...")
            security_start = time.time()
            security_result = await orchestrator.run_security_validation(
                request.requirements, request.actual_diagram
            )
            security_duration = time.time() - security_start
            agent_results["security"] = security_result
            logger.info(f"✅ Security validation completed in {security_duration:.2f}s")
            logger.info(f"   - Security score: {security_result.get('security_score', 0)}%")
            logger.info(f"   - Critical issues: {len(security_result.get('critical_issues', []))}")
            
            # Performance Agent Validation  
            logger.info("⚡ Running Performance Agent validation...")
            perf_start = time.time()
            performance_result = await orchestrator.run_performance_validation(
                request.requirements, request.actual_diagram
            )
            perf_duration = time.time() - perf_start
            agent_results["performance"] = performance_result
            logger.info(f"✅ Performance validation completed in {perf_duration:.2f}s")
            logger.info(f"   - Performance score: {performance_result.get('performance_score', 0)}%")
            logger.info(f"   - Optimization opportunities: {len(performance_result.get('optimizations', []))}")
            
            # Architecture Agent Validation
            logger.info("🏗️ Running Architecture Agent validation...")
            arch_start = time.time()
            architecture_result = await orchestrator.run_architecture_validation(
                request.requirements, request.actual_diagram
            )
            arch_duration = time.time() - arch_start
            agent_results["architecture"] = architecture_result
            logger.info(f"✅ Architecture validation completed in {arch_duration:.2f}s")
            logger.info(f"   - Architecture score: {architecture_result.get('architecture_score', 0)}%")
            logger.info(f"   - Pattern compliance: {architecture_result.get('pattern_compliance', 'N/A')}")
            
            # Cost Optimization Agent (Optional)
            if request.validation_type == "full":
                logger.info("💰 Running Cost Optimization validation...")
                cost_start = time.time()
                cost_result = await orchestrator.run_cost_validation(
                    request.requirements, request.actual_diagram
                )
                cost_duration = time.time() - cost_start
                agent_results["cost"] = cost_result
                logger.info(f"✅ Cost validation completed in {cost_duration:.2f}s")
                logger.info(f"   - Cost score: {cost_result.get('cost_score', 0)}%")
                logger.info(f"   - Savings opportunities: {len(cost_result.get('savings_opportunities', []))}")
            
        except Exception as e:
            logger.error(f"❌ Multi-agent validation failed: {str(e)}")
            agent_results = {
                "error": str(e),
                "fallback": True
            }
        
        # Step 3: AI-Powered Diagram Comparison (if diagrams provided)
        logger.info("🧠 Step 3: AI-powered diagram analysis...")
        ai_comparison_result = {}
        
        try:
            if request.actual_diagram or request.expected_diagram:
                logger.info("🔍 Analyzing provided diagrams with AI...")
                ai_comparison_result = await ai_validator.compare_diagrams_with_ai(
                    actual_diagram=request.actual_diagram,
                    expected_diagram=request.expected_diagram,
                    requirements=request.requirements
                )
                logger.info("✅ AI diagram comparison completed")
                logger.info(f"   - Overall score: {ai_comparison_result.get('overall_score', 0)}%")
                logger.info(f"   - Strengths found: {len(ai_comparison_result.get('strengths', []))}")
                logger.info(f"   - Gaps identified: {len(ai_comparison_result.get('gaps', []))}")
            else:
                logger.info("📝 No diagrams provided, performing text-based validation...")
                ai_comparison_result = await ai_validator.validate_requirements_only(
                    request.requirements
                )
                logger.info("✅ Text-based validation completed")
                
        except Exception as e:
            logger.error(f"❌ AI diagram analysis failed: {str(e)}")
            ai_comparison_result = {
                "error": f"AI comparison failed: {str(e)}",
                "overall_score": 0,
                "insights": "AI analysis unavailable"
            }
        
        # Step 4: Calculate comprehensive compliance score
        logger.info("📊 Step 4: Calculating comprehensive compliance score...")
        
        try:
            scores = []
            if "security" in agent_results and "security_score" in agent_results["security"]:
                scores.append(agent_results["security"]["security_score"])
            if "performance" in agent_results and "performance_score" in agent_results["performance"]:
                scores.append(agent_results["performance"]["performance_score"])
            if "architecture" in agent_results and "architecture_score" in agent_results["architecture"]:
                scores.append(agent_results["architecture"]["architecture_score"])
            if "cost" in agent_results and "cost_score" in agent_results["cost"]:
                scores.append(agent_results["cost"]["cost_score"])
            if ai_comparison_result.get("overall_score"):
                scores.append(ai_comparison_result["overall_score"])
            
            if scores:
                overall_compliance_score = sum(scores) / len(scores)
            else:
                overall_compliance_score = agent_config.FALLBACK_AVERAGE_SCORE  # Default score if no valid scores
                
            logger.info(f"✅ Compliance score calculated: {overall_compliance_score:.1f}%")
            logger.info(f"   - Based on {len(scores)} validation components")
            
        except Exception as e:
            logger.error(f"❌ Score calculation failed: {str(e)}")
            overall_compliance_score = 0
        
        # Step 5: Aggregate critical issues and quick wins
        logger.info("🔧 Step 5: Aggregating issues and recommendations...")
        
        critical_issues = []
        quick_wins = []
        recommendations = {"critical": [], "high": [], "medium": []}
        
        try:
            # Collect from all agent results
            for agent_name, agent_result in agent_results.items():
                if isinstance(agent_result, dict):
                    # Critical issues
                    if "critical_issues" in agent_result:
                        for issue in agent_result["critical_issues"][:3]:  # Limit to top 3 per agent
                            critical_issues.append({
                                "agent": agent_name,
                                "issue": issue,
                                "severity": "critical"
                            })
                    
                    # Quick wins
                    if "quick_wins" in agent_result:
                        for win in agent_result["quick_wins"][:3]:  # Limit to top 3 per agent
                            quick_wins.append({
                                "agent": agent_name,
                                "improvement": win,
                                "impact": "quick_win"
                            })
                    
                    # Recommendations
                    if "recommendations" in agent_result:
                        for rec in agent_result["recommendations"][:2]:  # Limit per agent
                            recommendations["high"].append({
                                "agent": agent_name,
                                "title": f"{agent_name.title()} Recommendation",
                                "description": rec,
                                "priority": "high"
                            })
            
            # Add AI comparison insights
            if ai_comparison_result.get("gaps"):
                for gap in ai_comparison_result["gaps"][:3]:
                    critical_issues.append({
                        "agent": "ai_analysis",
                        "issue": gap,
                        "severity": "critical"
                    })
            
            if ai_comparison_result.get("strengths"):
                for strength in ai_comparison_result["strengths"][:2]:
                    quick_wins.append({
                        "agent": "ai_analysis", 
                        "improvement": f"Leverage: {strength}",
                        "impact": "positive"
                    })
            
            logger.info(f"✅ Issues aggregated:")
            logger.info(f"   - Critical issues: {len(critical_issues)}")
            logger.info(f"   - Quick wins: {len(quick_wins)}")
            logger.info(f"   - Recommendations: {len(recommendations['critical']) + len(recommendations['high']) + len(recommendations['medium'])}")
            
        except Exception as e:
            logger.error(f"❌ Issue aggregation failed: {str(e)}")
            critical_issues = [{"issue": f"Aggregation error: {str(e)}", "severity": "critical"}]
            quick_wins = []
        
        # Step 6: Prepare comprehensive validation response
        total_duration = time.time() - start_time
        logger.info(f"⏱️ Total validation time: {total_duration:.2f} seconds")
        
        validation_response = {
            "validation_id": validation_id,
            "validation_score": round(overall_compliance_score, 1),
            "compliance_score": round(overall_compliance_score, 1),
            "critical_issues": critical_issues,
            "quick_wins": quick_wins,
            "ai_comparison": ai_comparison_result,
            "agent_recommendations": {
                "agents_results": [
                    {"agent": agent, "results": result} for agent, result in agent_results.items()
                ],
                "summary": {
                    "total_agents": len(agent_results),
                    "agents_completed": len([r for r in agent_results.values() if not isinstance(r, dict) or "error" not in r]),
                    "critical_issues_found": len(critical_issues),
                    "recommendations_generated": sum(len(recs) for recs in recommendations.values())
                }
            },
            "recommendations": recommendations,
            "validation_type": request.validation_type,
            "architecture_complexity": "standard" if overall_compliance_score >= validation_config.SCORE_THRESHOLD_GOOD else "needs_improvement",
            "processing_details": {
                "total_duration": round(total_duration, 2),
                "components_executed": list(agent_results.keys()),
                "services_detected": len(detected_services),
                "validation_timestamp": datetime.now().isoformat()
            },
            "status": {
                "overall": "completed",
                "ai_analysis": "completed" if not ai_comparison_result.get("error") else "failed",
                "multi_agent": "completed" if not agent_results.get("error") else "failed",
                "requirements_analysis": "completed"
            }
        }
        
        logger.info("🎉 Comprehensive validation completed successfully!")
        logger.info(f"📋 Validation Summary:")
        logger.info(f"   - Overall Score: {validation_response['compliance_score']}%")
        logger.info(f"   - Critical Issues: {len(validation_response['critical_issues'])}")
        logger.info(f"   - Quick Wins: {len(validation_response['quick_wins'])}")
        logger.info(f"   - Total Duration: {validation_response['processing_details']['total_duration']}s")
        logger.info(f"   - Validation ID: {validation_id}")
        
        return validation_response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ Comprehensive validation error: {str(e)}")
        logger.error(f"Full traceback: {error_details}")
        
        # Return structured error response for frontend
        return {
            "validation_id": f"error_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "error": True,
            "message": f"Validation failed: {str(e)}",
            "validation_score": 0,
            "compliance_score": 0,
            "critical_issues": [{"issue": f"Validation system error: {str(e)}", "severity": "critical"}],
            "quick_wins": [{"improvement": "Check system logs and restart validation service", "impact": "system"}],
            "ai_comparison": {"error": str(e)},
            "agent_recommendations": {"agents_results": [], "summary": {"total_agents": 0}},
            "recommendations": {"critical": [], "high": [], "medium": []},
            "validation_type": request.validation_type,
            "status": {
                "overall": "failed",
                "error_details": str(e)
            }
        }


@app.post("/api/validate/image")
async def validate_architecture_from_image(
    actual_diagram: UploadFile = File(..., description="Actual architecture diagram image (PNG, JPG, JPEG, WEBP)"),
    expected_diagram: Optional[UploadFile] = File(None, description="Optional expected architecture diagram image"),
    requirements: str = Form("", description="Architecture requirements text")
):
    """
    Validate architecture diagram from uploaded image files (PNG, JPG, etc.)
    
    - Accepts actual_diagram: Required image file of the architecture diagram
    - Accepts expected_diagram: Optional image file to compare against
    - Accepts requirements: Text description of architecture requirements
    
    Returns comprehensive AI-powered validation with scores and recommendations.
    """
    try:
        validation_id = f"img_validation_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        logger.info(f"🖼️ Starting image-based architecture validation - ID: {validation_id}")
        
        # Validate file types
        allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
        
        if actual_diagram.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type for actual_diagram. Allowed types: PNG, JPG, JPEG, WEBP. Got: {actual_diagram.content_type}"
            )
        
        if expected_diagram and expected_diagram.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for expected_diagram. Allowed types: PNG, JPG, JPEG, WEBP. Got: {expected_diagram.content_type}"
            )
        
        # Read and encode actual diagram
        logger.info(f"📤 Reading actual diagram: {actual_diagram.filename} ({actual_diagram.content_type})")
        actual_content = await actual_diagram.read()
        actual_b64 = base64.b64encode(actual_content).decode("utf-8")
        actual_content_type = actual_diagram.content_type
        
        # Read and encode expected diagram if provided
        expected_b64 = None
        expected_content_type = None
        if expected_diagram:
            logger.info(f"📤 Reading expected diagram: {expected_diagram.filename} ({expected_diagram.content_type})")
            expected_content = await expected_diagram.read()
            expected_b64 = base64.b64encode(expected_content).decode("utf-8")
            expected_content_type = expected_diagram.content_type
        
        # Use default requirements if not provided
        if not requirements or not requirements.strip():
            requirements = "General Azure architecture validation"
        
        logger.info(f"📝 Requirements: {requirements[:100]}...")
        
        # Run AI-powered image validation
        logger.info("🧠 Running AI-powered image analysis...")
        ai_validator = AIArchitectureValidator()
        
        validation_result = await ai_validator.validate_architecture_from_images(
            actual_image_b64=actual_b64,
            expected_image_b64=expected_b64,
            requirements=requirements,
            actual_content_type=actual_content_type,
            expected_content_type=expected_content_type
        )
        
        # Enhance response with metadata
        validation_result["validation_id"] = validation_id
        validation_result["input_metadata"] = {
            "actual_diagram_filename": actual_diagram.filename,
            "actual_diagram_type": actual_content_type,
            "actual_diagram_size_bytes": len(actual_content),
            "expected_diagram_provided": expected_diagram is not None,
            "expected_diagram_filename": expected_diagram.filename if expected_diagram else None,
            "requirements_length": len(requirements)
        }
        validation_result["validation_type"] = "image"
        validation_result["timestamp"] = datetime.now().isoformat()
        
        logger.info(f"✅ Image validation completed - Score: {validation_result.get('compliance_score', 0)}%")
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ Image validation error: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        
        return {
            "validation_id": f"error_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "error": True,
            "message": f"Image validation failed: {str(e)}",
            "compliance_score": 0,
            "critical_issues": [{"issue": f"Image analysis error: {str(e)}", "severity": "critical"}],
            "quick_wins": [],
            "ai_comparison": {"error": str(e)},
            "validation_type": "image",
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        }

 
@app.get("/api/validation-report/{validation_id}")
async def get_validation_report(validation_id: str):
    # In production, retrieve from database
    return {"message": "Detailed report available", "validation_id": validation_id}


# ═══════════════════════════════════════════════════════════════════
# REVERSE ENGINEERING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/reverse-engineer/drawio")
async def reverse_engineer_drawio(drawio_xml: str = Form(...)):
    """
    🔍 Reverse engineer a Draw.io XML file.
    Extracts services, connections, patterns, and generates requirements.
    """
    try:
        logger.info("🔍 Reverse engineering Draw.io file...")
        orchestrator = ReverseEngineerOrchestrator()
        result = await orchestrator.reverse_engineer_drawio(drawio_xml)
        logger.info(f"✅ Reverse engineering complete: {result['summary']['total_services']} services found")
        return result
    except Exception as e:
        logger.error(f"❌ Draw.io reverse engineering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reverse engineering failed: {str(e)}")


@app.post("/api/reverse-engineer/visio")
async def reverse_engineer_visio(file: UploadFile = File(...)):
    """
    🔍 Reverse engineer a Visio (.vsdx) file.
    Extracts shapes, connections, and maps to Azure services.
    """
    try:
        if not file.filename.endswith(('.vsdx', '.vsd')):
            raise HTTPException(400, "Only .vsdx files are supported")
        
        logger.info(f"🔍 Reverse engineering Visio file: {file.filename}")
        content = await file.read()
        orchestrator = ReverseEngineerOrchestrator()
        result = await orchestrator.reverse_engineer_visio(content, file.filename)
        logger.info(f"✅ Visio reverse engineering complete: {result['summary']['total_services']} services")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Visio reverse engineering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Visio reverse engineering failed: {str(e)}")


@app.post("/api/reverse-engineer/image")
async def reverse_engineer_image(file: UploadFile = File(...)):
    """
    🔍 Reverse engineer architecture from an image using GPT-4o Vision.
    Extracts services, connections, patterns from PNG/JPG diagrams.
    """
    try:
        allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(400, f"Invalid image type. Allowed: PNG, JPG, WEBP. Got: {file.content_type}")
        
        logger.info(f"🔍 Reverse engineering image: {file.filename}")
        content = await file.read()
        image_b64 = base64.b64encode(content).decode("utf-8")
        
        orchestrator = ReverseEngineerOrchestrator()
        result = await orchestrator.reverse_engineer_image(image_b64, file.content_type, file.filename)
        logger.info(f"✅ Image reverse engineering complete: {result['summary']['total_services']} services")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Image reverse engineering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image reverse engineering failed: {str(e)}")


@app.post("/api/reverse-engineer/terraform")
async def reverse_engineer_terraform(file: UploadFile = File(...)):
    """
    🔍 Reverse engineer architecture from Terraform ZIP.
    Parses .tf files and maps resources to Azure services.
    """
    try:
        if not file.filename.endswith('.zip'):
            raise HTTPException(400, "Only ZIP files are supported")
        
        logger.info(f"🔍 Reverse engineering Terraform: {file.filename}")
        content = await file.read()
        orchestrator = ReverseEngineerOrchestrator()
        result = await orchestrator.reverse_engineer_terraform(content, file.filename)
        logger.info(f"✅ Terraform reverse engineering complete: {result['summary']['total_services']} services")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Terraform reverse engineering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Terraform reverse engineering failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# ARCHITECTURE STORY / DEEP ANALYSIS ENDPOINT
# ═══════════════════════════════════════════════════════════════════

class ArchitectureStoryRequest(BaseModel):
    architecture: Dict[str, Any] = Field(..., description="Architecture data with services, connections")
    ai_enhancement: Optional[Dict[str, Any]] = Field(None, description="Existing AI enhancement data")
    source_type: Optional[str] = Field("", description="Source type (drawio, visio, image, terraform)")

@app.post("/api/reverse-engineer/analyze-story")
async def analyze_architecture_story(request: ArchitectureStoryRequest):
    """
    📖 Generate a comprehensive architecture story using multiple AI agents.
    Tells the complete story: what this architecture is, what it does, 
    data flow, security posture, performance profile, cost analysis, and recommendations.
    """
    try:
        logger.info("📖 Generating architecture story...")
        start_time = time.time()
        
        architecture = request.architecture
        ai_enhancement = request.ai_enhancement or {}
        
        services = architecture.get("services", [])
        connections = architecture.get("connections", [])
        service_names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in services]
        
        # Build requirements context from architecture 
        inferred_req = architecture.get("requirements_inferred", "") or ai_enhancement.get("inferred_requirements", "")
        
        # If no inferred requirements, build a meaningful one from available data
        if not inferred_req and service_names:
            pattern = architecture.get("architecture_pattern", "")
            inferred_req = (
                f"Azure architecture ({pattern or 'cloud'}) with {len(service_names)} services: "
                f"{', '.join(service_names[:15])}. "
                f"Has {len(connections)} connections between services. "
                f"Analyze for security, performance, and cost optimization."
            )
        
        # Run multiple agent analyses in parallel
        from agents import (
            SecurityAgent, PerformanceAgent, CostOptimizationAgent,
            ConnectionExpertAgent, RequirementsValidationAgent
        )
        
        # Prepare context for agents — include architecture data so agents can reason about actual services
        service_details_str = json.dumps(services[:30], indent=2) if services else "[]"
        connection_details_str = json.dumps(connections[:20], indent=2) if connections else "[]"
        
        agent_context = {
            "architecture_analysis": {
                "status": "completed",
                "services": services,
                "connections": connections,
                "containers": architecture.get("resource_groups", []),
                "architecture_pattern": architecture.get("architecture_pattern", ""),
                "is_reverse_engineered": True
            },
            # Simulate component_extraction so agents get richer context
            "component_extraction": {
                "status": "completed",
                "apis": [],
                "nfrs": [f"Architecture has {len(services)} services and {len(connections)} connections"],
                "technical_requirements": [inferred_req] if inferred_req else [],
                "tech_stack": [s.get("type", s.get("name", "")) if isinstance(s, dict) else str(s) for s in services[:15]],
                "integration_points": [f"{c.get('source','')} → {c.get('target','')}" for c in connections[:10] if isinstance(c, dict)],
                "data_requirements": [],
                "summary": {
                    "complexity_level": architecture.get("complexity", "Medium")
                }
            }
        }
        
        # Use Azure OpenAI for the main story narrative
        story_analysis = {}
        
        try:
            from ai_validator import AIArchitectureValidator
            validator = AIArchitectureValidator()
            
            story_prompt = f"""You are an expert Azure Solutions Architect. Analyze this architecture and tell its complete story.

ARCHITECTURE:
- Services: {json.dumps(service_names, indent=2)}
- Connections: {json.dumps(connections[:20], indent=2)}
- Pattern: {architecture.get('architecture_pattern', 'Unknown')}
- Complexity: {architecture.get('complexity', 'Unknown')}

Provide a comprehensive analysis as JSON:
{{
    "overview": {{
        "title": "Architecture title (e.g., 'E-Commerce Microservices Platform')",
        "description": "2-3 sentence executive summary of what this architecture does",
        "architecture_style": "e.g., Microservices, N-tier, Event-driven, Serverless",
        "primary_purpose": "The main business purpose this serves",
        "target_audience": "Who uses this system"
    }},
    "data_flow": {{
        "summary": "How data flows through the system end-to-end",
        "entry_points": ["User-facing entry points"],
        "processing_layers": ["Description of each processing layer"],
        "data_stores": ["Where data is persisted and why"],
        "exit_points": ["External integrations or outputs"]
    }},
    "key_capabilities": [
        {{"capability": "Name", "description": "What it enables", "services_involved": ["Service1"]}}
    ],
    "strengths": ["What this architecture does well"],
    "weaknesses": ["Potential issues or gaps"],
    "use_cases": ["Business scenarios this architecture supports"],
    "scalability_profile": {{
        "horizontal": "Can it scale horizontally? How?",
        "vertical": "Vertical scaling options",
        "bottlenecks": ["Potential bottlenecks"],
        "max_load_estimate": "Estimated concurrent users/requests"
    }},
    "disaster_recovery": {{
        "rpo": "Recovery Point Objective estimate",
        "rto": "Recovery Time Objective estimate", 
        "ha_features": ["High availability features present"],
        "gaps": ["Missing DR capabilities"]
    }},
    "compliance_readiness": ["GDPR", "SOC2", etc. - which standards this could meet"],
    "estimated_monthly_cost": {{
        "range": "$X - $Y/month",
        "breakdown": [{{"service": "Name", "estimated_cost": "$X/month"}}],
        "optimization_tips": ["Ways to reduce cost"]
    }}
}}"""

            response = validator.client.chat.completions.create(
                model=validator.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Azure Solutions Architect. Respond with detailed, accurate JSON only. No markdown."},
                    {"role": "user", "content": story_prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            cleaned = validator._clean_json_response(content)
            story_analysis = json.loads(cleaned)
            
        except Exception as e:
            logger.warning(f"AI story generation failed: {e}")
            # Fallback story from available data
            story_analysis = {
                "overview": {
                    "title": architecture.get("architecture_pattern", "Azure Architecture"),
                    "description": inferred_req or "An Azure cloud architecture",
                    "architecture_style": architecture.get("architecture_pattern", "Unknown"),
                    "primary_purpose": "Cloud infrastructure",
                    "target_audience": "End users"
                },
                "data_flow": {
                    "summary": f"Data flows through {len(services)} services with {len(connections)} connections",
                    "entry_points": [],
                    "processing_layers": [],
                    "data_stores": [],
                    "exit_points": []
                },
                "key_capabilities": [],
                "strengths": [],
                "weaknesses": [],
                "use_cases": [],
                "error": str(e)
            }
        
        # Run all 3 agents concurrently for speed
        async def run_security():
            try:
                agent = SecurityAgent()
                return await agent.analyze(inferred_req, agent_context)
            except Exception as e:
                logger.warning(f"Security agent failed: {e}")
                return {"status": "error", "error": str(e)}
        
        async def run_performance():
            try:
                agent = PerformanceAgent()
                return await agent.analyze(inferred_req, agent_context)
            except Exception as e:
                logger.warning(f"Performance agent failed: {e}")
                return {"status": "error", "error": str(e)}
        
        async def run_cost():
            try:
                agent = CostOptimizationAgent()
                return await agent.analyze(inferred_req, agent_context)
            except Exception as e:
                logger.warning(f"Cost agent failed: {e}")
                return {"status": "error", "error": str(e)}
        
        logger.info("🤖 Running Security, Performance, and Cost agents concurrently...")
        security_result, performance_result, cost_result = await asyncio.gather(
            run_security(), run_performance(), run_cost()
        )
        logger.info(f"✅ All agents completed — Security: {security_result.get('status')}, Perf: {performance_result.get('status')}, Cost: {cost_result.get('status')}")
        
        duration = time.time() - start_time
        
        # ─── Extract ACTUAL fields from each agent's response ───
        # SecurityAgent returns: compliance_score, zero_trust_score, critical_issues (list of dicts),
        #   security_services, compliance_requirements, quick_wins, security_baseline, threat_model
        sec_score = max(
            security_result.get("compliance_score", 0),
            security_result.get("zero_trust_score", 0),
            ai_enhancement.get("well_architected_scores", {}).get("security", 0)
        )
        sec_critical = security_result.get("critical_issues", [])
        # Flatten critical issues from dicts to strings
        sec_critical_flat = []
        for issue in sec_critical[:8]:
            if isinstance(issue, dict):
                txt = issue.get("issue", issue.get("threat", ""))
                sev = issue.get("severity", "")
                rem = issue.get("remediation", issue.get("fix", ""))
                sec_critical_flat.append(f"[{sev}] {txt}" + (f" → {rem}" if rem else ""))
            else:
                sec_critical_flat.append(str(issue))
        
        sec_recs = []
        for qw in security_result.get("quick_wins", [])[:3]:
            if isinstance(qw, dict):
                sec_recs.append(f"{qw.get('improvement', '')} (Impact: {qw.get('impact', 'N/A')})")
            else:
                sec_recs.append(str(qw))
        for svc in security_result.get("security_services", [])[:3]:
            if isinstance(svc, dict):
                sec_recs.append(f"Add {svc.get('service', svc.get('name', ''))} — {svc.get('purpose', svc.get('role', ''))}")
            else:
                sec_recs.append(str(svc))
        
        sec_compliance = []
        for cr in security_result.get("compliance_requirements", [])[:5]:
            if isinstance(cr, dict):
                sec_compliance.append(cr.get("framework", str(cr)))
            else:
                sec_compliance.append(str(cr))
        
        sec_assessment = ai_enhancement.get("security_assessment", "")
        sec_baseline = security_result.get("security_baseline", {})
        if sec_baseline and not sec_assessment:
            parts = []
            for domain, info in sec_baseline.items():
                if isinstance(info, dict):
                    score = info.get("score", 0)
                    gaps = info.get("gaps", [])
                    parts.append(f"{domain.title()}: {score}/100" + (f" (gaps: {', '.join(gaps[:2])})" if gaps else ""))
            if parts:
                sec_assessment = "Security Baseline — " + " | ".join(parts)
        
        # PerformanceAgent returns: performance_score, bottleneck_analysis (list of dicts),
        #   performance_services, caching_strategy, scaling_strategy, quick_wins, latency_targets
        perf_score = max(
            performance_result.get("performance_score", 0),
            ai_enhancement.get("well_architected_scores", {}).get("performance", 0)
        )
        
        perf_bottlenecks = []
        for bn in performance_result.get("bottleneck_analysis", [])[:5]:
            if isinstance(bn, dict):
                perf_bottlenecks.append(f"{bn.get('bottleneck', '')} — Impact: {bn.get('impact', 'N/A')}")
            else:
                perf_bottlenecks.append(str(bn))
        
        perf_recs = []
        for qw in performance_result.get("quick_wins", performance_result.get("quick_performance_wins", []))[:3]:
            if isinstance(qw, dict):
                perf_recs.append(f"{qw.get('improvement', '')} (Impact: {qw.get('impact', 'N/A')})")
            else:
                perf_recs.append(str(qw))
        for svc in performance_result.get("performance_services", [])[:3]:
            if isinstance(svc, dict):
                perf_recs.append(f"{svc.get('service', '')} — {svc.get('optimization', svc.get('expected_improvement', ''))}")
            else:
                perf_recs.append(str(svc))
        
        perf_assessment = ai_enhancement.get("performance_assessment", "")
        latency = performance_result.get("latency_targets", {})
        if latency and not perf_assessment:
            perf_assessment = f"Latency targets — P50: {latency.get('p50', 'N/A')}, P95: {latency.get('p95', 'N/A')}, P99: {latency.get('p99', 'N/A')}"
        
        # CostOptimizationAgent returns: cost_score, total_cost_analysis (dict),
        #   cost_optimization_services, rightsizing_opportunities, quick_wins, governance_recommendations
        cost_score_val = max(
            cost_result.get("cost_score", 0),
            ai_enhancement.get("well_architected_scores", {}).get("cost_optimization", 0)
        )
        
        cost_analysis = cost_result.get("total_cost_analysis", {})
        monthly_est = cost_analysis.get("estimated_monthly_optimized", "") or cost_analysis.get("estimated_monthly_unoptimized", "")
        if not monthly_est:
            monthly_est = story_analysis.get("estimated_monthly_cost", {}).get("range", "")
        
        cost_savings = []
        for rs in cost_result.get("rightsizing_opportunities", [])[:3]:
            if isinstance(rs, dict):
                cost_savings.append(f"Rightsize {rs.get('resource', '')} ({rs.get('current_sku', '')} → {rs.get('recommended_sku', '')}) — save {rs.get('monthly_savings', 'N/A')}/mo")
            else:
                cost_savings.append(str(rs))
        for qw in cost_result.get("quick_wins", cost_result.get("quick_cost_wins", []))[:3]:
            if isinstance(qw, dict):
                cost_savings.append(f"{qw.get('optimization', '')} — save {qw.get('monthly_savings', 'N/A')}/mo")
            else:
                cost_savings.append(str(qw))
        
        cost_recs = []
        for svc in cost_result.get("cost_optimization_services", [])[:3]:
            if isinstance(svc, dict):
                cost_recs.append(f"{svc.get('service', '')}: {svc.get('current_pricing', '')} → {svc.get('recommended_pricing', '')} (save {svc.get('savings_percentage', 'N/A')})")
            else:
                cost_recs.append(str(svc))
        for gr in cost_result.get("governance_recommendations", [])[:2]:
            if isinstance(gr, dict):
                cost_recs.append(f"[{gr.get('category', '')}] {gr.get('recommendation', '')}")
            else:
                cost_recs.append(str(gr))
        
        # ─── Build WAF scores from best available sources ───
        waf_ai = ai_enhancement.get("well_architected_scores", {})
        well_architected = {
            "security": max(sec_score, waf_ai.get("security", 0)),
            "reliability": waf_ai.get("reliability", 0),
            "performance": max(perf_score, waf_ai.get("performance", 0)),
            "cost_optimization": max(cost_score_val, waf_ai.get("cost_optimization", 0)),
            "operational_excellence": waf_ai.get("operational_excellence", 0)
        }
        
        # ─── Aggregate all recommendations ───
        all_recs = ai_enhancement.get("recommendations", [])
        for ci in cost_result.get("critical_cost_issues", [])[:2]:
            if isinstance(ci, dict):
                all_recs.append(f"💰 Cost: {ci.get('issue', '')} (waste: {ci.get('monthly_waste', 'N/A')}/mo)")
        for ap in performance_result.get("anti_patterns_detected", [])[:2]:
            if isinstance(ap, dict):
                all_recs.append(f"⚡ Perf: {ap.get('anti_pattern', '')} → {ap.get('fix', '')}")
        
        logger.info(f"📖 Story complete in {round(duration, 2)}s — WAF scores: {well_architected}")
        
        return {
            "status": "success",
            "story": story_analysis,
            "agents": {
                "security": {
                    "score": sec_score,
                    "critical_issues": sec_critical_flat,
                    "recommendations": sec_recs[:6],
                    "compliance": sec_compliance,
                    "assessment": sec_assessment
                },
                "performance": {
                    "score": perf_score,
                    "bottlenecks": perf_bottlenecks,
                    "recommendations": perf_recs[:6],
                    "assessment": perf_assessment
                },
                "cost": {
                    "score": cost_score_val,
                    "monthly_estimate": monthly_est,
                    "savings_opportunities": cost_savings[:6],
                    "recommendations": cost_recs[:6]
                }
            },
            "well_architected_scores": well_architected,
            "missing_services": ai_enhancement.get("missing_services", []),
            "missing_connections": ai_enhancement.get("missing_connections", []),
            "recommendations": all_recs,
            "processing_time": round(duration, 2),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Architecture story analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Story analysis failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# ARCHITECTURE DIFF / COMPARISON ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

class CompareRequest(BaseModel):
    actual_architecture: Dict[str, Any] = Field(..., description="Actual architecture with services and connections")
    expected_architecture: Dict[str, Any] = Field(..., description="Expected architecture with services and connections")
    requirements: Optional[str] = Field("", description="Architecture requirements for context")
    include_ai_analysis: Optional[bool] = Field(True, description="Include AI-enhanced analysis")
    report_format: Optional[str] = Field("json", description="Report format: json or markdown")


@app.post("/api/compare")
async def compare_architectures(request: CompareRequest):
    """
    🔄 Compare actual vs expected architectures.
    Returns detailed diff with impact analysis and remediation plan.
    """
    try:
        logger.info("🔄 Starting architecture comparison...")
        start_time = time.time()
        
        # Run diff analysis
        analyzer = ArchitectureDiffAnalyzer()
        diff_result = analyzer.analyze(
            actual=request.actual_architecture,
            expected=request.expected_architecture,
            requirements=request.requirements or ""
        )
        
        # Optional AI enhancement
        ai_enhancement = {}
        if request.include_ai_analysis:
            try:
                ai_analyzer = AIEnhancedDiffAnalyzer()
                ai_enhancement = await ai_analyzer.enhance_diff(diff_result, request.requirements or "")
            except Exception as e:
                logger.warning(f"AI enhancement skipped: {e}")
                ai_enhancement = {"enhanced": False, "reason": str(e)}
        
        # Generate report
        report_gen = DiffReportGenerator()
        
        if request.report_format == "markdown":
            report = report_gen.generate_markdown_report(diff_result, ai_enhancement)
            response_data = {
                "format": "markdown",
                "report": report,
                "diff_summary": diff_result.to_dict(),
            }
        else:
            report = report_gen.generate_json_report(diff_result, ai_enhancement)
            response_data = report
        
        duration = time.time() - start_time
        response_data["comparison_id"] = f"compare_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        response_data["processing_time"] = round(duration, 2)
        response_data["timestamp"] = datetime.now().isoformat()
        
        logger.info(f"✅ Comparison complete in {duration:.2f}s — {diff_result.overall_match_percentage:.1f}% match")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Architecture comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.post("/api/compare/diagrams")
async def compare_diagram_files(
    actual_diagram: UploadFile = File(..., description="Actual architecture diagram"),
    expected_diagram: UploadFile = File(..., description="Expected architecture diagram"),
    requirements: str = Form("", description="Architecture requirements"),
):
    """
    🔄 Compare two uploaded diagram files (Draw.io, images, or Visio).
    Reverse engineers both diagrams, then performs diff analysis.
    """
    try:
        logger.info(f"🔄 Comparing diagrams: {actual_diagram.filename} vs {expected_diagram.filename}")
        re_orchestrator = ReverseEngineerOrchestrator()
        
        # Reverse engineer actual diagram
        actual_arch = await _reverse_engineer_file(re_orchestrator, actual_diagram)
        
        # Reverse engineer expected diagram
        expected_arch = await _reverse_engineer_file(re_orchestrator, expected_diagram)
        
        # Run diff
        analyzer = ArchitectureDiffAnalyzer()
        diff_result = analyzer.analyze(
            actual=actual_arch.get("architecture", {}),
            expected=expected_arch.get("architecture", {}),
            requirements=requirements
        )
        
        # AI enhancement
        ai_enhancement = {}
        try:
            ai_analyzer = AIEnhancedDiffAnalyzer()
            ai_enhancement = await ai_analyzer.enhance_diff(diff_result, requirements)
        except Exception as e:
            logger.warning(f"AI enhancement skipped: {e}")
        
        # Generate report
        report_gen = DiffReportGenerator()
        report = report_gen.generate_json_report(diff_result, ai_enhancement)
        
        report["actual_source"] = {
            "filename": actual_diagram.filename,
            "services_found": actual_arch.get("summary", {}).get("total_services", 0),
        }
        report["expected_source"] = {
            "filename": expected_diagram.filename,
            "services_found": expected_arch.get("summary", {}).get("total_services", 0),
        }
        report["comparison_id"] = f"file_compare_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        report["timestamp"] = datetime.now().isoformat()
        
        logger.info(f"✅ Diagram comparison complete — {diff_result.overall_match_percentage:.1f}% match")
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Diagram comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagram comparison failed: {str(e)}")


@app.post("/api/diff-report")
async def generate_diff_report(request: CompareRequest):
    """
    📋 Generate a formatted diff report (Markdown) for download/display.
    """
    try:
        analyzer = ArchitectureDiffAnalyzer()
        diff_result = analyzer.analyze(
            actual=request.actual_architecture,
            expected=request.expected_architecture,
            requirements=request.requirements or ""
        )
        
        ai_enhancement = {}
        if request.include_ai_analysis:
            try:
                ai_analyzer = AIEnhancedDiffAnalyzer()
                ai_enhancement = await ai_analyzer.enhance_diff(diff_result, request.requirements or "")
            except Exception:
                pass
        
        report_gen = DiffReportGenerator()
        markdown_report = report_gen.generate_markdown_report(diff_result, ai_enhancement)
        json_report = report_gen.generate_json_report(diff_result, ai_enhancement)
        
        return {
            "markdown_report": markdown_report,
            "json_report": json_report,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


async def _reverse_engineer_file(orchestrator: ReverseEngineerOrchestrator, file: UploadFile) -> Dict[str, Any]:
    """Helper to reverse engineer a file based on its type"""
    content = await file.read()
    filename = file.filename or ""
    
    if filename.endswith('.drawio'):
        xml_content = content.decode('utf-8', errors='replace')
        return await orchestrator.reverse_engineer_drawio(xml_content, filename, enhance_with_ai=False)
    elif filename.endswith(('.vsdx', '.vsd')):
        return await orchestrator.reverse_engineer_visio(content, filename, enhance_with_ai=False)
    elif filename.endswith('.zip'):
        return await orchestrator.reverse_engineer_terraform(content, filename, enhance_with_ai=False)
    elif file.content_type and file.content_type.startswith('image/'):
        image_b64 = base64.b64encode(content).decode("utf-8")
        return await orchestrator.reverse_engineer_image(image_b64, file.content_type, filename, enhance_with_ai=False)
    else:
        raise HTTPException(400, f"Unsupported file type: {filename}. Supported: .drawio, .vsdx, .zip, images")


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE & REINFORCEMENT LEARNING API
# ═══════════════════════════════════════════════════════════════════════════════

# Import knowledge base
try:
    from knowledge_base import (
        get_knowledge_manager, get_rl_learner,
        PatternType, FeedbackType, learn_from_architecture, get_suggestions_for_services
    )
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

class FeedbackRequest(BaseModel):
    """User feedback on generated architecture"""
    generation_id: str = Field(..., description="ID of the generation/validation")
    feedback_type: str = Field(..., description="positive, negative, rating, correction, comment")
    value: Any = Field(None, description="Rating value (1-5), correction text, or comment")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class PatternStoreRequest(BaseModel):
    """Store a new pattern in knowledge base"""
    pattern_type: str = Field(..., description="architecture, connection, service, security, performance, layout, prompt, custom")
    name: str = Field(..., description="Pattern name")
    content: Dict[str, Any] = Field(..., description="Pattern content")
    tags: Optional[List[str]] = Field(None, description="Tags for searching")
    source: Optional[str] = Field("api", description="Source of the pattern")

class PatternSearchRequest(BaseModel):
    """Search patterns"""
    pattern_type: Optional[str] = None
    tags: Optional[List[str]] = None
    query: Optional[str] = None
    min_confidence: Optional[float] = 0.0
    limit: Optional[int] = 20


@app.get("/api/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge base and RL statistics"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        rl = get_rl_learner()
        return {
            "knowledge_base": km.get_statistics(),
            "reinforcement_learning": rl.get_statistics(),
            "status": "active"
        }
    except Exception as e:
        raise HTTPException(500, f"Error getting KB stats: {str(e)}")


@app.post("/api/knowledge/pattern")
async def store_pattern(request: PatternStoreRequest):
    """Store a new pattern in the knowledge base"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        try:
            pt = PatternType(request.pattern_type)
        except ValueError:
            raise HTTPException(400, f"Invalid pattern_type: {request.pattern_type}. Valid: {[e.value for e in PatternType]}")
        
        pattern_id = km.store_pattern(
            pattern_type=pt,
            name=request.name,
            content=request.content,
            tags=request.tags or [],
            source=request.source or "api"
        )
        return {"pattern_id": pattern_id, "status": "stored"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error storing pattern: {str(e)}")


@app.post("/api/knowledge/search")
async def search_patterns_endpoint(request: PatternSearchRequest):
    """Search patterns in the knowledge base"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        pt = None
        if request.pattern_type:
            try:
                pt = PatternType(request.pattern_type)
            except ValueError:
                pass
        
        results = km.search_patterns(
            pattern_type=pt,
            tags=request.tags,
            query=request.query,
            min_confidence=request.min_confidence or 0.0,
            limit=request.limit or 20
        )
        return {
            "patterns": [p.to_dict() for p in results],
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(500, f"Error searching patterns: {str(e)}")


@app.get("/api/knowledge/patterns/{pattern_type}")
async def get_patterns_by_type(pattern_type: str):
    """Get all patterns of a specific type"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        try:
            pt = PatternType(pattern_type)
        except ValueError:
            raise HTTPException(400, f"Invalid pattern_type: {pattern_type}")
        
        patterns = km.get_patterns_by_type(pt)
        return {"patterns": [p.to_dict() for p in patterns], "total": len(patterns)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/knowledge/feedback")
async def record_feedback(request: FeedbackRequest):
    """Record user feedback and update RL model"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        rl = get_rl_learner()
        
        # Map feedback type
        try:
            ft = FeedbackType(request.feedback_type)
        except ValueError:
            raise HTTPException(400, f"Invalid feedback_type: {request.feedback_type}. Valid: {[e.value for e in FeedbackType]}")
        
        # Record in knowledge base
        feedback_id = km.record_feedback(
            knowledge_id=request.generation_id,
            feedback_type=ft,
            value=request.value,
            context=request.context or {}
        )
        
        # Also feed to RL learner
        rl.learn_from_feedback(
            pattern_id=request.generation_id,
            feedback_type=request.feedback_type,
            feedback_value=request.value
        )
        
        return {
            "feedback_id": feedback_id,
            "status": "recorded",
            "rl_updated": True,
            "exploration_rate": round(rl.exploration_rate, 4)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error recording feedback: {str(e)}")


@app.post("/api/knowledge/learn")
async def learn_from_generated_architecture(architecture: Dict[str, Any]):
    """Learn from a generated architecture (store as pattern + update RL)"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        pattern_id = learn_from_architecture(
            architecture=architecture,
            feedback="positive",
            requirements=architecture.get("requirements", "")
        )
        return {"pattern_id": pattern_id, "status": "learned"}
    except Exception as e:
        raise HTTPException(500, f"Error learning from architecture: {str(e)}")


@app.get("/api/knowledge/suggestions")
async def get_service_suggestions(services: str = Query(..., description="Comma-separated service names")):
    """Get knowledge-based suggestions for services"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        service_list = [s.strip() for s in services.split(",") if s.strip()]
        suggestions = get_suggestions_for_services(service_list)
        return suggestions
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/knowledge/session/{session_id}")
async def get_kb_session(session_id: str):
    """Get a knowledge base session by ID"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        km = get_knowledge_manager()
        sessions_dir = os.path.join(os.path.dirname(__file__), path_config.KNOWLEDGE_SESSIONS_DIR)
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            raise HTTPException(404, f"Session {session_id} not found")
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/sessions")
async def list_sessions(limit: int = Query(20, description="Max sessions to return"), offset: int = Query(0)):
    """List all saved sessions with pagination"""
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), path_config.KNOWLEDGE_SESSIONS_DIR)
        if not os.path.exists(sessions_dir):
            return {"sessions": [], "total": 0}
        
        session_files = sorted(
            glob.glob(os.path.join(sessions_dir, "*.json")),
            key=os.path.getmtime,
            reverse=True
        )
        total = len(session_files)
        page = session_files[offset:offset + limit]
        
        sessions = []
        for sf in page:
            try:
                with open(sf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data.get("session_id", os.path.splitext(os.path.basename(sf))[0]),
                    "requirements": data.get("requirements", "")[:200],
                    "started_at": data.get("started_at", ""),
                    "ended_at": data.get("ended_at", ""),
                    "services_count": len(data.get("services_used", [])),
                    "patterns_count": len(data.get("patterns_applied", [])),
                    "feedback_count": len(data.get("feedback_received", [])),
                    "outputs_count": len(data.get("outputs_generated", [])),
                })
            except Exception:
                continue
        
        return {"sessions": sessions, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get full session history with all details"""
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), path_config.KNOWLEDGE_SESSIONS_DIR)
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            raise HTTPException(404, f"Session {session_id} not found")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Enrich with related files
        base_dir = os.path.dirname(__file__)
        xml_dir = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml')
        responses_dir = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses')
        
        related_files = []
        if os.path.exists(xml_dir):
            for f_name in os.listdir(xml_dir):
                if session_id in f_name or (session_data.get("started_at", "")[:10] in f_name):
                    related_files.append({"type": "diagram", "filename": f_name})
        if os.path.exists(responses_dir):
            for f_name in os.listdir(responses_dir):
                if session_id in f_name:
                    related_files.append({"type": "response", "filename": f_name})
        
        session_data["related_files"] = related_files
        return session_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


class SessionResumeRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to resume")
    additional_requirements: str = Field("", description="Additional requirements for the resumed session")


@app.post("/api/session/{session_id}/resume")
async def resume_session(session_id: str, request: SessionResumeRequest):
    """Resume a previous session with optional additional requirements"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), path_config.KNOWLEDGE_SESSIONS_DIR)
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            raise HTTPException(404, f"Session {session_id} not found")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            prev_session = json.load(f)
        
        km = get_knowledge_manager()
        
        # Start new session with previous context
        combined_requirements = prev_session.get("requirements", "")
        if request.additional_requirements:
            combined_requirements += f"\n\nAdditional requirements: {request.additional_requirements}"
        
        new_session_id = km.start_session(combined_requirements)
        
        # Copy over tracked data from previous session
        for svc in prev_session.get("services_used", []):
            km.track_service_used(svc)
        for pat in prev_session.get("patterns_applied", []):
            km.track_pattern_applied(pat)
        
        return {
            "new_session_id": new_session_id,
            "previous_session_id": session_id,
            "combined_requirements": combined_requirements,
            "inherited_services": prev_session.get("services_used", []),
            "inherited_patterns": prev_session.get("patterns_applied", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), path_config.KNOWLEDGE_SESSIONS_DIR)
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            raise HTTPException(404, f"Session {session_id} not found")
        os.remove(filepath)
        return {"deleted": True, "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/rl/stats")
async def get_rl_stats():
    """Get reinforcement learning statistics"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        rl = get_rl_learner()
        return rl.get_statistics()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/rl/rankings")
async def get_rl_rankings(services: str = Query("", description="Comma-separated service/pattern IDs")):
    """Get RL-based pattern rankings"""
    if not KB_AVAILABLE:
        raise HTTPException(503, "Knowledge base not available")
    try:
        rl = get_rl_learner()
        pattern_list = [s.strip() for s in services.split(",") if s.strip()]
        if not pattern_list:
            return {"rankings": [], "message": "Provide pattern IDs via ?services= query"}
        rankings = rl.get_pattern_rankings(pattern_list)
        return {"rankings": [{"pattern": p, "q_value": round(v, 4)} for p, v in rankings]}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/saved-files")
async def get_saved_files():
    """Get list of all saved diagram files"""
    try:
        base_dir = os.path.dirname(__file__)
        xml_dir = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml')
        responses_dir = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses')
        diagrams_dir = os.path.join(base_dir, path_config.FRONTEND_DIAGRAMS_DIR)
        
        saved_files = {
            "xml_files": [],
            "response_files": [],
            "diagram_images": []
        }
        
        # Get XML files (DrawIO, Mermaid, Terraform)
        if os.path.exists(xml_dir):
            for file_path in glob.glob(os.path.join(xml_dir, "*")):
                filename = os.path.basename(file_path)
                file_info = {
                    "filename": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path),
                    "type": filename.split('.')[-1] if '.' in filename else 'unknown'
                }
                saved_files["xml_files"].append(file_info)
        
        # Get response JSON files
        if os.path.exists(responses_dir):
            for file_path in glob.glob(os.path.join(responses_dir, "*.json")):
                filename = os.path.basename(file_path)
                file_info = {
                    "filename": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path),
                    "type": "json"
                }
                saved_files["response_files"].append(file_info)
        
        # Get diagram images
        if os.path.exists(diagrams_dir):
            for file_path in glob.glob(os.path.join(diagrams_dir, "*.png")):
                filename = os.path.basename(file_path)
                file_info = {
                    "filename": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path),
                    "type": "png",
                    "url": f"/diagrams/{filename}"
                }
                saved_files["diagram_images"].append(file_info)
        
        # Sort by modification time (newest first)
        for category in saved_files:
            saved_files[category].sort(key=lambda x: x["modified"], reverse=True)
        
        return saved_files
    
    except Exception as e:
        logger.error(f"Error retrieving saved files: {str(e)}")
        return {"error": str(e)}

@app.get("/api/download/{file_type}/{filename}")
async def download_file(file_type: str, filename: str):
    """Download saved files"""
    try:
        base_dir = os.path.dirname(__file__)
        
        if file_type == "xml":
            file_path = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', filename)
        elif file_type == "response":
            file_path = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses', filename)
        elif file_type == "diagram":
            file_path = os.path.join(base_dir, path_config.FRONTEND_DIAGRAMS_DIR, filename)
        else:
            raise HTTPException(400, "Invalid file type")
        
        if not os.path.exists(file_path):
            raise HTTPException(404, "File not found")
        
        return FileResponse(file_path, filename=filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(500, f"Error downloading file: {str(e)}")
 
async def run_agent_workflow_background(session_id: str, request: GenerateRequest):
    """Background task to run the actual multi-agent workflow with real-time progress"""
    try:
        # Update status to running
        agent_progress_store[session_id]["status"] = "running"
        
        def update_progress(agent_name: str, status: str, progress: float):
            """Progress callback to update real-time status"""
            agents = agent_progress_store[session_id]["agents"]
            for i, agent in enumerate(agents):
                if agent_name.lower() in agent["name"].lower():  # Match partial names
                    agent_progress_store[session_id]["agents"][i]["status"] = status
                    agent_progress_store[session_id]["current_agent"] = agent["name"]
                    agent_progress_store[session_id]["progress_percentage"] = progress
                    logger.info(f"Real-time progress: {agent['name']} - {status} ({progress:.1f}%)")
                    break
        
        # Execute real multi-agent workflow with progress tracking
        try:
            workflow_pipeline = MultiAgentWorkflowPipeline()
            
            # Track progress through each agent
            update_progress("Security", "running", 10)
            
            result = await workflow_pipeline.execute_workflow(
                user_prompt=request.requirements,
                project_name=request.project_name,
                include_connection_agent=True
            )
            
            # Update each agent as complete based on actual execution
            agent_types = ["Security", "Performance", "Architecture", "Connection"]
            agents = agent_progress_store[session_id]["agents"]
            
            for i, agent_type in enumerate(agent_types):
                if i < len(agents):
                    progress = ((i + 1) / len(agents)) * 100
                    update_progress(agent_type, "complete", progress)
            
            # Final completion
            agent_progress_store[session_id]["status"] = "completed"
            agent_progress_store[session_id]["progress_percentage"] = 100
            agent_progress_store[session_id]["current_agent"] = None
            agent_progress_store[session_id]["result"] = result
            
            logger.info(f"✅ Multi-agent workflow completed for session {session_id}")
            
        except Exception as workflow_error:
            logger.error(f"❌ Workflow error for session {session_id}: {str(workflow_error)}")
            agent_progress_store[session_id]["status"] = "error"
            agent_progress_store[session_id]["error"] = str(workflow_error)
        
    except Exception as e:
        logger.error(f"❌ Background workflow error for session {session_id}: {str(e)}")
        agent_progress_store[session_id]["status"] = "error"
        agent_progress_store[session_id]["error"] = str(e)

@app.get("/api/response/{timestamp}")
async def get_response_by_timestamp(timestamp: str):
    """Get full response data by timestamp"""
    try:
        base_dir = os.path.dirname(__file__)
        response_path = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses', f'response-{timestamp}.json')
        
        if not os.path.exists(response_path):
            raise HTTPException(404, "Response not found")
        
        with open(response_path, 'r', encoding='utf-8') as f:
            response_data = json.load(f)
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving response: {str(e)}")
        raise HTTPException(500, f"Error retrieving response: {str(e)}")

@app.delete("/api/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str):
    """Delete saved files"""
    try:
        base_dir = os.path.dirname(__file__)
        
        if file_type == "xml":
            file_path = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'xml', filename)
        elif file_type == "response":
            file_path = os.path.join(base_dir, path_config.SAVED_DIAGRAMS_DIR, 'responses', filename)
        elif file_type == "diagram":
            file_path = os.path.join(base_dir, path_config.FRONTEND_DIAGRAMS_DIR, filename)
        else:
            raise HTTPException(400, "Invalid file type")
        
        if not os.path.exists(file_path):
            raise HTTPException(404, "File not found")
        
        os.remove(file_path)
        return {"message": f"File {filename} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(500, f"Error deleting file: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# Clarifying Questions Endpoint
# ═══════════════════════════════════════════════════════════════════

class ClarifyRequest(BaseModel):
    requirements: str = Field(..., description="User requirements text", min_length=10)

@app.post("/api/clarify")
async def generate_clarifying_questions(request: ClarifyRequest):
    """
    Analyze user requirements and generate intelligent clarifying questions.
    This helps the AI produce more accurate architecture designs by identifying
    gaps, ambiguities, and missing context in the requirements.
    """
    logger.info(f"🤔 Clarify endpoint called with requirements: {request.requirements[:100]}...")
    
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=azure_openai_config.API_KEY or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=azure_openai_config.API_VERSION,
            azure_endpoint=azure_openai_config.ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        clarify_prompt = f"""You are an expert Azure Solutions Architect conducting a requirements interview.
Analyze the user's requirements and identify GAPS, AMBIGUITIES, and MISSING CONTEXT that would significantly impact the architecture design.

USER REQUIREMENTS:
\"\"\"{request.requirements}\"\"\"

Generate 3-6 targeted clarifying questions. Focus on:
1. Scale/load expectations (if not specified)
2. Security/compliance requirements (if vague)
3. Integration with existing systems (if unclear)
4. Performance targets (latency, throughput)
5. Budget/cost constraints
6. Disaster recovery / availability needs

Rules:
- Only ask about things NOT already clear in the requirements
- Each question should directly impact the architecture design
- Provide sensible options when possible
- Mark importance: "critical" (will change entire design), "recommended" (improves design), "optional" (nice to have)

Return ONLY valid JSON array:
[
  {{
    "id": "q1",
    "question": "<clear, concise question>",
    "category": "<architecture|security|performance|scale|integration|business>",
    "options": ["option1", "option2", "option3"],
    "placeholder": "<hint for free text>",
    "type": "<select|text|multi-select>",
    "importance": "<critical|recommended|optional>",
    "why": "<1 sentence explaining why this matters for the architecture>"
  }}
]

If requirements are already very detailed and clear, return an empty array: []
"""
        
        response = await client.chat.completions.create(
            model=azure_openai_config.DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are an expert Azure Solutions Architect. Generate clarifying questions to improve architecture accuracy. Return only valid JSON."},
                {"role": "user", "content": clarify_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
        else:
            questions = []
        
        logger.info(f"✅ Generated {len(questions)} clarifying questions")
        return {"questions": questions, "requirements_length": len(request.requirements)}
        
    except Exception as e:
        logger.error(f"Error generating clarifying questions: {e}")
        # Return empty questions on error - don't block the workflow
        return {"questions": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# Real-time Agent Progress Endpoints (SSE + Polling)
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/generate-stream")
async def generate_stream(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Start architecture generation as a background task and return a session_id.
    Use /api/progress/{session_id} to poll for real-time agent progress updates.
    """
    logger.info(f"🚀 generate-stream called with requirements: {request.requirements[:100]}...")
    
    if not request.requirements or not isinstance(request.requirements, str) or not request.requirements.strip():
        raise HTTPException(status_code=400, detail="Valid requirements text is required")

    session_id = f"session_{uuid.uuid4().hex[:workflow_config.SESSION_ID_LENGTH]}_{int(time.time())}"
    logger.info(f"📋 Created session: {session_id}")
    
    agent_progress_store[session_id] = {
        "status": "queued",
        "current_agent": None,
        "progress_percentage": 0,
        "agent_logs": [],
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "requirements": request.requirements[:200],
        "interaction": None,  # Human-in-the-loop interaction request
    }
    
    # Initialize interaction store for this session
    agent_interaction_store[session_id] = {
        "pending": None,     # Current pending interaction request
        "response": None,    # User response to pending interaction
        "history": [],       # History of all interactions
        "event": asyncio.Event()  # Signal for when user responds
    }
    
    background_tasks.add_task(run_drawio_generation_background, session_id, request)
    
    return {
        "session_id": session_id,
        "status": "queued",
        "message": "Workflow started. Poll /api/progress/{session_id} for real-time updates."
    }


@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """
    Get real-time progress for a running workflow session.
    Returns current agent, progress percentage, agent logs with output summaries,
    and the final result when completed.
    """
    # Opportunistic cleanup of expired sessions
    cleanup_expired_sessions()

    if session_id not in agent_progress_store:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = agent_progress_store[session_id]
    
    response = {
        "session_id": session_id,
        "status": session_data.get("status", "unknown"),
        "current_agent": session_data.get("current_agent"),
        "progress_percentage": session_data.get("progress_percentage", 0),
        "agent_logs": session_data.get("agent_logs", []),
        "error": session_data.get("error"),
        "interaction": session_data.get("interaction"),  # Human-in-the-loop
        "live_thoughts": session_data.get("live_thoughts", []),  # Real-time agent thinking
    }
    
    logger.debug(f"Progress for {session_id}: {response['status']} - {response['progress_percentage']}% - {len(response['agent_logs'])} logs - {len(response['live_thoughts'])} thoughts")
    
    # Include result only when completed
    if session_data.get("status") == "completed" and session_data.get("result"):
        response["result"] = session_data["result"]
    
    return response


@app.post("/api/interaction/{session_id}/respond")
async def respond_to_interaction(session_id: str, response: InteractionResponse):
    """
    User responds to an agent's interaction request (approve/reject/modify).
    This unblocks the waiting agent to continue or adjust its work.
    """
    if session_id not in agent_interaction_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    interaction = agent_interaction_store[session_id]
    if not interaction.get("pending"):
        raise HTTPException(status_code=400, detail="No pending interaction for this session")
    
    # Record the response
    interaction["response"] = {
        "decision": response.decision,
        "feedback": response.feedback,
        "selected_items": response.selected_items,
        "responded_at": datetime.now().isoformat()
    }
    
    # Save to history
    interaction["history"].append({
        "request": interaction["pending"],
        "response": interaction["response"],
        "timestamp": datetime.now().isoformat()
    })
    
    # Clear the interaction from progress store
    if session_id in agent_progress_store:
        agent_progress_store[session_id]["interaction"] = None
        agent_progress_store[session_id]["status"] = "running"  # Resume
    
    # Signal the waiting agent
    interaction["event"].set()
    
    logger.info(f"🤝 User responded to interaction for {session_id}: {response.decision}")
    
    return {"status": "ok", "decision": response.decision}


@app.get("/api/progress-stream/{session_id}")
async def progress_stream(session_id: str):
    """
    Server-Sent Events (SSE) endpoint for real-time agent progress streaming.
    Frontend can use EventSource to receive live updates.
    """
    if session_id not in agent_progress_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def event_generator():
        last_log_count = 0
        while True:
            if session_id not in agent_progress_store:
                yield f"data: {json.dumps({'status': 'expired'})}\n\n"
                break
            
            session_data = agent_progress_store[session_id]
            current_logs = session_data.get("agent_logs", [])
            
            # Send new log entries as they arrive
            if len(current_logs) > last_log_count:
                for log_entry in current_logs[last_log_count:]:
                    yield f"data: {json.dumps({'type': 'agent_log', 'data': log_entry})}\n\n"
                last_log_count = len(current_logs)
            
            # Send status update
            status_update = {
                "type": "status",
                "data": {
                    "status": session_data.get("status"),
                    "current_agent": session_data.get("current_agent"),
                    "progress_percentage": session_data.get("progress_percentage", 0)
                }
            }
            yield f"data: {json.dumps(status_update)}\n\n"
            
            # Check termination conditions
            if session_data.get("status") == "completed":
                yield f"data: {json.dumps({'type': 'complete', 'data': session_data.get('result', {})})}\n\n"
                break
            elif session_data.get("status") == "error":
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': session_data.get('error', 'Unknown error')}})}\n\n"
                break
            
            await asyncio.sleep(workflow_config.POLLING_INTERVAL_SEC)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== CHAT API ENDPOINTS ====================

class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="Chat session identifier")
    message: str = Field(..., description="User message", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Current diagram/architecture context")

class ChatResponse(BaseModel):
    message: str
    thinking_process: Optional[List[Dict[str, str]]] = None
    diagram_xml: Optional[str] = None
    architecture: Optional[Dict[str, Any]] = None
    mermaid: Optional[str] = None
    terraform: Optional[str] = None
    session_id: str
    timestamp: str

# Store chat sessions in memory (in production, use Redis or database)
chat_sessions = {}


@app.post("/api/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatMessageRequest):
    """
    Process a chat message for architecture design/modification.
    Analyzes user intent and updates the architecture accordingly.
    """
    try:
        session_id = request.session_id
        user_message = request.message.strip()
        current_architecture = request.context.get("current_architecture") if request.context else None
        
        logger.info(f"Chat message received for session {session_id}: {user_message[:100]}...")
        
        thinking_process = []
        
        # Initialize or get session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "architecture": current_architecture or {"services": [], "connections": [], "architecture_pattern": "Custom"},
                "history": []
            }
        
        session = chat_sessions[session_id]
        
        # Update architecture from context if provided
        if current_architecture:
            session["architecture"] = current_architecture
        
        thinking_process.append({
            "type": "reasoning",
            "content": f"Analyzing request: '{user_message}'"
        })
        
        # Use Azure OpenAI to analyze intent and generate architecture changes
        analyzer = AzureOpenAIAnalyzer()
        
        # Create a detailed prompt for intent analysis
        intent_prompt = f"""Analyze this user request for an Azure architecture diagram and provide a structured response.

User Request: {user_message}

Current Architecture:
- Services: {json.dumps(session["architecture"].get("services", []), indent=2)}
- Connections: {json.dumps(session["architecture"].get("connections", []), indent=2)}
- Pattern: {session["architecture"].get("architecture_pattern", "Custom")}

Respond with JSON containing:
{{
    "intent": "create" | "add" | "remove" | "modify" | "connect" | "explain" | "query",
    "services_to_add": [
        {{"name": "Service Name", "type": "azure_service_type", "category": "compute|storage|network|database|ai|security|integration"}}
    ],
    "services_to_remove": ["Service Name"],
    "connections_to_add": [
        {{"from": "Source Service", "to": "Target Service", "type": "https|eventhub|queue|database|private_endpoint", "label": "optional label"}}
    ],
    "connections_to_remove": [{{"from": "Source", "to": "Target"}}],
    "architecture_pattern": "N-Tier" | "Microservices" | "Event-Driven" | "Hub-Spoke" | null,
    "explanation": "Brief explanation of changes",
    "response_message": "Friendly response to user"
}}

Only include changes that are explicitly or implicitly requested. Be smart about inferring standard connections."""
        
        try:
            intent_result = analyzer.analyze_requirements(intent_prompt)
            # Parse the JSON from the response
            intent_json = None
            if isinstance(intent_result, dict):
                intent_json = intent_result
            else:
                # Try to extract JSON from text response
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(intent_result))
                if json_match:
                    intent_json = json.loads(json_match.group())
            
            if not intent_json:
                raise ValueError("Could not parse intent response")
                
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            # Fallback: simple keyword-based intent detection
            intent_json = {
                "intent": "create" if not session["architecture"].get("services") else "modify",
                "services_to_add": [],
                "connections_to_add": [],
                "explanation": "Processing your request...",
                "response_message": "I'll help you with that architecture design."
            }
        
        thinking_process.append({
            "type": "planning",
            "content": f"Intent detected: {intent_json.get('intent', 'unknown')}"
        })
        
        # Apply changes to architecture
        arch = session["architecture"]
        changes_made = False
        
        # Add new services
        services_to_add = intent_json.get("services_to_add", [])
        for service in services_to_add:
            if service.get("name") and service["name"] not in [s.get("name") for s in arch.get("services", [])]:
                if "services" not in arch:
                    arch["services"] = []
                arch["services"].append({
                    "name": service["name"],
                    "type": service.get("type", "generic"),
                    "category": service.get("category", "compute")
                })
                changes_made = True
                thinking_process.append({
                    "type": "action",
                    "content": f"Adding service: {service['name']}"
                })
        
        # Remove services
        services_to_remove = intent_json.get("services_to_remove", [])
        for service_name in services_to_remove:
            arch["services"] = [s for s in arch.get("services", []) if s.get("name") != service_name]
            # Also remove related connections
            arch["connections"] = [c for c in arch.get("connections", []) 
                                   if c.get("from") != service_name and c.get("to") != service_name]
            changes_made = True
            thinking_process.append({
                "type": "action",
                "content": f"Removing service: {service_name}"
            })
        
        # Add connections
        connections_to_add = intent_json.get("connections_to_add", [])
        for conn in connections_to_add:
            if conn.get("from") and conn.get("to"):
                existing = [c for c in arch.get("connections", []) 
                           if c.get("from") == conn["from"] and c.get("to") == conn["to"]]
                if not existing:
                    if "connections" not in arch:
                        arch["connections"] = []
                    arch["connections"].append({
                        "from": conn["from"],
                        "to": conn["to"],
                        "type": conn.get("type", "https"),
                        "label": conn.get("label", "")
                    })
                    changes_made = True
                    thinking_process.append({
                        "type": "action",
                        "content": f"Adding connection: {conn['from']} → {conn['to']}"
                    })
        
        # Remove connections
        connections_to_remove = intent_json.get("connections_to_remove", [])
        for conn in connections_to_remove:
            arch["connections"] = [c for c in arch.get("connections", []) 
                                   if not (c.get("from") == conn.get("from") and c.get("to") == conn.get("to"))]
            changes_made = True
        
        # Update architecture pattern if specified
        if intent_json.get("architecture_pattern"):
            arch["architecture_pattern"] = intent_json["architecture_pattern"]
        
        # Update session
        session["architecture"] = arch
        session["history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate diagram if we have services
        diagram_xml = None
        mermaid_code = None
        terraform_code = None
        
        if arch.get("services") and changes_made:
            thinking_process.append({
                "type": "generating",
                "content": "Generating architecture diagram..."
            })
            
            try:
                # Use DrawioParser to generate the diagram
                diagram_xml = generate_drawio_from_architecture(arch)
                logger.info("✅ Draw.io diagram generated from chat")
                
                # Generate Mermaid
                try:
                    azure_generator = AzureIconDiagramGenerator()
                    mermaid_code = azure_generator.generate_mermaid_diagram(arch)
                except Exception as e:
                    logger.warning(f"Mermaid generation failed: {e}")
                
                # Generate Terraform
                try:
                    azure_generator = AzureIconDiagramGenerator()
                    terraform_code = azure_generator.generate_terraform_template(arch)
                except Exception as e:
                    logger.warning(f"Terraform generation failed: {e}")
                    
            except Exception as e:
                logger.error(f"Diagram generation failed: {e}")
                thinking_process.append({
                    "type": "error",
                    "content": f"Diagram generation encountered an issue: {str(e)}"
                })
        
        thinking_process.append({
            "type": "complete",
            "content": "Architecture updated successfully"
        })
        
        response_message = intent_json.get("response_message", "I've updated your architecture based on your request.")
        
        # Add summary of changes
        if changes_made:
            changes_summary = []
            if services_to_add:
                changes_summary.append(f"Added {len(services_to_add)} service(s)")
            if services_to_remove:
                changes_summary.append(f"Removed {len(services_to_remove)} service(s)")
            if connections_to_add:
                changes_summary.append(f"Added {len(connections_to_add)} connection(s)")
            if changes_summary:
                response_message += f"\n\nChanges: {', '.join(changes_summary)}."
        
        session["history"].append({
            "role": "assistant",
            "content": response_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_message,
            thinking_process=thinking_process,
            diagram_xml=diagram_xml,
            architecture=arch,
            mermaid=mermaid_code,
            terraform=terraform_code,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat message error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/api/chat/regenerate")
async def chat_regenerate(request: Dict[str, Any]):
    """
    Regenerate diagram from existing architecture without AI processing.
    """
    try:
        session_id = request.get("session_id", "")
        architecture = request.get("architecture", {})
        
        if not architecture.get("services"):
            return JSONResponse(
                status_code=400,
                content={"error": "No services in architecture"}
            )
        
        # Generate diagram
        diagram_xml = generate_drawio_from_architecture(architecture)
        
        # Generate Mermaid
        mermaid_code = None
        terraform_code = None
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            mermaid_code = azure_generator.generate_mermaid_diagram(architecture)
        except Exception as e:
            logger.warning(f"Mermaid generation failed: {e}")
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            terraform_code = azure_generator.generate_terraform_template(architecture)
        except Exception as e:
            logger.warning(f"Terraform generation failed: {e}")
        
        return {
            "diagram_xml": diagram_xml,
            "mermaid": mermaid_code,
            "terraform": terraform_code,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Regenerate error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/session/{session_id}")
async def get_chat_session(session_id: str):
    """Get chat session history and current architecture."""
    if session_id not in chat_sessions:
        return JSONResponse(
            status_code=404,
            content={"error": "Session not found"}
        )
    
    session = chat_sessions[session_id]
    return {
        "session_id": session_id,
        "architecture": session["architecture"],
        "history": session["history"],
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/api/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"message": "Session deleted", "session_id": session_id}


# ==================== DIAGRAM IMPROVEMENT ENDPOINT ====================

class DiagramImproveRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    improvement_prompt: str = Field(..., description="User's improvement request", min_length=1)
    current_architecture: Dict[str, Any] = Field(..., description="Current architecture JSON")

class DiagramModifyRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    modification_prompt: str = Field(..., description="User's modification request", min_length=1)
    current_architecture: Dict[str, Any] = Field(..., description="Current architecture JSON")
    current_xml: str = Field(default="", description="Current Draw.io XML")
    strategy: str = Field(default="hybrid", description="Modification strategy: direct_xml, architecture_regeneration, hybrid")
    original_requirements: str = Field(default="", description="Original generation requirements")

@app.post("/api/diagram/improve")
async def improve_diagram(request: DiagramImproveRequest):
    """
    Apply an improvement to an existing architecture diagram.
    Parses user intent, modifies architecture, and regenerates diagram.
    """
    try:
        session_id = request.session_id
        prompt = request.improvement_prompt.strip()
        architecture = request.current_architecture
        
        logger.info(f"Diagram improvement request: {prompt[:100]}...")
        
        if not architecture.get("services"):
            raise HTTPException(status_code=400, detail="No services in current architecture")
        
        changes_applied = []
        
        # Use Azure OpenAI to analyze improvement intent
        analyzer = AzureOpenAIAnalyzer()
        
        # Get existing service names and connections for context
        existing_services = [s.get('name') for s in architecture.get('services', []) if isinstance(s, dict)]
        existing_connections = architecture.get('connections', [])
        
        intent_prompt = f"""Analyze this improvement request for an Azure architecture diagram.

User Request: "{prompt}"

Current Architecture Services: {json.dumps(existing_services, indent=2)}
Current Connections: {json.dumps(existing_connections, indent=2)}

IMPORTANT RULES:
1. Use EXACT service names from the current architecture when creating connections
2. For "between X and Y" requests: add the new service, connect FROM X TO new_service, and FROM new_service TO Y
3. New services need proper Azure naming (e.g., "Azure Cache for Redis", "Azure Key Vault")
4. Categories: compute, data, networking, security, monitoring, integration, ai, storage
5. Connection types: https, private_endpoint, queue, event, vnet_peering
6. Service connection labels should describe the data flow (e.g., "Cache Query", "Secrets", "Telemetry")

Respond with JSON ONLY (no markdown):
{{
    "action": "add" | "remove" | "modify" | "connect" | "disconnect",
    "services_to_add": [
        {{"name": "Full Azure Service Name", "type": "service_type", "category": "category"}}
    ],
    "services_to_remove": ["Exact Service Name from list"],
    "connections_to_add": [
        {{"from": "Exact Source Service Name", "to": "Exact Target Service Name", "type": "https", "label": "Flow Description"}}
    ],
    "connections_to_remove": [{{"from": "Source", "to": "Target"}}],
    "explanation": "Brief description of what this improvement does"
}}

Example for "add redis cache between App Service and SQL Database":
{{
    "action": "add",
    "services_to_add": [{{"name": "Azure Cache for Redis", "type": "redis", "category": "data"}}],
    "services_to_remove": [],
    "connections_to_add": [
        {{"from": "App Service", "to": "Azure Cache for Redis", "type": "https", "label": "Cache Query"}},
        {{"from": "Azure Cache for Redis", "to": "Azure SQL Database", "type": "private_endpoint", "label": "Cache Miss"}}
    ],
    "connections_to_remove": [{{"from": "App Service", "to": "Azure SQL Database"}}],
    "explanation": "Added Redis cache layer between App Service and SQL Database for improved performance"
}}"""
        
        try:
            intent_result = analyzer.analyze_requirements(intent_prompt)
            intent_json = None
            
            if isinstance(intent_result, dict):
                intent_json = intent_result
            else:
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(intent_result))
                if json_match:
                    intent_json = json.loads(json_match.group())
            
            if not intent_json:
                raise ValueError("Could not parse intent")
                
        except Exception as e:
            logger.warning(f"AI intent parsing failed: {e}, using keyword matching")
            intent_json = _parse_improvement_keywords(prompt, architecture)
        
        # Apply changes to architecture
        services = list(architecture.get("services", []))
        connections = list(architecture.get("connections", []))
        
        # Add new services
        for svc in intent_json.get("services_to_add", []):
            svc_name = svc.get("name", "")
            if svc_name and svc_name not in [s.get("name") for s in services if isinstance(s, dict)]:
                services.append({
                    "name": svc_name,
                    "type": svc.get("type", "generic"),
                    "category": svc.get("category", "compute")
                })
                changes_applied.append(f"Added {svc_name}")
        
        # Remove services
        for svc_name in intent_json.get("services_to_remove", []):
            original_count = len(services)
            services = [s for s in services if isinstance(s, dict) and s.get("name") != svc_name]
            connections = [c for c in connections if c.get("source") != svc_name and c.get("target") != svc_name]
            if len(services) < original_count:
                changes_applied.append(f"Removed {svc_name}")
        
        # Add connections
        for conn in intent_json.get("connections_to_add", []):
            source = conn.get("from", "")
            target = conn.get("to", "")
            if source and target:
                existing = [c for c in connections if c.get("source") == source and c.get("target") == target]
                if not existing:
                    connections.append({
                        "source": source,
                        "target": target,
                        "type": conn.get("type", "https"),
                        "label": conn.get("label", "")
                    })
                    changes_applied.append(f"Connected {source} → {target}")
        
        # Remove connections
        for conn in intent_json.get("connections_to_remove", []):
            source = conn.get("from", "")
            target = conn.get("to", "")
            original_count = len(connections)
            connections = [c for c in connections if not (c.get("source") == source and c.get("target") == target)]
            if len(connections) < original_count:
                changes_applied.append(f"Disconnected {source} → {target}")
        
        # Build updated architecture
        updated_architecture = {
            **architecture,
            "services": services,
            "connections": connections
        }
        
        # Use ConnectionExpertAgent to validate and fix connections
        try:
            from agents import ConnectionExpertAgent
            connection_agent = ConnectionExpertAgent()
            
            # Prepare context for the agent
            agent_context = {
                "architecture_analysis": {
                    "status": "completed",
                    "services": services,
                    "connections": connections,
                    "containers": architecture.get("containers", [])
                }
            }
            
            # Run validation (synchronous wrapper for async)
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context
                validation_result = await connection_agent.analyze("", agent_context)
            else:
                validation_result = asyncio.run(connection_agent.analyze("", agent_context))
            
            if validation_result.get("status") == "completed":
                enhanced = validation_result.get("enhanced_architecture", {})
                services = enhanced.get("services", services)
                connections = enhanced.get("connections", connections)
                
                # Add auto-fix info to changes
                auto_fixes = validation_result.get("auto_fixes_applied", [])
                for fix in auto_fixes:
                    changes_applied.append(f"Auto-fix: {fix}")
                
                updated_architecture["services"] = services
                updated_architecture["connections"] = connections
                
        except Exception as e:
            logger.warning(f"ConnectionExpertAgent validation skipped: {e}")
        
        # Generate updated diagram (requires requirements string)
        requirements_str = architecture.get("requirements", "") or request.improvement_prompt
        diagram_xml = await generate_drawio_from_architecture(updated_architecture, requirements_str)
        
        # Generate Mermaid and Terraform
        mermaid_code = None
        terraform_code = None
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            mermaid_code = azure_generator.generate_mermaid_diagram(updated_architecture)
        except Exception as e:
            logger.warning(f"Mermaid generation failed: {e}")
        
        try:
            azure_generator = AzureIconDiagramGenerator()
            terraform_code = azure_generator.generate_terraform_template(updated_architecture)
        except Exception as e:
            logger.warning(f"Terraform generation failed: {e}")
        
        logger.info(f"Improvement applied: {len(changes_applied)} changes")
        
        return {
            "success": True,
            "architecture": updated_architecture,
            "diagram_xml": diagram_xml,
            "mermaid": mermaid_code,
            "terraform": terraform_code,
            "changes_applied": changes_applied,
            "explanation": intent_json.get("explanation", "Improvement applied"),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagram improvement error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Improvement failed: {str(e)}")


# ==================== DIAGRAM MODIFICATION AGENT ENDPOINT ====================

@app.post("/api/diagram/modify")
async def modify_diagram(request: DiagramModifyRequest):
    """
    Apply a modification to an existing architecture diagram using the DiagramModificationAgent.
    Supports 3 strategies: direct_xml, architecture_regeneration, hybrid.
    Includes full validation pipeline (connection, WAF, requirements, XML).
    """
    try:
        session_id = request.session_id
        prompt = request.modification_prompt.strip()
        architecture = request.current_architecture
        current_xml = request.current_xml
        strategy = request.strategy
        original_requirements = request.original_requirements

        logger.info(f"Diagram modification request: strategy={strategy}, prompt={prompt[:100]}...")

        if not architecture.get("services"):
            raise HTTPException(status_code=400, detail="No services in current architecture")

        # Validate strategy
        valid_strategies = ["direct_xml", "architecture_regeneration", "hybrid"]
        if strategy not in valid_strategies:
            strategy = "hybrid"

        # Initialize the modification agent
        agent = DiagramModificationAgent()

        # Build context for the agent
        context = {
            "current_architecture": architecture,
            "current_xml": current_xml,
            "modification_request": prompt,
            "strategy": strategy,
            "original_requirements": original_requirements,
        }

        # Run the agent
        result = await agent.analyze(prompt, context)

        if not result.get("success"):
            status_hint = result.get("status_hint", 500)
            error_msg = result.get("error", "Modification agent failed")
            thinking = result.get("thinking_process", [])
            raise HTTPException(
                status_code=status_hint,
                detail={
                    "message": error_msg,
                    "thinking_process": thinking,
                },
            )

        # Generate Mermaid and Terraform from updated architecture
        updated_arch = result.get("updated_architecture", architecture)
        mermaid_code = None
        terraform_code = None

        try:
            azure_generator = AzureIconDiagramGenerator()
            mermaid_code = azure_generator.generate_mermaid_diagram(updated_arch)
        except Exception as e:
            logger.warning(f"Mermaid generation failed: {e}")

        try:
            azure_generator = AzureIconDiagramGenerator()
            terraform_code = azure_generator.generate_terraform_template(updated_arch)
        except Exception as e:
            logger.warning(f"Terraform generation failed: {e}")

        logger.info(f"Modification complete: strategy={result.get('strategy_used')}, changes={len(result.get('changes_applied', []))}")

        return {
            "success": True,
            "strategy_used": result.get("strategy_used", strategy),
            "architecture": updated_arch,
            "diagram_xml": result.get("updated_xml", ""),
            "mermaid": mermaid_code,
            "terraform": terraform_code,
            "changes_applied": result.get("changes_applied", []),
            "validation_results": result.get("validation_results", {}),
            "thinking_process": result.get("thinking_process", []),
            "diff_summary": result.get("diff_summary", {}),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagram modification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Modification failed: {str(e)}")


def _parse_improvement_keywords(prompt: str, architecture: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback keyword-based intent parsing when AI is unavailable"""
    prompt_lower = prompt.lower()
    result = {
        "action": "modify",
        "services_to_add": [],
        "services_to_remove": [],
        "connections_to_add": [],
        "connections_to_remove": [],
        "explanation": "Parsed from keywords"
    }
    
    # Common service patterns with proper Azure naming
    service_patterns = {
        "redis": {"name": "Azure Cache for Redis", "type": "redis", "category": "data"},
        "cache": {"name": "Azure Cache for Redis", "type": "redis", "category": "data"},
        "cdn": {"name": "Azure CDN", "type": "cdn", "category": "networking"},
        "front door": {"name": "Azure Front Door", "type": "front_door", "category": "networking"},
        "frontdoor": {"name": "Azure Front Door", "type": "front_door", "category": "networking"},
        "application insights": {"name": "Application Insights", "type": "app_insights", "category": "monitoring"},
        "app insights": {"name": "Application Insights", "type": "app_insights", "category": "monitoring"},
        "monitor": {"name": "Azure Monitor", "type": "monitor", "category": "monitoring"},
        "monitoring": {"name": "Azure Monitor", "type": "monitor", "category": "monitoring"},
        "key vault": {"name": "Azure Key Vault", "type": "key_vault", "category": "security"},
        "keyvault": {"name": "Azure Key Vault", "type": "key_vault", "category": "security"},
        "function": {"name": "Azure Functions", "type": "functions", "category": "compute"},
        "functions": {"name": "Azure Functions", "type": "functions", "category": "compute"},
        "cosmos": {"name": "Azure Cosmos DB", "type": "cosmos_db", "category": "data"},
        "cosmosdb": {"name": "Azure Cosmos DB", "type": "cosmos_db", "category": "data"},
        "service bus": {"name": "Azure Service Bus", "type": "service_bus", "category": "integration"},
        "servicebus": {"name": "Azure Service Bus", "type": "service_bus", "category": "integration"},
        "event hub": {"name": "Azure Event Hubs", "type": "event_hubs", "category": "integration"},
        "eventhub": {"name": "Azure Event Hubs", "type": "event_hubs", "category": "integration"},
        "sql": {"name": "Azure SQL Database", "type": "sql_database", "category": "data"},
        "sql database": {"name": "Azure SQL Database", "type": "sql_database", "category": "data"},
        "storage": {"name": "Azure Storage Account", "type": "storage_account", "category": "storage"},
        "blob": {"name": "Azure Blob Storage", "type": "blob_storage", "category": "storage"},
        "api management": {"name": "Azure API Management", "type": "apim", "category": "integration"},
        "apim": {"name": "Azure API Management", "type": "apim", "category": "integration"},
        "load balancer": {"name": "Azure Load Balancer", "type": "load_balancer", "category": "networking"},
        "app gateway": {"name": "Application Gateway", "type": "app_gateway", "category": "networking"},
        "application gateway": {"name": "Application Gateway", "type": "app_gateway", "category": "networking"},
        "aks": {"name": "Azure Kubernetes Service", "type": "aks", "category": "compute"},
        "kubernetes": {"name": "Azure Kubernetes Service", "type": "aks", "category": "compute"},
        "container apps": {"name": "Azure Container Apps", "type": "container_apps", "category": "compute"},
        "logic apps": {"name": "Azure Logic Apps", "type": "logic_apps", "category": "integration"},
        "openai": {"name": "Azure OpenAI", "type": "openai", "category": "ai"},
        "cognitive": {"name": "Azure Cognitive Services", "type": "cognitive_services", "category": "ai"},
    }
    
    # Check for action keywords
    add_keywords = ["add", "include", "create", "insert", "need", "want", "put", "place"]
    remove_keywords = ["remove", "delete", "drop", "eliminate", "get rid", "take out"]
    connect_keywords = ["connect", "link", "attach", "wire", "integrate", "route"]
    
    is_add = any(kw in prompt_lower for kw in add_keywords)
    is_remove = any(kw in prompt_lower for kw in remove_keywords)
    is_connect = any(kw in prompt_lower for kw in connect_keywords)
    
    # Get existing services for reference
    existing_services = [s.get("name", "") for s in architecture.get("services", []) if isinstance(s, dict)]
    existing_services_lower = {s.lower(): s for s in existing_services}
    
    # Find mentioned services
    services_to_add = []
    for pattern, svc_info in service_patterns.items():
        if pattern in prompt_lower:
            if is_remove:
                result["services_to_remove"].append(svc_info["name"])
            elif is_add or not is_connect:
                # Don't add if already exists
                if svc_info["name"] not in existing_services:
                    services_to_add.append(svc_info)
    
    result["services_to_add"] = services_to_add
    
    # Handle "between X and Y" pattern for cache/intermediary services
    import re
    between_match = re.search(r'between\s+(.+?)\s+and\s+(.+?)(?:\s|$|\.)', prompt_lower)
    if between_match and services_to_add:
        source_hint = between_match.group(1).strip()
        target_hint = between_match.group(2).strip()
        
        # Find matching existing services
        source_svc = None
        target_svc = None
        for svc_name in existing_services:
            svc_lower = svc_name.lower()
            if source_hint in svc_lower or svc_lower in source_hint:
                source_svc = svc_name
            if target_hint in svc_lower or svc_lower in target_hint:
                target_svc = svc_name
        
        # Add connections through the new service
        if source_svc and target_svc and services_to_add:
            new_svc = services_to_add[0]["name"]
            result["connections_to_add"].append({
                "from": source_svc,
                "to": new_svc,
                "type": "https",
                "label": "Data"
            })
            result["connections_to_add"].append({
                "from": new_svc,
                "to": target_svc,
                "type": "https",
                "label": "Data"
            })
            # Remove direct connection if exists
            result["connections_to_remove"].append({
                "from": source_svc,
                "to": target_svc
            })
    
    # Handle explicit connection requests
    if is_connect and "to" in prompt_lower:
        # Try to extract "connect X to Y" pattern
        connect_match = re.search(r'connect\s+(.+?)\s+to\s+(.+?)(?:\s|$|\.)', prompt_lower)
        if connect_match:
            source_hint = connect_match.group(1).strip()
            target_hint = connect_match.group(2).strip()
            
            source_svc = None
            target_svc = None
            
            # Match against existing services
            for svc_name in existing_services:
                svc_lower = svc_name.lower()
                if source_hint in svc_lower or svc_lower in source_hint:
                    source_svc = svc_name
                if target_hint in svc_lower or svc_lower in target_hint:
                    target_svc = svc_name
            
            # Also check newly added services
            for svc in services_to_add:
                svc_lower = svc["name"].lower()
                if source_hint in svc_lower or svc_lower in source_hint:
                    source_svc = svc["name"]
                if target_hint in svc_lower or svc_lower in target_hint:
                    target_svc = svc["name"]
            
            if source_svc and target_svc:
                result["connections_to_add"].append({
                    "from": source_svc,
                    "to": target_svc,
                    "type": "https",
                    "label": "Integration"
                })
    
    # Auto-connect new services based on category
    if services_to_add and not result["connections_to_add"]:
        for new_svc in services_to_add:
            category = new_svc.get("category", "compute")
            svc_type = new_svc.get("type", "")
            
            # Find appropriate services to connect to
            compute_services = [s for s in existing_services if any(k in s.lower() for k in ["app", "function", "aks", "container", "service"])]
            data_services = [s for s in existing_services if any(k in s.lower() for k in ["sql", "cosmos", "database", "storage", "redis"])]
            
            if category == "data" and compute_services:
                # Connect from compute to data service
                result["connections_to_add"].append({
                    "from": compute_services[0],
                    "to": new_svc["name"],
                    "type": "private_endpoint" if "sql" in svc_type or "cosmos" in svc_type else "https",
                    "label": "Data Access"
                })
            elif category == "monitoring" and compute_services:
                # Connect compute services to monitoring
                for compute_svc in compute_services[:2]:  # Connect first 2
                    result["connections_to_add"].append({
                        "from": compute_svc,
                        "to": new_svc["name"],
                        "type": "https",
                        "label": "Telemetry"
                    })
            elif category == "security" and compute_services:
                # Connect all compute services to Key Vault
                for compute_svc in compute_services:
                    result["connections_to_add"].append({
                        "from": compute_svc,
                        "to": new_svc["name"],
                        "type": "private_endpoint",
                        "label": "Secrets"
                    })
            elif category == "networking" and compute_services:
                # Front-facing services connect TO compute
                result["connections_to_add"].append({
                    "from": new_svc["name"],
                    "to": compute_services[0],
                    "type": "https",
                    "label": "Traffic"
                })
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=api_config.HOST, port=api_config.PORT)