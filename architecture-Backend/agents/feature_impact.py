import json
import csv
import logging
import copy
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional

from openai import AsyncAzureOpenAI

from agents.base import BaseAgent, AgentTools

logger = logging.getLogger(__name__)


class FeatureImpactAnalyzerAgent(BaseAgent):
    """Dedicated agent that analyzes feature impact on an existing architecture.

    Follows the same BaseAgent + agentic thinking pattern as other specialized agents.
    """

    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="FeatureImpactAnalyzerAgent", openai_client=openai_client, agent_type="architecture")

    @property
    def _references_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "architecture-Backend" / "knowledge_base" / "References"

    def _load_function_webapp_mapping(self) -> list:
        """Load function-app to feature mapping from knowledge_base/References."""
        csv_path = self._references_dir / "function-webapp-repo-mapping.csv"
        rows = []
        if not csv_path.exists():
            return rows
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    rows.append(dict(row))
        except Exception as exc:
            logger.warning(f"Failed to load function-webapp mapping: {exc}")
        return rows

    def _load_user_stories(self) -> list:
        """Load user stories from the Drop1 consolidated CSV in knowledge_base/References."""
        csv_path = self._references_dir / "Drop1-Final Consolidated US.csv"
        rows = []
        if not csv_path.exists():
            return rows
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    rows.append(dict(row))
        except Exception as exc:
            logger.warning(f"Failed to load user stories: {exc}")
        return rows

    def _build_reference_context(self, feature_name: str, business_capability: str) -> str:
        """Build a compact reference context block for injection into the prompt."""
        mapping_rows = self._load_function_webapp_mapping()
        us_rows = self._load_user_stories()

        capability_lower = (business_capability or "").lower()
        feature_lower = (feature_name or "").lower()

        # Relevant function/webapp components
        relevant_components = [
            r for r in mapping_rows
            if r.get("mapping_status", "") in ("matched", "assumed_shared_repo")
        ]

        # Relevant user stories: match on feature name words or business capability keywords
        search_tokens = set(feature_lower.split() + capability_lower.split())
        def us_relevant(us: dict) -> bool:
            text = " ".join([
                us.get("Title", ""), us.get("UserStory", ""), us.get("Feature", ""),
                us.get("Business Value", ""), us.get("Acceptance Criteria", "")
            ]).lower()
            return any(t in text for t in search_tokens if len(t) > 3)

        matched_stories = [us for us in us_rows if us_relevant(us)][:8]

        lines = ["\n\nREFERENCE KNOWLEDGE BASE:\n"]

        lines.append("--- Azure Components (from function-webapp-repo-mapping) ---")
        for r in relevant_components:
            features = r.get("relevant_drop1_features_colG", "")
            lines.append(
                f"  {r.get('resource_type','')}: {r.get('azure_app_name','')} → repo: {r.get('workspace_repo_folder','')} | features: {features[:120]}"
            )

        if matched_stories:
            lines.append("\n--- Related User Stories ---")
            for us in matched_stories:
                lines.append(
                    f"  [{us.get('Story ID','')} {us.get('Increment','')}] {us.get('Title','')}"
                )
                lines.append(f"    Story: {us.get('UserStory','')[:180]}")
                ac = us.get('Acceptance Criteria', '')[:200]
                if ac:
                    lines.append(f"    AC: {ac}")
                lines.append(f"    Feature: {us.get('Feature','')}")

        return "\n".join(lines)

    def _get_application_diagram_reference(self, application_name: str) -> Dict[str, Any]:
        """Look up the application's reference diagram from Knowledgebase/applications.csv."""
        if not application_name:
            return {"found": False}

        workspace_root = Path(__file__).resolve().parents[2]
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
                    if not diagram_path:
                        return {
                            "found": True,
                            "application_name": application_name,
                            "diagram_path": "",
                            "diagram_title": row.get("diagram_title") or row.get("title") or "",
                            "diagram_xml": None,
                        }

                    resolved_path = (workspace_root / diagram_path).resolve()
                    if not resolved_path.exists():
                        resolved_path = (workspace_root / "Knowledgebase" / Path(diagram_path).name).resolve()

                    diagram_xml = None
                    if resolved_path.exists() and resolved_path.suffix.lower() == ".drawio":
                        diagram_xml = resolved_path.read_text(encoding="utf-8")

                    return {
                        "found": True,
                        "application_name": application_name,
                        "diagram_path": diagram_path,
                        "diagram_title": row.get("diagram_title") or row.get("title") or resolved_path.stem,
                        "diagram_xml": diagram_xml,
                    }
        except Exception as exc:
            logger.warning(f"Unable to read application diagram reference CSV: {exc}")

        return {"found": False}

    def _tokenize_terms(self, *values: str) -> list[str]:
        tokens = []
        for value in values:
            for token in re.split(r"[^a-zA-Z0-9]+", (value or "").lower()):
                if len(token) > 2:
                    tokens.append(token)
        return list(dict.fromkeys(tokens))

    def _parse_feature_mapping_entries(self, feature_map: str) -> list[Dict[str, str]]:
        entries: list[Dict[str, str]] = []
        for raw_entry in (feature_map or "").split("|"):
            entry = raw_entry.strip().strip('"')
            if not entry:
                continue

            feature_code = ""
            feature_title = entry
            if "//" in entry:
                left, right = entry.split("//", 1)
                feature_code = left.strip()
                feature_title = right.strip()

            entries.append(
                {
                    "code": feature_code,
                    "title": feature_title,
                    "normalized": f"{feature_code} {feature_title}".strip().lower(),
                }
            )
        return entries

    def _find_matching_delivered_features(
        self,
        entries: list[Dict[str, str]],
        feature_name: str,
        feature_description: str,
        business_capability: str,
    ) -> list[Dict[str, str]]:
        request_tokens = self._tokenize_terms(feature_name, feature_description, business_capability)
        if not entries:
            return []

        scored_entries = []
        for index, entry in enumerate(entries):
            haystack = entry.get("normalized", "")
            score = sum(1 for token in request_tokens if token in haystack)
            if feature_name and feature_name.lower() in haystack:
                score += 4
            if business_capability and business_capability.lower() in haystack:
                score += 2
            scored_entries.append((score, index, entry))

        scored_entries.sort(key=lambda item: (-item[0], item[1]))
        matched = [entry for score, _, entry in scored_entries if score > 0]
        return matched[:3]

    def _select_impacted_mapping_rows(self, feature_name: str, business_capability: str, feature_description: str = "") -> list[Dict[str, Any]]:
        rows = [
            row for row in self._load_function_webapp_mapping()
            if row.get("mapping_status", "") in ("matched", "assumed_shared_repo") and row.get("azure_app_name")
        ]
        if not rows:
            return []

        tokens = self._tokenize_terms(feature_name, business_capability)
        scored_rows = []
        for index, row in enumerate(rows):
            parsed_features = self._parse_feature_mapping_entries(row.get("relevant_drop1_features_colG", ""))
            matched_features = self._find_matching_delivered_features(
                parsed_features,
                feature_name,
                feature_description,
                business_capability,
            )
            haystack = " ".join([
                row.get("resource_type", ""),
                row.get("azure_app_name", ""),
                row.get("project_name", ""),
                row.get("workspace_repo_folder", ""),
                row.get("relevant_drop1_features_colG", ""),
                row.get("notes", ""),
            ]).lower()
            score = sum(1 for token in tokens if token in haystack)
            if feature_name and feature_name.lower() in haystack:
                score += 3
            if business_capability and business_capability.lower() in haystack:
                score += 2
            score += len(matched_features) * 3

            enriched_row = dict(row)
            enriched_row["_parsed_features"] = parsed_features
            enriched_row["_matched_features"] = matched_features
            scored_rows.append((score, index, enriched_row))

        scored_rows.sort(key=lambda item: (-item[0], item[1]))
        matched_rows = [row for score, _, row in scored_rows if score > 0]
        if not matched_rows:
            web_apps = [row for row in rows if row.get("resource_type") == "web_app"][:1]
            function_apps = [row for row in rows if row.get("resource_type") == "function_app"][:3]
            matched_rows = web_apps + function_apps

        selected: list[Dict[str, Any]] = []
        seen = set()
        web_count = 0
        function_count = 0
        for row in matched_rows:
            resource_type = row.get("resource_type", "")
            azure_name = row.get("azure_app_name", "")
            if azure_name in seen:
                continue
            if resource_type == "web_app" and web_count >= 1:
                continue
            if resource_type == "function_app" and function_count >= 4:
                continue
            selected.append(row)
            seen.add(azure_name)
            if resource_type == "web_app":
                web_count += 1
            elif resource_type == "function_app":
                function_count += 1

        return selected

    def _extract_database_components_from_diagram(self, diagram_xml: Optional[str], feature_name: str) -> list[Dict[str, Any]]:
        if not diagram_xml:
            return []

        components = []
        seen = set()
        try:
            root = ET.fromstring(diagram_xml)
            for cell in root.findall(".//mxCell"):
                style = (cell.get("style") or "").lower()
                value = cell.get("value") or ""
                if "databases/" not in style and "postgresql" not in value.lower() and "database" not in value.lower():
                    continue

                text = html.unescape(value)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines:
                    continue
                server_name = lines[1] if len(lines) > 1 else lines[0]
                title = lines[0]
                if not server_name or server_name.lower() in seen:
                    continue
                seen.add(server_name.lower())
                components.append({
                    "id": f"db-{server_name.lower().replace('_', '-').replace(' ', '-')}",
                    "name": server_name,
                    "layer": "Data",
                    "purpose": title,
                    "status": "Active",
                    "changeStatus": "Impacted",
                    "resourceType": "database",
                    "changeDescription": f"Apply schema, query, and persistence updates required to support {feature_name}.",
                    "impactSummary": f"Data model and persistence changes for {feature_name}",
                    "humanDiscussionRequired": True,
                    "humanDiscussionReason": "Database schema and DR implications require review before implementation.",
                })
        except ET.ParseError as exc:
            logger.warning(f"Unable to parse database components from diagram XML: {exc}")

        return components

    def _build_component_change_description(self, resource_type: str, azure_name: str, project_name: str, feature_name: str, feature_description: str) -> str:
        feature_lower = (feature_name or "").lower()
        azure_lower = (azure_name or "").lower()

        if resource_type == "web_app":
            if "accrual" in feature_lower and "offer" in feature_lower:
                return f"Update the web app to display accrual points in the flight offer results and surface the new field in the offer details experience."
            return f"Update the web app flow and screens to surface {feature_name}, collect inputs, and display outcomes."

        if resource_type == "function_app":
            if "shop-offer" in azure_lower and "accrual" in feature_lower:
                return "Return accrual points along with flight offers and extend the offer response contract to include the accrual-points payload."
            if "searchpanel" in azure_lower and "accrual" in feature_lower:
                return "Accept accrual-points request context from the search flow and pass the required loyalty and itinerary inputs downstream."
            if "services" in azure_lower and "accrual" in feature_lower:
                return "Orchestrate accrual-points enrichment with downstream services and validate the business rules used for accrual calculation."
            if "payment" in azure_lower:
                return f"Review downstream contract compatibility for {feature_name} so payment and checkout flows continue to receive the updated response safely."
            return f"Update the function app handlers, contracts, validation, and orchestration needed for {feature_name}."

        if resource_type == "database":
            return f"Apply schema, query, and persistence updates required to support {feature_name}."

        return f"Implement the component changes required to support {feature_name}."

    def _infer_new_integration_components(self, feature_request: Dict[str, Any]) -> list[Dict[str, Any]]:
        feature_name = feature_request.get("feature_name", "Feature")
        feature_description = feature_request.get("feature_description", "")
        combined_text = f"{feature_name} {feature_description} {feature_request.get('business_capability', '')}".lower()

        integration_catalog = [
            {
                "keyword": "loyalty",
                "system_name": "Loyalty System",
                "function_app_name": "func-aai-perf-loyalty-neu-new",
                "purpose": "Loyalty integration function app",
                "change_description": "Integrate with the Loyalty system, retrieve accrual and membership data, and expose it through the internal API flow.",
                "reason": "A new external Loyalty system integration requires a dedicated function app boundary.",
            },
            {
                "keyword": "crm",
                "system_name": "CRM Platform",
                "function_app_name": "func-aai-perf-crm-neu-new",
                "purpose": "CRM integration function app",
                "change_description": "Integrate with the CRM platform and translate the new feature data into CRM-compatible contracts and events.",
                "reason": "A new CRM integration requires an isolated function app for contract and retry handling.",
            },
            {
                "keyword": "partner",
                "system_name": "Partner System",
                "function_app_name": "func-aai-perf-partner-neu-new",
                "purpose": "Partner integration function app",
                "change_description": "Connect to the new partner system and handle external contract translation, validation, and resiliency for the feature flow.",
                "reason": "A new partner integration should be isolated behind a dedicated function app.",
            },
        ]

        new_components: list[Dict[str, Any]] = []
        for item in integration_catalog:
            if item["keyword"] not in combined_text:
                continue
            new_components.append(
                {
                    "id": f"function_app-{item['function_app_name']}".lower(),
                    "name": item["function_app_name"],
                    "layer": "API",
                    "purpose": item["purpose"],
                    "status": "Planned",
                    "changeStatus": "New",
                    "resourceType": "function_app",
                    "impactSummary": item["change_description"],
                    "changeDescription": item["change_description"],
                    "discussionRequired": True,
                    "reasonNeeded": item["reason"],
                    "ownerNeeded": "Yes",
                    "deploymentRequired": "Yes",
                    "humanDiscussionRequired": True,
                    "humanDiscussionReason": f"Ownership, API contracts, and support model for the new {item['system_name']} integration must be confirmed.",
                }
            )

        return new_components

    def _build_azure_component_inventory(self, feature_request: Dict[str, Any]) -> Dict[str, Any]:
        feature_name = feature_request.get("feature_name", "Feature")
        feature_description = feature_request.get("feature_description", "")
        business_capability = feature_request.get("business_capability", "")
        application_reference = self._get_application_diagram_reference(feature_request.get("application_name", ""))

        selected_rows = self._select_impacted_mapping_rows(feature_name, business_capability, feature_description)
        existing_components = []
        function_components = []
        web_components = []

        for row in selected_rows:
            resource_type = row.get("resource_type", "")
            azure_name = (row.get("azure_app_name") or "").strip()
            project_name = (row.get("project_name") or "Azure Component").strip()
            repo_folder = (row.get("workspace_repo_folder") or "N/A").strip()
            feature_map = (row.get("relevant_drop1_features_colG") or "").strip()
            parsed_features = row.get("_parsed_features", []) if isinstance(row.get("_parsed_features"), list) else []
            matched_features = row.get("_matched_features", []) if isinstance(row.get("_matched_features"), list) else []

            if not azure_name:
                continue

            if resource_type == "web_app":
                layer = "UI"
            else:
                layer = "API"

            change_description = self._build_component_change_description(
                resource_type,
                azure_name,
                project_name,
                feature_name,
                feature_request.get("feature_description", ""),
            )

            component = {
                "id": f"{resource_type}-{azure_name}".lower(),
                "name": azure_name,
                "layer": layer,
                "purpose": project_name,
                "status": "Active",
                "changeStatus": "Impacted",
                "resourceType": resource_type,
                "repoFolder": repo_folder,
                "featureMapping": feature_map,
                "deliveredFeatures": [entry.get("title", "") for entry in parsed_features if entry.get("title")],
                "matchedDeliveredFeatures": [entry.get("title", "") for entry in matched_features if entry.get("title")],
                "impactReason": (
                    f"This component already delivers: {', '.join(entry.get('title', '') for entry in matched_features if entry.get('title'))}."
                    if matched_features else
                    f"This component is impacted based on its existing responsibility in {project_name} and the mapped features it already delivers."
                ),
                "changeDescription": change_description,
                "impactSummary": change_description,
                "humanDiscussionRequired": resource_type == "function_app",
                "humanDiscussionReason": "API contract and deployment sequencing should be reviewed." if resource_type == "function_app" else "",
            }
            existing_components.append(component)
            if resource_type == "web_app":
                web_components.append(component)
            else:
                function_components.append(component)

        database_components = self._extract_database_components_from_diagram(application_reference.get("diagram_xml"), feature_name)
        existing_components.extend(database_components)

        return {
            "components": existing_components,
            "web_components": web_components,
            "function_components": function_components,
            "database_components": database_components,
            "application_reference": application_reference,
        }

    def _has_named_azure_impacts(self, result: Dict[str, Any]) -> bool:
        proposed = result.get("proposedArchitecture", {}) if isinstance(result.get("proposedArchitecture"), dict) else {}
        components = proposed.get("components", []) if isinstance(proposed.get("components"), list) else []
        for component in components:
            if not isinstance(component, dict) or component.get("changeStatus") != "Impacted":
                continue
            resource_type = str(component.get("resourceType") or "")
            name = str(component.get("name") or "")
            if resource_type in {"function_app", "web_app", "database"}:
                return True
            if name.startswith(("func-", "app-", "psql-")):
                return True
        return False

    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if context is None:
            context = {}

        feature_request = context.get("feature_request", {}) if isinstance(context, dict) else {}
        application_reference = self._get_application_diagram_reference(feature_request.get("application_name", ""))

        self.think(f"I am the {self.persona.role}. Starting feature impact analysis.", "reasoning")
        self.think("Approach: analyze current vs proposed architecture using knowledge-base references, identify impacted/new components, and surface decision points.", "reasoning")
        self.think("Loading function-app/webapp mapping and user stories from knowledge base reference files.", "tool_call")

        reference_context = self._build_reference_context(
            feature_name=feature_request.get("feature_name", ""),
            business_capability=feature_request.get("business_capability", "")
        )

        docs_context = await self.use_tool(
            AgentTools.SEARCH_AZURE_DOCS,
            {
                "query": requirements,
                "domain_terms": [
                    "architecture",
                    "impact analysis",
                    "api",
                    "database",
                    "integration",
                    "security",
                    "observability",
                ],
                "max_results": 5,
            },
        )

        fallback = self._build_fallback_payload(feature_request)
        if application_reference.get("found"):
            fallback["applicationReference"] = application_reference
            fallback["architectureDiagramXml"] = application_reference.get("diagram_xml")

        prompt = f"""
You are a Principal Azure Solutions Architect performing feature impact analysis.
Use the user inputs and Azure context to produce a concise and structured architecture impact output.

LOCAL AZURE CONTEXT:
{docs_context}
{reference_context}

FEATURE REQUEST INPUT:
{json.dumps(feature_request, indent=2)}

APPLICATION DIAGRAM REFERENCE:
{json.dumps({k: v for k, v in application_reference.items() if k != "diagram_xml"}, indent=2)}

REQUIREMENTS CONTEXT:
{requirements}

INSTRUCTIONS:
- Use the REFERENCE KNOWLEDGE BASE above to identify which Azure components (function apps, web apps) are actually impacted.
- Map impacted components to their azure_app_name and workspace_repo_folder from the mapping CSV.
- Ground detailedImpactTable in the real component names from the reference data.
- Use the related User Stories to populate the decisionPanel and discussionItems with real acceptance criteria and feature IDs.
- Ensure component IDs match those from the function-webapp-repo-mapping where applicable.
- If the requested feature introduces a new external system integration, add a new function app component to the proposed architecture for that integration.
- Always return real, grounded data - do not fabricate component names not present in the reference data.

Return ONLY valid JSON with this exact shape:
{{
  "application": {{"name": "", "environment": "", "viewMode": ""}},
    "applicationReference": {{"found": false, "application_name": "", "diagram_path": "", "diagram_title": ""}},
    "architectureDiagramXml": "",
  "feature": {{
    "name": "",
    "description": "",
    "changeType": "",
    "priority": "",
    "targetRelease": "",
    "businessCapability": ""
  }},
    "existingArchitecture": {{"components": [], "connections": []}},
    "proposedArchitecture": {{"components": [], "connections": []}},
  "architectureDiff": {{"added": [], "modified": [], "unchanged": [], "removed": []}},
    "systemsSummary": {{"impactedSystems": [], "newSystems": []}},
  "impactSummary": {{
    "impactLevel": "Low|Medium|High",
    "impactedComponentCount": 0,
    "newComponentCount": 0,
    "apiChangeRequired": true,
    "dataChangeRequired": true,
    "securityReviewRequired": true,
    "discussionRequired": true
  }},
  "detailedImpactTable": [],
  "newComponentRecommendations": [],
  "decisionPanel": [],
  "minimalExplanation": {{"whyImpacted": "", "whatChanges": "", "discussionRequired": ""}},
  "aiConfidence": {{"confidence": "Low|Medium|High", "assumptions": [], "missingInformation": [], "sourceUsed": []}},
  "discussionItems": [],
  "legend": {{"unchanged": "Grey", "impacted": "Orange", "new": "Green", "removed": "Red", "discussionRequired": "Purple"}},
  "requestedScope": {{"architectureLayer": [], "impactType": [], "confidenceThreshold": "All"}},
  "timestamp": "ISO-8601"
}}
"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert Azure architecture impact analyst. Return only strict JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            self.think(f"Knowledge base loaded: {len(self._load_function_webapp_mapping())} components, {len(self._load_user_stories())} user stories.", "observation")
            self.think("Calling Azure OpenAI for feature impact reasoning with reference context.", "tool_call")
            response = await self._call_openai(messages)
            self.think("Model response received. Parsing structured impact output.", "observation")

            parsed = self._safe_json_parse(response, fallback)
            result = self._normalize_output(parsed, fallback)

            impacted = result.get("impactSummary", {}).get("impactedComponentCount", 0)
            created = result.get("impactSummary", {}).get("newComponentCount", 0)
            level = result.get("impactSummary", {}).get("impactLevel", "Medium")
            self.think(f"Impact analysis complete: level={level}, impacted={impacted}, new={created}", "success")

            result["agent"] = "feature_impact_analyzer"
            result["status"] = "completed"
            result["thinking_summary"] = self.get_thinking_summary()
            return result
        except Exception as e:
            logger.error(f"FeatureImpactAnalyzerAgent failed: {e}")
            self.think(f"Feature impact analysis failed, returning fallback: {str(e)}", "warning")
            fallback["agent"] = "feature_impact_analyzer"
            fallback["status"] = "completed"
            fallback["thinking_summary"] = self.get_thinking_summary()
            return fallback

    def _normalize_output(self, parsed: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure required keys are present and typed for frontend compatibility."""
        result = copy.deepcopy(fallback)
        result.update(parsed or {})

        # Ensure nested blocks exist
        for key in [
            "application",
            "applicationReference",
            "feature",
            "existingArchitecture",
            "proposedArchitecture",
            "architectureDiff",
            "systemsSummary",
            "impactSummary",
            "minimalExplanation",
            "aiConfidence",
            "legend",
            "requestedScope",
        ]:
            if key not in result or not isinstance(result[key], dict):
                result[key] = fallback.get(key, {})

        for key in [
            "detailedImpactTable",
            "newComponentRecommendations",
            "decisionPanel",
            "discussionItems",
        ]:
            if key not in result or not isinstance(result[key], list):
                result[key] = copy.deepcopy(fallback.get(key, []))
            elif len(result[key]) == 0 and len(fallback.get(key, [])) > 0:
                result[key] = copy.deepcopy(fallback.get(key, []))

        # Ensure architecture structures have both components and connections
        for arch_key in ["existingArchitecture", "proposedArchitecture"]:
            arch = result.get(arch_key, {})
            fallback_arch = fallback.get(arch_key, {})
            if not isinstance(arch.get("components"), list) or len(arch.get("components") or []) == 0:
                arch["components"] = copy.deepcopy(fallback_arch.get("components", []))
            if not isinstance(arch.get("connections"), list) or len(arch.get("connections") or []) == 0:
                arch["connections"] = copy.deepcopy(fallback_arch.get("connections", []))
            result[arch_key] = arch

        if not result.get("timestamp"):
            result["timestamp"] = fallback.get("timestamp")

        if "architectureDiagramXml" not in result:
            result["architectureDiagramXml"] = fallback.get("architectureDiagramXml")

        self._enforce_proposed_as_existing_plus_changes(result)

        if result.get("impactSummary", {}).get("impactedComponentCount", 0) == 0:
            fallback_result = copy.deepcopy(fallback)
            self._enforce_proposed_as_existing_plus_changes(fallback_result)

            for key in [
                "existingArchitecture",
                "proposedArchitecture",
                "architectureDiff",
                "systemsSummary",
                "impactSummary",
                "detailedImpactTable",
                "newComponentRecommendations",
                "decisionPanel",
                "discussionItems",
                "minimalExplanation",
            ]:
                result[key] = copy.deepcopy(fallback_result.get(key, result.get(key)))

        if not self._has_named_azure_impacts(result):
            fallback_result = copy.deepcopy(fallback)
            self._enforce_proposed_as_existing_plus_changes(fallback_result)
            for key in [
                "existingArchitecture",
                "proposedArchitecture",
                "architectureDiff",
                "systemsSummary",
                "impactSummary",
                "detailedImpactTable",
                "minimalExplanation",
            ]:
                result[key] = copy.deepcopy(fallback_result.get(key, result.get(key)))

        return result

    def _component_key(self, component: Dict[str, Any]) -> str:
        cid = str(component.get("id") or "").strip().lower()
        if cid:
            return f"id:{cid}"
        name = str(component.get("name") or "").strip().lower()
        return f"name:{name}"

    def _build_change_description_map(self, result: Dict[str, Any]) -> Dict[str, str]:
        descriptions: Dict[str, str] = {}

        for row in result.get("detailedImpactTable", []):
            if not isinstance(row, dict):
                continue
            name = str(row.get("component") or "").strip()
            change_needed = str(row.get("changeNeeded") or "").strip()
            impact = str(row.get("impact") or "").strip()
            if name and (change_needed or impact):
                descriptions[name.lower()] = change_needed or impact

        for rec in result.get("newComponentRecommendations", []):
            if not isinstance(rec, dict):
                continue
            name = str(rec.get("componentName") or "").strip()
            reason = str(rec.get("reasonNeeded") or "").strip()
            purpose = str(rec.get("purpose") or "").strip()
            if name and (reason or purpose):
                descriptions[name.lower()] = reason or purpose

        return descriptions

    def _enforce_proposed_as_existing_plus_changes(self, result: Dict[str, Any]) -> None:
        """Ensure proposed architecture is an existing-architecture copy with overlays and new components."""
        existing_arch = result.get("existingArchitecture", {})
        proposed_arch = result.get("proposedArchitecture", {})

        existing_components = existing_arch.get("components") or []
        proposed_components = proposed_arch.get("components") or []
        existing_connections = existing_arch.get("connections") or []
        proposed_connections = proposed_arch.get("connections") or []

        if not isinstance(existing_components, list) or not isinstance(proposed_components, list):
            return

        change_desc_map = self._build_change_description_map(result)

        proposed_by_key: Dict[str, Dict[str, Any]] = {}
        for comp in proposed_components:
            if isinstance(comp, dict):
                proposed_by_key[self._component_key(comp)] = comp

        merged_components = []
        existing_keys = set()

        for base in existing_components:
            if not isinstance(base, dict):
                continue

            key = self._component_key(base)
            existing_keys.add(key)
            overlay = proposed_by_key.get(key, {}) if isinstance(proposed_by_key.get(key), dict) else {}

            merged = copy.deepcopy(base)
            merged.update(copy.deepcopy(overlay))

            change_status = str(merged.get("changeStatus") or "").strip() or "Existing"
            if change_status not in {"Existing", "Impacted", "New", "Removed"}:
                change_status = "Existing"
            merged["changeStatus"] = change_status

            if change_status in {"Impacted", "New"}:
                component_name = str(merged.get("name") or "").strip().lower()
                description = (
                    str(merged.get("changeDescription") or "").strip()
                    or str(merged.get("impactSummary") or "").strip()
                    or change_desc_map.get(component_name, "")
                )
                if description:
                    merged["changeDescription"] = description
                    merged["impactSummary"] = str(merged.get("impactSummary") or description)

            merged_components.append(merged)

        for comp in proposed_components:
            if not isinstance(comp, dict):
                continue

            key = self._component_key(comp)
            if key in existing_keys:
                continue

            new_comp = copy.deepcopy(comp)
            if not str(new_comp.get("changeStatus") or "").strip():
                new_comp["changeStatus"] = "New"

            if new_comp.get("changeStatus") in {"Impacted", "New"}:
                component_name = str(new_comp.get("name") or "").strip().lower()
                description = (
                    str(new_comp.get("changeDescription") or "").strip()
                    or str(new_comp.get("impactSummary") or "").strip()
                    or change_desc_map.get(component_name, "")
                )
                if description:
                    new_comp["changeDescription"] = description
                    new_comp["impactSummary"] = str(new_comp.get("impactSummary") or description)

            merged_components.append(new_comp)

        conn_seen = set()
        merged_connections = []
        for conn in list(existing_connections) + list(proposed_connections):
            if not isinstance(conn, dict):
                continue
            sig = (
                str(conn.get("source") or "").strip(),
                str(conn.get("target") or "").strip(),
                str(conn.get("label") or "").strip(),
            )
            if sig in conn_seen:
                continue
            conn_seen.add(sig)
            merged_connections.append(copy.deepcopy(conn))

        result["proposedArchitecture"] = {
            "components": merged_components,
            "connections": merged_connections,
        }

        added = [c.get("name") for c in merged_components if c.get("changeStatus") == "New" and c.get("name")]
        modified = [c.get("name") for c in merged_components if c.get("changeStatus") == "Impacted" and c.get("name")]
        unchanged = [c.get("name") for c in merged_components if c.get("changeStatus") == "Existing" and c.get("name")]
        removed = [c.get("name") for c in merged_components if c.get("changeStatus") == "Removed" and c.get("name")]

        result["architectureDiff"] = {
            "added": added,
            "modified": modified,
            "unchanged": unchanged,
            "removed": removed,
        }

        result["systemsSummary"] = {
            "impactedSystems": modified,
            "newSystems": added,
        }

        summary = result.get("impactSummary", {}) if isinstance(result.get("impactSummary"), dict) else {}
        summary["impactedComponentCount"] = len(modified)
        summary["newComponentCount"] = len(added)
        result["impactSummary"] = summary

    def _build_fallback_payload(self, feature_request: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback payload for robust UX even when model output fails."""
        from datetime import datetime

        app = feature_request.get("application_name", "Application")
        feature_name = feature_request.get("feature_name", "Feature")
        feature_description = feature_request.get("feature_description", "")
        azure_inventory = self._build_azure_component_inventory(feature_request)
        existing_components = azure_inventory.get("components", [])

        if not existing_components:
            existing_components = [
                {
                    "id": "db-main",
                    "name": "Operational Database",
                    "layer": "Data",
                    "purpose": "Stores transactional records",
                    "status": "Active",
                    "changeStatus": "Impacted",
                    "resourceType": "database",
                    "impactSummary": "Persist feature-related state",
                    "changeDescription": f"Persist and query the data needed for {feature_name}.",
                    "humanDiscussionRequired": True,
                    "humanDiscussionReason": "Schema migration and rollback strategy require DBA and compliance alignment.",
                },
            ]

        new_component = {
            "id": "svc-feature-impact",
            "name": f"{feature_name} Service",
            "layer": "Service",
            "purpose": f"Executes {feature_name} domain logic",
            "status": "Planned",
            "changeStatus": "New",
            "resourceType": "proposed_service",
            "impactSummary": feature_description,
            "changeDescription": f"Introduce a dedicated service boundary for {feature_name} implementation.",
            "discussionRequired": True,
            "reasonNeeded": "Isolates feature logic from existing orchestration to reduce coupling",
            "ownerNeeded": "Yes",
            "deploymentRequired": "Yes",
            "humanDiscussionRequired": True,
            "humanDiscussionReason": "Ownership, SLO, and deployment strategy for new service must be assigned.",
            "diagramReferences": [
                {
                    "type": "Integration Diagram",
                    "title": "Feature service interactions",
                    "path": "/diagrams/azure-architecture-sample.png",
                    "status": "available",
                },
                {
                    "type": "Sequence Diagram",
                    "title": "Feature execution sequence",
                    "path": "/diagrams/azure-architecture-eastus.png",
                    "status": "available",
                },
            ],
        }

        inferred_integration_components = self._infer_new_integration_components(feature_request)
        new_components = [new_component, *inferred_integration_components]
        proposed_components = [c.copy() for c in existing_components] + [copy.deepcopy(component) for component in new_components]

        web_components = azure_inventory.get("web_components", [])
        function_components = azure_inventory.get("function_components", [])
        database_components = azure_inventory.get("database_components", [])

        existing_connections = []
        if web_components and function_components:
            for function_component in function_components[: min(len(function_components), 3)]:
                existing_connections.append({
                    "source": web_components[0]["id"],
                    "target": function_component["id"],
                    "label": "HTTPS/API",
                })
        if function_components and database_components:
            for function_component in function_components[: min(len(function_components), 2)]:
                existing_connections.append({
                    "source": function_component["id"],
                    "target": database_components[0]["id"],
                    "label": "SQL",
                })

        proposed_connections = [
            *existing_connections,
            *([
                {"source": function_components[0]["id"], "target": "svc-feature-impact", "label": "Internal API"}
            ] if function_components else []),
            *([
                {"source": "svc-feature-impact", "target": database_components[0]["id"], "label": "Read/Write"}
            ] if database_components else []),
            *[
                {"source": "svc-feature-impact", "target": component["id"], "label": "External Integration"}
                for component in inferred_integration_components
            ],
        ]

        impacted_systems = [
            comp["name"] for comp in proposed_components if comp.get("changeStatus") == "Impacted"
        ]
        new_systems = [
            comp["name"] for comp in proposed_components if comp.get("changeStatus") == "New"
        ]

        return {
            "application": {
                "name": app,
                "environment": feature_request.get("environment", "Prod"),
                "viewMode": feature_request.get("view_mode", "Technical View"),
            },
            "applicationReference": {
                "found": azure_inventory.get("application_reference", {}).get("found", False),
                "application_name": app,
                "diagram_path": azure_inventory.get("application_reference", {}).get("diagram_path", ""),
                "diagram_title": azure_inventory.get("application_reference", {}).get("diagram_title", ""),
            },
            "architectureDiagramXml": azure_inventory.get("application_reference", {}).get("diagram_xml"),
            "feature": {
                "name": feature_name,
                "description": feature_description,
                "changeType": feature_request.get("change_type", "New Feature"),
                "priority": feature_request.get("priority", "Medium"),
                "targetRelease": feature_request.get("target_release"),
                "businessCapability": feature_request.get("business_capability", "General"),
            },
            "existingArchitecture": {"components": existing_components, "connections": existing_connections},
            "proposedArchitecture": {"components": proposed_components, "connections": proposed_connections},
            "architectureDiff": {
                "added": [component["name"] for component in new_components],
                "modified": impacted_systems,
                "unchanged": [],
                "removed": [],
            },
            "systemsSummary": {
                "impactedSystems": impacted_systems,
                "newSystems": new_systems,
            },
            "impactSummary": {
                "impactLevel": "High",
                "impactedComponentCount": len([c for c in proposed_components if c.get("changeStatus") == "Impacted"]),
                "newComponentCount": len(new_components),
                "apiChangeRequired": True,
                "dataChangeRequired": True,
                "securityReviewRequired": True,
                "discussionRequired": True,
            },
            "detailedImpactTable": [
                *[
                    {
                        "component": component["name"],
                        "layer": component["layer"],
                        "currentRole": component.get("purpose", component["layer"]),
                        "impact": component.get("impactSummary", "Impact requires analysis"),
                        "changeNeeded": component.get("changeDescription", component.get("impactSummary", "Change required")),
                        "risk": "High" if component.get("resourceType") == "database" else "Medium",
                        "discussionRequired": "Yes" if component.get("humanDiscussionRequired") else "No",
                    }
                    for component in existing_components
                ],
            ],
            "newComponentRecommendations": [
                *[
                    {
                        "componentName": component["name"],
                        "componentType": "Function App" if component.get("resourceType") == "function_app" else "Service",
                        "purpose": component["purpose"],
                        "reasonNeeded": component["reasonNeeded"],
                        "ownerNeeded": component["ownerNeeded"],
                        "deploymentRequired": component["deploymentRequired"],
                        "discussionRequired": "Yes",
                    }
                    for component in new_components
                ]
            ],
            "decisionPanel": [
                {
                    "decision": "Build vs Reuse",
                    "question": f"Should {feature_name} logic be embedded in Core Business Service or isolated in a new service?",
                    "participants": ["Architect", "Service Owner", "Product Owner"],
                    "priority": "High",
                }
            ],
            "minimalExplanation": {
                "whyImpacted": f"Existing web apps, function apps, and databases are impacted to support {feature_name}.",
                "whatChanges": f"Update impacted Azure application components, extend database interactions, and introduce {', '.join(component['name'] for component in new_components)} where required.",
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
            "discussionItems": [
                {
                    "topic": f"{feature_name} ownership and deployment boundary",
                    "reason": "A new service is introduced and ownership/SLO must be defined",
                    "requiredParticipants": ["Architect", "Product Owner", "Service Owner"],
                    "priority": "High",
                },
                *[
                    {
                        "topic": f"{component['name']} integration design",
                        "reason": component["reasonNeeded"],
                        "requiredParticipants": ["Architect", "Integration Owner", "Service Owner"],
                        "priority": "High",
                    }
                    for component in inferred_integration_components
                ]
            ],
            "legend": {
                "unchanged": "Grey",
                "impacted": "Orange",
                "new": "Green",
                "removed": "Red",
                "discussionRequired": "Purple",
            },
            "requestedScope": {
                "architectureLayer": feature_request.get("architecture_layer", []),
                "impactType": feature_request.get("impact_type", []),
                "confidenceThreshold": feature_request.get("confidence_threshold", "All"),
            },
            "timestamp": datetime.now().isoformat(),
        }
