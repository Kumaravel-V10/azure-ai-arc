"""
Draw.io Reference Analyzer
Analyzes converted Draw.io diagrams to learn connection patterns, layouts, and architectural relationships.
Provides reference data for intelligent architecture generation with professional diagrams.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
import math
from config import drawio_config

logger = logging.getLogger(__name__)


@dataclass
class ServicePattern:
    """Represents a service and its common connection patterns"""
    name: str
    normalized_name: str
    category: str
    common_sources: List[str] = field(default_factory=list)  # Services that connect TO this
    common_targets: List[str] = field(default_factory=list)  # Services this connects TO
    connection_labels: List[str] = field(default_factory=list)  # Common connection labels
    typical_position: Dict[str, float] = field(default_factory=dict)  # Average x, y position ratio
    container_types: List[str] = field(default_factory=list)  # Types of containers it appears in
    occurrence_count: int = 0


@dataclass
class ConnectionPattern:
    """Represents a common connection pattern between services"""
    source_category: str
    target_category: str
    source_service: str
    target_service: str
    labels: List[str] = field(default_factory=list)
    frequency: int = 0


@dataclass
class LayoutPattern:
    """Represents layout patterns learned from reference diagrams"""
    category: str
    typical_x_ratio: float  # Position as ratio of canvas width (0-1)
    typical_y_ratio: float  # Position as ratio of canvas height (0-1)
    z_layer: int  # Vertical layer (0=top/entry, 1=middle, 2=backend, 3=data)
    horizontal_order: int  # Horizontal position within layer


class DrawioReferenceAnalyzer:
    """
    Analyzes converted Draw.io diagrams to extract patterns for:
    - Connection patterns (what connects to what)
    - Layout patterns (where services should be positioned)
    - Grouping patterns (how to organize containers)
    - Label patterns (meaningful connection descriptions)
    """
    
    AZURE_SERVICE_CATEGORIES = {
        # Entry/Edge Layer (z=0)
        "networking_edge": ["front door", "cdn", "traffic manager", "waf", "ddos", "dns"],
        # Gateway Layer (z=1)  
        "networking_gateway": ["application gateway", "load balancer", "api management", "firewall"],
        # Compute Layer (z=2)
        "compute": ["app service", "function", "web app", "kubernetes", "aks", "container", "vm", "virtual machine", "batch"],
        # Integration Layer (z=2)
        "integration": ["service bus", "event hub", "event grid", "logic app", "data factory"],
        # Data Layer (z=3)
        "data": ["sql", "cosmos", "database", "postgresql", "mysql", "redis", "cache", "storage", "blob"],
        # Security (distributed across layers)
        "security": ["key vault", "entra", "identity", "certificate", "managed identity", "defender", "sentinel"],
        # Monitoring (distributed)
        "monitoring": ["monitor", "insights", "log analytics", "diagnostic"],
        # AI/ML
        "ai": ["cognitive", "openai", "machine learning", "search", "bot"]
    }
    
    # Layer assignments for proper vertical positioning
    CATEGORY_LAYERS = {
        "networking_edge": 0,
        "networking_gateway": 1,
        "compute": 2,
        "integration": 2,
        "ai": 2,
        "data": 3,
        "security": 2,
        "monitoring": 3
    }
    
    def __init__(self, reference_dir: str = None):
        self.reference_dir = Path(reference_dir) if reference_dir else Path(__file__).parent.parent / "visiofiles" / "drawio_output"
        self.service_patterns: Dict[str, ServicePattern] = {}
        self.connection_patterns: List[ConnectionPattern] = []
        self.layout_patterns: Dict[str, LayoutPattern] = {}
        self.common_connection_labels: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        self.reference_architectures: List[Dict] = []
        self._is_indexed = False
        
    def build_index(self, force_rebuild: bool = False) -> bool:
        """Build the reference index by analyzing all Draw.io files"""
        if self._is_indexed and not force_rebuild:
            return True
            
        if not self.reference_dir.exists():
            logger.warning(f"Reference directory not found: {self.reference_dir}")
            return False
        
        drawio_files = list(self.reference_dir.glob("*.drawio"))
        if not drawio_files:
            logger.warning(f"No Draw.io files found in {self.reference_dir}")
            return False
        
        logger.info(f"Building reference index from {len(drawio_files)} Draw.io diagrams...")
        
        for drawio_file in drawio_files:
            try:
                self._analyze_file(drawio_file)
            except Exception as e:
                logger.warning(f"Error analyzing {drawio_file.name}: {e}")
                continue
        
        # Post-process to calculate averages and patterns
        self._calculate_layout_patterns()
        self._calculate_connection_patterns()
        
        self._is_indexed = True
        logger.info(f"Reference index built: {len(self.service_patterns)} services, {len(self.connection_patterns)} connection patterns")
        return True
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Draw.io file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            root = ET.fromstring(content)
            diagram = root.find('.//diagram')
            if diagram is None:
                return
            
            model = diagram.find('.//mxGraphModel')
            if model is None:
                return
            
            # Get canvas dimensions
            canvas_w = float(model.get('pageWidth', drawio_config.FALLBACK_PAGE_WIDTH))
            canvas_h = float(model.get('pageHeight', drawio_config.FALLBACK_PAGE_HEIGHT))
            
            # Extract components
            components = self._extract_components_from_model(model, canvas_w, canvas_h)
            connections = self._extract_connections_from_model(model)
            
            # Store reference architecture
            self.reference_architectures.append({
                "name": file_path.stem,
                "components": components,
                "connections": connections,
                "canvas_size": (canvas_w, canvas_h)
            })
            
            # Update service patterns
            for comp in components:
                self._update_service_pattern(comp, canvas_w, canvas_h)
            
            # Update connection patterns
            for conn in connections:
                self._update_connection_pattern(conn, components)
                
        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")
    
    def _extract_components_from_model(self, model: ET.Element, canvas_w: float, canvas_h: float) -> List[Dict]:
        """Extract components from mxGraphModel"""
        components = []
        
        for cell in model.findall('.//mxCell[@vertex="1"]'):
            cell_id = cell.get('id', '')
            if cell_id in ['0', '1']:
                continue
            
            value = cell.get('value', '')
            style = cell.get('style', '')
            
            # Skip empty or container-only cells
            if not value or 'swimlane' in style.lower():
                continue
            
            # Clean the service name
            cleaned_name = self._clean_service_name(value)
            
            # Skip invalid/internal service names
            if not self._is_valid_service_name(cleaned_name):
                continue
            
            # Get position
            geometry = cell.find('mxGeometry')
            x, y, w, h = 0, 0, 64, 64
            if geometry is not None:
                x = float(geometry.get('x', 0))
                y = float(geometry.get('y', 0))
                w = float(geometry.get('width', 64))
                h = float(geometry.get('height', 64))
            
            # Determine service category
            category = self._categorize_service(cleaned_name, style)
            
            components.append({
                "id": cell_id,
                "name": cleaned_name,
                "category": category,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "x_ratio": x / canvas_w if canvas_w > 0 else 0.5,
                "y_ratio": y / canvas_h if canvas_h > 0 else 0.5
            })
        
        return components
    
    def _is_valid_service_name(self, name: str) -> bool:
        """Check if a name is a valid Azure service name (not internal XML structure)"""
        if not name or len(name) < 3:
            return False
        
        name_lower = name.lower().strip()
        
        # Exclude internal XML/SVG structure names
        invalid_prefixes = [
            'page', 'layer', 'path', 'rect', 'circle', 'ellipse', 'polygon',
            'group', 'defs', 'clippath', 'mask', 'filter', 'lineargradient',
            'radialgradient', 'svg', 'tspan', 'use', 'symbol',
            'image', 'style', 'script', 'metadata', 'title', 'desc',
            'hexagon', 'icon', 'solid', 'dashed', 'arrow', 'line',
            'shape', 'connector', 'edge', 'vertex', 'cell', 'mxcell'
        ]
        
        # Check exact matches for short invalid names
        invalid_exact = [
            'solid', 'dashed', 'dotted', 'none', 'hidden', 'visible',
            'true', 'false', 'yes', 'no', 'on', 'off', 'auto',
            'left', 'right', 'top', 'bottom', 'center', 'middle',
            'rectangle', 'square', 'triangle', 'diamond', 'star',
            'container', 'default', 'normal', 'bold', 'italic'
        ]
        
        if name_lower in invalid_exact:
            return False
        
        # Check if name starts with invalid prefixes followed by numbers
        for pattern in invalid_prefixes:
            if name_lower.startswith(pattern):
                remainder = name_lower[len(pattern):]
                # If remainder is empty, digits, or digits with dashes/underscores
                if not remainder or remainder.replace('-', '').replace('_', '').isdigit():
                    return False
        
        # Exclude purely numeric or hex strings (like cell IDs)
        cleaned = name_lower.replace('-', '').replace('_', '')
        if cleaned.isdigit():
            return False
        
        # Check for hex-like strings (common in IDs) - more than 8 chars of hex
        if len(name) > 8 and all(c in '0123456789abcdef' for c in cleaned):
            return False
        
        # Check for patterns like "g70", "ee75dd061aca...", "iconnetworking67" etc
        if re.match(r'^[a-z]\d+$', name_lower):  # Single letter + digits
            return False
        
        # Check for patterns like "iconXXX123" or "hexagonXXX" (word ending with numbers)
        if re.match(r'^[a-z]+\d{2,}$', name_lower):  # Letters followed by 2+ digits
            return False
        
        # Check for single digit or short meaningless names
        if len(name) <= 2 or name.isdigit():
            return False
        
        # Valid names should contain at least 2 letters
        letter_count = sum(1 for c in name if c.isalpha())
        if letter_count < 2:
            return False
        
        # Prefer names that look like Azure services (have spaces or contain azure keywords)
        azure_keywords = [
            'azure', 'app', 'service', 'function', 'storage', 'sql', 'cosmos',
            'redis', 'key vault', 'monitor', 'gateway', 'front door', 'cdn',
            'api', 'event', 'bus', 'hub', 'kubernetes', 'aks', 'container',
            'vm', 'virtual', 'network', 'vnet', 'subnet', 'firewall', 'waf',
            'load balancer', 'identity', 'entra', 'database', 'postgresql',
            'mysql', 'synapse', 'data', 'factory', 'logic', 'search', 'cognitive',
            'openai', 'machine learning', 'bot', 'dns', 'private', 'endpoint',
            'certificate', 'defender', 'sentinel', 'backup', 'site recovery',
            'traffic manager', 'expressroute', 'vpn', 'bastion', 'nat', 'policy'
        ]
        
        # If name contains Azure keywords, it's likely valid
        if any(kw in name_lower for kw in azure_keywords):
            return True
        
        # If name has spaces and reasonable length, probably a label
        if ' ' in name and len(name) >= 4:
            return True
        
        # Default: accept if it looks like a reasonable name (alphanumeric with some letters)
        return len(name) >= 4 and letter_count >= 3
    
    def _extract_connections_from_model(self, model: ET.Element) -> List[Dict]:
        """Extract connections from mxGraphModel"""
        connections = []
        
        for cell in model.findall('.//mxCell[@edge="1"]'):
            source = cell.get('source', '')
            target = cell.get('target', '')
            label = cell.get('value', '')
            
            if source and target:
                connections.append({
                    "source_id": source,
                    "target_id": target,
                    "label": self._clean_connection_label(label)
                })
        
        return connections
    
    def _update_service_pattern(self, component: Dict, canvas_w: float, canvas_h: float):
        """Update service pattern statistics"""
        name = component["name"]
        normalized = self._normalize_service_name(name)
        category = component["category"]
        
        if normalized not in self.service_patterns:
            self.service_patterns[normalized] = ServicePattern(
                name=name,
                normalized_name=normalized,
                category=category,
                typical_position={"x_sum": 0, "y_sum": 0, "count": 0}
            )
        
        pattern = self.service_patterns[normalized]
        pattern.occurrence_count += 1
        pattern.typical_position["x_sum"] += component["x_ratio"]
        pattern.typical_position["y_sum"] += component["y_ratio"]
        pattern.typical_position["count"] += 1
    
    def _update_connection_pattern(self, connection: Dict, components: List[Dict]):
        """Update connection pattern statistics"""
        # Find source and target components
        source_comp = next((c for c in components if c["id"] == connection["source_id"]), None)
        target_comp = next((c for c in components if c["id"] == connection["target_id"]), None)
        
        if not source_comp or not target_comp:
            return
        
        source_name = self._normalize_service_name(source_comp["name"])
        target_name = self._normalize_service_name(target_comp["name"])
        source_cat = source_comp["category"]
        target_cat = target_comp["category"]
        label = connection["label"]
        
        # Update service patterns with connection info
        if source_name in self.service_patterns:
            if target_name not in self.service_patterns[source_name].common_targets:
                self.service_patterns[source_name].common_targets.append(target_name)
        
        if target_name in self.service_patterns:
            if source_name not in self.service_patterns[target_name].common_sources:
                self.service_patterns[target_name].common_sources.append(source_name)
        
        # Store connection labels
        key = (source_cat, target_cat)
        if label and label not in self.common_connection_labels[key]:
            self.common_connection_labels[key].append(label)
    
    def _calculate_layout_patterns(self):
        """Calculate average layout patterns from collected data"""
        for normalized_name, pattern in self.service_patterns.items():
            if pattern.typical_position["count"] > 0:
                avg_x = pattern.typical_position["x_sum"] / pattern.typical_position["count"]
                avg_y = pattern.typical_position["y_sum"] / pattern.typical_position["count"]
                
                # Determine layer based on category and vertical position
                layer = self.CATEGORY_LAYERS.get(pattern.category, 2)
                
                self.layout_patterns[normalized_name] = LayoutPattern(
                    category=pattern.category,
                    typical_x_ratio=avg_x,
                    typical_y_ratio=avg_y,
                    z_layer=layer,
                    horizontal_order=int(avg_x * 10)  # 0-10 scale
                )
    
    def _calculate_connection_patterns(self):
        """Calculate common connection patterns"""
        pattern_counts = defaultdict(lambda: {"count": 0, "labels": []})
        
        for ref in self.reference_architectures:
            components = {c["id"]: c for c in ref["components"]}
            
            for conn in ref["connections"]:
                source = components.get(conn["source_id"])
                target = components.get(conn["target_id"])
                
                if source and target:
                    key = (source["category"], target["category"], 
                           self._normalize_service_name(source["name"]),
                           self._normalize_service_name(target["name"]))
                    pattern_counts[key]["count"] += 1
                    if conn["label"]:
                        pattern_counts[key]["labels"].append(conn["label"])
        
        # Convert to ConnectionPattern objects
        for key, data in pattern_counts.items():
            if data["count"] >= 2:  # Only patterns that appear multiple times
                self.connection_patterns.append(ConnectionPattern(
                    source_category=key[0],
                    target_category=key[1],
                    source_service=key[2],
                    target_service=key[3],
                    labels=list(set(data["labels"]))[:5],  # Top 5 unique labels
                    frequency=data["count"]
                ))
        
        # Sort by frequency
        self.connection_patterns.sort(key=lambda x: x.frequency, reverse=True)
    
    def _categorize_service(self, name: str, style: str) -> str:
        """Categorize a service based on its name and style"""
        name_lower = name.lower()
        style_lower = style.lower()
        combined = name_lower + " " + style_lower
        
        for category, keywords in self.AZURE_SERVICE_CATEGORIES.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return "compute"  # Default
    
    def _normalize_service_name(self, name: str) -> str:
        """Normalize service name for pattern matching"""
        name = name.lower().strip()
        
        # Remove Azure/Microsoft prefixes
        for prefix in ["azure ", "microsoft "]:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Common normalizations
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[^a-z0-9 ]', '', name)
        
        return name.strip()
    
    def _clean_service_name(self, name: str) -> str:
        """Clean service name but preserve meaningful text"""
        # Remove HTML tags
        name = re.sub(r'<[^>]+>', '', name)
        # Decode HTML entities
        name = name.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return name.strip()
    
    def _clean_connection_label(self, label: str) -> str:
        """Clean connection label"""
        if not label:
            return ""
        # Remove HTML tags
        label = re.sub(r'<[^>]+>', '', label)
        return label.strip()
    
    # ========== PUBLIC METHODS FOR AGENT INTEGRATION ==========
    
    def get_connection_suggestions(self, source_service: str, target_service: str) -> List[str]:
        """Get suggested connection labels between two services"""
        source_norm = self._normalize_service_name(source_service)
        target_norm = self._normalize_service_name(target_service)
        
        suggestions = []
        
        # Look for exact service match patterns
        for pattern in self.connection_patterns:
            if pattern.source_service == source_norm and pattern.target_service == target_norm:
                suggestions.extend(pattern.labels)
        
        # Look for category-based patterns
        source_cat = self._get_service_category(source_service)
        target_cat = self._get_service_category(target_service)
        
        key = (source_cat, target_cat)
        if key in self.common_connection_labels:
            suggestions.extend(self.common_connection_labels[key])
        
        # Deduplicate and return
        return list(dict.fromkeys(suggestions))[:5]
    
    def get_optimal_position(self, service_name: str, canvas_width: int = None, canvas_height: int = None) -> Tuple[int, int]:
        """Get optimal position for a service based on learned patterns"""
        canvas_width = canvas_width or drawio_config.DEFAULT_CANVAS_WIDTH
        canvas_height = canvas_height or drawio_config.DEFAULT_CANVAS_HEIGHT
        normalized = self._normalize_service_name(service_name)
        
        if normalized in self.layout_patterns:
            pattern = self.layout_patterns[normalized]
            x = int(pattern.typical_x_ratio * canvas_width)
            y = int(pattern.typical_y_ratio * canvas_height)
            return (x, y)
        
        # Fallback to category-based positioning
        category = self._get_service_category(service_name)
        layer = self.CATEGORY_LAYERS.get(category, 2)
        
        # Layer-based vertical positioning
        y = 50 + layer * 180
        x = canvas_width // 2
        
        return (x, y)
    
    def _get_service_category(self, service_name: str) -> str:
        """Get category for a service"""
        name_lower = service_name.lower()
        
        for category, keywords in self.AZURE_SERVICE_CATEGORIES.items():
            if any(kw in name_lower for kw in keywords):
                return category
        
        return "compute"
    
    def get_related_services(self, service_name: str) -> Dict[str, List[str]]:
        """Get commonly related services (sources and targets)"""
        normalized = self._normalize_service_name(service_name)
        
        if normalized in self.service_patterns:
            pattern = self.service_patterns[normalized]
            return {
                "commonly_connects_to": pattern.common_targets[:10],
                "commonly_receives_from": pattern.common_sources[:10]
            }
        
        return {"commonly_connects_to": [], "commonly_receives_from": []}
    
    def get_reference_architecture_by_pattern(self, pattern_keywords: List[str]) -> List[Dict]:
        """Find reference architectures matching given keywords"""
        matches = []
        
        for ref in self.reference_architectures:
            name_lower = ref["name"].lower()
            score = sum(1 for kw in pattern_keywords if kw.lower() in name_lower)
            
            if score > 0:
                matches.append({
                    "name": ref["name"],
                    "score": score,
                    "component_count": len(ref["components"]),
                    "connection_count": len(ref["connections"]),
                    "services": [c["name"] for c in ref["components"][:15]]
                })
        
        # Sort by relevance score
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:5]
    
    def generate_connection_label(self, source_service: str, target_service: str) -> str:
        """Generate a meaningful connection label based on learned patterns"""
        suggestions = self.get_connection_suggestions(source_service, target_service)
        
        if suggestions:
            return suggestions[0]
        
        # Fallback to category-based labels
        source_cat = self._get_service_category(source_service)
        target_cat = self._get_service_category(target_service)
        
        label_map = {
            ("networking_edge", "networking_gateway"): "HTTPS traffic routing",
            ("networking_gateway", "compute"): "Application traffic",
            ("compute", "data"): "Data queries",
            ("compute", "integration"): "Message publishing",
            ("integration", "compute"): "Event processing",
            ("compute", "security"): "Secrets & certificates",
            ("compute", "monitoring"): "Telemetry & logs",
            ("networking_gateway", "security"): "WAF protection",
            ("data", "data"): "Data replication",
            ("compute", "ai"): "AI/ML inference",
            ("ai", "data"): "Model data access",
            ("security", "compute"): "Identity validation",
        }
        
        return label_map.get((source_cat, target_cat), "Service integration")
    
    def get_architecture_template(self, architecture_type: str) -> Dict[str, Any]:
        """Get a template architecture based on common patterns"""
        type_lower = architecture_type.lower()
        
        # Find best matching reference
        keywords = type_lower.split()
        matches = self.get_reference_architecture_by_pattern(keywords)
        
        if matches:
            best_match = matches[0]
            # Find full reference
            for ref in self.reference_architectures:
                if ref["name"] == best_match["name"]:
                    return {
                        "template_name": ref["name"],
                        "components": ref["components"],
                        "connections": ref["connections"],
                        "suggested_layout": self._generate_layout_template(ref["components"])
                    }
        
        return {"template_name": None, "components": [], "connections": []}
    
    def _generate_layout_template(self, components: List[Dict]) -> Dict[str, Any]:
        """Generate a layout template from components"""
        layers = defaultdict(list)
        
        for comp in components:
            category = comp.get("category", "compute")
            layer = self.CATEGORY_LAYERS.get(category, 2)
            layers[layer].append(comp)
        
        return {
            "layers": dict(layers),
            "layer_order": ["networking_edge", "networking_gateway", "compute", "integration", "data", "monitoring"]
        }
    
    def get_prompt_context(self, requirements: str, max_references: int = 3) -> str:
        """Generate context string for AI agent prompts"""
        if not self._is_indexed:
            self.build_index()
        
        # Find relevant reference architectures
        keywords = [w.lower() for w in requirements.split() if len(w) > 3][:10]
        matches = self.get_reference_architecture_by_pattern(keywords)
        
        context = "\n\n=== REFERENCE ARCHITECTURE PATTERNS (from real Azure diagrams) ===\n"
        
        if matches:
            for i, match in enumerate(matches[:max_references], 1):
                context += f"\n--- Reference {i}: {match['name']} ---\n"
                context += f"Components: {match['component_count']} | Connections: {match['connection_count']}\n"
                context += f"Services: {', '.join(match['services'][:10])}\n"
        
        # Add common connection patterns
        context += "\n\n=== COMMON CONNECTION PATTERNS ===\n"
        for pattern in self.connection_patterns[:15]:
            if pattern.labels:
                context += f"• {pattern.source_service} → {pattern.target_service}: \"{pattern.labels[0]}\"\n"
        
        # Add layout guidance
        context += "\n\n=== LAYOUT GUIDANCE ===\n"
        context += "Layer 0 (Top): Edge services (Front Door, CDN, WAF, Traffic Manager)\n"
        context += "Layer 1: Gateways (Application Gateway, Load Balancer, API Management)\n"
        context += "Layer 2: Compute & Integration (App Service, Functions, Service Bus)\n"
        context += "Layer 3 (Bottom): Data & Storage (SQL, Cosmos DB, Storage, Redis)\n"
        context += "Security & Monitoring: Distributed across layers, connected to what they protect/monitor\n"
        
        return context
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the reference index"""
        return {
            "total_reference_diagrams": len(self.reference_architectures),
            "unique_services_learned": len(self.service_patterns),
            "connection_patterns": len(self.connection_patterns),
            "top_services": sorted(
                [(k, v.occurrence_count) for k, v in self.service_patterns.items()],
                key=lambda x: x[1],
                reverse=True
            )[:20],
            "indexed": self._is_indexed
        }


# Singleton instance
_analyzer_instance: Optional[DrawioReferenceAnalyzer] = None


def get_reference_analyzer(reference_dir: str = None) -> DrawioReferenceAnalyzer:
    """Get or create the singleton reference analyzer instance"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = DrawioReferenceAnalyzer(reference_dir)
        _analyzer_instance.build_index()
    
    return _analyzer_instance


def reset_reference_analyzer():
    """Reset the singleton instance (for testing)"""
    global _analyzer_instance
    _analyzer_instance = None
