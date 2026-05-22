"""
Diagram Modification Agent — Comprehensive Rewrite
Handles post-generation modifications to Draw.io architecture diagrams.
Supports 3 strategies: Direct XML editing, Architecture Regeneration, and Hybrid.
Includes a full validation pipeline (connection 8-check, WAF, requirements, XML structure).
Features: container-aware placement, few-shot intent parsing, 45+ thinking steps,
          error/warning classification, self-reflection, inter-agent messaging.
"""

import xml.etree.ElementTree as ET
import json
import re
import os
import logging
import copy
import time
from enum import Enum
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from config import azure_openai_config, SERVICE_LAYERS
from agents import BaseAgent, ConnectionExpertAgent
from drawio_parser import DrawioParser, generate_drawio_from_architecture

logger = logging.getLogger(__name__)


class ModificationStrategy(str, Enum):
    DIRECT_XML = "direct_xml"
    ARCHITECTURE_REGENERATION = "architecture_regeneration"
    HYBRID = "hybrid"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_TO_SUBNET_KEYWORDS: Dict[str, List[str]] = {
    "data":        ["data", "database", "sql", "redis", "storage", "db"],
    "compute":     ["backend", "compute", "app", "function", "web"],
    "networking":  ["frontend", "web", "ingress", "gateway", "dmz"],
    "integration": ["integration", "apim", "api", "messaging", "bus"],
    "ai":          ["ai", "ml", "cognitive", "openai"],
    "security":    ["security", "identity", "keyvault"],
    "monitoring":  ["monitoring", "observability", "log", "insights"],
    "storage":     ["data", "storage", "blob", "lake"],
}

EDGE_SERVICE_KEYWORDS: List[str] = [
    "front door", "cdn", "waf", "web application firewall",
    "traffic manager", "ddos", "users", "user", "client", "internet",
]

FEW_SHOT_MODIFICATION_EXAMPLES = """
EXAMPLES:

User: "Add Redis cache between App Service and SQL Database"
Response:
{
  "action": "add",
  "confidence": 0.95,
  "ambiguity_notes": "",
  "services_to_add": [{"name": "Azure Cache for Redis", "type": "redis", "category": "data", "resource_group": "", "subnet": ""}],
  "services_to_remove": [],
  "connections_to_add": [
    {"from": "Azure App Service", "to": "Azure Cache for Redis", "type": "private_endpoint", "label": "Cache reads/writes"},
    {"from": "Azure Cache for Redis", "to": "Azure SQL Database", "type": "private_endpoint", "label": "Cache miss fallback"}
  ],
  "connections_to_remove": [],
  "explanation": "Adding Redis as a caching layer between compute and database tiers"
}

User: "Remove the CDN"
Response:
{
  "action": "remove",
  "confidence": 0.90,
  "ambiguity_notes": "",
  "services_to_add": [],
  "services_to_remove": ["Azure CDN"],
  "connections_to_add": [],
  "connections_to_remove": [],
  "explanation": "Removing CDN service and all its connections"
}

User: "Add monitoring with Application Insights and Log Analytics"
Response:
{
  "action": "add",
  "confidence": 0.92,
  "ambiguity_notes": "",
  "services_to_add": [
    {"name": "Application Insights", "type": "appinsights", "category": "monitoring", "resource_group": "", "subnet": ""},
    {"name": "Azure Log Analytics", "type": "loganalytics", "category": "monitoring", "resource_group": "", "subnet": ""}
  ],
  "services_to_remove": [],
  "connections_to_add": [
    {"from": "Azure App Service", "to": "Application Insights", "type": "https", "label": "Telemetry"},
    {"from": "Application Insights", "to": "Azure Log Analytics", "type": "https", "label": "Log sink"}
  ],
  "connections_to_remove": [],
  "explanation": "Adding monitoring stack with Application Insights feeding into Log Analytics"
}

User: "Connect Key Vault to App Service and Functions"
Response:
{
  "action": "connect",
  "confidence": 0.95,
  "ambiguity_notes": "",
  "services_to_add": [],
  "services_to_remove": [],
  "connections_to_add": [
    {"from": "Azure App Service", "to": "Azure Key Vault", "type": "private_endpoint", "label": "Secrets"},
    {"from": "Azure Functions", "to": "Azure Key Vault", "type": "private_endpoint", "label": "Secrets"}
  ],
  "connections_to_remove": [],
  "explanation": "Creating secure connections from compute services to Key Vault for secret management"
}
"""

LAYER_KEYWORDS: Dict[int, List[str]] = {
    0: ["front door", "cdn", "traffic manager", "waf", "users", "client", "ddos", "internet"],
    1: ["gateway", "firewall", "load balancer", "api management", "apim"],
    2: ["app service", "function", "aks", "kubernetes", "container", "service bus",
        "event hub", "event grid", "logic app"],
    3: ["sql", "cosmos", "database", "redis", "storage", "blob", "data lake",
        "postgresql", "mysql"],
    -1: ["key vault", "monitor", "insights", "entra", "defender", "sentinel",
         "log analytics", "active directory"],
}


class DiagramModificationAgent(BaseAgent):
    """Agent that modifies existing Draw.io architecture diagrams based on user requests.

    Supports three strategies:
      - direct_xml: Parse and surgically edit the XML, preserving layout.
      - architecture_regeneration: Modify the architecture JSON and regenerate the full diagram.
      - hybrid (default): Auto-select based on multi-factor complexity scoring.

    Features:
      - Container-aware placement (RG -> VNet -> Subnet hierarchy)
      - Few-shot intent parsing with confidence scoring
      - 8-check validation pipeline with error/warning classification
      - 45+ reasoning steps for full transparency
      - Self-reflection and inter-agent messaging
    """

    def __init__(self, openai_client: Optional[Any] = None):
        super().__init__(
            name="DiagramModificationAgent",
            openai_client=openai_client,
            agent_type="modification",
        )
        self._parser = DrawioParser()

    # ==================================================================
    # PUBLIC ENTRY POINT
    # ==================================================================
    async def analyze(self, requirements: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point.

        Context keys:
          - current_architecture: dict with services, connections, containers
          - current_xml: str (existing Draw.io XML)
          - modification_request: str (user prompt)
          - strategy: str (direct_xml | architecture_regeneration | hybrid)
          - original_requirements: str (for validation)
        """
        self.status = self.status.__class__("working")
        start = time.time()

        modification_request = context.get("modification_request", requirements)
        strategy_name = context.get("strategy", "hybrid")
        current_xml = context.get("current_xml", "")
        current_arch = context.get("current_architecture", {})
        original_reqs = context.get("original_requirements", "")

        # --- Thinking: receive & classify ---
        self.think(
            f"Received modification request: \"{modification_request[:150]}\"",
            "reasoning",
        )
        self.think(
            f"Current architecture: {len(current_arch.get('services', []))} services, "
            f"{len(current_arch.get('connections', []))} connections, "
            f"{len(current_arch.get('containers', []))} containers",
            "observation",
        )
        self.think(f"User-selected strategy: {strategy_name}", "decision")

        # 1. Parse user intent via LLM (container-aware, few-shot)
        self.think("Phase 1: Parsing modification intent with container-aware LLM prompt...", "reasoning")
        intent = await self._parse_intent(modification_request, current_arch)

        action = intent.get("action", "add")
        confidence = intent.get("confidence", 1.0)
        adds = len(intent.get("services_to_add", []))
        removes = len(intent.get("services_to_remove", []))
        conn_adds = len(intent.get("connections_to_add", []))
        conn_removes = len(intent.get("connections_to_remove", []))

        self.think(
            f"Intent parsed: action={action}, confidence={confidence:.2f}, "
            f"+{adds} services, -{removes} services, "
            f"+{conn_adds} connections, -{conn_removes} connections",
            "observation",
        )

        if confidence < 0.5:
            self.think(
                f"LOW CONFIDENCE ({confidence:.2f}): {intent.get('ambiguity_notes', 'Unclear request')}. "
                "Proceeding with best-effort interpretation.",
                "warning",
            )

        # 2. Snapshot old architecture for diff
        old_arch = copy.deepcopy(current_arch)

        # 3. Route to strategy
        try:
            strategy = ModificationStrategy(strategy_name)
        except ValueError:
            strategy = ModificationStrategy.HYBRID
            self.think(f"Unknown strategy '{strategy_name}', defaulting to hybrid.", "warning")

        self.think(f"Phase 2: Executing {strategy.value} strategy...", "reasoning")

        try:
            if strategy == ModificationStrategy.DIRECT_XML:
                result = await self._execute_direct_xml(intent, current_xml, current_arch)
            elif strategy == ModificationStrategy.ARCHITECTURE_REGENERATION:
                result = await self._execute_regeneration(
                    intent, current_arch, original_reqs or modification_request
                )
            else:
                result = await self._execute_hybrid(
                    intent, current_xml, current_arch, original_reqs or modification_request
                )
        except ET.ParseError as e:
            self.think(f"XML parse error during execution: {e}", "warning")
            return {
                "success": False,
                "error": f"XML parse error: {e}",
                "status_hint": 422,
                "thinking_process": self._serialize_thoughts(),
            }
        except Exception as e:
            logger.exception("Modification agent execution failed")
            self.think(f"Execution failed: {e}", "warning")
            return {
                "success": False,
                "error": str(e),
                "status_hint": 500,
                "thinking_process": self._serialize_thoughts(),
            }

        updated_xml = result["xml"]
        updated_arch = result["architecture"]
        changes = result["changes"]
        strategy_used = result["strategy_used"]

        # 4. Validation pipeline
        self.think("Phase 3: Running 4-check validation pipeline...", "tool_call")
        validation = await self._run_validation_pipeline(
            updated_arch, updated_xml, original_reqs or modification_request
        )

        conn_val = validation.get("connection_validation", {})
        waf = validation.get("waf_scores", {})
        reqs_val = validation.get("requirements_fulfillment", {})
        xml_val = validation.get("xml_validation", {})

        waf_avg = (
            sum(waf.values()) / max(len(waf), 1) if waf else 0
        )
        self.think(
            f"Validation complete: "
            f"connections={conn_val.get('error_count', 0)} errors / {conn_val.get('warning_count', 0)} warnings, "
            f"WAF avg={waf_avg:.0f}, "
            f"requirements={reqs_val.get('score', 0)}%, "
            f"XML={'valid' if xml_val.get('valid', False) else 'INVALID'}",
            "observation",
        )

        # 5. Compute diff
        diff = self._compute_diff(old_arch, updated_arch)
        self.think(
            f"Diff: +{len(diff.get('services_added', []))} services, "
            f"-{len(diff.get('services_removed', []))} services, "
            f"+{len(diff.get('connections_added', []))} connections, "
            f"-{len(diff.get('connections_removed', []))} connections",
            "observation",
        )

        # 6. Self-reflection
        self.think("Phase 4: Reflecting on modification quality...", "reflection")
        reflection = self.reflect(
            {"services": updated_arch.get("services", []),
             "connections": updated_arch.get("connections", [])},
            criteria=["completeness", "correctness", "container_placement", "connection_coverage"],
        )
        if reflection.get("improvements_suggested"):
            for suggestion in reflection["improvements_suggested"]:
                self.think(f"Reflection concern: {suggestion}", "reflection")

        # 7. Inter-agent messaging
        error_count = conn_val.get("error_count", 0)
        warning_count = conn_val.get("warning_count", 0)
        if error_count > 0:
            self.send_message(
                "ValidationAgent", "warning",
                f"Modification produced {error_count} connection errors that may need review",
            )
        self.send_message(
            "ReviewAgent", "insight",
            f"Modification complete: strategy={strategy_used}, changes={len(changes)}, "
            f"errors={error_count}, warnings={warning_count}",
        )

        elapsed = round(time.time() - start, 2)
        self.think(f"Modification complete in {elapsed}s using {strategy_used} strategy.", "success")

        self.status = self.status.__class__("completed")
        return {
            "success": True,
            "strategy_used": strategy_used,
            "updated_xml": updated_xml,
            "updated_architecture": updated_arch,
            "changes_applied": changes,
            "validation_results": validation,
            "thinking_process": self._serialize_thoughts(),
            "diff_summary": diff,
            "timestamp": datetime.now().isoformat(),
        }

    # ==================================================================
    # INTENT PARSING (container-aware, few-shot, confidence)
    # ==================================================================
    async def _parse_intent(self, prompt: str, architecture: Dict) -> Dict:
        """Parse user modification request into structured intent using LLM."""
        existing_services = [
            s.get("name") for s in architecture.get("services", []) if isinstance(s, dict)
        ]
        existing_connections = architecture.get("connections", [])
        containers = architecture.get("containers", [])

        # Build container summary for the LLM
        rg_names = list({
            c.get("name", "") for c in containers
            if c.get("type") in ("resource_group", "rg")
        })
        subnet_names = list({
            c.get("name", "") for c in containers
            if c.get("type") == "subnet"
        })

        self.think(
            f"Building container-aware prompt: {len(rg_names)} RGs, {len(subnet_names)} subnets, "
            f"{len(existing_services)} existing services",
            "tool_call",
        )

        container_summary = {
            "resource_groups": rg_names,
            "subnets": subnet_names,
        }

        system_prompt = f"""You are an Azure architecture modification specialist.
Analyze the user's request and return a JSON object describing what to change.

RULES:
- Use EXACT service names from the current architecture when referencing existing services.
- For new services, use canonical Azure naming (e.g., "Azure Cache for Redis", "Azure Key Vault").
- Categories: compute, data, networking, security, monitoring, integration, ai, storage.
- Connection types: https, private_endpoint, queue, event, vnet_peering.
- Assign resource_group and subnet fields to new services. Use empty string "" if unsure.
- Set confidence (0.0-1.0) based on how clearly you understand the request.
- Set ambiguity_notes if the request could be interpreted multiple ways.

CURRENT CONTAINER HIERARCHY:
{json.dumps(container_summary, indent=2)}

{FEW_SHOT_MODIFICATION_EXAMPLES}

Respond with JSON ONLY (no markdown, no code fences, no explanation text)."""

        user_prompt = f"""User Request: "{prompt}"

Current Services: {json.dumps(existing_services)}
Current Connections (first 20): {json.dumps(existing_connections[:20])}

Return JSON:
{{
    "action": "add"|"remove"|"modify"|"connect"|"disconnect",
    "confidence": 0.0-1.0,
    "ambiguity_notes": "",
    "services_to_add": [{{"name":"...", "type":"...", "category":"...", "resource_group":"...", "subnet":"..."}}],
    "services_to_remove": ["Exact Service Name"],
    "connections_to_add": [{{"from":"Source Name","to":"Target Name","type":"https","label":"..."}}],
    "connections_to_remove": [{{"from":"Source Name","to":"Target Name"}}],
    "explanation": "Brief description of changes"
}}"""

        self.think("Calling LLM for intent parsing with few-shot examples...", "tool_call")

        try:
            resp = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.15,
                max_tokens=2000,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            intent = json.loads(raw)

            self.think(
                f"LLM intent parsed: action={intent.get('action')}, "
                f"confidence={intent.get('confidence', 'N/A')}, "
                f"explanation: {intent.get('explanation', '')[:100]}",
                "observation",
            )

            # Validate and normalize
            for svc in intent.get("services_to_add", []):
                svc.setdefault("resource_group", "")
                svc.setdefault("subnet", "")
                svc.setdefault("category", "compute")
                svc.setdefault("type", "generic")

            intent.setdefault("confidence", 0.8)
            intent.setdefault("ambiguity_notes", "")

            if intent.get("ambiguity_notes"):
                self.think(f"Ambiguity detected: {intent['ambiguity_notes']}", "warning")

            return intent

        except json.JSONDecodeError as e:
            self.think(f"JSON parse error from LLM response: {e}. Using keyword fallback.", "warning")
            return self._keyword_fallback(prompt)
        except Exception as e:
            self.think(f"Intent parsing LLM call failed: {e}. Using keyword fallback.", "warning")
            return self._keyword_fallback(prompt)

    def _keyword_fallback(self, prompt: str) -> Dict:
        """Simple keyword-based fallback when LLM is unavailable."""
        prompt_lower = prompt.lower()
        result: Dict[str, Any] = {
            "action": "add",
            "confidence": 0.4,
            "ambiguity_notes": "Used keyword fallback — LLM was unavailable",
            "services_to_add": [],
            "services_to_remove": [],
            "connections_to_add": [],
            "connections_to_remove": [],
            "explanation": prompt,
        }
        patterns = {
            "redis": {"name": "Azure Cache for Redis", "type": "redis", "category": "data",
                       "resource_group": "", "subnet": ""},
            "cache": {"name": "Azure Cache for Redis", "type": "redis", "category": "data",
                       "resource_group": "", "subnet": ""},
            "cdn": {"name": "Azure CDN", "type": "cdn", "category": "networking",
                     "resource_group": "", "subnet": ""},
            "key vault": {"name": "Azure Key Vault", "type": "keyvault", "category": "security",
                          "resource_group": "", "subnet": ""},
            "monitor": {"name": "Azure Monitor", "type": "monitor", "category": "monitoring",
                        "resource_group": "", "subnet": ""},
            "function": {"name": "Azure Functions", "type": "functions", "category": "compute",
                         "resource_group": "", "subnet": ""},
            "cosmos": {"name": "Azure Cosmos DB", "type": "cosmosdb", "category": "data",
                       "resource_group": "", "subnet": ""},
            "sql": {"name": "Azure SQL Database", "type": "sql", "category": "data",
                     "resource_group": "", "subnet": ""},
            "app insights": {"name": "Application Insights", "type": "appinsights",
                             "category": "monitoring", "resource_group": "", "subnet": ""},
            "log analytics": {"name": "Azure Log Analytics", "type": "loganalytics",
                              "category": "monitoring", "resource_group": "", "subnet": ""},
            "service bus": {"name": "Azure Service Bus", "type": "servicebus",
                            "category": "integration", "resource_group": "", "subnet": ""},
            "event hub": {"name": "Azure Event Hubs", "type": "eventhubs",
                          "category": "integration", "resource_group": "", "subnet": ""},
        }
        for kw, svc in patterns.items():
            if kw in prompt_lower:
                result["services_to_add"].append(svc)
                break

        # Detect remove action
        if any(w in prompt_lower for w in ["remove", "delete", "drop"]):
            result["action"] = "remove"

        return result

    # ==================================================================
    # XML HIERARCHY ANALYSIS
    # ==================================================================
    def _analyze_xml_hierarchy(self, graph_root: ET.Element) -> Dict[str, Any]:
        """Scan existing XML cells and build a complete container hierarchy map.

        Returns a structure documenting all RGs, VNets, Subnets, Services and
        their parent-child relationships, bounding boxes, and labels.
        """
        self.think(
            "Scanning XML cells to discover container hierarchy (RG -> VNet -> Subnet -> Service)...",
            "tool_call",
        )

        hierarchy: Dict[str, Any] = {
            "subscription_id": "2",
            "resource_groups": {},
            "edge_services": [],
            "service_to_container": {},
            "name_to_cell": {},
        }

        # Index all cells
        cells = {}
        for cell in graph_root.findall("mxCell"):
            cid = cell.get("id", "")
            cells[cid] = cell

        # Classify cells by ID pattern
        rg_cells = {}     # rg-* -> cell
        vnet_cells = {}   # vnet-* -> cell
        sn_cells = {}     # sn-* -> cell
        svc_cells = {}    # svc-* (not -label) -> cell
        label_cells = {}  # *-label -> cell

        for cid, cell in cells.items():
            if cid.startswith("rg-") and not cid.endswith("-label"):
                rg_cells[cid] = cell
            elif cid.startswith("vnet-") and not cid.endswith("-label"):
                vnet_cells[cid] = cell
            elif cid.startswith("sn-") and not cid.endswith("-label"):
                sn_cells[cid] = cell
            elif cid.startswith("svc-") and not cid.endswith("-label"):
                svc_cells[cid] = cell
            elif cid.endswith("-label"):
                label_cells[cid] = cell

        # Extract bounds helper
        def get_bounds(cell: ET.Element) -> Dict[str, float]:
            geom = cell.find("mxGeometry")
            if geom is None:
                return {"x": 0, "y": 0, "w": 400, "h": 300}
            return {
                "x": float(geom.get("x", "0")),
                "y": float(geom.get("y", "0")),
                "w": float(geom.get("width", "400")),
                "h": float(geom.get("height", "300")),
            }

        # Get label for a cell (check both cell value and companion *-label cell)
        def get_label(cell_id: str) -> str:
            # Check direct value
            cell = cells.get(cell_id)
            if cell is not None:
                val = (cell.get("value") or "").strip()
                if val:
                    return val
            # Check companion label cell
            lbl = label_cells.get(f"{cell_id}-label")
            if lbl is not None:
                return (lbl.get("value") or "").strip()
            return ""

        # Build RG -> VNet -> Subnet -> Service hierarchy
        for rg_id, rg_cell in rg_cells.items():
            rg_label = get_label(rg_id)
            rg_entry = {
                "cell_id": rg_id,
                "label": rg_label,
                "vnets": {},
                "loose_services": [],
                "bounds": get_bounds(rg_cell),
            }
            hierarchy["resource_groups"][rg_id] = rg_entry

        for vnet_id, vnet_cell in vnet_cells.items():
            parent = vnet_cell.get("parent", "")
            vnet_label = get_label(vnet_id)
            vnet_entry = {
                "cell_id": vnet_id,
                "label": vnet_label,
                "subnets": {},
                "bounds": get_bounds(vnet_cell),
            }
            # Find parent RG
            if parent in hierarchy["resource_groups"]:
                hierarchy["resource_groups"][parent]["vnets"][vnet_id] = vnet_entry

        for sn_id, sn_cell in sn_cells.items():
            parent = sn_cell.get("parent", "")
            sn_label = get_label(sn_id)
            # Derive purpose keywords from label
            purpose_keywords = [
                w.lower() for w in re.split(r"[\s\-_/]+", sn_label)
                if len(w) > 2
            ]
            sn_entry = {
                "cell_id": sn_id,
                "label": sn_label,
                "purpose_keywords": purpose_keywords,
                "services": [],
                "bounds": get_bounds(sn_cell),
            }
            # Find parent VNet (search all RGs)
            placed = False
            for rg_data in hierarchy["resource_groups"].values():
                if parent in rg_data["vnets"]:
                    rg_data["vnets"][parent]["subnets"][sn_id] = sn_entry
                    placed = True
                    break
            if not placed:
                # Orphan subnet — try to attach to first RG with matching VNet
                for rg_data in hierarchy["resource_groups"].values():
                    for vnet_data in rg_data["vnets"].values():
                        if parent == vnet_data["cell_id"]:
                            vnet_data["subnets"][sn_id] = sn_entry
                            placed = True
                            break
                    if placed:
                        break

        # Place services in their containers
        for svc_id, svc_cell in svc_cells.items():
            parent = svc_cell.get("parent", "")
            svc_label = get_label(svc_id)

            hierarchy["name_to_cell"][svc_label.lower()] = svc_id
            hierarchy["service_to_container"][svc_id] = parent

            # Classify: edge (parent="2") or inside container
            if parent == "2" or parent == hierarchy["subscription_id"]:
                hierarchy["edge_services"].append(svc_id)
            else:
                # Find the subnet container
                placed = False
                for rg_data in hierarchy["resource_groups"].values():
                    for vnet_data in rg_data["vnets"].values():
                        if parent in vnet_data["subnets"]:
                            vnet_data["subnets"][parent]["services"].append(svc_id)
                            placed = True
                            break
                    if placed:
                        break
                    # Maybe parented directly to RG (loose service)
                    if parent == rg_data["cell_id"]:
                        rg_data["loose_services"].append(svc_id)
                        placed = True
                        break

        total_rgs = len(hierarchy["resource_groups"])
        total_vnets = sum(
            len(rg["vnets"]) for rg in hierarchy["resource_groups"].values()
        )
        total_subnets = sum(
            len(vn["subnets"])
            for rg in hierarchy["resource_groups"].values()
            for vn in rg["vnets"].values()
        )
        total_svcs = len(svc_cells)

        self.think(
            f"Discovered {total_rgs} RGs, {total_vnets} VNets, {total_subnets} subnets, "
            f"{total_svcs} services ({len(hierarchy['edge_services'])} edge)",
            "observation",
        )
        self.think(
            f"Container map: RGs={list(hierarchy['resource_groups'].keys())}, "
            f"service names={list(hierarchy['name_to_cell'].keys())[:8]}...",
            "observation",
        )

        return hierarchy

    # ==================================================================
    # PARENT RESOLUTION
    # ==================================================================
    def _resolve_parent_for_service(
        self, service: Dict[str, Any], hierarchy: Dict[str, Any]
    ) -> Tuple[str, Tuple[int, int]]:
        """Resolve correct parent cell ID and relative position for a new service.

        Priority: explicit subnet > explicit RG > edge detection > category matching > fallback.
        """
        svc_name = service.get("name", "")
        category = service.get("category", "compute")
        rg_hint = service.get("resource_group", "")
        subnet_hint = service.get("subnet", "")
        name_lower = svc_name.lower()

        self.think(
            f"Resolving parent for '{svc_name}' (category={category}, rg_hint='{rg_hint}', subnet_hint='{subnet_hint}')",
            "reasoning",
        )

        # Helper: compute grid position inside a subnet
        def grid_pos(sn_data: Dict, service_count: int) -> Tuple[int, int]:
            bounds = sn_data.get("bounds", {"x": 0, "y": 0, "w": 400, "h": 300})
            pad_x, pad_y = 30, 50
            h_gap, v_gap = 160, 120
            n = service_count
            col = n % 4
            row = n // 4
            x = pad_x + col * h_gap
            y = pad_y + row * v_gap
            return (int(x), int(y))

        # 1. Try explicit subnet match
        if subnet_hint:
            for rg_data in hierarchy["resource_groups"].values():
                for vnet_data in rg_data["vnets"].values():
                    for sn_id, sn_data in vnet_data["subnets"].items():
                        label_lower = sn_data["label"].lower()
                        if subnet_hint.lower() in label_lower or label_lower in subnet_hint.lower():
                            pos = grid_pos(sn_data, len(sn_data["services"]))
                            self.think(
                                f"  -> Matched subnet '{sn_data['label']}' (cell {sn_id}) by explicit hint",
                                "decision",
                            )
                            return sn_id, pos

        # 2. Try explicit RG match -> search best subnet by category
        if rg_hint:
            for rg_id, rg_data in hierarchy["resource_groups"].items():
                rg_label_lower = rg_data["label"].lower()
                if rg_hint.lower() in rg_label_lower or rg_label_lower in rg_hint.lower():
                    best_sn = self._find_best_subnet_in_rg(rg_data, category)
                    if best_sn:
                        sn_data = None
                        for vn in rg_data["vnets"].values():
                            if best_sn in vn["subnets"]:
                                sn_data = vn["subnets"][best_sn]
                                break
                        if sn_data:
                            pos = grid_pos(sn_data, len(sn_data["services"]))
                            self.think(
                                f"  -> Matched RG '{rg_data['label']}', best subnet '{best_sn}' for category={category}",
                                "decision",
                            )
                            return best_sn, pos
                    # No matching subnet — place loose in RG
                    bounds = rg_data["bounds"]
                    loose_count = len(rg_data["loose_services"])
                    x = int(bounds["x"]) + 30 + (loose_count % 4) * 160
                    y = int(bounds["y"]) + int(bounds["h"]) - 140
                    self.think(
                        f"  -> Matched RG '{rg_data['label']}' but no suitable subnet; placing loose",
                        "decision",
                    )
                    return rg_id, (x, y)

        # 3. Edge service check
        if any(kw in name_lower for kw in EDGE_SERVICE_KEYWORDS):
            sub_id = hierarchy.get("subscription_id", "2")
            # Place edge services at the top
            edge_count = len(hierarchy.get("edge_services", []))
            x = 80 + edge_count * 180
            y = 40
            self.think(f"  -> Edge service detected, placing at subscription level (id={sub_id})", "decision")
            return sub_id, (x, y)

        # 4. Category-based search across all subnets
        keywords = CATEGORY_TO_SUBNET_KEYWORDS.get(category, [])
        if keywords:
            for rg_data in hierarchy["resource_groups"].values():
                for vnet_data in rg_data["vnets"].values():
                    for sn_id, sn_data in vnet_data["subnets"].items():
                        purpose = " ".join(sn_data.get("purpose_keywords", []))
                        sn_label = sn_data["label"].lower()
                        combined = purpose + " " + sn_label
                        if any(kw in combined for kw in keywords):
                            pos = grid_pos(sn_data, len(sn_data["services"]))
                            self.think(
                                f"  -> Category match: '{sn_data['label']}' (cell {sn_id}) for category={category}",
                                "decision",
                            )
                            return sn_id, pos

        # 5. Fallback: first RG's first VNet's first subnet, or first RG, or subscription
        for rg_id, rg_data in hierarchy["resource_groups"].items():
            for vnet_data in rg_data["vnets"].values():
                for sn_id, sn_data in vnet_data["subnets"].items():
                    pos = grid_pos(sn_data, len(sn_data["services"]))
                    self.think(
                        f"  -> Fallback: using first subnet '{sn_data['label']}' (cell {sn_id})",
                        "decision",
                    )
                    return sn_id, pos
            # RG exists but no subnets
            bounds = rg_data["bounds"]
            self.think(f"  -> Fallback: placing in RG '{rg_data['label']}' (cell {rg_id})", "decision")
            return rg_id, (int(bounds["x"]) + 30, int(bounds["y"]) + 50)

        # Ultimate fallback: subscription
        self.think("  -> No containers found. Placing at subscription level (id=2)", "warning")
        return "2", (100, 200)

    def _find_best_subnet_in_rg(self, rg_data: Dict, category: str) -> Optional[str]:
        """Find the best subnet in a RG for a given category."""
        keywords = CATEGORY_TO_SUBNET_KEYWORDS.get(category, [])
        for vnet_data in rg_data["vnets"].values():
            for sn_id, sn_data in vnet_data["subnets"].items():
                purpose = " ".join(sn_data.get("purpose_keywords", []))
                sn_label = sn_data["label"].lower()
                combined = purpose + " " + sn_label
                if any(kw in combined for kw in keywords):
                    return sn_id
        # Return first subnet as fallback
        for vnet_data in rg_data["vnets"].values():
            for sn_id in vnet_data["subnets"]:
                return sn_id
        return None

    def _auto_assign_container(
        self, category: str, containers: List[Dict]
    ) -> Tuple[str, str]:
        """Auto-assign resource_group and subnet for regeneration strategy."""
        keywords = CATEGORY_TO_SUBNET_KEYWORDS.get(category, [])
        subnets = [c for c in containers if c.get("type") == "subnet"]
        rgs = [c for c in containers if c.get("type") in ("resource_group", "rg")]

        # Try subnet match by purpose
        for sn in subnets:
            purpose = (sn.get("purpose", "") + " " + sn.get("name", "")).lower()
            if any(kw in purpose for kw in keywords):
                # Find the RG that owns this subnet
                for rg in rgs:
                    return rg["name"], sn["name"]

        # Monitoring/security -> dedicated RG
        if category in ("monitoring", "security"):
            for rg in rgs:
                if any(k in rg.get("name", "").lower() for k in ["monitor", "security", "observ", "mgmt"]):
                    return rg["name"], ""

        # Fallback: first RG
        if rgs:
            return rgs[0].get("name", ""), ""
        return "", ""

    # ==================================================================
    # STRATEGY: DIRECT XML (hierarchy-aware)
    # ==================================================================
    async def _execute_direct_xml(
        self, intent: Dict, current_xml: str, current_arch: Dict
    ) -> Dict:
        """Surgically edit the Draw.io XML preserving layout.

        Uses _analyze_xml_hierarchy() to discover containers and
        _resolve_parent_for_service() for correct parent assignment.
        """
        self.think("Strategy: Direct XML — parsing existing diagram cells...", "reasoning")
        self.think("Step 1: Parse XML tree and validate structure", "reasoning")

        # Keep backup for recovery
        xml_backup = current_xml

        try:
            tree = ET.ElementTree(ET.fromstring(current_xml))
        except ET.ParseError as e:
            self.think(f"XML parse error: {e}. Falling back to regeneration.", "warning")
            return await self._execute_regeneration(intent, current_arch, "")

        root_elem = tree.getroot()
        diagram = root_elem.find(".//diagram")
        model = diagram.find(".//mxGraphModel") if diagram is not None else None
        graph_root = model.find("root") if model is not None else None
        if graph_root is None:
            self.think("Could not locate <root> in XML. Falling back to regeneration.", "warning")
            return await self._execute_regeneration(intent, current_arch, "")

        # Step 2: Analyze hierarchy (CRITICAL NEW STEP)
        self.think("Step 2: Discovering container hierarchy from existing XML...", "tool_call")
        hierarchy = self._analyze_xml_hierarchy(graph_root)

        # Build cell index
        cell_map = {c.get("id"): c for c in graph_root.findall("mxCell")}
        name_to_id = self._build_name_index(cell_map)

        changes: List[str] = []
        services = list(current_arch.get("services", []))
        connections = list(current_arch.get("connections", []))
        next_id = self._next_cell_id(cell_map)

        # --- ADD SERVICES (with hierarchy-aware parent resolution) ---
        for svc in intent.get("services_to_add", []):
            svc_name = svc.get("name", "")
            if not svc_name:
                continue
            if any(s.get("name") == svc_name for s in services if isinstance(s, dict)):
                self.think(f"Service '{svc_name}' already exists — skipping", "observation")
                continue

            self.think(f"Step 3a: Adding service '{svc_name}' (category={svc.get('category', 'compute')})", "tool_call")

            # CRITICAL FIX: Resolve parent from hierarchy
            parent_id, rel_pos = self._resolve_parent_for_service(svc, hierarchy)

            icon_path = self._parser._get_azure_icon_path(svc_name)
            svc_id = f"svc-{next_id}"
            label_id = f"svc-{next_id}-label"
            next_id += 1

            # Icon cell with CORRECT parent
            icon_cell = ET.SubElement(graph_root, "mxCell")
            icon_cell.set("id", svc_id)
            icon_cell.set("value", "")
            icon_cell.set("style",
                          f"image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image={icon_path};")
            icon_cell.set("vertex", "1")
            icon_cell.set("parent", parent_id)
            geom = ET.SubElement(icon_cell, "mxGeometry")
            geom.set("x", str(rel_pos[0]))
            geom.set("y", str(rel_pos[1]))
            geom.set("width", "64")
            geom.set("height", "64")
            geom.set("as", "geometry")

            # Label cell with SAME parent
            lbl_cell = ET.SubElement(graph_root, "mxCell")
            lbl_cell.set("id", label_id)
            lbl_cell.set("value", svc_name)
            lbl_cell.set("style",
                         "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
                         "autosize=1;strokeColor=none;fillColor=none;")
            lbl_cell.set("vertex", "1")
            lbl_cell.set("parent", parent_id)
            lbl_geom = ET.SubElement(lbl_cell, "mxGeometry")
            lbl_geom.set("x", str(rel_pos[0] - 20))
            lbl_geom.set("y", str(rel_pos[1] + 66))
            lbl_geom.set("width", str(max(len(svc_name) * 8, 80)))
            lbl_geom.set("height", "30")
            lbl_geom.set("as", "geometry")

            services.append({
                "name": svc_name,
                "type": svc.get("type", "generic"),
                "category": svc.get("category", "compute"),
                "resource_group": svc.get("resource_group", ""),
                "subnet": svc.get("subnet", ""),
            })
            name_to_id[svc_name.lower()] = svc_id
            changes.append(f"Added {svc_name}")
            self.think(f"  Inserted '{svc_name}' into container '{parent_id}' at ({rel_pos[0]}, {rel_pos[1]})", "success")

        # --- REMOVE SERVICES ---
        for svc_name in intent.get("services_to_remove", []):
            matched_id = self._fuzzy_find_id(svc_name, name_to_id)
            if matched_id:
                self.think(f"Step 3b: Removing service '{svc_name}' (cell {matched_id})", "tool_call")
                self._remove_cell_and_edges(graph_root, matched_id, cell_map)
                self._remove_cell_and_edges(graph_root, f"{matched_id}-label", cell_map)
                services = [s for s in services if isinstance(s, dict) and s.get("name") != svc_name]
                connections = [c for c in connections
                               if c.get("source") != svc_name and c.get("target") != svc_name]
                changes.append(f"Removed {svc_name}")
                self.think(f"  Removed '{svc_name}' and all connected edges", "success")
            else:
                self.think(f"  Could not find '{svc_name}' in diagram — skipping removal", "warning")

        # --- ADD CONNECTIONS ---
        conn_id = next_id + 500
        for conn in intent.get("connections_to_add", []):
            src = conn.get("from", "")
            tgt = conn.get("to", "")
            src_id = self._fuzzy_find_id(src, name_to_id)
            tgt_id = self._fuzzy_find_id(tgt, name_to_id)

            if src_id and tgt_id:
                self.think(f"Step 3c: Connecting '{src}' -> '{tgt}'", "tool_call")
                edge = ET.SubElement(graph_root, "mxCell")
                edge.set("id", f"conn-{conn_id}")
                edge.set("value", "")
                edge.set("style",
                         "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
                         "jettySize=auto;html=1;")
                edge.set("edge", "1")
                edge.set("parent", "1")  # Connections always at canvas level
                edge.set("source", src_id)
                edge.set("target", tgt_id)
                geom = ET.SubElement(edge, "mxGeometry")
                geom.set("relative", "1")
                geom.set("as", "geometry")
                conn_id += 1
                connections.append({
                    "source": src, "target": tgt,
                    "type": conn.get("type", "https"),
                    "label": conn.get("label", ""),
                })
                changes.append(f"Connected {src} -> {tgt}")
            else:
                missing = []
                if not src_id:
                    missing.append(f"source '{src}'")
                if not tgt_id:
                    missing.append(f"target '{tgt}'")
                self.think(f"  Could not find {', '.join(missing)} for connection — skipping", "warning")

        # --- REMOVE CONNECTIONS ---
        for conn in intent.get("connections_to_remove", []):
            src = conn.get("from", "")
            tgt = conn.get("to", "")
            src_id = self._fuzzy_find_id(src, name_to_id)
            tgt_id = self._fuzzy_find_id(tgt, name_to_id)
            removed = False
            for cell in list(graph_root.findall("mxCell")):
                if cell.get("edge") == "1":
                    if cell.get("source") == src_id and cell.get("target") == tgt_id:
                        graph_root.remove(cell)
                        removed = True
            if removed:
                connections = [c for c in connections
                               if not (c.get("source") == src and c.get("target") == tgt)]
                changes.append(f"Disconnected {src} -> {tgt}")
                self.think(f"Step 3d: Disconnected '{src}' -> '{tgt}'", "tool_call")

        # Serialize
        self.think(f"Step 4: Serializing XML with {len(changes)} changes applied", "tool_call")
        updated_xml = ET.tostring(root_elem, encoding="unicode", xml_declaration=True)
        updated_arch = {**current_arch, "services": services, "connections": connections}

        # Validate the output XML
        if not self._validate_xml_structure(updated_xml):
            self.think("Direct XML produced invalid output. Recovering from backup and falling back.", "warning")
            return await self._execute_regeneration(intent, current_arch, "")

        self.think(f"Direct XML modification complete: {', '.join(changes)}", "success")
        return {
            "xml": updated_xml,
            "architecture": updated_arch,
            "changes": changes,
            "strategy_used": "direct_xml",
        }

    # ==================================================================
    # STRATEGY: ARCHITECTURE REGENERATION (container-preserving)
    # ==================================================================
    async def _execute_regeneration(
        self, intent: Dict, current_arch: Dict, requirements_str: str
    ) -> Dict:
        """Modify the architecture JSON and regenerate the full diagram.

        Preserves containers and assigns resource_group/subnet to new services.
        """
        self.think("Strategy: Architecture Regeneration — modifying architecture JSON...", "reasoning")

        services = list(current_arch.get("services", []))
        connections = list(current_arch.get("connections", []))
        containers = current_arch.get("containers", [])
        changes: List[str] = []

        # Add services (with container fields)
        for svc in intent.get("services_to_add", []):
            svc_name = svc.get("name", "")
            if svc_name and svc_name not in [s.get("name") for s in services if isinstance(s, dict)]:
                new_svc = {
                    "name": svc_name,
                    "type": svc.get("type", "generic"),
                    "category": svc.get("category", "compute"),
                    "resource_group": svc.get("resource_group", ""),
                    "subnet": svc.get("subnet", ""),
                }
                # Auto-assign container if not specified
                if not new_svc["resource_group"] and not new_svc["subnet"]:
                    rg, sn = self._auto_assign_container(new_svc["category"], containers)
                    new_svc["resource_group"] = rg
                    new_svc["subnet"] = sn
                    self.think(
                        f"Auto-assigned '{svc_name}' to RG='{rg}', subnet='{sn}'",
                        "decision",
                    )

                services.append(new_svc)
                changes.append(f"Added {svc_name}")
                self.think(f"Added service '{svc_name}' (category={new_svc['category']})", "tool_call")

        # Remove services
        for svc_name in intent.get("services_to_remove", []):
            original = len(services)
            services = [s for s in services if isinstance(s, dict) and s.get("name") != svc_name]
            connections = [c for c in connections
                           if c.get("source") != svc_name and c.get("target") != svc_name]
            if len(services) < original:
                changes.append(f"Removed {svc_name}")
                self.think(f"Removed service '{svc_name}' and its connections", "tool_call")

        # Add connections
        for conn in intent.get("connections_to_add", []):
            src, tgt = conn.get("from", ""), conn.get("to", "")
            if src and tgt and not any(
                c.get("source") == src and c.get("target") == tgt for c in connections
            ):
                connections.append({
                    "source": src, "target": tgt,
                    "type": conn.get("type", "https"),
                    "label": conn.get("label", ""),
                })
                changes.append(f"Connected {src} -> {tgt}")
                self.think(f"Added connection {src} -> {tgt}", "tool_call")

        # Remove connections
        for conn in intent.get("connections_to_remove", []):
            src, tgt = conn.get("from", ""), conn.get("to", "")
            original = len(connections)
            connections = [c for c in connections
                           if not (c.get("source") == src and c.get("target") == tgt)]
            if len(connections) < original:
                changes.append(f"Disconnected {src} -> {tgt}")
                self.think(f"Removed connection {src} -> {tgt}", "tool_call")

        # Preserve containers in updated architecture
        updated_arch = {
            **current_arch,
            "services": services,
            "connections": connections,
            "containers": containers,
        }

        # Run ConnectionExpertAgent for connection optimization
        self.think("Running ConnectionExpertAgent for connection optimization and auto-fix...", "tool_call")
        try:
            conn_agent = ConnectionExpertAgent()
            agent_ctx = {
                "architecture_analysis": {
                    "status": "completed",
                    "services": services,
                    "connections": connections,
                    "containers": containers,
                }
            }
            val_result = await conn_agent.analyze("", agent_ctx)
            if val_result.get("status") == "completed":
                enhanced = val_result.get("enhanced_architecture", {})
                updated_arch["services"] = enhanced.get("services", services)
                updated_arch["connections"] = enhanced.get("connections", connections)
                fixes = val_result.get("auto_fixes_applied", [])
                for fix in fixes:
                    changes.append(f"Auto-fix: {fix}")
                self.think(
                    f"ConnectionExpert applied {len(fixes)} auto-fixes, "
                    f"validated {len(updated_arch['connections'])} connections",
                    "observation",
                )
        except Exception as e:
            self.think(f"ConnectionExpert skipped: {e}", "warning")

        # Regenerate full diagram
        self.think("Regenerating full Draw.io diagram from updated architecture...", "tool_call")
        updated_xml = await generate_drawio_from_architecture(updated_arch, requirements_str)

        self.think(f"Regeneration complete with {len(changes)} changes", "success")
        return {
            "xml": updated_xml,
            "architecture": updated_arch,
            "changes": changes,
            "strategy_used": "architecture_regeneration",
        }

    # ==================================================================
    # STRATEGY: HYBRID (multi-factor complexity scoring)
    # ==================================================================
    async def _execute_hybrid(
        self, intent: Dict, current_xml: str, current_arch: Dict, requirements_str: str
    ) -> Dict:
        """Auto-select strategy based on multi-factor complexity scoring."""
        self.think("Strategy: Hybrid — evaluating modification complexity with multi-factor analysis...", "reasoning")

        total_changes = sum(
            len(intent.get(k, []))
            for k in ["services_to_add", "services_to_remove",
                       "connections_to_add", "connections_to_remove"]
        )
        action = intent.get("action", "add")
        is_structural = action in ("modify", "restructure", "replace")
        has_removes = len(intent.get("services_to_remove", [])) > 0
        adds_cross_rg = any(
            svc.get("resource_group", "") != ""
            for svc in intent.get("services_to_add", [])
        )
        confidence = intent.get("confidence", 1.0)

        # Multi-factor complexity score
        complexity = 0
        if total_changes > 4:
            complexity += 2
        if is_structural:
            complexity += 3
        if has_removes and total_changes > 2:
            complexity += 1
        if adds_cross_rg:
            complexity += 1
        if confidence < 0.7:
            complexity += 1

        self.think(
            f"Complexity analysis: changes={total_changes}, structural={is_structural}, "
            f"has_removes={has_removes}, cross_rg={adds_cross_rg}, confidence={confidence:.2f}, "
            f"score={complexity}",
            "reasoning",
        )

        if complexity <= 2 and current_xml:
            self.think(
                f"Low complexity (score={complexity}) — using Direct XML to preserve layout.",
                "decision",
            )
            result = await self._execute_direct_xml(intent, current_xml, current_arch)
            if not self._validate_xml_structure(result["xml"]):
                self.think("Direct XML produced invalid output. Falling back to regeneration.", "warning")
                return await self._execute_regeneration(intent, current_arch, requirements_str)
            return result
        else:
            self.think(
                f"High complexity (score={complexity}) — using full regeneration for accuracy.",
                "decision",
            )
            return await self._execute_regeneration(intent, current_arch, requirements_str)

    # ==================================================================
    # VALIDATION PIPELINE
    # ==================================================================
    async def _run_validation_pipeline(
        self, architecture: Dict, xml_str: str, requirements: str
    ) -> Dict:
        """Run all 4 validation checks."""
        self.think("Running validation check 1/4: Connection validation (8 checks)...", "tool_call")
        conn_val = await self._validate_connections(architecture)

        self.think("Running validation check 2/4: WAF pillar scoring...", "tool_call")
        waf = await self._score_waf_pillars(architecture)

        self.think("Running validation check 3/4: Requirements fulfillment...", "tool_call")
        reqs = await self._check_requirements(architecture, requirements)

        self.think("Running validation check 4/4: XML structure validation...", "tool_call")
        xml_val = self._validate_xml(xml_str)

        return {
            "connection_validation": conn_val,
            "waf_scores": waf,
            "requirements_fulfillment": reqs,
            "xml_validation": xml_val,
        }

    async def _validate_connections(self, arch: Dict) -> Dict:
        """Full 8-check connection validation with error/warning classification.

        Mirrors ConnectionExpertAgent patterns:
        ERRORS: missing source/target, self-references
        WARNINGS: duplicates, orphans, reverse flows, missing entry point, disconnected security
        """
        self.think("Validating connections: orphans, missing refs, self-refs, duplicates, reverse flows, security...", "tool_call")

        errors: List[Dict] = []
        warnings: List[Dict] = []
        services = arch.get("services", [])
        connections = arch.get("connections", [])
        service_names = {s.get("name") for s in services if isinstance(s, dict)}

        # 1. Missing source/target (ERROR)
        for c in connections:
            src = c.get("source", "")
            tgt = c.get("target", "")
            if src and src not in service_names:
                errors.append({
                    "type": "missing_source",
                    "message": f"Connection source '{src}' not found in services",
                    "severity": "error",
                    "auto_fix_available": False,
                })
            if tgt and tgt not in service_names:
                errors.append({
                    "type": "missing_target",
                    "message": f"Connection target '{tgt}' not found in services",
                    "severity": "error",
                    "auto_fix_available": False,
                })

        # 2. Self-references (ERROR)
        for c in connections:
            if c.get("source") and c.get("source") == c.get("target"):
                errors.append({
                    "type": "self_reference",
                    "message": f"Self-reference: '{c.get('source')}' connects to itself",
                    "severity": "error",
                    "auto_fix_available": True,
                    "suggested_fix": "remove",
                })

        # 3. Duplicates (WARNING)
        seen_pairs: set = set()
        for c in connections:
            pair = (c.get("source", ""), c.get("target", ""))
            if pair in seen_pairs:
                warnings.append({
                    "type": "duplicate_connection",
                    "message": f"Duplicate connection: {pair[0]} -> {pair[1]}",
                    "severity": "warning",
                    "auto_fix_available": True,
                })
            seen_pairs.add(pair)

        # 4. Orphan services (WARNING)
        connected: set = set()
        for c in connections:
            connected.add(c.get("source", ""))
            connected.add(c.get("target", ""))
        orphans = [
            n for n in service_names
            if n not in connected and n.lower() not in ("users", "user", "client")
        ]
        for orphan in orphans:
            warnings.append({
                "type": "orphan_service",
                "message": f"Orphan: '{orphan}' has no connections",
                "severity": "warning",
                "auto_fix_available": True,
            })

        # 5. Reverse flow detection (WARNING) using SERVICE_LAYERS
        for c in connections:
            src_layer = self._get_service_layer(c.get("source", ""))
            tgt_layer = self._get_service_layer(c.get("target", ""))
            if (src_layer != -1 and tgt_layer != -1
                    and src_layer > tgt_layer
                    and src_layer != 0 and tgt_layer != 0):
                warnings.append({
                    "type": "reverse_flow",
                    "message": (
                        f"Reverse flow: {c.get('source')} (L{src_layer}) -> "
                        f"{c.get('target')} (L{tgt_layer})"
                    ),
                    "severity": "warning",
                    "auto_fix_available": True,
                    "suggested_fix": {
                        "source": c.get("target"),
                        "target": c.get("source"),
                    },
                })

        # 6. Missing entry point (WARNING)
        has_entry = any(
            c.get("source", "").lower() in ("users", "user", "client", "internet")
            for c in connections
        )
        if not has_entry and len(services) > 1:
            warnings.append({
                "type": "missing_entry_point",
                "message": "No Users/Client entry point connection detected",
                "severity": "warning",
                "auto_fix_available": True,
            })

        # 7. Disconnected security (WARNING)
        has_kv = any(
            "key vault" in s.get("name", "").lower()
            for s in services if isinstance(s, dict)
        )
        kv_connected = any(
            "key vault" in c.get("target", "").lower()
            or "key vault" in c.get("source", "").lower()
            for c in connections
        )
        if has_kv and not kv_connected:
            warnings.append({
                "type": "disconnected_security",
                "message": "Azure Key Vault exists but has no connections — compute services should reference it",
                "severity": "warning",
                "auto_fix_available": True,
            })

        # 8. Disconnected monitoring (WARNING)
        has_monitor = any(
            any(kw in s.get("name", "").lower() for kw in ["monitor", "insights", "log analytics"])
            for s in services if isinstance(s, dict)
        )
        monitor_connected = any(
            any(kw in c.get("target", "").lower() or kw in c.get("source", "").lower()
                for kw in ["monitor", "insights", "log analytics"])
            for c in connections
        )
        if has_monitor and not monitor_connected:
            warnings.append({
                "type": "disconnected_monitoring",
                "message": "Monitoring service exists but has no connections",
                "severity": "warning",
                "auto_fix_available": True,
            })

        self.think(
            f"Connection validation: {len(errors)} errors, {len(warnings)} warnings, {len(orphans)} orphans",
            "observation",
        )

        all_issues = [e["message"] for e in errors] + [w["message"] for w in warnings]

        return {
            "valid_flow": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "orphan_services": orphans,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "issues": all_issues,
        }

    def _get_service_layer(self, service_name: str) -> int:
        """Map a service name to its flow layer (0-3, or -1 for cross-cutting)."""
        if not service_name:
            return 2
        name_lower = service_name.lower().strip()

        # Direct match
        if name_lower in SERVICE_LAYERS:
            return SERVICE_LAYERS[name_lower]

        # Strip common prefixes
        for prefix in ["azure ", "microsoft "]:
            if name_lower.startswith(prefix):
                stripped = name_lower[len(prefix):]
                if stripped in SERVICE_LAYERS:
                    return SERVICE_LAYERS[stripped]

        # Keyword fallback
        for layer, keywords in LAYER_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return layer

        return 2  # Default to compute layer

    async def _score_waf_pillars(self, arch: Dict) -> Dict:
        """Score architecture against WAF pillars using LLM."""
        services = [s.get("name", "") for s in arch.get("services", []) if isinstance(s, dict)]
        connections_summary = [
            f"{c.get('source', '')} -> {c.get('target', '')}"
            for c in arch.get("connections", [])[:20]
        ]
        try:
            resp = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content":
                     "Score this Azure architecture on the 5 Well-Architected Framework pillars (0-100). "
                     "Consider the services and their connections. "
                     "Return JSON only: {\"security\":N, \"reliability\":N, \"performance\":N, "
                     "\"cost_optimization\":N, \"operational_excellence\":N}"},
                    {"role": "user", "content":
                     f"Services: {json.dumps(services)}\n"
                     f"Connections: {json.dumps(connections_summary)}"},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            scores = json.loads(raw)
            return {
                k: int(v) for k, v in scores.items()
                if k in ("security", "reliability", "performance",
                          "cost_optimization", "operational_excellence")
            }
        except Exception as e:
            logger.warning(f"WAF scoring failed: {e}")
            return {
                "security": 0, "reliability": 0, "performance": 0,
                "cost_optimization": 0, "operational_excellence": 0,
            }

    async def _check_requirements(self, arch: Dict, requirements: str) -> Dict:
        """Check if architecture fulfills original requirements."""
        if not requirements.strip():
            return {
                "score": 100,
                "missing_requirements": [],
                "covered_requirements": ["No requirements specified"],
            }
        services = [s.get("name", "") for s in arch.get("services", []) if isinstance(s, dict)]
        try:
            resp = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content":
                     "Evaluate if the architecture fulfills these requirements. "
                     "Return JSON only: {\"score\":0-100, "
                     "\"missing_requirements\":[\"...\"], \"covered_requirements\":[\"...\"]}"},
                    {"role": "user", "content":
                     f"Requirements: {requirements}\n\nServices: {json.dumps(services)}"},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Requirements check failed: {e}")
            return {
                "score": 0,
                "missing_requirements": ["Validation unavailable"],
                "covered_requirements": [],
            }

    def _validate_xml(self, xml_str: str) -> Dict:
        """Validate XML structure for Draw.io compatibility."""
        return self._validate_xml_detail(xml_str)

    def _validate_xml_structure(self, xml_str: str) -> bool:
        """Quick boolean check for XML validity."""
        return self._validate_xml_detail(xml_str)["valid"]

    def _validate_xml_detail(self, xml_str: str) -> Dict:
        """Detailed XML validation."""
        issues = []
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            return {"valid": False, "issues": [f"XML parse error: {e}"]}

        if root.tag != "mxfile" and root.find(".//mxfile") is None:
            issues.append("Missing <mxfile> root element")
        diagram = root.find(".//diagram")
        if diagram is None:
            issues.append("Missing <diagram> element")
        model = root.find(".//mxGraphModel")
        if model is None:
            issues.append("Missing <mxGraphModel> element")
        graph_root = root.find(".//root")
        if graph_root is None:
            issues.append("Missing <root> element")
        else:
            vertices = [c for c in graph_root.findall("mxCell") if c.get("vertex") == "1"]
            if len(vertices) == 0:
                issues.append("No vertex cells found (empty diagram)")

        return {"valid": len(issues) == 0, "issues": issues}

    # ==================================================================
    # DIFF COMPUTATION
    # ==================================================================
    def _compute_diff(self, old_arch: Dict, new_arch: Dict) -> Dict:
        """Compute what changed between old and new architecture."""
        old_svcs = {s.get("name"): s for s in old_arch.get("services", []) if isinstance(s, dict)}
        new_svcs = {s.get("name"): s for s in new_arch.get("services", []) if isinstance(s, dict)}

        added_names = set(new_svcs.keys()) - set(old_svcs.keys())
        removed_names = set(old_svcs.keys()) - set(new_svcs.keys())

        old_conns = {(c.get("source"), c.get("target")) for c in old_arch.get("connections", [])}
        new_conns = {(c.get("source"), c.get("target")) for c in new_arch.get("connections", [])}

        conns_added = new_conns - old_conns
        conns_removed = old_conns - new_conns

        return {
            "services_added": [
                {"name": n, "category": new_svcs[n].get("category", "")} for n in added_names
            ],
            "services_removed": [
                {"name": n, "category": old_svcs[n].get("category", "")} for n in removed_names
            ],
            "connections_added": [
                {"source": s, "target": t, "label": ""} for s, t in conns_added
            ],
            "connections_removed": [
                {"source": s, "target": t, "label": ""} for s, t in conns_removed
            ],
        }

    # ==================================================================
    # XML UTILITY HELPERS
    # ==================================================================
    def _build_name_index(self, cell_map: Dict[str, ET.Element]) -> Dict[str, str]:
        """Build a lowercase service-name -> cell-id map."""
        index: Dict[str, str] = {}
        for cid, cell in cell_map.items():
            val = (cell.get("value") or "").strip()
            if val and cell.get("vertex") == "1":
                if cid.endswith("-label"):
                    icon_id = cid[:-6]
                    index[val.lower()] = icon_id
                else:
                    index[val.lower()] = cid
        return index

    def _fuzzy_find_id(self, name: str, name_to_id: Dict[str, str]) -> Optional[str]:
        """3-tier fuzzy find: exact -> normalized -> substring."""
        if not name:
            return None
        key = name.lower().strip()

        # Tier 1: Exact match
        if key in name_to_id:
            return name_to_id[key]

        # Tier 2: Normalized match (strip "azure " prefix)
        for prefix in ["azure ", "microsoft "]:
            normalized = key.replace(prefix, "").strip()
            if normalized in name_to_id:
                return name_to_id[normalized]
            # Check if any key matches after stripping prefix
            for k, v in name_to_id.items():
                k_normalized = k.replace(prefix, "").strip()
                if k_normalized == normalized:
                    return v

        # Tier 3: Substring match
        for k, v in name_to_id.items():
            if key in k or k in key:
                return v

        return None

    def _find_free_position(self, cell_map: Dict, root_elem: ET.Element) -> Tuple[int, int]:
        """Find a free position by scanning existing cell positions."""
        max_x, max_y = 100, 100
        for cell in root_elem.findall("mxCell"):
            geom = cell.find("mxGeometry")
            if geom is not None and cell.get("vertex") == "1":
                x = int(float(geom.get("x", "0")))
                y = int(float(geom.get("y", "0")))
                w = int(float(geom.get("width", "64")))
                if x + w > max_x:
                    max_x = x + w
                if y > max_y:
                    max_y = y
        return max_x + 60, max(max_y, 200)

    def _remove_cell_and_edges(
        self, root_elem: ET.Element, cell_id: str, cell_map: Dict
    ) -> None:
        """Remove a cell and any edges connected to it."""
        for cell in list(root_elem.findall("mxCell")):
            if cell.get("id") == cell_id:
                root_elem.remove(cell)
        for cell in list(root_elem.findall("mxCell")):
            if cell.get("edge") == "1":
                if cell.get("source") == cell_id or cell.get("target") == cell_id:
                    root_elem.remove(cell)

    def _next_cell_id(self, cell_map: Dict) -> int:
        """Find the next available numeric cell ID."""
        max_num = 100
        for cid in cell_map:
            parts = (
                cid.replace("svc-", "")
                .replace("conn-", "")
                .replace("rg-", "")
                .replace("vnet-", "")
                .replace("sn-", "")
                .replace("sub-", "")
                .split("-")
            )
            for p in parts:
                try:
                    n = int(p)
                    if n > max_num:
                        max_num = n
                except ValueError:
                    pass
        return max_num + 1

    def _serialize_thoughts(self) -> List[Dict]:
        """Serialize thinking steps for API response."""
        return [
            {
                "type": t.thought_type,
                "content": t.content,
                "timestamp": t.timestamp,
                "emoji": self._emoji_for(t.thought_type),
            }
            for t in self.thoughts
        ]

    def _emoji_for(self, thought_type: str) -> str:
        """Map thought type to emoji for frontend display."""
        return {
            "reasoning": "\U0001f9e0",     # brain
            "tool_call": "\U0001f527",     # wrench
            "observation": "\U0001f441\ufe0f",  # eye
            "reflection": "\U0001fa9e",    # mirror
            "decision": "\u26a1",          # lightning
            "warning": "\u26a0\ufe0f",     # warning
            "success": "\u2705",           # check
            "communication": "\U0001f4ac", # speech bubble
        }.get(thought_type, "\U0001f4ad")  # thought bubble
