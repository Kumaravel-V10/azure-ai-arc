"""
Architecture Diff Analyzer
===========================
Compares two architectures (actual vs expected) and produces:
- Service-level diff (missing, extra, matching)
- Connection-level diff
- Impact analysis per difference
- Prioritized remediation plan
- Full summary report
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from config import agent_config, content_config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# ENUMS AND MODELS
# ═══════════════════════════════════════════════════════════════════

class DiffType(Enum):
    MISSING = "missing"          # In expected but not in actual
    EXTRA = "extra"              # In actual but not in expected
    MODIFIED = "modified"        # Present in both but different
    MATCHING = "matching"        # Identical in both


class ImpactCategory(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    COST = "cost"
    OPERATIONAL = "operational"


class ImpactSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ServiceDiff:
    """Difference for a single service"""
    service_name: str
    diff_type: str  # DiffType value
    category: str = ""
    impact_severity: str = "medium"  # ImpactSeverity value
    impact_categories: List[str] = field(default_factory=list)
    impact_description: str = ""
    remediation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConnectionDiff:
    """Difference for a single connection"""
    source: str
    target: str
    diff_type: str  # DiffType value
    label: str = ""
    impact_severity: str = "medium"
    impact_categories: List[str] = field(default_factory=list)
    impact_description: str = ""
    remediation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArchitectureDiffResult:
    """Complete diff result between two architectures"""
    # Summary counts
    total_actual_services: int = 0
    total_expected_services: int = 0
    total_actual_connections: int = 0
    total_expected_connections: int = 0

    # Service diffs
    matching_services: List[ServiceDiff] = field(default_factory=list)
    missing_services: List[ServiceDiff] = field(default_factory=list)
    extra_services: List[ServiceDiff] = field(default_factory=list)

    # Connection diffs
    matching_connections: List[ConnectionDiff] = field(default_factory=list)
    missing_connections: List[ConnectionDiff] = field(default_factory=list)
    extra_connections: List[ConnectionDiff] = field(default_factory=list)

    # Scores
    service_match_percentage: float = 0.0
    connection_match_percentage: float = 0.0
    overall_match_percentage: float = 0.0

    # Impact analysis
    impact_summary: Dict[str, Any] = field(default_factory=dict)
    remediation_plan: List[Dict[str, Any]] = field(default_factory=list)

    # Pattern comparison
    actual_pattern: str = ""
    expected_pattern: str = ""
    pattern_match: bool = False

    # Executive summary
    executive_summary: str = ""
    detailed_findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_actual_services": self.total_actual_services,
            "total_expected_services": self.total_expected_services,
            "total_actual_connections": self.total_actual_connections,
            "total_expected_connections": self.total_expected_connections,
            "matching_services": [s.to_dict() for s in self.matching_services],
            "missing_services": [s.to_dict() for s in self.missing_services],
            "extra_services": [s.to_dict() for s in self.extra_services],
            "matching_connections": [c.to_dict() for c in self.matching_connections],
            "missing_connections": [c.to_dict() for c in self.missing_connections],
            "extra_connections": [c.to_dict() for c in self.extra_connections],
            "service_match_percentage": round(self.service_match_percentage, 1),
            "connection_match_percentage": round(self.connection_match_percentage, 1),
            "overall_match_percentage": round(self.overall_match_percentage, 1),
            "impact_summary": self.impact_summary,
            "remediation_plan": self.remediation_plan,
            "actual_pattern": self.actual_pattern,
            "expected_pattern": self.expected_pattern,
            "pattern_match": self.pattern_match,
            "executive_summary": self.executive_summary,
            "detailed_findings": self.detailed_findings,
        }


# ═══════════════════════════════════════════════════════════════════
# IMPACT RULES ENGINE
# ═══════════════════════════════════════════════════════════════════

# Maps service categories to their impact when missing
MISSING_SERVICE_IMPACT: Dict[str, Dict[str, Any]] = {
    "security": {
        "severity": "critical",
        "categories": ["security", "reliability"],
        "description": "Missing security service exposes the architecture to vulnerabilities and compliance violations.",
        "remediation_template": "Add {service} to ensure proper security posture. Configure with least-privilege access and enable audit logging."
    },
    "networking": {
        "severity": "high",
        "categories": ["security", "performance", "reliability"],
        "description": "Missing networking component may impact traffic flow, security boundaries, and availability.",
        "remediation_template": "Deploy {service} to ensure proper network segmentation and traffic management."
    },
    "monitoring": {
        "severity": "high",
        "categories": ["operational", "reliability"],
        "description": "Missing monitoring reduces visibility into system health, making incident response slower.",
        "remediation_template": "Implement {service} for observability. Configure alerts for critical metrics and set up dashboards."
    },
    "data": {
        "severity": "high",
        "categories": ["reliability", "performance"],
        "description": "Missing data service affects data persistence, caching, or processing capabilities.",
        "remediation_template": "Provision {service} with appropriate redundancy and backup configuration."
    },
    "compute": {
        "severity": "medium",
        "categories": ["performance", "reliability"],
        "description": "Missing compute service may indicate underprovisioned processing capacity.",
        "remediation_template": "Deploy {service} and configure auto-scaling based on workload patterns."
    },
    "integration": {
        "severity": "medium",
        "categories": ["performance", "operational"],
        "description": "Missing integration service may cause tight coupling or unreliable messaging.",
        "remediation_template": "Add {service} to decouple services and improve message reliability."
    },
    "storage": {
        "severity": "medium",
        "categories": ["reliability", "cost"],
        "description": "Missing storage service affects data durability and access patterns.",
        "remediation_template": "Provision {service} with appropriate redundancy tier (LRS/GRS/ZRS)."
    },
    "ai": {
        "severity": "low",
        "categories": ["performance"],
        "description": "Missing AI service may reduce intelligent capabilities or require external alternatives.",
        "remediation_template": "Consider adding {service} if AI/ML capabilities are in requirements."
    }
}

# Connection-level impact rules
MISSING_CONNECTION_IMPACTS = {
    ("security", "compute"): {"severity": "critical", "desc": "Compute services not connected to security — secrets may be hardcoded."},
    ("compute", "monitoring"): {"severity": "high", "desc": "Compute not sending telemetry — blind spot in observability."},
    ("networking", "compute"): {"severity": "high", "desc": "No network path to compute — service may be unreachable."},
    ("compute", "data"): {"severity": "high", "desc": "Compute not connected to data tier — data access path missing."},
    ("compute", "integration"): {"severity": "medium", "desc": "Direct coupling between services — consider async messaging."},
}


# ═══════════════════════════════════════════════════════════════════
# FUZZY SERVICE MATCHING
# ═══════════════════════════════════════════════════════════════════

def _normalize_service_name(name: str) -> str:
    """Normalize service name for comparison"""
    name = name.lower().strip()
    # Remove common Azure prefixes
    for prefix in ["azure ", "microsoft ", "ms "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Remove parenthetical resource names like "(my-app)"
    import re
    name = re.sub(r'\s*\(.*?\)\s*', '', name)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _service_matches(name_a: str, name_b: str) -> bool:
    """Check if two service names likely refer to the same service"""
    norm_a = _normalize_service_name(name_a)
    norm_b = _normalize_service_name(name_b)

    # Exact match after normalization
    if norm_a == norm_b:
        return True

    # One contains the other
    if norm_a in norm_b or norm_b in norm_a:
        return True

    # Common abbreviation matching
    abbreviations = {
        "aks": "kubernetes service",
        "apim": "api management",
        "appgw": "application gateway",
        "nsg": "network security group",
        "vnet": "virtual network",
        "sql db": "sql database",
        "app insights": "application insights",
        "kv": "key vault",
    }
    for abbr, full in abbreviations.items():
        if (abbr in norm_a and full in norm_b) or (full in norm_a and abbr in norm_b):
            return True

    return False


def _categorize_service(service_name: str) -> str:
    """Categorize a service by name"""
    name_lower = service_name.lower()
    from reverse_engineer import AZURE_CATEGORY_MAP
    for category, keywords in AZURE_CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return "compute"


# ═══════════════════════════════════════════════════════════════════
# MAIN DIFF ANALYZER
# ═══════════════════════════════════════════════════════════════════

class ArchitectureDiffAnalyzer:
    """
    Compares two architectures and produces a comprehensive diff with impact analysis.
    
    Input: Two architecture dicts with "services" and "connections" lists.
    Output: ArchitectureDiffResult with full diff, impact, and remediation.
    """

    def analyze(
        self,
        actual: Dict[str, Any],
        expected: Dict[str, Any],
        requirements: str = ""
    ) -> ArchitectureDiffResult:
        """
        Compare actual vs expected architecture.
        
        Args:
            actual: Architecture dict with "services" and "connections"
            expected: Architecture dict with "services" and "connections"
            requirements: Optional requirements text for context
            
        Returns:
            ArchitectureDiffResult with complete diff analysis
        """
        result = ArchitectureDiffResult()

        # Extract service names
        actual_services = self._extract_service_names(actual.get("services", []))
        expected_services = self._extract_service_names(expected.get("services", []))

        result.total_actual_services = len(actual_services)
        result.total_expected_services = len(expected_services)

        # ── Service Diff ────────────────────────────────────
        matched_actual = set()
        matched_expected = set()

        for act_name in actual_services:
            for exp_name in expected_services:
                if exp_name in matched_expected:
                    continue
                if _service_matches(act_name, exp_name):
                    matched_actual.add(act_name)
                    matched_expected.add(exp_name)
                    result.matching_services.append(ServiceDiff(
                        service_name=act_name,
                        diff_type=DiffType.MATCHING.value,
                        category=_categorize_service(act_name),
                    ))
                    break

        # Missing services (in expected but not actual)
        for exp_name in expected_services:
            if exp_name not in matched_expected:
                category = _categorize_service(exp_name)
                impact = MISSING_SERVICE_IMPACT.get(category, MISSING_SERVICE_IMPACT["compute"])
                result.missing_services.append(ServiceDiff(
                    service_name=exp_name,
                    diff_type=DiffType.MISSING.value,
                    category=category,
                    impact_severity=impact["severity"],
                    impact_categories=impact["categories"],
                    impact_description=impact["description"],
                    remediation=impact["remediation_template"].format(service=exp_name),
                ))

        # Extra services (in actual but not expected)
        for act_name in actual_services:
            if act_name not in matched_actual:
                category = _categorize_service(act_name)
                result.extra_services.append(ServiceDiff(
                    service_name=act_name,
                    diff_type=DiffType.EXTRA.value,
                    category=category,
                    impact_severity="low",
                    impact_categories=["cost"],
                    impact_description=f"Extra service '{act_name}' not in expected architecture. May increase cost without planned benefit.",
                    remediation=f"Review whether '{act_name}' is needed. Remove if not required to reduce cost.",
                ))

        # Service match percentage
        total_unique = len(set(actual_services) | matched_expected | (set(expected_services) - matched_expected))
        if total_unique > 0:
            result.service_match_percentage = (len(result.matching_services) / max(len(expected_services), 1)) * 100

        # ── Connection Diff ────────────────────────────────
        actual_conns = self._extract_connections(actual.get("connections", []))
        expected_conns = self._extract_connections(expected.get("connections", []))

        result.total_actual_connections = len(actual_conns)
        result.total_expected_connections = len(expected_conns)

        matched_act_conns = set()
        matched_exp_conns = set()

        for act_key, act_label in actual_conns.items():
            for exp_key, exp_label in expected_conns.items():
                if exp_key in matched_exp_conns:
                    continue
                if self._connections_match(act_key, exp_key):
                    matched_act_conns.add(act_key)
                    matched_exp_conns.add(exp_key)
                    result.matching_connections.append(ConnectionDiff(
                        source=act_key[0],
                        target=act_key[1],
                        diff_type=DiffType.MATCHING.value,
                        label=act_label,
                    ))
                    break

        for exp_key, exp_label in expected_conns.items():
            if exp_key not in matched_exp_conns:
                src_cat = _categorize_service(exp_key[0])
                tgt_cat = _categorize_service(exp_key[1])
                impact = self._get_connection_impact(src_cat, tgt_cat)
                result.missing_connections.append(ConnectionDiff(
                    source=exp_key[0],
                    target=exp_key[1],
                    diff_type=DiffType.MISSING.value,
                    label=exp_label,
                    impact_severity=impact.get("severity", "medium"),
                    impact_categories=["reliability", "performance"],
                    impact_description=impact.get("desc", f"Missing connection from {exp_key[0]} to {exp_key[1]}."),
                    remediation=f"Add connection from {exp_key[0]} to {exp_key[1]}.",
                ))

        for act_key, act_label in actual_conns.items():
            if act_key not in matched_act_conns:
                result.extra_connections.append(ConnectionDiff(
                    source=act_key[0],
                    target=act_key[1],
                    diff_type=DiffType.EXTRA.value,
                    label=act_label,
                    impact_severity="low",
                    impact_categories=["cost", "operational"],
                    impact_description=f"Extra connection not in expected architecture.",
                    remediation=f"Review connection {act_key[0]} → {act_key[1]}. Remove if unnecessary.",
                ))

        if len(expected_conns) > 0:
            result.connection_match_percentage = (len(result.matching_connections) / len(expected_conns)) * 100

        # ── Overall Match ──────────────────────────────────
        svc_weight = 0.6
        conn_weight = 0.4
        result.overall_match_percentage = (
            result.service_match_percentage * svc_weight +
            result.connection_match_percentage * conn_weight
        )

        # ── Pattern Comparison ─────────────────────────────
        result.actual_pattern = actual.get("architecture_pattern", "Unknown")
        result.expected_pattern = expected.get("architecture_pattern", "Unknown")
        result.pattern_match = _normalize_service_name(result.actual_pattern) == _normalize_service_name(result.expected_pattern)

        # ── Impact Summary ─────────────────────────────────
        result.impact_summary = self._calculate_impact_summary(result)

        # ── Remediation Plan ───────────────────────────────
        result.remediation_plan = self._build_remediation_plan(result)

        # ── Executive Summary ──────────────────────────────
        result.executive_summary = self._generate_executive_summary(result, requirements)
        result.detailed_findings = self._generate_detailed_findings(result)

        return result

    # ── Helper Methods ──────────────────────────────────────

    def _extract_service_names(self, services: List[Any]) -> List[str]:
        """Extract service names from various formats"""
        names = []
        for s in services:
            if isinstance(s, str):
                names.append(s)
            elif isinstance(s, dict):
                names.append(s.get("name", s.get("service_name", "")))
        return [n for n in names if n]

    def _extract_connections(self, connections: List[Dict]) -> Dict[Tuple[str, str], str]:
        """Extract connections as (source, target) → label mapping"""
        result = {}
        for c in connections:
            source = c.get("source", c.get("from", ""))
            target = c.get("target", c.get("to", ""))
            label = c.get("label", "")
            if source and target:
                result[(source, target)] = label
        return result

    def _connections_match(self, conn_a: Tuple[str, str], conn_b: Tuple[str, str]) -> bool:
        """Check if two connections match (fuzzy source/target matching)"""
        return _service_matches(conn_a[0], conn_b[0]) and _service_matches(conn_a[1], conn_b[1])

    def _get_connection_impact(self, src_category: str, tgt_category: str) -> Dict[str, str]:
        """Get impact for a missing connection based on categories"""
        for (cat_a, cat_b), impact in MISSING_CONNECTION_IMPACTS.items():
            if (src_category == cat_a and tgt_category == cat_b) or \
               (src_category == cat_b and tgt_category == cat_a):
                return impact
        return {"severity": "medium", "desc": "Missing connection may affect system behavior."}

    def _calculate_impact_summary(self, result: ArchitectureDiffResult) -> Dict[str, Any]:
        """Calculate aggregate impact summary"""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_impacts: Dict[str, int] = {}

        all_diffs = list(result.missing_services) + list(result.extra_services) + \
                    list(result.missing_connections) + list(result.extra_connections)

        for diff in all_diffs:
            severity = diff.impact_severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            for cat in diff.impact_categories:
                category_impacts[cat] = category_impacts.get(cat, 0) + 1

        # Calculate risk score (0-100)
        risk_score = min(100, severity_counts["critical"] * 25 + severity_counts["high"] * 15 +
                         severity_counts["medium"] * 8 + severity_counts["low"] * 3)

        return {
            "risk_score": risk_score,
            "risk_level": "Critical" if risk_score >= 60 else "High" if risk_score >= 35 else "Medium" if risk_score >= 15 else "Low",
            "severity_counts": severity_counts,
            "category_impacts": category_impacts,
            "total_differences": len(all_diffs),
            "total_missing": len(result.missing_services) + len(result.missing_connections),
            "total_extra": len(result.extra_services) + len(result.extra_connections),
        }

    def _build_remediation_plan(self, result: ArchitectureDiffResult) -> List[Dict[str, Any]]:
        """Build prioritized remediation plan"""
        plan = []
        priority = 1

        # Critical items first
        for svc in sorted(result.missing_services, key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s.impact_severity, 4)):
            plan.append({
                "priority": priority,
                "type": "missing_service",
                "item": svc.service_name,
                "severity": svc.impact_severity,
                "action": svc.remediation,
                "impact": svc.impact_description,
                "categories": svc.impact_categories,
                "estimated_effort": "high" if svc.impact_severity == "critical" else "medium",
            })
            priority += 1

        for conn in sorted(result.missing_connections, key=lambda c: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(c.impact_severity, 4)):
            plan.append({
                "priority": priority,
                "type": "missing_connection",
                "item": f"{conn.source} → {conn.target}",
                "severity": conn.impact_severity,
                "action": conn.remediation,
                "impact": conn.impact_description,
                "categories": conn.impact_categories,
                "estimated_effort": "low",
            })
            priority += 1

        # Extra items (lower priority — review and potentially remove)
        for svc in result.extra_services:
            plan.append({
                "priority": priority,
                "type": "extra_service",
                "item": svc.service_name,
                "severity": "low",
                "action": svc.remediation,
                "impact": svc.impact_description,
                "categories": svc.impact_categories,
                "estimated_effort": "low",
            })
            priority += 1

        return plan

    def _generate_executive_summary(self, result: ArchitectureDiffResult, requirements: str) -> str:
        """Generate executive summary of the diff"""
        parts = []

        match_pct = result.overall_match_percentage
        if match_pct >= 90:
            parts.append(f"The actual architecture closely matches the expected design ({match_pct:.0f}% overall match).")
        elif match_pct >= 70:
            parts.append(f"The actual architecture partially matches the expected design ({match_pct:.0f}% overall match) with notable gaps.")
        elif match_pct >= 40:
            parts.append(f"Significant differences exist between actual and expected architectures ({match_pct:.0f}% match).")
        else:
            parts.append(f"The actual architecture substantially differs from the expected design ({match_pct:.0f}% match). Major remediation needed.")

        if result.missing_services:
            critical_missing = [s for s in result.missing_services if s.impact_severity == "critical"]
            if critical_missing:
                names = ", ".join(s.service_name for s in critical_missing[:3])
                parts.append(f"CRITICAL: {len(critical_missing)} critical services missing including {names}.")
            parts.append(f"{len(result.missing_services)} services from expected architecture are not implemented.")

        if result.extra_services:
            parts.append(f"{len(result.extra_services)} additional services exist beyond expected architecture (review for cost).")

        if result.missing_connections:
            parts.append(f"{len(result.missing_connections)} expected connections are missing.")

        risk = result.impact_summary.get("risk_level", "Medium")
        parts.append(f"Overall risk level: {risk}.")

        if not result.pattern_match:
            parts.append(f"Architecture pattern mismatch: actual='{result.actual_pattern}', expected='{result.expected_pattern}'.")

        return " ".join(parts)

    def _generate_detailed_findings(self, result: ArchitectureDiffResult) -> List[str]:
        """Generate list of detailed findings"""
        findings = []

        for svc in result.missing_services:
            findings.append(f"[{svc.impact_severity.upper()}] Missing service: {svc.service_name} ({svc.category}) — {svc.impact_description}")

        for svc in result.extra_services:
            findings.append(f"[INFO] Extra service: {svc.service_name} ({svc.category}) — Not in expected architecture")

        for conn in result.missing_connections:
            findings.append(f"[{conn.impact_severity.upper()}] Missing connection: {conn.source} → {conn.target} — {conn.impact_description}")

        for conn in result.extra_connections:
            findings.append(f"[INFO] Extra connection: {conn.source} → {conn.target}")

        if not result.pattern_match:
            findings.append(f"[MEDIUM] Architecture pattern mismatch: '{result.actual_pattern}' vs '{result.expected_pattern}'")

        return findings


# ═══════════════════════════════════════════════════════════════════
# AI-ENHANCED DIFF (uses GPT-4o for deeper analysis)
# ═══════════════════════════════════════════════════════════════════

class AIEnhancedDiffAnalyzer:
    """Enhances diff analysis with GPT-4o for contextual understanding"""

    async def enhance_diff(self, diff_result: ArchitectureDiffResult, requirements: str = "") -> Dict[str, Any]:
        """Use AI to provide deeper analysis of architecture differences"""
        try:
            from ai_validator import AIArchitectureValidator
            validator = AIArchitectureValidator()
        except Exception as e:
            logger.warning(f"AI enhancement not available: {e}")
            return {"enhanced": False, "reason": str(e)}

        prompt = f"""Analyze these architecture differences and provide expert assessment:

REQUIREMENTS: {requirements}

MISSING SERVICES ({len(diff_result.missing_services)}):
{json.dumps([s.to_dict() for s in diff_result.missing_services[:content_config.MAX_DIFF_ITEMS]], indent=2)}

EXTRA SERVICES ({len(diff_result.extra_services)}):
{json.dumps([s.to_dict() for s in diff_result.extra_services[:content_config.MAX_DIFF_ITEMS]], indent=2)}

MISSING CONNECTIONS ({len(diff_result.missing_connections)}):
{json.dumps([c.to_dict() for c in diff_result.missing_connections[:content_config.MAX_DIFF_ITEMS]], indent=2)}

MATCH PERCENTAGE: {diff_result.overall_match_percentage:.1f}%

Provide JSON:
{{
    "expert_assessment": "paragraph about overall architectural gap assessment",
    "priority_actions": ["top 5 most important actions"],
    "risk_analysis": "what could go wrong if differences aren't addressed",
    "cost_impact": "estimated cost impact of differences",
    "timeline_estimate": "estimated time to remediate all gaps",
    "well_architected_impact": {{
        "security": "how gaps affect security pillar",
        "reliability": "how gaps affect reliability pillar",
        "performance": "how gaps affect performance pillar",
        "cost_optimization": "how gaps affect cost pillar",
        "operational_excellence": "how gaps affect ops pillar"
    }}
}}"""

        try:
            response = validator.client.chat.completions.create(
                model=validator.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Azure Solutions Architect. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=agent_config.AGENT_MAX_TOKENS_DEFAULT,
                temperature=agent_config.AGENT_TEMPERATURE
            )
            content = response.choices[0].message.content
            cleaned = validator._clean_json_response(content)
            ai_result = json.loads(cleaned)
            ai_result["enhanced"] = True
            return ai_result
        except Exception as e:
            logger.warning(f"AI diff enhancement failed: {e}")
            return {"enhanced": False, "reason": str(e)}


# ═══════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════

class DiffReportGenerator:
    """Generates formatted reports from diff analysis"""

    def generate_json_report(self, diff_result: ArchitectureDiffResult, ai_enhancement: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive JSON report"""
        report = {
            "report_type": "Architecture Comparison Report",
            "generated_at": datetime.now().isoformat(),
            "executive_summary": diff_result.executive_summary,
            "overall_match": {
                "percentage": round(diff_result.overall_match_percentage, 1),
                "service_match": round(diff_result.service_match_percentage, 1),
                "connection_match": round(diff_result.connection_match_percentage, 1),
                "pattern_match": diff_result.pattern_match,
            },
            "impact_analysis": diff_result.impact_summary,
            "services": {
                "matching": [s.to_dict() for s in diff_result.matching_services],
                "missing": [s.to_dict() for s in diff_result.missing_services],
                "extra": [s.to_dict() for s in diff_result.extra_services],
            },
            "connections": {
                "matching": [c.to_dict() for c in diff_result.matching_connections],
                "missing": [c.to_dict() for c in diff_result.missing_connections],
                "extra": [c.to_dict() for c in diff_result.extra_connections],
            },
            "remediation_plan": diff_result.remediation_plan,
            "detailed_findings": diff_result.detailed_findings,
        }

        if ai_enhancement and ai_enhancement.get("enhanced"):
            report["ai_expert_analysis"] = ai_enhancement

        return report

    def generate_markdown_report(self, diff_result: ArchitectureDiffResult, ai_enhancement: Dict[str, Any] = None) -> str:
        """Generate Markdown formatted report"""
        lines = []
        lines.append("# Architecture Comparison Report")
        lines.append(f"\n**Generated:** {datetime.now().isoformat()}")
        lines.append(f"\n## Executive Summary\n\n{diff_result.executive_summary}")

        # Match scores
        lines.append("\n## Match Scores\n")
        lines.append(f"| Metric | Score |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Overall Match | {diff_result.overall_match_percentage:.1f}% |")
        lines.append(f"| Service Match | {diff_result.service_match_percentage:.1f}% |")
        lines.append(f"| Connection Match | {diff_result.connection_match_percentage:.1f}% |")
        lines.append(f"| Pattern Match | {'Yes' if diff_result.pattern_match else 'No'} |")

        # Impact
        impact = diff_result.impact_summary
        lines.append(f"\n## Impact Analysis\n")
        lines.append(f"- **Risk Level:** {impact.get('risk_level', 'Unknown')}")
        lines.append(f"- **Risk Score:** {impact.get('risk_score', 0)}/100")
        lines.append(f"- **Total Differences:** {impact.get('total_differences', 0)}")

        sev = impact.get("severity_counts", {})
        if any(sev.values()):
            lines.append(f"\n| Severity | Count |")
            lines.append(f"|----------|-------|")
            for s, c in sev.items():
                if c > 0:
                    lines.append(f"| {s.capitalize()} | {c} |")

        # Missing services
        if diff_result.missing_services:
            lines.append(f"\n## Missing Services ({len(diff_result.missing_services)})\n")
            for svc in diff_result.missing_services:
                lines.append(f"### {svc.service_name}")
                lines.append(f"- **Severity:** {svc.impact_severity}")
                lines.append(f"- **Category:** {svc.category}")
                lines.append(f"- **Impact:** {svc.impact_description}")
                lines.append(f"- **Remediation:** {svc.remediation}\n")

        # Extra services
        if diff_result.extra_services:
            lines.append(f"\n## Extra Services ({len(diff_result.extra_services)})\n")
            for svc in diff_result.extra_services:
                lines.append(f"- **{svc.service_name}** ({svc.category}) — {svc.impact_description}")

        # Missing connections
        if diff_result.missing_connections:
            lines.append(f"\n## Missing Connections ({len(diff_result.missing_connections)})\n")
            for conn in diff_result.missing_connections:
                lines.append(f"- **{conn.source} → {conn.target}** [{conn.impact_severity}] — {conn.impact_description}")

        # Remediation Plan
        if diff_result.remediation_plan:
            lines.append(f"\n## Remediation Plan\n")
            lines.append(f"| Priority | Type | Item | Severity | Action |")
            lines.append(f"|----------|------|------|----------|--------|")
            for item in diff_result.remediation_plan[:content_config.MAX_REMEDIATION_ITEMS]:
                lines.append(f"| {item['priority']} | {item['type']} | {item['item']} | {item['severity']} | {item['action'][:60]}... |")

        # AI Enhancement
        if ai_enhancement and ai_enhancement.get("enhanced"):
            lines.append(f"\n## AI Expert Analysis\n")
            lines.append(ai_enhancement.get("expert_assessment", ""))
            if ai_enhancement.get("priority_actions"):
                lines.append("\n### Priority Actions\n")
                for i, action in enumerate(ai_enhancement["priority_actions"], 1):
                    lines.append(f"{i}. {action}")
            if ai_enhancement.get("risk_analysis"):
                lines.append(f"\n### Risk Analysis\n{ai_enhancement['risk_analysis']}")

        lines.append(f"\n---\n*Report generated by Azure Architecture Studio*")
        return "\n".join(lines)
