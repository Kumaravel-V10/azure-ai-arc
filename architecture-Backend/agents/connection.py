import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from openai import AsyncAzureOpenAI
from agents.base import BaseAgent
from config import SERVICE_LAYERS as _SERVICE_LAYERS

logger = logging.getLogger(__name__)


class ConnectionExpertAgent(BaseAgent):
    """Principal Connection Expert - validates and optimizes connections between architecture components.
    Takes the architecture from ArchitectureAgent and ensures professional, well-structured connections.
    
    EXPERTISE DOMAINS:
    - Professional diagram connection patterns (like Draw.io reference architectures)
    - Layer-based flow validation (Users â†’ Edge â†’ Gateway â†’ Compute â†’ Data)
    - Connection labeling best practices
    - Orphan service detection and auto-connection
    - Duplicate connection removal
    - Cross-cutting service connection patterns
    """
    
    def __init__(self, openai_client: Optional[AsyncAzureOpenAI] = None):
        super().__init__(name="ConnectionExpertAgent", openai_client=openai_client, agent_type="connection")
    
    # Service layer mapping (imported from config)
    SERVICE_LAYERS = _SERVICE_LAYERS
    
    # Professional connection label templates
    CONNECTION_LABELS = {
        "entry_point": ["User requests", "HTTPS requests", "Client traffic", "Incoming traffic"],
        "edge_to_gateway": ["HTTPS routing", "SSL termination", "Traffic routing", "WAF inspection"],
        "gateway_to_compute": ["Backend routing", "API requests", "Application traffic", "Load balanced traffic"],
        "compute_to_data": ["SQL queries", "Data queries", "Document operations", "Cache operations", "Read/Write operations"],
        "compute_to_integration": ["Message publishing", "Event publishing", "Queue messages", "Async operations"],
        "integration_to_compute": ["Queue trigger", "Event processing", "Message consumption", "Subscriber notification"],
        "compute_to_crosscutting": ["Secrets retrieval", "Telemetry", "Diagnostics", "Monitoring data", "Identity validation"]
    }
    
    async def analyze(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze and optimize connections in the architecture.
        Takes architecture from ArchitectureAgent and returns enhanced version with professional connections."""
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Chain-of-Thought reasoning
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        self.think(f"I am the {self.persona.role}. Starting connection optimization.", "reasoning")
        self.think("My approach: Validate layer flow, optimize labels, detect orphans", "reasoning")
        
        # Check for messages from upstream agents
        messages = self.receive_messages()
        if messages:
            self.think(f"Received {len(messages)} messages from upstream agents", "communication")
            for msg in messages:
                self.think(f"From {msg.from_agent}: {msg.content[:100]}", "observation")
        
        if context is None:
            context = {}
        
        architecture_data = context.get("architecture_analysis", {})
        
        if not architecture_data or architecture_data.get("status") != "completed":
            logger.warning("ConnectionExpertAgent: No valid architecture data received")
            self.think("No valid architecture data received - cannot optimize connections", "warning")
            return {
                "agent": "connection_expert",
                "status": "error",
                "error": "No architecture data to process",
                "enhanced_architecture": {},
                "thinking_summary": self.get_thinking_summary()
            }
        
        logger.info("=" * 70)
        logger.info("ðŸ”— CONNECTION EXPERT AGENT - Optimizing Architecture Connections")
        logger.info("=" * 70)
        
        # Extract services and connections
        services = architecture_data.get("services", [])
        connections = architecture_data.get("connections", [])
        containers = architecture_data.get("containers", [])
        primary_flow = architecture_data.get("primary_flow", [])
        
        self.think(f"Analyzing architecture: {len(services)} services, {len(connections)} connections", "observation")
        logger.info(f"  Input: {len(services)} services, {len(connections)} connections")
        
        # Step 1: Ensure Users entry point exists
        services, users_added = self._ensure_users_entry_point(services)
        if users_added:
            logger.info("  âœ“ Added 'Users' entry point")
        
        # Step 2: Build service layer mapping
        service_layer_map = self._build_service_layer_map(services)
        
        # Step 3: Categorize services by layer
        layer_services = self._categorize_by_layer(services, service_layer_map)
        self.think(f"Layer distribution: L0={len(layer_services[0])}, L1={len(layer_services[1])}, L2={len(layer_services[2])}, L3={len(layer_services[3])}", "observation")
        logger.info(f"  Services by layer: L0={len(layer_services[0])}, L1={len(layer_services[1])}, L2={len(layer_services[2])}, L3={len(layer_services[3])}, Cross-cutting={len(layer_services[-1])}")
        
        # Step 4: Build primary flow chain if not present
        self.think("Building primary flow chain if not present...", "reasoning")
        if not primary_flow or len(primary_flow) < 2:
            primary_flow = self._build_primary_flow(layer_services)
            self.think(f"Primary flow: {' â†’ '.join(primary_flow)}", "decision")
            logger.info(f"  Primary flow: {' â†’ '.join(primary_flow)}")
        primary_flow = self._normalize_primary_flow_top_to_bottom(primary_flow, layer_services, service_layer_map)
        
        # Step 5: Validate and optimize connections
        self.think("Optimizing connections: removing duplicates, adding missing links, fixing labels...", "tool_call")
        optimized_connections = self._optimize_connections(
            connections, services, service_layer_map, layer_services, primary_flow
        )
        
        logger.info(f"  Output: {len(optimized_connections)} optimized connections")
        
        # Step 6: VALIDATION - Detect warnings and errors
        self.think("Validating connections for warnings and errors...", "tool_call")
        validation_result = self.validate_connections(services, optimized_connections)
        
        errors_count = len(validation_result.get("errors", []))
        warnings_count = len(validation_result.get("warnings", []))
        
        if errors_count > 0:
            self.think(f"âš ï¸ Found {errors_count} error(s) in connections", "warning")
            logger.warning(f"  Validation: {errors_count} error(s), {warnings_count} warning(s)")
            for error in validation_result["errors"]:
                logger.warning(f"    ERROR: {error['message']}")
                self.think(f"Error: {error['message']}", "error")
        
        if warnings_count > 0:
            self.think(f"Found {warnings_count} warning(s) in connections", "observation")
            for warning in validation_result["warnings"][:5]:  # Log first 5
                logger.info(f"    WARNING: {warning['message']}")
        
        # Step 7: AUTO-FIX - Apply fixes for detected issues
        if errors_count > 0 or warnings_count > 0:
            self.think("Applying automatic fixes for detected issues...", "tool_call")
            services, optimized_connections, applied_fixes = self.auto_fix_connections(
                services, optimized_connections, validation_result
            )
            
            if applied_fixes:
                self.think(f"Applied {len(applied_fixes)} auto-fix(es)", "success")
                logger.info(f"  Auto-fixes applied: {len(applied_fixes)}")
                for fix in applied_fixes:
                    logger.info(f"    âœ“ {fix}")
                    self.think(f"Fixed: {fix}", "action")
                
                # Re-validate after fixes
                validation_result = self.validate_connections(services, optimized_connections)
                validation_result["auto_fixes_applied"] = applied_fixes
                
                remaining_errors = len(validation_result.get("errors", []))
                remaining_warnings = len(validation_result.get("warnings", []))
                self.think(f"Post-fix validation: {remaining_errors} errors, {remaining_warnings} warnings", "reflection")

            # Enforce top-to-bottom layout metadata and non-overlapping routing hints
            optimized_connections = self._apply_vertical_layout_constraints(optimized_connections, service_layer_map)
        
        # Step 8: Generate connection statistics
        connection_stats = self._generate_connection_stats(optimized_connections, services)
        connection_stats["validation"] = {
            "errors": errors_count,
            "warnings": warnings_count,
            "auto_fixes_applied": len(validation_result.get("auto_fixes_applied", []))
        }
        
        # Step 9: Build enhanced architecture
        enhanced_architecture = {
            **architecture_data,
            "services": services,
            "connections": optimized_connections,
            "primary_flow": primary_flow,
            "layout_direction": "top_to_bottom",
            "connection_routing": {
                "strategy": "orthogonal_lanes",
                "avoid_overlap": True
            },
            "connection_stats": connection_stats,
            "validation_result": validation_result
        }
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Self-Reflection
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        optimizations = connection_stats.get("optimizations_applied", [])
        self.think(f"Optimizations applied: {', '.join(optimizations) if optimizations else 'None needed'}", "reflection")
        
        reflection = self.reflect(enhanced_architecture, ["connection_coverage", "flow_direction"])
        if reflection.get("improvements_suggested"):
            self.think(f"Connection concerns: {', '.join(reflection['improvements_suggested'])}", "reflection")
        
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # AGENTIC BEHAVIOR: Inter-Agent Communication
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        orphan_count = connection_stats.get("orphan_services", 0)
        if orphan_count > 0:
            self.send_message(
                "ValidationAgent", "warning",
                f"Found {orphan_count} orphan services that were auto-connected. Review may be needed."
            )
        
        # Send validation summary to downstream agents
        validation_summary = connection_stats.get("validation", {})
        if validation_summary.get("errors", 0) > 0:
            self.send_message(
                "ValidationAgent", "error",
                f"Connection validation found {validation_summary['errors']} error(s) - some may need manual review"
            )
        
        if validation_summary.get("auto_fixes_applied", 0) > 0:
            self.send_message(
                "DiagramAgent", "info",
                f"Applied {validation_summary['auto_fixes_applied']} auto-fix(es) to connection issues"
            )
        
        self.send_message(
            "ReviewAgent", "insight",
            f"Connection optimization complete: {len(optimized_connections)} connections, primary flow established."
        )
        
        self.think(f"Connection optimization complete: {connection_stats.get('total_connections', 0)} connections", "success")
        logger.info(f"  Connection optimization complete: {connection_stats.get('total_connections', 0)} connections")
        logger.info("=" * 70)
        
        return {
            "agent": "connection_expert",
            "status": "completed",
            "enhanced_architecture": enhanced_architecture,
            "connection_stats": connection_stats,
            "primary_flow": primary_flow,
            "layout_direction": "top_to_bottom",
            "optimizations_applied": connection_stats.get("optimizations_applied", []),
            "validation_result": validation_result,
            "errors_found": errors_count,
            "warnings_found": warnings_count,
            "auto_fixes_applied": validation_result.get("auto_fixes_applied", []),
            "thinking_summary": self.get_thinking_summary()
        }
    
    def _ensure_users_entry_point(self, services: List[Dict]) -> tuple:
        """Ensure Users entry point exists in services"""
        has_users = any(
            s.get("name", "").lower() in ["users", "user", "client"] 
            for s in services if isinstance(s, dict)
        )
        
        if not has_users:
            users_service = {
                "name": "Users",
                "category": "external",
                "layer": 0,
                "resource_group": "",
                "subnet": "",
                "description": "End users accessing the application"
            }
            services.insert(0, users_service)
            return services, True
        
        return services, False
    
    def _build_service_layer_map(self, services: List[Dict]) -> Dict[str, int]:
        """Build mapping of service names to their layers"""
        layer_map = {}
        for svc in services:
            if isinstance(svc, dict):
                name = svc.get("name", "")
                # Use explicit layer if provided
                layer = svc.get("layer")
                if layer is None:
                    layer = self._get_service_layer(name)
                layer_map[name] = layer
        return layer_map
    
    def _get_service_layer(self, service_name: str) -> int:
        """Get layer for a service name"""
        name_lower = service_name.lower().strip()
        
        # Direct match
        if name_lower in self.SERVICE_LAYERS:
            return self.SERVICE_LAYERS[name_lower]
        
        # Strip Azure/Microsoft prefix
        for prefix in ["azure ", "microsoft "]:
            if name_lower.startswith(prefix):
                stripped = name_lower[len(prefix):]
                if stripped in self.SERVICE_LAYERS:
                    return self.SERVICE_LAYERS[stripped]
        
        # Keyword matching
        layer_keywords = {
            0: ["front door", "cdn", "traffic manager", "waf", "users", "client", "internet user"],
            1: ["gateway", "firewall", "load balancer", "api management", "apim"],
            2: ["app service", "function", "func-", "aks", "kubernetes", "container", "service bus", "event hub", "logic app", "portal"],
            3: ["sql", "cosmos", "database", "redis", "storage", "blob", "data lake", "postgresql", "mysql"],
            -1: ["key vault", "monitor", "insights", "entra", "defender", "sentinel", "log analytics"]
        }
        
        for layer, keywords in layer_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return layer
        
        return 2  # Default to compute
    
    def _categorize_by_layer(self, services: List[Dict], layer_map: Dict[str, int]) -> Dict[int, List[str]]:
        """Categorize services by their layer"""
        layer_services = {0: [], 1: [], 2: [], 3: [], -1: []}
        
        for svc in services:
            if isinstance(svc, dict):
                name = svc.get("name", "")
                layer = layer_map.get(name, 2)
                if layer in layer_services:
                    layer_services[layer].append(name)
        
        return layer_services
    
    def _build_primary_flow(self, layer_services: Dict[int, List[str]]) -> List[str]:
        """Build the primary flow chain from services"""
        flow = []
        
        # Layer 0: Users or edge service
        if "Users" in layer_services[0]:
            flow.append("Users")
        for svc in layer_services[0]:
            if svc != "Users":
                flow.append(svc)
                break
        
        # Layer 1: First gateway
        if layer_services[1]:
            flow.append(layer_services[1][0])
        
        # Layer 2: First compute
        for svc in layer_services[2]:
            # Prefer app service/functions over messaging
            if any(kw in svc.lower() for kw in ["app service", "function", "aks", "container"]):
                flow.append(svc)
                break
        else:
            if layer_services[2]:
                flow.append(layer_services[2][0])
        
        # Layer 3: First data service
        if layer_services[3]:
            flow.append(layer_services[3][0])
        
        return flow

    def _normalize_primary_flow_top_to_bottom(
        self,
        primary_flow: List[str],
        layer_services: Dict[int, List[str]],
        layer_map: Dict[str, int],
    ) -> List[str]:
        """Normalize primary flow to strict top-to-bottom ordering by layer."""
        normalized: List[str] = []

        # Always start from Users if available
        if "Users" in layer_services.get(0, []):
            normalized.append("Users")

        # Preserve existing flow services while enforcing ascending layer order
        for svc in primary_flow:
            if svc in normalized:
                continue
            if svc not in layer_map:
                continue
            normalized.append(svc)

        normalized.sort(key=lambda s: (layer_map.get(s, self._get_service_layer(s)), s.lower()))

        # Ensure users remains first if present
        if "Users" in normalized:
            normalized = ["Users"] + [s for s in normalized if s != "Users"]

        # Ensure at least one representative from each core layer exists
        for layer in [0, 1, 2, 3]:
            if not any(layer_map.get(s, self._get_service_layer(s)) == layer for s in normalized):
                candidates = layer_services.get(layer, [])
                if candidates:
                    candidate = candidates[0]
                    if candidate not in normalized:
                        normalized.append(candidate)

        return normalized
    
    def _optimize_connections(self, connections: List[Dict], services: List[Dict], 
                              layer_map: Dict[str, int], layer_services: Dict[int, List[str]],
                              primary_flow: List[str]) -> List[Dict]:
        """Optimize connections for professional diagram layout"""
        optimized = []
        existing_pairs = set()
        optimizations = []
        
        # Step 1: Process existing connections - validate and fix direction
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            
            source = conn.get("source", "")
            target = conn.get("target", "")
            label = conn.get("label", "")
            conn_type = conn.get("type", "")
            
            if not source or not target:
                continue
            
            # Skip VNet peering
            if conn_type in ("vnet_peering", "peering"):
                optimized.append(conn)
                existing_pairs.add((source, target))
                continue
            
            source_layer = layer_map.get(source, self._get_service_layer(source))
            target_layer = layer_map.get(target, self._get_service_layer(target))
            
            # Fix reverse connections
            if source_layer > target_layer and source_layer != -1 and target_layer != -1:
                # Flip the connection
                source, target = target, source
                source_layer, target_layer = target_layer, source_layer
                label = self._get_professional_label(source_layer, target_layer, source, target)
                optimizations.append(f"Flipped: {conn.get('source')} â†’ {conn.get('target')}")
            
            # Skip duplicates
            if (source, target) in existing_pairs:
                continue

            # Route skip-layer traffic through intermediate layers to keep vertical topology clean
            if source_layer != -1 and target_layer != -1 and abs(target_layer - source_layer) > 1:
                segmented_pairs = self._route_via_intermediate_layers(source, target, layer_services, layer_map)
                for seg_src, seg_tgt in segmented_pairs:
                    if (seg_src, seg_tgt) in existing_pairs:
                        continue
                    seg_src_layer = layer_map.get(seg_src, self._get_service_layer(seg_src))
                    seg_tgt_layer = layer_map.get(seg_tgt, self._get_service_layer(seg_tgt))
                    optimized.append({
                        "source": seg_src,
                        "target": seg_tgt,
                        "label": self._get_professional_label(seg_src_layer, seg_tgt_layer, seg_src, seg_tgt),
                        "flow_type": self._determine_flow_type(seg_src_layer, seg_tgt_layer)
                    })
                    existing_pairs.add((seg_src, seg_tgt))
                optimizations.append(f"Rerouted skip-layer connection: {source} â†’ {target}")
                continue
            
            # Add flow_type if missing
            flow_type = conn.get("flow_type") or self._determine_flow_type(source_layer, target_layer)
            
            # Ensure professional label
            if not label or label in ["", "connection", "link"]:
                label = self._get_professional_label(source_layer, target_layer, source, target)
            
            optimized.append({
                "source": source,
                "target": target,
                "label": label,
                "flow_type": flow_type,
                **({"type": conn_type} if conn_type else {})
            })
            existing_pairs.add((source, target))
        
        # Step 2: Inject primary flow chain connections if missing
        for i in range(len(primary_flow) - 1):
            src = primary_flow[i]
            tgt = primary_flow[i + 1]
            
            if (src, tgt) not in existing_pairs:
                src_layer = layer_map.get(src, self._get_service_layer(src))
                tgt_layer = layer_map.get(tgt, self._get_service_layer(tgt))
                
                label = self._get_professional_label(src_layer, tgt_layer, src, tgt)
                flow_type = self._determine_flow_type(src_layer, tgt_layer)
                
                optimized.append({
                    "source": src,
                    "target": tgt,
                    "label": label,
                    "flow_type": flow_type
                })
                existing_pairs.add((src, tgt))
                optimizations.append(f"Chain injected: {src} â†’ {tgt}")
        
        # Step 3: Connect orphan services
        connected_services = set()
        for conn in optimized:
            connected_services.add(conn.get("source", ""))
            connected_services.add(conn.get("target", ""))
        
        orphans = [svc.get("name", "") for svc in services 
                   if isinstance(svc, dict) and svc.get("name", "") not in connected_services]
        
        for orphan in orphans:
            orphan_layer = layer_map.get(orphan, self._get_service_layer(orphan))
            
            # Find best connection target based on layer
            target = None
            if orphan_layer == -1:  # Cross-cutting
                # Connect FROM compute TO cross-cutting
                for compute_svc in layer_services[2]:
                    if compute_svc in connected_services:
                        target = compute_svc
                        break
                if target:
                    label = self._get_professional_label(2, -1, target, orphan)
                    optimized.append({
                        "source": target,
                        "target": orphan,
                        "label": label,
                        "flow_type": "compute_to_crosscutting"
                    })
                    connected_services.add(orphan)
                    optimizations.append(f"Orphan connected: {target} â†’ {orphan}")
            else:
                # Find upstream service to connect from
                for check_layer in range(orphan_layer - 1, -2, -1):
                    if check_layer == -1:
                        continue
                    for svc in layer_services.get(check_layer, []):
                        if svc in connected_services:
                            target = svc
                            break
                    if target:
                        break
                
                if target:
                    label = self._get_professional_label(layer_map.get(target, 2), orphan_layer, target, orphan)
                    optimized.append({
                        "source": target,
                        "target": orphan,
                        "label": label,
                        "flow_type": self._determine_flow_type(layer_map.get(target, 2), orphan_layer)
                    })
                    connected_services.add(orphan)
                    optimizations.append(f"Orphan connected: {target} â†’ {orphan}")
        
        return optimized

    def _route_via_intermediate_layers(
        self,
        source: str,
        target: str,
        layer_services: Dict[int, List[str]],
        layer_map: Dict[str, int],
    ) -> List[Tuple[str, str]]:
        """Break skip-layer connections into adjacent-layer segments for vertical routing."""
        source_layer = layer_map.get(source, self._get_service_layer(source))
        target_layer = layer_map.get(target, self._get_service_layer(target))

        if source_layer == -1 or target_layer == -1:
            return [(source, target)]

        if abs(target_layer - source_layer) <= 1:
            return [(source, target)]

        step = 1 if target_layer > source_layer else -1
        current = source
        segments: List[Tuple[str, str]] = []

        for layer in range(source_layer + step, target_layer, step):
            candidates = [s for s in layer_services.get(layer, []) if s != current and s != target]
            if not candidates:
                # Fallback to direct connection when no intermediate service exists
                return [(source, target)]
            next_hop = candidates[0]
            segments.append((current, next_hop))
            current = next_hop

        segments.append((current, target))
        return segments

    def _apply_vertical_layout_constraints(
        self,
        connections: List[Dict],
        layer_map: Dict[str, int],
    ) -> List[Dict]:
        """Attach deterministic top-to-bottom orthogonal routing hints and lane indexes."""
        lane_counters: Dict[Tuple[int, int], int] = {}
        constrained: List[Dict] = []

        # Stable sort keeps routing lanes deterministic between runs.
        sorted_connections = sorted(
            connections,
            key=lambda c: (
                layer_map.get(c.get("source", ""), self._get_service_layer(c.get("source", ""))),
                layer_map.get(c.get("target", ""), self._get_service_layer(c.get("target", ""))),
                c.get("source", ""),
                c.get("target", ""),
            ),
        )

        for conn in sorted_connections:
            source = conn.get("source", "")
            target = conn.get("target", "")
            source_layer = layer_map.get(source, self._get_service_layer(source))
            target_layer = layer_map.get(target, self._get_service_layer(target))

            lane_key = (source_layer, target_layer)
            lane_index = lane_counters.get(lane_key, 0)
            lane_counters[lane_key] = lane_index + 1

            routing_hints = {
                "layout_direction": "top_to_bottom",
                "line_style": "orthogonal",
                "avoid_overlap": True,
                "source_port": "south",
                "target_port": "north",
                "lane": lane_index,
            }

            constrained.append({
                **conn,
                "routing_hints": routing_hints,
            })

        return constrained
    
    def _determine_flow_type(self, source_layer: int, target_layer: int) -> str:
        """Determine connection flow type"""
        if source_layer == 0 and target_layer == 0:
            return "entry_point"
        if source_layer == 0 and target_layer == 1:
            return "edge_to_gateway"
        if source_layer == 1 and target_layer == 2:
            return "gateway_to_compute"
        if source_layer == 2 and target_layer == 3:
            return "compute_to_data"
        if source_layer == 2 and target_layer == 2:
            return "compute_to_integration"
        if target_layer == -1:
            return "compute_to_crosscutting"
        return "service_integration"
    
    def _get_professional_label(self, source_layer: int, target_layer: int, source: str, target: str) -> str:
        """Get a professional connection label"""
        import random
        
        flow_type = self._determine_flow_type(source_layer, target_layer)
        
        if flow_type in self.CONNECTION_LABELS:
            labels = self.CONNECTION_LABELS[flow_type]
            # Try to match based on service names
            target_lower = target.lower()
            if "sql" in target_lower:
                return "SQL queries"
            if "cosmos" in target_lower:
                return "Document operations"
            if "redis" in target_lower:
                return "Cache operations"
            if "key vault" in target_lower:
                return "Secrets retrieval"
            if "monitor" in target_lower or "insights" in target_lower:
                return "Telemetry & diagnostics"
            if "service bus" in target_lower:
                return "Message publishing"
            if "event" in target_lower:
                return "Event publishing"
            if "storage" in target_lower:
                return "Blob operations"
            
            return labels[0]  # Return first label as default
        
        return "Service integration"
    
    def _generate_connection_stats(self, connections: List[Dict], services: List[Dict]) -> Dict[str, Any]:
        """Generate statistics about the connections"""
        flow_type_counts = {}
        for conn in connections:
            ft = conn.get("flow_type", "unknown")
            flow_type_counts[ft] = flow_type_counts.get(ft, 0) + 1
        
        connected_services = set()
        for conn in connections:
            connected_services.add(conn.get("source", ""))
            connected_services.add(conn.get("target", ""))
        
        orphan_count = len([s for s in services if isinstance(s, dict) and s.get("name", "") not in connected_services])
        
        return {
            "total_connections": len(connections),
            "flow_type_distribution": flow_type_counts,
            "services_connected": len(connected_services),
            "orphan_services": orphan_count,
            "has_entry_point": any(c.get("flow_type") == "entry_point" for c in connections),
            "has_primary_chain": all(ft in flow_type_counts for ft in ["entry_point", "gateway_to_compute", "compute_to_data"]) if flow_type_counts else False
        }
    
    def validate_connections(self, services: List[Dict], connections: List[Dict]) -> Dict[str, Any]:
        """
        Validate connections and detect warnings/errors that need fixing.
        Returns validation result with issues and auto-fix suggestions.
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "auto_fixes_applied": [],
            "suggestions": []
        }
        
        service_names = {s.get("name", "") for s in services if isinstance(s, dict)}
        
        # --- ERROR Detection ---
        
        # 1. Check for connections to non-existent services
        for conn in connections:
            source = conn.get("source", "")
            target = conn.get("target", "")
            
            if source and source not in service_names:
                validation_result["errors"].append({
                    "type": "missing_source",
                    "message": f"Connection source '{source}' does not exist in services",
                    "connection": conn,
                    "severity": "error"
                })
                validation_result["is_valid"] = False
            
            if target and target not in service_names:
                validation_result["errors"].append({
                    "type": "missing_target",
                    "message": f"Connection target '{target}' does not exist in services",
                    "connection": conn,
                    "severity": "error"
                })
                validation_result["is_valid"] = False
        
        # 2. Check for self-referencing connections
        for conn in connections:
            if conn.get("source") == conn.get("target"):
                validation_result["errors"].append({
                    "type": "self_reference",
                    "message": f"Service '{conn.get('source')}' has a connection to itself",
                    "connection": conn,
                    "severity": "error"
                })
        
        # 3. Check for duplicate connections
        seen_pairs = set()
        for conn in connections:
            pair = (conn.get("source", ""), conn.get("target", ""))
            if pair in seen_pairs:
                validation_result["warnings"].append({
                    "type": "duplicate_connection",
                    "message": f"Duplicate connection: {pair[0]} â†’ {pair[1]}",
                    "connection": conn,
                    "severity": "warning"
                })
            seen_pairs.add(pair)
        
        # --- WARNING Detection ---
        
        # 4. Check for orphan services (no connections)
        connected_services = set()
        for conn in connections:
            connected_services.add(conn.get("source", ""))
            connected_services.add(conn.get("target", ""))
        
        orphans = service_names - connected_services
        # Exclude Users/external services from orphan check
        orphans = {o for o in orphans if o.lower() not in ["users", "client", "external"]}
        
        for orphan in orphans:
            validation_result["warnings"].append({
                "type": "orphan_service",
                "message": f"Service '{orphan}' has no connections",
                "service": orphan,
                "severity": "warning",
                "auto_fix_available": True
            })
        
        # 5. Check for missing entry point
        has_users = any(s.get("name", "").lower() in ["users", "user", "client"] for s in services if isinstance(s, dict))
        has_entry_connection = any(
            conn.get("source", "").lower() in ["users", "user", "client"]
            for conn in connections
        )
        
        if not has_entry_connection and len(services) > 1:
            validation_result["warnings"].append({
                "type": "missing_entry_point",
                "message": "No entry point connection from Users detected",
                "severity": "warning",
                "auto_fix_available": True
            })
        
        # 6. Check for reverse layer flows (data â†’ compute instead of compute â†’ data)
        reverse_flows = []
        for conn in connections:
            source = conn.get("source", "")
            target = conn.get("target", "")
            source_layer = self._get_service_layer(source)
            target_layer = self._get_service_layer(target)
            
            # Skip cross-cutting services
            if source_layer == -1 or target_layer == -1:
                continue
            
            # Check if flow is reversed (higher layer â†’ lower layer)
            if source_layer > target_layer and source_layer != -1 and target_layer != -1:
                validation_result["warnings"].append({
                    "type": "reverse_flow",
                    "message": f"Reverse flow detected: {source} (L{source_layer}) â†’ {target} (L{target_layer})",
                    "connection": conn,
                    "severity": "warning",
                    "auto_fix_available": True,
                    "suggested_fix": {"source": target, "target": source}
                })
                reverse_flows.append(conn)
        
        # 7. Check for missing security connections
        has_key_vault = any("key vault" in s.get("name", "").lower() for s in services if isinstance(s, dict))
        has_key_vault_connections = any(
            "key vault" in conn.get("target", "").lower() or "key vault" in conn.get("source", "").lower()
            for conn in connections
        )
        
        if has_key_vault and not has_key_vault_connections:
            validation_result["warnings"].append({
                "type": "disconnected_security",
                "message": "Key Vault exists but has no connections - compute services should retrieve secrets",
                "severity": "warning",
                "auto_fix_available": True
            })
        
        # 8. Check for potentially crossing connections (heuristic)
        crossing_risk = self._detect_crossing_risk(services, connections)
        if crossing_risk:
            validation_result["warnings"].extend(crossing_risk)
        
        # --- Generate Suggestions ---
        
        # Suggest monitoring connections if monitor services exist but aren't connected to all compute
        monitor_services = [s.get("name") for s in services 
                          if isinstance(s, dict) and any(m in s.get("name", "").lower() 
                              for m in ["monitor", "insights", "log analytics"])]
        
        compute_services = [s.get("name") for s in services
                          if isinstance(s, dict) and self._get_service_layer(s.get("name", "")) == 2]
        
        if monitor_services and compute_services:
            connected_to_monitor = set()
            for conn in connections:
                if conn.get("target", "") in monitor_services:
                    connected_to_monitor.add(conn.get("source", ""))
            
            unmonitored = set(compute_services) - connected_to_monitor
            for svc in unmonitored:
                validation_result["suggestions"].append({
                    "type": "add_monitoring",
                    "message": f"Consider connecting '{svc}' to monitoring services",
                    "suggestion": {"source": svc, "target": monitor_services[0], "label": "Telemetry"}
                })
        
        return validation_result
    
    def _detect_crossing_risk(self, services: List[Dict], connections: List[Dict]) -> List[Dict]:
        """Detect connections that might cross over other components"""
        warnings = []
        
        # Build simple position model based on layer distribution
        layer_positions = {}
        for svc in services:
            if isinstance(svc, dict):
                name = svc.get("name", "")
                layer = self._get_service_layer(name)
                if layer not in layer_positions:
                    layer_positions[layer] = []
                layer_positions[layer].append(name)
        
        # Check for "skip-layer" connections that might cross
        for conn in connections:
            source = conn.get("source", "")
            target = conn.get("target", "")
            source_layer = self._get_service_layer(source)
            target_layer = self._get_service_layer(target)
            
            # Skip cross-cutting
            if source_layer == -1 or target_layer == -1:
                continue
            
            # If connection skips more than 1 layer, it might cross other services
            layer_diff = abs(target_layer - source_layer)
            if layer_diff > 1:
                # Check if there are services in between
                intermediate_layers = range(min(source_layer, target_layer) + 1, max(source_layer, target_layer))
                intermediate_services = sum(len(layer_positions.get(l, [])) for l in intermediate_layers)
                
                if intermediate_services > 0:
                    warnings.append({
                        "type": "potential_crossing",
                        "message": f"Connection {source} â†’ {target} spans {layer_diff} layers with {intermediate_services} services in between",
                        "connection": conn,
                        "severity": "info",
                        "suggestion": "Consider using waypoint routing or intermediate service"
                    })
        
        return warnings
    
    def auto_fix_connections(self, services: List[Dict], connections: List[Dict], 
                            validation_result: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], List[str]]:
        """
        Auto-fix detected connection issues.
        Returns: (fixed_services, fixed_connections, applied_fixes)
        """
        fixed_connections = list(connections)
        fixed_services = list(services)
        applied_fixes = []
        
        # Fix 1: Remove duplicate connections
        duplicates = [w for w in validation_result.get("warnings", []) if w.get("type") == "duplicate_connection"]
        if duplicates:
            seen_pairs = set()
            deduped = []
            for conn in fixed_connections:
                pair = (conn.get("source", ""), conn.get("target", ""))
                if pair not in seen_pairs:
                    deduped.append(conn)
                    seen_pairs.add(pair)
                else:
                    applied_fixes.append(f"Removed duplicate: {pair[0]} â†’ {pair[1]}")
            fixed_connections = deduped
        
        # Fix 2: Remove self-referencing connections
        self_refs = [e for e in validation_result.get("errors", []) if e.get("type") == "self_reference"]
        if self_refs:
            before_count = len(fixed_connections)
            fixed_connections = [c for c in fixed_connections if c.get("source") != c.get("target")]
            if len(fixed_connections) < before_count:
                applied_fixes.append(f"Removed {before_count - len(fixed_connections)} self-referencing connection(s)")
        
        # Fix 3: Flip reverse flow connections
        reverse_flows = [w for w in validation_result.get("warnings", []) if w.get("type") == "reverse_flow"]
        for rf in reverse_flows:
            conn = rf.get("connection", {})
            for i, c in enumerate(fixed_connections):
                if c.get("source") == conn.get("source") and c.get("target") == conn.get("target"):
                    # Flip the connection
                    fixed_connections[i] = {
                        **c,
                        "source": c.get("target"),
                        "target": c.get("source"),
                        "label": self._get_professional_label(
                            self._get_service_layer(c.get("target", "")),
                            self._get_service_layer(c.get("source", "")),
                            c.get("target", ""),
                            c.get("source", "")
                        )
                    }
                    applied_fixes.append(f"Flipped reverse flow: {conn.get('source')} â†” {conn.get('target')}")
                    break
        
        # Fix 4: Add Users entry point if missing
        missing_entry = [w for w in validation_result.get("warnings", []) if w.get("type") == "missing_entry_point"]
        if missing_entry:
            # Find first edge/gateway service
            has_users = any(s.get("name", "").lower() in ["users", "user"] for s in fixed_services if isinstance(s, dict))
            if not has_users:
                fixed_services.insert(0, {
                    "name": "Users",
                    "category": "external",
                    "layer": 0,
                    "description": "End users"
                })
                applied_fixes.append("Added Users entry point")
            
            # Connect to first gateway/edge service
            edge_services = [s.get("name") for s in fixed_services 
                           if isinstance(s, dict) and self._get_service_layer(s.get("name", "")) in [0, 1]
                           and s.get("name", "").lower() not in ["users", "user"]]
            
            if edge_services:
                first_edge = edge_services[0]
                if not any(c.get("source") == "Users" for c in fixed_connections):
                    fixed_connections.insert(0, {
                        "source": "Users",
                        "target": first_edge,
                        "label": "HTTPS requests",
                        "flow_type": "entry_point"
                    })
                    applied_fixes.append(f"Connected Users â†’ {first_edge}")
        
        # Fix 5: Connect orphan services
        orphans = [w for w in validation_result.get("warnings", []) if w.get("type") == "orphan_service"]
        service_names = {s.get("name", "") for s in fixed_services if isinstance(s, dict)}
        connected = set()
        for c in fixed_connections:
            connected.add(c.get("source", ""))
            connected.add(c.get("target", ""))
        
        for orphan_warning in orphans:
            orphan_name = orphan_warning.get("service", "")
            if orphan_name and orphan_name not in connected:
                orphan_layer = self._get_service_layer(orphan_name)
                
                # Find best upstream service to connect from
                best_source = None
                best_distance = float('inf')
                
                for svc in fixed_services:
                    if isinstance(svc, dict):
                        svc_name = svc.get("name", "")
                        if svc_name in connected and svc_name != orphan_name:
                            svc_layer = self._get_service_layer(svc_name)
                            
                            # Cross-cutting services should connect FROM compute
                            if orphan_layer == -1:
                                if svc_layer == 2:  # Compute layer
                                    best_source = svc_name
                                    break
                            # Normal services connect from upstream layer
                            elif svc_layer == orphan_layer - 1:
                                best_source = svc_name
                                break
                            elif svc_layer < orphan_layer and abs(svc_layer - orphan_layer) < best_distance:
                                best_source = svc_name
                                best_distance = abs(svc_layer - orphan_layer)
                
                if best_source:
                    label = self._get_professional_label(
                        self._get_service_layer(best_source),
                        orphan_layer,
                        best_source,
                        orphan_name
                    )
                    fixed_connections.append({
                        "source": best_source,
                        "target": orphan_name,
                        "label": label,
                        "flow_type": self._determine_flow_type(self._get_service_layer(best_source), orphan_layer)
                    })
                    connected.add(orphan_name)
                    applied_fixes.append(f"Connected orphan: {best_source} â†’ {orphan_name}")
        
        return fixed_services, fixed_connections, applied_fixes


