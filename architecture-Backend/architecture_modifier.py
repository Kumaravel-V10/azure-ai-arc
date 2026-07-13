import base64
import csv
import logging
import os
import re
import uuid
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from agents import (
    ArchitectureAgent,
    AzureArchitectureReviewAgent,
    ComponentExtractionAgent,
    ConnectionExpertAgent,
)

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


logger = logging.getLogger(__name__)

router = APIRouter(tags=["diagram-modifier"])

MIN_CHANGE_MAX_NEW_SERVICES_DEFAULT = 3
MIN_CHANGE_MAX_NEW_EDGES_PER_SERVICE = 6


SERVICE_ALIAS_GROUPS: Dict[str, List[str]] = {
    "azure functions": ["azure functions", "functions", "function app", "function", "serverless"],
    "azure app service": ["azure app service", "app service", "web app", "webapp"],
    "azure sql database": [
        "azure sql database",
        "azure sql",
        "sql database",
        "sql db",
        "sql server",
        "plsql",
        "postgresql sql",
        "rdbms",
    ],
    "azure database for postgresql": [
        "azure database for postgresql",
        "postgres",
        "postgresql",
        "pgsql",
        "plpgsql",
    ],
    "azure database for mysql": ["azure database for mysql", "mysql", "mysql database"],
    "azure cosmos db": ["azure cosmos db", "cosmos", "cosmosdb", "documentdb", "nosql"],
    "azure cache for redis": ["azure cache for redis", "redis", "redis cache", "cache"],
    "azure key vault": ["azure key vault", "key vault", "keyvault", "secrets vault"],
    "application insights": ["application insights", "app insights", "appinsights"],
    "azure monitor": ["azure monitor", "monitor", "monitoring"],
    "azure service bus": ["azure service bus", "service bus", "queue"],
    "azure event hubs": ["azure event hubs", "event hubs", "event hub", "stream hub"],
}


SERVICE_IMAGE_HINTS: Dict[str, List[str]] = {
    "azure functions": ["Function-Apps", "Function_Apps", "functions"],
    "azure app service": ["App-Service", "App_Services", "app service"],
    "azure sql database": ["SQL-Database", "SQL_Database", "sql"],
    "azure database for postgresql": ["PostgreSQL", "PostgreSQL-Server", "postgres"],
    "azure database for mysql": ["MySQL", "mysql"],
    "azure cosmos db": ["Cosmos-DB", "Cosmos_DB", "cosmos"],
    "azure cache for redis": ["Cache-Redis", "Redis", "redis"],
    "azure key vault": ["Key-Vault", "Key_Vault", "key vault"],
    "application insights": ["Application-Insights", "Application_Insights", "insights"],
    "azure monitor": ["Monitor", "monitor"],
    "azure service bus": ["Service-Bus", "Service_Bus", "service bus"],
    "azure event hubs": ["Event-Hubs", "Event_Hubs", "event hub"],
}


TARGET_DRAWIO_PATH = Path(
    r"C:\Users\2862531\Desktop\VsCode\azure-ai-arc\azure-ai-arc\Environment-Architecture-Production 1.drawio"
)
REFERENCE_MAPPING_CSV = Path(
    r"C:\Users\2862531\Desktop\VsCode\azure-ai-arc\azure-ai-arc\function-webapp-repo-mapping.csv"
)
USER_STORIES_CSV = Path(
    r"C:\Users\2862531\Desktop\VsCode\azure-ai-arc\azure-ai-arc\Drop1-Final Consolidated US.csv"
)
CONSTRAINTS_TXT = Path(
    r"C:\Users\2862531\Desktop\VsCode\azure-ai-arc\azure-ai-arc\similar-architecture-diagram-principles.txt"
)
BACKUP_DIR = TARGET_DRAWIO_PATH.parent / "drawio_backups"
LOCKED_DIAGRAM_SESSIONS: Dict[str, Dict[str, Any]] = {}


class ModifyArchRequest(BaseModel):
    modification_prompt: str = Field(..., min_length=3)
    connection_mode: str = Field(default="enhanced")


class DiagramLockRequest(BaseModel):
    diagram_id: str = Field(..., min_length=1)


class DiagramLockDecisionRequest(BaseModel):
    lock_id: str = Field(..., min_length=8)
    manual_xml: Optional[str] = None


class ModifyArchState(TypedDict, total=False):
    modification_prompt: str
    connection_mode: str
    baseline_architecture: Dict[str, Any]
    baseline_xml: str
    csv_context_summary: str
    hard_constraints: str
    extracted_delta: Dict[str, Any]
    candidate_services: List[Dict[str, Any]]
    services_to_add: List[Dict[str, Any]]
    proposed_connections: List[Dict[str, Any]]
    validated_connections: List[Dict[str, Any]]
    review_result: Dict[str, Any]
    correction_attempts: int
    requires_correction: bool
    updated_architecture: Dict[str, Any]
    updated_xml: str
    backup_path: str
    workflow_trace: List[Dict[str, Any]]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _normalize_service_name(name: str) -> str:
    tokens = _tokenize(name)
    filtered = [t for t in tokens if t not in {"azure", "service", "services", "database"}]
    return " ".join(filtered)


def _canonical_service_key(name: str) -> str:
    lowered = (name or "").lower().strip()
    normalized = _normalize_service_name(name)

    for canonical, aliases in SERVICE_ALIAS_GROUPS.items():
        for alias in aliases:
            if alias in lowered or alias in normalized:
                return canonical

    for canonical, aliases in SERVICE_ALIAS_GROUPS.items():
        canonical_norm = _normalize_service_name(canonical)
        if canonical_norm and canonical_norm in normalized:
            return canonical

    return normalized or lowered


def _extract_image_path(style: str) -> str:
    match = re.search(r"(?:^|;)image=([^;]+)", style or "")
    return match.group(1) if match else ""


def _decode_drawio_value(value: str) -> str:
    if not value:
        return ""
    text = value.replace("&#xa;", " ").replace("&amp;#xa;", " ").replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_legend_or_decoration(cell_id: str, value: str, style: str) -> bool:
    value_lower = _decode_drawio_value(value).lower()
    style_lower = (style or "").lower()
    cell_lower = (cell_id or "").lower()

    if "legend" in value_lower or cell_lower.startswith("legend"):
        return True
    if "production additions" in value_lower:
        return True
    if value_lower.startswith("───") or value_lower.startswith("╌╌╌"):
        return True
    if "deployment slot" in value_lower or "runbooks" in value_lower or "health probes" in value_lower:
        return True
    if "group" == style_lower or style_lower.startswith("group;"):
        return True
    return False


def _is_architecture_container(cell_id: str, value: str, style: str) -> bool:
    value_lower = _decode_drawio_value(value).lower()
    style_lower = (style or "").lower()
    cell_lower = (cell_id or "").lower()

    if any(token in cell_lower for token in ["layer", "section", "container", "box"]):
        return True
    if any(
        phrase in value_lower
        for phrase in [
            "data layer",
            "security /",
            "observability /",
            "edge / cdn layer",
            "web application",
            "secondary region",
            "azure functions (",
            "vnet-",
            "gateway vnet",
            "dmz vnet",
            "private dns zones",
        ]
    ):
        return True
    if "rounded=1" in style_lower and "image=" not in style_lower and "text;" not in style_lower:
        return True
    return False


def _distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    ax = a.get("x", 0.0) + (a.get("width", 0.0) / 2.0)
    ay = a.get("y", 0.0) + (a.get("height", 0.0) / 2.0)
    bx = b.get("x", 0.0) + (b.get("width", 0.0) / 2.0)
    by = b.get("y", 0.0) + (b.get("height", 0.0) / 2.0)
    return abs(ax - bx) + abs(ay - by)


def _extract_service_display_name(raw_label: str) -> str:
    cleaned = _decode_drawio_value(raw_label)
    if not cleaned:
        return ""

    first_segment = cleaned.split("  ")[0].split(" · ")[0].strip()
    parts = [part.strip() for part in re.split(r"[\n\r]+", first_segment) if part.strip()]
    candidate = parts[0] if parts else first_segment
    return candidate.strip("- ")


def _extract_primary_service_name(raw_label: str) -> str:
    cleaned = _decode_drawio_value(raw_label)
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    alias_candidates: List[Tuple[int, str]] = []
    for canonical, aliases in SERVICE_ALIAS_GROUPS.items():
        for alias in aliases:
            pos = lowered.find(alias)
            if pos >= 0:
                alias_candidates.append((pos, canonical))

    if alias_candidates:
        alias_candidates.sort(key=lambda item: item[0])
        canonical = alias_candidates[0][1]
        return canonical.title() if canonical.startswith("azure ") else " ".join(p.capitalize() for p in canonical.split())

    return _extract_service_display_name(raw_label)


def _infer_service_name_from_image(style: str) -> str:
    image = _extract_image_path(style).lower()
    for canonical, hints in SERVICE_IMAGE_HINTS.items():
        if any(h.lower() in image for h in hints):
            return canonical.title() if canonical.startswith("azure ") else " ".join(p.capitalize() for p in canonical.split())
    return ""


def _build_existing_service_indexes(current_architecture: Dict[str, Any]) -> Dict[str, Any]:
    by_exact: Dict[str, Dict[str, Any]] = {}
    by_canonical: Dict[str, List[Dict[str, Any]]] = {}
    image_style_bank: List[Tuple[str, str]] = []

    for v in current_architecture.get("vertices", []):
        if v.get("category") != "service":
            continue
        name = (v.get("name") or "").strip()
        if not name:
            continue
        if _is_legend_or_decoration(v.get("id", ""), name, v.get("style", "")):
            continue
        style = v.get("style", "")
        if not _extract_image_path(style):
            continue
        by_exact[name.lower()] = v

        canonical = _canonical_service_key(name)
        by_canonical.setdefault(canonical, []).append(v)

        img = _extract_image_path(style)
        if img:
            image_style_bank.append((img.lower(), style))

    return {
        "by_exact": by_exact,
        "by_canonical": by_canonical,
        "image_style_bank": image_style_bank,
    }


def _extract_prompt_requested_canonicals(prompt: str) -> set:
    prompt_lower = (prompt or "").lower()
    requested: set = set()

    def _alias_present(alias: str) -> bool:
        return bool(re.search(rf"\b{re.escape(alias)}\b", prompt_lower, re.IGNORECASE))

    def _alias_is_negated(alias: str) -> bool:
        # Detect phrases like: "do not add monitoring", "without sql", "exclude monitor".
        pattern = re.compile(
            rf"(?:do\s+not|don't|not|without|exclude|avoid|no)\b[^\n\r\.;,]{{0,35}}\b{re.escape(alias)}\b",
            re.IGNORECASE,
        )
        return bool(pattern.search(prompt_lower))

    for canonical, aliases in SERVICE_ALIAS_GROUPS.items():
        positive = False
        for alias in aliases:
            if _alias_present(alias) and not _alias_is_negated(alias):
                positive = True
                break
        if positive:
            requested.add(canonical)
    return requested


def _canonical_to_display_name(canonical: str) -> str:
    if canonical.startswith("azure "):
        return " ".join(part.capitalize() for part in canonical.split())
    return " ".join(part.capitalize() for part in canonical.split())


def _extract_named_function_service(prompt: str) -> Optional[Dict[str, Any]]:
    prompt_lower = (prompt or "").lower()
    if "function" not in prompt_lower:
        return None

    match = re.search(
        r"\b(?:create|add|introduce|build)\s+(?:a|an)?\s*(?:new\s+)?([a-z0-9][a-z0-9\s\-/]{1,40}?)\s+function\b",
        prompt_lower,
        re.IGNORECASE,
    )
    if not match:
        return None

    workload = re.sub(r"\s+", " ", match.group(1)).strip(" -")
    if not workload:
        return None

    title_name = " ".join(part.capitalize() for part in workload.split())
    return {
        "name": f"{title_name} Function",
        "category": _layer_name(2),
        "layer": 2,
        "custom_workload": True,
        "platform_canonical": "azure functions",
    }


def _extract_feature_named_service(prompt: str, csv_context_summary: str = "") -> Optional[Dict[str, Any]]:
    prompt_lower = (prompt or "").lower()
    combined = f"{prompt}\n{csv_context_summary}".lower()

    if any(term in combined for term in ["loyalty", "accrual", "miles", "points"]):
        return {
            "name": "Loyalty Accrual Function",
            "category": _layer_name(2),
            "layer": 2,
            "custom_workload": True,
            "platform_canonical": "azure functions",
        }

    if any(term in combined for term in ["offer comparison", "search results", "display_offers", "offer search"]):
        return {
            "name": "Offer Enrichment Function",
            "category": _layer_name(2),
            "layer": 2,
            "custom_workload": True,
            "platform_canonical": "azure functions",
        }

    return None


def _infer_feature_supporting_endpoints(prompt: str, requested_endpoints: List[str]) -> List[str]:
    prompt_lower = (prompt or "").lower()
    ordered: List[str] = []

    def _append_matches(predicate):
        for endpoint in requested_endpoints:
            if endpoint not in ordered and predicate(endpoint.lower()):
                ordered.append(endpoint)

    if any(term in prompt_lower for term in ["search results", "search", "itinerary"]):
        _append_matches(lambda ep: "search" in ep or "shop / flights" in ep or "offer" in ep)
    if any(term in prompt_lower for term in ["offer comparison", "flight offer", "fare family"]):
        _append_matches(lambda ep: "offer" in ep or "shop / flights" in ep)
    if any(term in prompt_lower for term in ["loyalty", "accrual", "miles", "points", "tier"]):
        _append_matches(lambda ep: "payment" in ep or "cart" in ep or "order" in ep)
        _append_matches(lambda ep: "postgres" in ep or "sql" in ep or "database" in ep)

    for endpoint in requested_endpoints:
        if endpoint not in ordered:
            ordered.append(endpoint)

    return ordered[:4]


def _infer_default_database_endpoint(baseline_architecture: Dict[str, Any]) -> Optional[str]:
    preferred: List[str] = []
    fallback: List[str] = []

    for vertex in baseline_architecture.get("vertices", []):
        if vertex.get("category") != "service":
            continue
        name = (vertex.get("name") or "").strip()
        if not name:
            continue
        lowered = name.lower()
        if "postgres" in lowered:
            preferred.append(name)
        elif any(token in lowered for token in ["sql", "database", "mysql", "cosmos", "redis"]):
            fallback.append(name)

    if preferred:
        return sorted(preferred, key=len)[0]
    if fallback:
        return sorted(fallback, key=len)[0]
    return None


def _extract_existing_endpoints_from_prompt(
    prompt: str,
    index: Dict[str, Any],
    current_architecture: Optional[Dict[str, Any]] = None,
    csv_context_summary: str = "",
) -> List[str]:
    prompt_lower = (prompt or "").lower()
    endpoints: List[str] = []

    by_exact = index.get("by_exact", {})
    for existing_name in by_exact.keys():
        if re.search(rf"\b{re.escape(existing_name)}\b", prompt_lower, re.IGNORECASE):
            resolved = _resolve_existing_service_name(existing_name, index)
            if resolved and resolved not in endpoints:
                endpoints.append(resolved)

    for canonical, aliases in SERVICE_ALIAS_GROUPS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", prompt_lower, re.IGNORECASE):
                resolved = _resolve_existing_service_name(_canonical_to_display_name(canonical), index)
                if resolved and resolved not in endpoints:
                    endpoints.append(resolved)
                break

    if current_architecture:
        workload_aliases = {
            "payment": ["payment", "payments"],
            "search": ["search", "search results", "searchpanel"],
            "offer": ["offer", "offers", "comparison", "shop offer", "flight offer"],
            "seat": ["seat", "seats", "seat services", "seat map"],
            "checkout": ["checkout"],
            "cart": ["cart"],
        }

        for v in current_architecture.get("vertices", []):
            if v.get("category") != "service":
                continue
            svc_name = (v.get("name") or "").strip()
            lowered = svc_name.lower()
            for aliases in workload_aliases.values():
                if any(alias in prompt_lower for alias in aliases) and any(alias.replace(" ", "-") in lowered or alias in lowered for alias in aliases):
                    resolved = _resolve_existing_service_name(svc_name, index) or svc_name
                    if resolved and resolved not in endpoints:
                        endpoints.append(resolved)
                    break

    if current_architecture:
        stopwords = {
            "azure",
            "service",
            "services",
            "server",
            "west",
            "europe",
            "east",
            "region",
            "details",
            "database",
            "data",
            "the",
            "with",
            "from",
            "into",
            "that",
            "this",
            "for",
            "and",
            "in",
            "to",
            "of",
            "i",
            "want",
            "get",
            "allocation",
            "connected",
            "connect",
        }
        match_tokens = {
            t
            for t in _tokenize(f"{prompt} {csv_context_summary}")
            if len(t) > 2 and t not in stopwords
        }

        scored: List[Tuple[int, str]] = []
        for v in current_architecture.get("vertices", []):
            if v.get("category") != "service":
                continue
            svc_name = (v.get("name") or "").strip()
            if not svc_name:
                continue
            if _is_legend_or_decoration(v.get("id", ""), svc_name, v.get("style", "")):
                continue

            svc_tokens = {t for t in _tokenize(svc_name) if len(t) > 2 and t not in stopwords}
            overlap = len(svc_tokens.intersection(match_tokens))
            if overlap <= 0:
                continue

            lowered = svc_name.lower()
            bonus = 0
            if "seat" in match_tokens and "seat" in lowered:
                bonus += 3
            if "postgres" in match_tokens and "postgres" in lowered:
                bonus += 2
            if "postgresql" in match_tokens and "postgres" in lowered:
                bonus += 2
            if "function" in match_tokens and ("func-" in lowered or "function" in lowered):
                bonus += 1

            scored.append((overlap + bonus, svc_name))

        scored.sort(key=lambda x: x[0], reverse=True)
        for _, name in scored[:6]:
            resolved = _resolve_existing_service_name(name, index) or name
            if resolved and resolved not in endpoints:
                endpoints.append(resolved)

    return endpoints


def _max_new_services_from_prompt(prompt: str, requested_canonicals: set) -> int:
    prompt_lower = (prompt or "").lower()
    if re.search(r"\b(and|also|plus|along with|as well as|multiple|several|two|three)\b", prompt_lower):
        return max(1, min(3, len(requested_canonicals) if requested_canonicals else 2))
    return MIN_CHANGE_MAX_NEW_SERVICES_DEFAULT


def _is_candidate_requested_by_prompt(candidate_name: str, prompt: str) -> bool:
    prompt_lower = (prompt or "").lower()
    candidate_lower = (candidate_name or "").lower().strip()
    if not candidate_lower:
        return False

    def _contains_non_negated(alias: str) -> bool:
        if not re.search(rf"\b{re.escape(alias)}\b", prompt_lower, re.IGNORECASE):
            return False
        neg_pattern = re.compile(
            rf"(?:do\s+not|don't|not|without|exclude|avoid|no)\b[^\n\r\.;,]{{0,35}}\b{re.escape(alias)}\b",
            re.IGNORECASE,
        )
        return not bool(neg_pattern.search(prompt_lower))

    if _contains_non_negated(candidate_lower):
        return True

    canonical = _canonical_service_key(candidate_name)
    aliases = SERVICE_ALIAS_GROUPS.get(canonical, [])
    return any(_contains_non_negated(alias) for alias in aliases)


def _resolve_existing_service_name(candidate_name: str, index: Dict[str, Any]) -> Optional[str]:
    exact = index.get("by_exact", {})
    if candidate_name.lower() in exact:
        return exact[candidate_name.lower()].get("name", candidate_name)

    canonical = _canonical_service_key(candidate_name)
    matches = index.get("by_canonical", {}).get(canonical, [])
    if matches:
        # Prefer the shortest existing label for canonical services to avoid creating synonyms.
        chosen = sorted(matches, key=lambda x: len((x.get("name") or "").strip()))[0]
        return chosen.get("name", candidate_name)

    return None


def _select_service_style_for_name(service_name: str, current_architecture: Dict[str, Any], fallback_style: str) -> str:
    index = _build_existing_service_indexes(current_architecture)
    canonical = _canonical_service_key(service_name)
    matches = index.get("by_canonical", {}).get(canonical, [])
    if matches:
        for m in matches:
            style = m.get("style", "")
            if _extract_image_path(style):
                return style

    hints = SERVICE_IMAGE_HINTS.get(canonical, [])
    for image_lower, style in index.get("image_style_bank", []):
        if any(h.lower() in image_lower for h in hints):
            return style

    return fallback_style


def _layer_name(layer: int) -> str:
    names = {
        0: "edge",
        1: "gateway",
        2: "compute",
        3: "data",
        -1: "cross-cutting",
    }
    return names.get(layer, "compute")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _read_csv_filtered_rows(csv_path: Path, prompt: str, max_rows: int = 20) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []

    prompt_tokens = set(_tokenize(prompt))
    ranked_rows: List[Tuple[int, Dict[str, str]]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            joined = " ".join(str(v) for v in row.values() if v is not None)
            row_tokens = set(_tokenize(joined))
            overlap = len(prompt_tokens.intersection(row_tokens))
            if overlap > 0:
                ranked_rows.append((overlap, {k: str(v) for k, v in row.items()}))

    ranked_rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in ranked_rows[:max_rows]]


def _rows_to_summary_block(title: str, rows: List[Dict[str, str]], max_cols: int = 6) -> str:
    if not rows:
        return f"{title}: no matching rows."

    lines = [f"{title}:"]
    for i, row in enumerate(rows, start=1):
        pairs = list(row.items())[:max_cols]
        compact = "; ".join(f"{k}={v}" for k, v in pairs if v)
        lines.append(f"  {i}. {compact}")
    return "\n".join(lines)


def _build_csv_context_summary(modification_prompt: str) -> str:
    mapping_rows = _read_csv_filtered_rows(REFERENCE_MAPPING_CSV, modification_prompt, max_rows=20)
    story_rows = _read_csv_filtered_rows(USER_STORIES_CSV, modification_prompt, max_rows=20)

    return "\n\n".join(
        [
            _rows_to_summary_block("Reference mapping matches", mapping_rows),
            _rows_to_summary_block("Consolidated user story matches", story_rows),
        ]
    )


def _read_hard_constraints() -> str:
    if not CONSTRAINTS_TXT.exists():
        return "⚠️ HARD ARCHITECTURAL CONSTRAINTS - DO NOT VIOLATE\nConstraint file not found."

    content = CONSTRAINTS_TXT.read_text(encoding="utf-8", errors="replace")
    return "\n".join(
        [
            "⚠️ HARD ARCHITECTURAL CONSTRAINTS - DO NOT VIOLATE",
            content.strip(),
        ]
    )


def _is_path_within_directory(file_path: Path, directory: Path) -> bool:
    try:
        file_path.resolve().relative_to(directory.resolve())
        return True
    except Exception:
        return False


def _get_diagrams_dir() -> Path:
    raw = os.getenv("MODIFY_ARCH_DIAGRAMS_DIR", str(TARGET_DRAWIO_PATH.parent))
    # Guard against quoted paths in .env such as "C:\\path\\to\\dir"
    normalized = (raw or "").strip().strip('"').strip("'")
    # Recover common escaped sequences when Windows paths are provided with
    # single backslashes in .env (e.g. "\a" becoming bell character).
    escape_recovery = {
        "\a": "a",
        "\b": "b",
        "\f": "f",
        "\n": "n",
        "\r": "r",
        "\t": "t",
        "\v": "v",
    }
    for escaped_char, replacement in escape_recovery.items():
        normalized = normalized.replace(escaped_char, replacement)
    return Path(normalized).resolve()


def _list_available_diagram_files() -> List[Dict[str, str]]:
    diagrams_dir = _get_diagrams_dir()
    if not diagrams_dir.exists() or not diagrams_dir.is_dir():
        return []

    diagrams: List[Dict[str, str]] = []
    for file_path in sorted(diagrams_dir.rglob("*.drawio")):
        if not file_path.is_file():
            continue
        if "drawio_backups" in file_path.parts:
            continue
        rel = file_path.relative_to(diagrams_dir).as_posix()
        diagrams.append(
            {
                "id": rel,
                "name": file_path.stem,
                "filename": file_path.name,
                "relative_path": rel,
                "absolute_path": str(file_path.resolve()),
            }
        )
    return diagrams


def _resolve_diagram_path(diagram_id: str) -> Path:
    diagrams_dir = _get_diagrams_dir()
    safe_id = (diagram_id or "").strip().replace("\\", "/")
    if not safe_id:
        raise HTTPException(status_code=400, detail="diagram_id is required")

    candidate = (diagrams_dir / safe_id).resolve()
    if not _is_path_within_directory(candidate, diagrams_dir):
        raise HTTPException(status_code=400, detail="diagram path is outside configured diagrams directory")
    if not candidate.exists() or not candidate.is_file() or candidate.suffix.lower() != ".drawio":
        raise HTTPException(status_code=404, detail=f"diagram not found in configured folder: {safe_id}")
    return candidate


def _get_session(lock_id: str) -> Dict[str, Any]:
    session = LOCKED_DIAGRAM_SESSIONS.get(lock_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired lock_id")
    return session


def _decode_drawio_diagram_payload(payload: str) -> str:
    compressed = base64.b64decode(payload)
    inflated = zlib.decompress(compressed, wbits=-15)
    return unquote(inflated.decode("utf-8"))


def _encode_drawio_diagram_payload(xml: str) -> str:
    quoted = quote(xml, safe="~()*!.'")
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(quoted.encode("utf-8")) + compressor.flush()
    return base64.b64encode(compressed).decode("utf-8")


def _extract_mxgraph_model(drawio_file_content: str) -> Tuple[ET.Element, ET.Element, ET.Element, bool]:
    root = ET.fromstring(drawio_file_content)
    diagram = root.find(".//diagram")
    if diagram is None:
        raise ValueError("Invalid draw.io file: missing <diagram> element")

    model = diagram.find("mxGraphModel")
    if model is not None:
        return root, diagram, model, False

    diagram_text = (diagram.text or "").strip()
    if not diagram_text:
        raise ValueError("Diagram payload is empty")

    decoded_xml = _decode_drawio_diagram_payload(diagram_text)
    model = ET.fromstring(decoded_xml)
    return root, diagram, model, True


def _materialize_mxgraph_model(root: ET.Element, diagram: ET.Element, model: ET.Element, was_compressed: bool) -> str:
    if was_compressed:
        diagram.text = _encode_drawio_diagram_payload(ET.tostring(model, encoding="unicode"))
        for child in list(diagram):
            diagram.remove(child)
    else:
        for child in list(diagram):
            if child.tag == "mxGraphModel":
                diagram.remove(child)
        diagram.append(model)

    return ET.tostring(root, encoding="unicode")


def _apply_preview_highlight_style(style: str, is_edge: bool) -> str:
    base = style or ""
    if not base.endswith(";"):
        base = f"{base};" if base else ""
    if is_edge:
        return f"{base}strokeColor=#ff6a00;strokeWidth=3;dashed=1;"
    return f"{base}strokeColor=#ff6a00;strokeWidth=3;shadow=1;"


def _geometry_signature(cell: ET.Element) -> str:
    geom = cell.find("mxGeometry")
    if geom is None:
        return ""
    return ET.tostring(geom, encoding="unicode")


def _cells_differ(original_cell: ET.Element, updated_cell: ET.Element) -> bool:
    keys_to_compare = [
        "value",
        "style",
        "source",
        "target",
        "parent",
        "vertex",
        "edge",
    ]
    for key in keys_to_compare:
        if (original_cell.get(key) or "") != (updated_cell.get(key) or ""):
            return True
    return _geometry_signature(original_cell) != _geometry_signature(updated_cell)


def _generate_highlighted_preview_xml(original_xml: str, updated_xml: str) -> str:
    _, _, original_model, _ = _extract_mxgraph_model(original_xml)
    updated_root, updated_diagram, updated_model, updated_was_compressed = _extract_mxgraph_model(updated_xml)

    original_graph_root = _get_graph_root(original_model)
    updated_graph_root = _get_graph_root(updated_model)

    original_cells = {
        c.get("id", ""): c
        for c in original_graph_root.findall("mxCell")
        if c.get("id")
    }

    for cell in updated_graph_root.findall("mxCell"):
        cell_id = cell.get("id", "")
        if not cell_id:
            continue

        original_cell = original_cells.get(cell_id)
        is_changed = original_cell is None or _cells_differ(original_cell, cell)
        if not is_changed:
            continue

        current_style = cell.get("style", "")
        cell.set("data-preview-highlight", "1")
        cell.set("data-preview-original-style", current_style)
        cell.set("style", _apply_preview_highlight_style(current_style, cell.get("edge") == "1"))

    return _materialize_mxgraph_model(updated_root, updated_diagram, updated_model, updated_was_compressed)


def _strip_preview_highlight_markers(xml_content: str) -> str:
    root, diagram, model, was_compressed = _extract_mxgraph_model(xml_content)
    graph_root = _get_graph_root(model)

    for cell in graph_root.findall("mxCell"):
        if cell.get("data-preview-highlight") != "1":
            continue
        original_style = cell.get("data-preview-original-style")
        if original_style is not None:
            cell.set("style", original_style)
        cell.attrib.pop("data-preview-highlight", None)
        cell.attrib.pop("data-preview-original-style", None)

    return _materialize_mxgraph_model(root, diagram, model, was_compressed)


def _get_graph_root(mx_graph_model: ET.Element) -> ET.Element:
    graph_root = mx_graph_model.find("root")
    if graph_root is None:
        raise ValueError("mxGraphModel missing <root>")
    return graph_root


def _parse_drawio_xml_to_dict(xml_content: str) -> Dict[str, Any]:
    _, _, model, _ = _extract_mxgraph_model(xml_content)
    graph_root = _get_graph_root(model)

    arch_agent = ArchitectureAgent()
    edges: List[Dict[str, Any]] = []
    containers: List[Dict[str, Any]] = []
    service_vertices: List[Dict[str, Any]] = []
    label_vertices: List[Dict[str, Any]] = []
    raw_vertices: List[Dict[str, Any]] = []

    for cell in graph_root.findall("mxCell"):
        cell_id = cell.get("id", "")
        style = cell.get("style", "")
        value = (cell.get("value", "") or "").strip()
        parent = cell.get("parent", "")
        if cell.get("data-mod-hash"):
            # Ignore previously generated artifacts when computing the baseline graph.
            continue
        geom = cell.find("mxGeometry")
        geometry = {
            "x": _safe_float(geom.get("x"), 0.0) if geom is not None else 0.0,
            "y": _safe_float(geom.get("y"), 0.0) if geom is not None else 0.0,
            "width": _safe_float(geom.get("width"), 0.0) if geom is not None else 0.0,
            "height": _safe_float(geom.get("height"), 0.0) if geom is not None else 0.0,
        }

        if cell.get("edge") == "1":
            edges.append(
                {
                    "id": cell_id,
                    "label": value,
                    "source": cell.get("source", ""),
                    "target": cell.get("target", ""),
                    "parent": parent,
                    "style": style,
                }
            )
            continue

        if cell.get("vertex") != "1":
            continue

        if _is_legend_or_decoration(cell_id, value, style):
            raw_vertices.append(
                {
                    "id": cell_id,
                    "name": _decode_drawio_value(value),
                    "category": "decoration",
                    "layer": -99,
                    "parent": parent,
                    "style": style,
                    "geometry": geometry,
                }
            )
            continue

        is_container = (
            "swimlane" in style.lower()
            or "resource group" in value.lower()
            or "virtual network" in value.lower()
            or ("dashed=1" in style and "image=" not in style and "text;" not in style)
            or style.lower().startswith("group")
            or _is_architecture_container(cell_id, value, style)
        )

        category = "service"
        if is_container:
            category = "container"
        elif "text;" in style.lower() and "image=" not in style.lower():
            category = "label"

        decoded_name = _decode_drawio_value(value)
        layer = arch_agent._get_service_layer(decoded_name) if category == "service" and decoded_name else 2

        vertex = {
            "id": cell_id,
            "name": decoded_name,
            "category": category,
            "layer": layer,
            "parent": parent,
            "style": style,
            "geometry": geometry,
        }
        raw_vertices.append(vertex)
        if is_container:
            containers.append(vertex)
        elif category == "label":
            label_vertices.append(vertex)
        elif category == "service":
            service_vertices.append(vertex)

    paired_label_ids: set = set()
    logical_services: List[Dict[str, Any]] = []

    for svc in service_vertices:
        style = svc.get("style", "")
        image_path = _extract_image_path(style)
        if not image_path:
            if svc.get("name"):
                logical_services.append(svc)
            continue

        best_label: Optional[Dict[str, Any]] = None
        best_distance: Optional[float] = None
        for lbl in label_vertices:
            if lbl.get("id") in paired_label_ids:
                continue
            if lbl.get("parent") != svc.get("parent"):
                continue
            dist = _distance(svc.get("geometry", {}), lbl.get("geometry", {}))
            if dist > 260:
                continue
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_label = lbl

        logical_name = ""
        if best_label:
            logical_name = _extract_primary_service_name(best_label.get("name", ""))
            paired_label_ids.add(best_label.get("id"))
        if not logical_name:
            logical_name = _infer_service_name_from_image(style)

        if _is_legend_or_decoration(svc.get("id", ""), logical_name, style):
            continue

        if logical_name:
            logical_services.append(
                {
                    **svc,
                    "name": logical_name,
                    "label_id": best_label.get("id") if best_label else None,
                    "layer": arch_agent._get_service_layer(logical_name),
                }
            )

    for lbl in label_vertices:
        if lbl.get("id") in paired_label_ids:
            continue
        if _is_legend_or_decoration(lbl.get("id", ""), lbl.get("name", ""), lbl.get("style", "")):
            continue
        if _is_architecture_container(lbl.get("id", ""), lbl.get("name", ""), lbl.get("style", "")):
            continue

        label_name = _extract_primary_service_name(lbl.get("name", ""))
        if not label_name:
            continue
        if any(v.get("name", "").lower() == label_name.lower() for v in logical_services):
            continue

        logical_services.append(
            {
                **lbl,
                "name": label_name,
                "category": "service",
                "layer": arch_agent._get_service_layer(label_name),
            }
        )

    return {
        "vertices": logical_services + containers + [v for v in raw_vertices if v.get("category") == "decoration"],
        "edges": edges,
        "containers": containers,
    }


def _select_template_service_style(current_architecture: Dict[str, Any]) -> str:
    for v in current_architecture.get("vertices", []):
        style = v.get("style", "")
        if v.get("category") == "service" and "image=" in style:
            return style
    return (
        "image;aspect=fixed;html=1;points=[];align=center;fontSize=11;"
        "image=img/lib/azure2/general/Resource_Groups.svg;"
    )


def _select_default_container(current_architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    containers = current_architecture.get("containers", [])
    if not containers:
        return None

    scored = []
    for c in containers:
        name = (c.get("name") or "").lower()
        score = 0
        if "resource group" in name:
            score += 5
        if "subscription" in name:
            score += 1
        score += int(c.get("geometry", {}).get("width", 0) // 100)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _find_platform_container(current_architecture: Dict[str, Any], platform_canonical: str) -> Optional[Dict[str, Any]]:
    if platform_canonical != "azure functions":
        return None

    for container in current_architecture.get("containers", []):
        name = (container.get("name") or "").lower()
        if "azure functions" in name:
            return container

    return None


def _find_target_container_for_layer(
    current_architecture: Dict[str, Any], layer: int, default_container: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if default_container is None:
        return None

    services = [
        v
        for v in current_architecture.get("vertices", [])
        if v.get("category") == "service" and v.get("layer") == layer
    ]
    if services:
        parent_counts: Dict[str, int] = {}
        for svc in services:
            parent = svc.get("parent", "")
            if parent:
                parent_counts[parent] = parent_counts.get(parent, 0) + 1
        if parent_counts:
            best_parent = max(parent_counts.items(), key=lambda x: x[1])[0]
            for c in current_architecture.get("containers", []):
                if c.get("id") == best_parent:
                    return c

    return default_container


def _calculate_new_node_coordinates(
    current_architecture: Dict[str, Any], new_services: List[Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    placements: Dict[str, Dict[str, float]] = {}
    default_container = _select_default_container(current_architecture)

    if default_container is None:
        base_x = 120.0
        base_y = 140.0
        for idx, svc in enumerate(new_services):
            placements[svc["name"]] = {
                "x": base_x + (idx * 180.0),
                "y": base_y + (float(svc.get("layer", 2)) * 120.0),
                "width": 64.0,
                "height": 64.0,
                "parent_id": "1",
                "expand_container": False,
            }
        return placements

    services = [v for v in current_architecture.get("vertices", []) if v.get("category") == "service"]

    for svc in new_services:
        layer = int(svc.get("layer", 2))
        target_container = _find_platform_container(current_architecture, str(svc.get("platform_canonical", "")))
        if target_container is None:
            target_container = _find_target_container_for_layer(current_architecture, layer, default_container)
        parent_id = target_container.get("id", "1") if target_container else "1"
        cgeom = (target_container or {}).get("geometry", {})

        in_parent = [s for s in services if s.get("parent") == parent_id and int(s.get("layer", 2)) == layer]
        if in_parent:
            rightmost = max(in_parent, key=lambda x: x.get("geometry", {}).get("x", 0.0))
            x_new = float(rightmost.get("geometry", {}).get("x", 0.0)) + 180.0
            y_new = float(rightmost.get("geometry", {}).get("y", 0.0))
        else:
            x_new = 40.0
            y_new = 70.0 + (layer * 140.0 if layer >= 0 else 420.0)

        node_w = 64.0
        node_h = 64.0
        container_w = float(cgeom.get("width", 1200.0))
        container_h = float(cgeom.get("height", 800.0))

        if x_new + node_w > container_w - 30.0:
            same_parent = [s for s in services if s.get("parent") == parent_id]
            max_y = max([s.get("geometry", {}).get("y", 0.0) for s in same_parent], default=70.0)
            x_new = 40.0
            y_new = float(max_y) + 120.0

        needs_expand_w = x_new + node_w > container_w - 20.0
        needs_expand_h = y_new + node_h + 40.0 > container_h - 20.0

        placements[svc["name"]] = {
            "x": x_new,
            "y": y_new,
            "width": node_w,
            "height": node_h,
            "parent_id": parent_id,
            "expand_container": bool(needs_expand_w or needs_expand_h),
            "required_width": max(container_w, x_new + node_w + 40.0),
            "required_height": max(container_h, y_new + node_h + 70.0),
        }

        services.append(
            {
                "name": svc["name"],
                "layer": layer,
                "parent": parent_id,
                "geometry": {"x": x_new, "y": y_new, "width": node_w, "height": node_h},
            }
        )

    return placements


def _build_service_lookup(current_architecture: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for v in current_architecture.get("vertices", []):
        if v.get("category") != "service":
            continue
        name = (v.get("name") or "").strip()
        if name:
            lookup[name.lower()] = v
    return lookup


def _build_baseline_services_and_connections(current_architecture: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    services: List[Dict[str, Any]] = []
    for v in current_architecture.get("vertices", []):
        if v.get("category") != "service":
            continue
        name = (v.get("name") or "").strip()
        if not name:
            continue
        if _is_legend_or_decoration(v.get("id", ""), name, v.get("style", "")):
            continue
        services.append(
            {
                "name": name,
                "category": _layer_name(int(v.get("layer", 2))),
                "layer": int(v.get("layer", 2)),
                "parent": v.get("parent", ""),
            }
        )

    id_to_name = {
        v.get("id"): (v.get("name") or "")
        for v in current_architecture.get("vertices", [])
        if v.get("category") == "service"
        and not _is_legend_or_decoration(v.get("id", ""), v.get("name", ""), v.get("style", ""))
    }
    connections: List[Dict[str, Any]] = []
    for e in current_architecture.get("edges", []):
        src_name = id_to_name.get(e.get("source", ""), "")
        tgt_name = id_to_name.get(e.get("target", ""), "")
        if not src_name or not tgt_name:
            continue
        if _is_legend_or_decoration("", src_name, "") or _is_legend_or_decoration("", tgt_name, ""):
            continue
        connections.append(
            {
                "source": src_name,
                "target": tgt_name,
                "label": e.get("label", ""),
                "type": "service_integration",
            }
        )
    return services, connections


def _extract_candidate_services_from_component_output(
    prompt: str, extraction_result: Dict[str, Any], arch_agent: ArchitectureAgent, csv_context_summary: str = ""
) -> List[Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}
    named_function_candidate = _extract_named_function_service(prompt)
    feature_named_candidate = _extract_feature_named_service(prompt, csv_context_summary)

    tech_stack = extraction_result.get("tech_stack", [])
    technical_reqs = extraction_result.get("technical_requirements", [])

    for item in tech_stack:
        if isinstance(item, dict):
            name = str(item.get("technology", "")).strip()
        else:
            name = str(item).strip()
        if not name:
            continue
        if "azure" in name.lower() or arch_agent._get_service_layer(name) != 2 or "service" in name.lower():
            layer = arch_agent._get_service_layer(name)
            candidates[name.lower()] = {
                "name": name,
                "category": _layer_name(layer),
                "layer": layer,
            }

    for item in technical_reqs:
        text = ""
        if isinstance(item, dict):
            text = f"{item.get('area', '')} {item.get('requirement', '')} {item.get('details', '')}"
        else:
            text = str(item)

        for key in arch_agent.SERVICE_LAYERS.keys():
            if key and key in text.lower() and len(key) > 3:
                pretty = " ".join(part.capitalize() for part in key.split())
                layer = arch_agent.SERVICE_LAYERS[key]
                candidates[pretty.lower()] = {
                    "name": pretty,
                    "category": _layer_name(layer),
                    "layer": layer,
                }

    for key in arch_agent.SERVICE_LAYERS.keys():
        if key and key in prompt.lower() and len(key) > 3:
            pretty = " ".join(part.capitalize() for part in key.split())
            layer = arch_agent.SERVICE_LAYERS[key]
            candidates[pretty.lower()] = {
                "name": pretty,
                "category": _layer_name(layer),
                "layer": layer,
            }

    requested_canonicals = _extract_prompt_requested_canonicals(prompt)
    if named_function_candidate:
        candidates.pop("azure functions", None)
        candidates[named_function_candidate["name"].lower()] = named_function_candidate
    elif feature_named_candidate:
        candidates.pop("azure functions", None)
        candidates[feature_named_candidate["name"].lower()] = feature_named_candidate

    # Minimum-change mode: if the prompt explicitly names service(s), only use those.
    if requested_canonicals and not named_function_candidate and not feature_named_candidate:
        max_new = _max_new_services_from_prompt(prompt, requested_canonicals)
        direct_candidates: List[Dict[str, Any]] = []
        for canonical in sorted(requested_canonicals):
            display_name = _canonical_to_display_name(canonical)
            layer = arch_agent._get_service_layer(display_name)
            direct_candidates.append(
                {
                    "name": display_name,
                    "category": _layer_name(layer),
                    "layer": layer,
                }
            )
        return direct_candidates[:max_new]

    filtered: List[Dict[str, Any]] = []
    seen_canonical: set = set()
    for c in candidates.values():
        name = c.get("name", "")
        if c.get("custom_workload"):
            filtered.append(c)
            continue
        canonical = _canonical_service_key(name)
        if canonical in seen_canonical:
            continue
        if requested_canonicals:
            if canonical in requested_canonicals:
                filtered.append(c)
                seen_canonical.add(canonical)
            continue

        # If no canonical aliases are detected, still require direct prompt relevance.
        if _is_candidate_requested_by_prompt(name, prompt):
            filtered.append(c)
            seen_canonical.add(canonical)

    max_new = max(1, _max_new_services_from_prompt(prompt, set())) if (named_function_candidate or feature_named_candidate) else _max_new_services_from_prompt(prompt, set())
    return filtered[:max_new]


def _dynamic_edge_stitching(
    baseline_architecture: Dict[str, Any],
    services_to_add: List[Dict[str, Any]],
    arch_agent: ArchitectureAgent,
    modification_prompt: str = "",
    csv_context_summary: str = "",
) -> List[Dict[str, Any]]:
    existing_services, _existing_connections = _build_baseline_services_and_connections(baseline_architecture)
    all_services = existing_services + services_to_add

    by_layer: Dict[int, List[str]] = {}
    for svc in all_services:
        layer = int(svc.get("layer", 2))
        by_layer.setdefault(layer, []).append(svc.get("name", ""))

    new_connections: List[Dict[str, Any]] = []
    existing_name_index = _build_existing_service_indexes(baseline_architecture)
    requested_endpoints = _extract_existing_endpoints_from_prompt(
        modification_prompt,
        existing_name_index,
        baseline_architecture,
        csv_context_summary,
    )
    supporting_endpoints = _infer_feature_supporting_endpoints(modification_prompt, requested_endpoints)
    prompt_lower = (modification_prompt or "").lower()
    explicit_connect_intent = bool(
        re.search(r"\b(connect\w*|link\w*|integrat\w*|between|route\w*|wire\w*|attach\w*)\b", prompt_lower)
    )

    # Existing-to-existing connection request path.
    if not services_to_add and explicit_connect_intent and len(requested_endpoints) >= 2:
        database_markers = ("postgres", "sql", "database", "mysql", "cosmos", "redis")
        db_endpoint = next(
            (ep for ep in requested_endpoints if any(m in ep.lower() for m in database_markers)),
            requested_endpoints[1],
        )
        non_db_endpoint = next(
            (ep for ep in requested_endpoints if ep != db_endpoint and not any(m in ep.lower() for m in database_markers)),
            requested_endpoints[0],
        )
        if non_db_endpoint != db_endpoint:
            # Keep this explicit user-requested connection as-is to avoid over-correction.
            return [
                {
                    "source": non_db_endpoint,
                    "target": db_endpoint,
                    "label": "Data flow",
                    "type": "service_integration",
                }
            ]

    for svc in services_to_add:
        name = svc.get("name", "")
        layer = int(svc.get("layer", 2))
        if not name:
            continue

        resolved_name = name if svc.get("custom_workload") else (_resolve_existing_service_name(name, existing_name_index) or name)

        svc_new_edges: List[Dict[str, Any]] = []

        # If user named existing endpoints, connect minimally to those endpoints only.
        if requested_endpoints:
            if svc.get("custom_workload"):
                database_markers = ("postgres", "sql", "database", "mysql", "cosmos", "redis")
                db_endpoint = next(
                    (ep for ep in supporting_endpoints if any(m in ep.lower() for m in database_markers)),
                    None,
                )
                if db_endpoint is None:
                    db_endpoint = _infer_default_database_endpoint(baseline_architecture)
                app_endpoint = next(
                    (
                        ep
                        for ep in supporting_endpoints
                        if ep != db_endpoint and any(token in ep.lower() for token in ["payment", "search", "offer", "shop / flights", "cart"])
                    ),
                    None,
                )
                secondary_endpoint = next(
                    (
                        ep
                        for ep in supporting_endpoints
                        if ep not in {db_endpoint, app_endpoint} and any(token in ep.lower() for token in ["offer", "search", "shop / flights"])
                    ),
                    None,
                )
                if db_endpoint:
                    svc_new_edges.append(
                        {"source": resolved_name, "target": db_endpoint, "label": "Data flow", "type": "service_integration"}
                    )
                if app_endpoint and app_endpoint != resolved_name:
                    svc_new_edges.append(
                        {"source": app_endpoint, "target": resolved_name, "label": "Data flow", "type": "service_integration"}
                    )
                if secondary_endpoint and secondary_endpoint != resolved_name and secondary_endpoint != app_endpoint:
                    svc_new_edges.append(
                        {"source": secondary_endpoint, "target": resolved_name, "label": "Data flow", "type": "service_integration"}
                    )
            elif "between" in prompt_lower and len(requested_endpoints) >= 2:
                a = requested_endpoints[0]
                b = requested_endpoints[1]
                if a != resolved_name:
                    svc_new_edges.append(
                        {"source": a, "target": resolved_name, "label": "Data flow", "type": "service_integration"}
                    )
                if b != resolved_name:
                    svc_new_edges.append(
                        {"source": resolved_name, "target": b, "label": "Data flow", "type": "service_integration"}
                    )
            else:
                a = requested_endpoints[0]
                if a != resolved_name:
                    svc_new_edges.append(
                        {"source": a, "target": resolved_name, "label": "Data flow", "type": "service_integration"}
                    )

        # Fallback: only one conservative connection if prompt implies linking.
        if not svc_new_edges and explicit_connect_intent:
            upstream_candidates = by_layer.get(layer - 1, []) or by_layer.get(layer, [])
            if upstream_candidates:
                source = upstream_candidates[0]
                if source != resolved_name:
                    svc_new_edges.append(
                        {"source": source, "target": resolved_name, "label": "Data flow", "type": "service_integration"}
                    )

        new_connections.extend(svc_new_edges[:MIN_CHANGE_MAX_NEW_EDGES_PER_SERVICE])

    # Validate only the newly proposed delta edges; do not return baseline edges.
    validated_delta = arch_agent._validate_and_fix_connections(new_connections, all_services)
    return validated_delta


def _filter_enhanced_connections(
    enhanced_connections: List[Dict[str, Any]],
    baseline_architecture: Dict[str, Any],
    services_to_add: List[Dict[str, Any]],
    modification_prompt: str,
    csv_context_summary: str,
) -> List[Dict[str, Any]]:
    existing_index = _build_existing_service_indexes(baseline_architecture)
    requested_endpoints = _extract_existing_endpoints_from_prompt(
        modification_prompt,
        existing_index,
        baseline_architecture,
        csv_context_summary,
    )
    supporting_endpoints = _infer_feature_supporting_endpoints(modification_prompt, requested_endpoints)

    relevant_names: Set[str] = set()
    for svc in services_to_add:
        name = (svc.get("name") or "").strip()
        if name:
            relevant_names.add(name.lower())
    for ep in supporting_endpoints:
        if ep:
            relevant_names.add(ep.lower())

    filtered: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for conn in enhanced_connections:
        source = (conn.get("source") or "").strip()
        target = (conn.get("target") or "").strip()
        if not source or not target:
            continue
        if source.lower() == target.lower():
            continue

        pair = (source.lower(), target.lower())
        if pair in seen_pairs:
            continue

        # Keep only prompt-relevant enhanced edges to prevent fan-out.
        if relevant_names:
            if source.lower() not in relevant_names and target.lower() not in relevant_names:
                continue
        elif services_to_add:
            # If no endpoints were resolved, keep only edges touching new services.
            new_names = {(svc.get("name") or "").lower() for svc in services_to_add if svc.get("name")}
            if source.lower() not in new_names and target.lower() not in new_names:
                continue

        filtered.append(conn)
        seen_pairs.add(pair)

    return filtered


def _next_numeric_id(graph_root: ET.Element) -> int:
    max_id = 1000
    for cell in graph_root.findall("mxCell"):
        cid = cell.get("id", "")
        if cid.isdigit():
            max_id = max(max_id, int(cid))
    return max_id + 1


def _find_or_create_label_style(current_architecture: Dict[str, Any]) -> str:
    for v in current_architecture.get("vertices", []):
        style = v.get("style", "")
        if v.get("category") == "label" and "text;" in style:
            return style
    return (
        "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=top;"
        "whiteSpace=wrap;rounded=0;fontSize=10;fontColor=#484848;"
    )


def _expand_container_if_needed(
    graph_root: ET.Element,
    container_id: str,
    required_width: float,
    required_height: float,
) -> None:
    for cell in graph_root.findall("mxCell"):
        if cell.get("id") != container_id:
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue
        width = _safe_float(geom.get("width"), 0.0)
        height = _safe_float(geom.get("height"), 0.0)
        if required_width > width:
            geom.set("width", str(int(required_width)))
        if required_height > height:
            geom.set("height", str(int(required_height)))
        break


def _remove_generated_artifacts_from_xml(xml_content: str) -> str:
    root, diagram, model, was_compressed = _extract_mxgraph_model(xml_content)
    graph_root = _get_graph_root(model)

    generated_ids = set()
    for cell in list(graph_root.findall("mxCell")):
        if cell.get("data-mod-hash"):
            generated_ids.add(cell.get("id", ""))
            graph_root.remove(cell)

    if generated_ids:
        for cell in list(graph_root.findall("mxCell")):
            if cell.get("edge") != "1":
                continue
            source = cell.get("source", "")
            target = cell.get("target", "")
            if source in generated_ids or target in generated_ids:
                graph_root.remove(cell)

    # Remove any existing connections that touch legend/decorative blocks,
    # including the "Production Additions" block.
    decoration_ids = set()
    for cell in graph_root.findall("mxCell"):
        if cell.get("vertex") != "1":
            continue
        if _is_legend_or_decoration(cell.get("id", ""), cell.get("value", ""), cell.get("style", "")):
            decoration_ids.add(cell.get("id", ""))

    if decoration_ids:
        for cell in list(graph_root.findall("mxCell")):
            if cell.get("edge") != "1":
                continue
            source = cell.get("source", "")
            target = cell.get("target", "")
            if source in decoration_ids or target in decoration_ids:
                graph_root.remove(cell)

    return _materialize_mxgraph_model(root, diagram, model, was_compressed)


def _inject_nodes_and_edges_into_xml(
    xml_content: str,
    current_architecture: Dict[str, Any],
    services_to_add: List[Dict[str, Any]],
    validated_connections: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, str]]]:
    root, diagram, model, was_compressed = _extract_mxgraph_model(xml_content)
    graph_root = _get_graph_root(model)

    existing_index = _build_existing_service_indexes(current_architecture)
    filtered_new_services: List[Dict[str, Any]] = []
    reused_services: List[Dict[str, str]] = []
    for svc in services_to_add:
        candidate_name = svc.get("name", "")
        if not candidate_name:
            continue
        matched_existing = None if svc.get("custom_workload") else _resolve_existing_service_name(candidate_name, existing_index)
        if matched_existing:
            reused_services.append({"requested": candidate_name, "reused": matched_existing})
            continue
        filtered_new_services.append(svc)

    placements = _calculate_new_node_coordinates(current_architecture, filtered_new_services)
    template_style = _select_template_service_style(current_architecture)
    label_style = _find_or_create_label_style(current_architecture)
    id_counter = _next_numeric_id(graph_root)

    service_name_to_icon_id: Dict[str, str] = {}
    for v in current_architecture.get("vertices", []):
        if v.get("category") == "service" and v.get("name"):
            service_name_to_icon_id[v["name"]] = v.get("id", "")

    # Also map canonical aliases to existing IDs to maximize edge reuse.
    for v in current_architecture.get("vertices", []):
        if v.get("category") != "service" or not v.get("name"):
            continue
        canonical = _canonical_service_key(v["name"])
        if canonical and canonical not in service_name_to_icon_id:
            service_name_to_icon_id[canonical] = v.get("id", "")

    for svc in filtered_new_services:
        svc_name = svc.get("name", "")
        if not svc_name:
            continue
        place = placements.get(svc_name, {})
        parent_id = place.get("parent_id", "1")

        if place.get("expand_container"):
            _expand_container_if_needed(
                graph_root,
                parent_id,
                place.get("required_width", 0.0),
                place.get("required_height", 0.0),
            )

        tracking_hash = uuid.uuid4().hex
        icon_id = str(id_counter)
        id_counter += 1
        label_id = str(id_counter)
        id_counter += 1

        icon_cell = ET.SubElement(graph_root, "mxCell")
        icon_cell.set("id", icon_id)
        icon_cell.set("value", "")
        icon_cell.set(
            "style",
            _select_service_style_for_name(
                service_name=svc_name,
                current_architecture=current_architecture,
                fallback_style=template_style,
            ),
        )
        icon_cell.set("vertex", "1")
        icon_cell.set("parent", parent_id)
        icon_cell.set("data-mod-hash", tracking_hash)

        icon_geom = ET.SubElement(icon_cell, "mxGeometry")
        icon_geom.set("x", str(int(place.get("x", 40.0))))
        icon_geom.set("y", str(int(place.get("y", 80.0))))
        icon_geom.set("width", str(int(place.get("width", 64.0))))
        icon_geom.set("height", str(int(place.get("height", 64.0))))
        icon_geom.set("as", "geometry")

        lbl_cell = ET.SubElement(graph_root, "mxCell")
        lbl_cell.set("id", label_id)
        lbl_cell.set("value", svc_name)
        lbl_cell.set("style", label_style)
        lbl_cell.set("vertex", "1")
        lbl_cell.set("parent", parent_id)
        lbl_cell.set("data-mod-hash", tracking_hash)

        lbl_geom = ET.SubElement(lbl_cell, "mxGeometry")
        lbl_geom.set("x", str(int(place.get("x", 40.0) - 16.0)))
        lbl_geom.set("y", str(int(place.get("y", 80.0) + place.get("height", 64.0) + 4.0)))
        lbl_geom.set("width", "96")
        lbl_geom.set("height", "26")
        lbl_geom.set("as", "geometry")

        service_name_to_icon_id[svc_name] = icon_id
        service_name_to_icon_id[_canonical_service_key(svc_name)] = icon_id

    existing_edge_pairs = set()
    for cell in graph_root.findall("mxCell"):
        if cell.get("edge") == "1":
            existing_edge_pairs.add((cell.get("source", ""), cell.get("target", "")))

    for conn in validated_connections:
        source_name = conn.get("source", "")
        target_name = conn.get("target", "")
        source_id = service_name_to_icon_id.get(source_name) or service_name_to_icon_id.get(
            _canonical_service_key(source_name)
        )
        target_id = service_name_to_icon_id.get(target_name) or service_name_to_icon_id.get(
            _canonical_service_key(target_name)
        )

        if not source_id or not target_id:
            continue
        if (source_id, target_id) in existing_edge_pairs:
            continue
        if (target_id, source_id) in existing_edge_pairs:
            continue

        edge_id = str(id_counter)
        id_counter += 1

        edge_cell = ET.SubElement(graph_root, "mxCell")
        edge_cell.set("id", edge_id)
        edge_cell.set("value", conn.get("label", ""))
        edge_cell.set(
            "style",
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=12;"
            "html=1;endArrow=blockThin;endFill=1;strokeColor=#0078d4;strokeWidth=1.5;"
            "fontSize=8;fontColor=#444444;labelBackgroundColor=#ffffff;",
        )
        edge_cell.set("edge", "1")
        edge_cell.set("parent", "1")
        edge_cell.set("source", source_id)
        edge_cell.set("target", target_id)

        edge_geom = ET.SubElement(edge_cell, "mxGeometry")
        edge_geom.set("relative", "1")
        edge_geom.set("as", "geometry")

        existing_edge_pairs.add((source_id, target_id))

    return _materialize_mxgraph_model(root, diagram, model, was_compressed), filtered_new_services, reused_services


def _create_rollback_backup(original_drawio_content: str, target_path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{target_path.stem}_BACKUP_{ts}.drawio"
    backup_path = BACKUP_DIR / backup_name
    backup_path.write_text(original_drawio_content, encoding="utf-8")
    return backup_path


class ModifyArchWorkflow:
    def __init__(self) -> None:
        self.component_agent = ComponentExtractionAgent()
        self.architecture_agent = ArchitectureAgent()
        self.connection_agent = ConnectionExpertAgent()
        self.review_agent = AzureArchitectureReviewAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        if not LANGGRAPH_AVAILABLE:
            return None

        graph = StateGraph(ModifyArchState)
        graph.add_node("ComponentExtractionAgent", self.component_extraction_node)
        graph.add_node("ArchitectureAgent", self.architecture_node)
        graph.add_node("ConnectionExpertAgent", self.connection_node)
        graph.add_node("AzureArchitectureReviewAgent", self.review_node)

        graph.add_edge(START, "ComponentExtractionAgent")
        graph.add_edge("ComponentExtractionAgent", "ArchitectureAgent")
        graph.add_edge("ArchitectureAgent", "ConnectionExpertAgent")
        graph.add_edge("ConnectionExpertAgent", "AzureArchitectureReviewAgent")
        graph.add_conditional_edges(
            "AzureArchitectureReviewAgent",
            self._route_after_review,
            {
                "architecture_retry": "ArchitectureAgent",
                "done": END,
            },
        )

        return graph.compile()

    def _route_after_review(self, state: ModifyArchState) -> str:
        if state.get("requires_correction") and int(state.get("correction_attempts", 0)) < 1:
            return "architecture_retry"
        return "done"

    async def component_extraction_node(self, state: ModifyArchState) -> ModifyArchState:
        prompt = state["modification_prompt"]
        context_summary = state.get("csv_context_summary", "")

        extraction_prompt = "\n\n".join(
            [
                "Identify only the architecture delta requested by the user.",
                f"USER DELTA REQUEST:\n{prompt}",
                f"CSV CONTEXT:\n{context_summary}",
            ]
        )

        extraction_result = await self.component_agent.analyze(extraction_prompt, context={"mode": "delta_extraction"})
        candidates = _extract_candidate_services_from_component_output(
            prompt,
            extraction_result,
            self.architecture_agent,
            context_summary,
        )

        trace = list(state.get("workflow_trace", []))
        trace.append(
            {
                "node": "ComponentExtractionAgent",
                "candidate_service_count": len(candidates),
            }
        )

        state["extracted_delta"] = extraction_result
        state["candidate_services"] = candidates
        state["workflow_trace"] = trace
        return state

    async def architecture_node(self, state: ModifyArchState) -> ModifyArchState:
        baseline = state["baseline_architecture"]
        baseline_lookup = _build_service_lookup(baseline)
        existing_name_index = _build_existing_service_indexes(baseline)
        candidates = state.get("candidate_services", [])

        services_to_add: List[Dict[str, Any]] = []
        dedupe: set = set()
        for svc in candidates:
            name = svc.get("name", "").strip()
            if not name:
                continue

            existing_equivalent = None if svc.get("custom_workload") else _resolve_existing_service_name(name, existing_name_index)
            if existing_equivalent or name.lower() in baseline_lookup:
                continue

            layer = self.architecture_agent._get_service_layer(name)
            canonical_key = _canonical_service_key(name)
            if canonical_key in dedupe:
                continue

            dedupe.add(canonical_key)
            services_to_add.append(
                {
                    "name": name,
                    "category": _layer_name(layer),
                    "layer": layer,
                    "canonical_key": canonical_key,
                    "custom_workload": bool(svc.get("custom_workload")),
                    "platform_canonical": svc.get("platform_canonical", ""),
                }
            )

        review_feedback = state.get("review_result", {}).get("correction_tasks", [])
        feedback_text = "\n".join(str(task) for task in review_feedback) if review_feedback else ""

        architecture_prompt = "\n\n".join(
            [
                "Use SERVICE_LAYERS to assign proper layer/container placement for these delta services.",
                f"Delta services: {services_to_add}",
                f"Review feedback: {feedback_text}",
                "Do not redesign baseline; only refine placement decisions for delta services.",
            ]
        )

        _ = await self.architecture_agent.analyze(
            architecture_prompt,
            context={
                "architecture_analysis": {
                    "status": "completed",
                    "services": [
                        {
                            "name": v.get("name", ""),
                            "layer": int(v.get("layer", 2)),
                            "category": v.get("category", "service"),
                        }
                        for v in baseline.get("vertices", [])
                        if v.get("category") == "service"
                    ],
                    "connections": baseline.get("edges", []),
                    "containers": baseline.get("containers", []),
                },
                "component_extraction": state.get("extracted_delta", {}),
            },
        )

        trace = list(state.get("workflow_trace", []))
        trace.append(
            {
                "node": "ArchitectureAgent",
                "services_to_add": [s.get("name") for s in services_to_add],
            }
        )

        state["services_to_add"] = services_to_add
        state["workflow_trace"] = trace
        state["correction_attempts"] = int(state.get("correction_attempts", 0)) + 1
        return state

    async def connection_node(self, state: ModifyArchState) -> ModifyArchState:
        baseline = state["baseline_architecture"]
        services_to_add = state.get("services_to_add", [])
        connection_mode = (state.get("connection_mode") or "enhanced").strip().lower()
        if connection_mode not in {"enhanced", "strict"}:
            connection_mode = "enhanced"

        validated_connections = _dynamic_edge_stitching(
            baseline,
            services_to_add,
            self.architecture_agent,
            state.get("modification_prompt", ""),
            state.get("csv_context_summary", ""),
        )

        baseline_services, _baseline_connections = _build_baseline_services_and_connections(baseline)
        all_services = baseline_services + services_to_add

        connection_result = await self.connection_agent.analyze(
            state["modification_prompt"],
            context={
                "architecture_analysis": {
                    "status": "completed",
                    "services": all_services,
                    "connections": validated_connections,
                    "containers": baseline.get("containers", []),
                }
            },
        )

        enhanced = connection_result.get("enhanced_architecture", {})
        enhanced_connections = enhanced.get("connections", validated_connections)
        if connection_mode == "strict":
            final_connections = validated_connections
        else:
            final_connections = _filter_enhanced_connections(
                enhanced_connections,
                baseline,
                services_to_add,
                state.get("modification_prompt", ""),
                state.get("csv_context_summary", ""),
            )
            if not final_connections:
                final_connections = validated_connections

        trace = list(state.get("workflow_trace", []))
        trace.append(
            {
                "node": "ConnectionExpertAgent",
                "connection_count": len(final_connections),
                "connection_mode": connection_mode,
            }
        )

        state["proposed_connections"] = enhanced_connections
        state["validated_connections"] = final_connections
        state["workflow_trace"] = trace
        return state

    async def review_node(self, state: ModifyArchState) -> ModifyArchState:
        hard_constraints = state.get("hard_constraints", "")
        baseline = state["baseline_architecture"]
        services_to_add = state.get("services_to_add", [])
        validated_connections = state.get("validated_connections", [])

        baseline_services, _baseline_connections = _build_baseline_services_and_connections(baseline)
        merged_services = baseline_services + services_to_add

        review_requirements = "\n\n".join(
            [
                f"User modification request:\n{state['modification_prompt']}",
                hard_constraints,
            ]
        )

        review_result = await self.review_agent.analyze(
            review_requirements,
            context={
                "component_extraction": state.get("extracted_delta", {}),
                "architecture_analysis": {
                    "status": "completed",
                    "services": merged_services,
                    "connections": validated_connections,
                    "containers": baseline.get("containers", []),
                    "architecture_pattern": "delta-modification",
                },
                "validation_result": {
                    "overall_status": "in_progress",
                    "overall_validation_score": 0,
                },
                "hard_constraints": hard_constraints,
            },
        )

        status = str(review_result.get("review_status", "APPROVED")).upper()
        requires_correction = status in {"NEEDS_CORRECTION", "CRITICAL_ISSUES"}

        trace = list(state.get("workflow_trace", []))
        trace.append(
            {
                "node": "AzureArchitectureReviewAgent",
                "review_status": status,
                "overall_score": review_result.get("overall_score"),
            }
        )

        state["review_result"] = review_result
        state["requires_correction"] = requires_correction
        state["workflow_trace"] = trace
        return state

    async def run(self, initial_state: ModifyArchState) -> ModifyArchState:
        if not self.graph:
            raise RuntimeError("LangGraph is not available. Install langgraph to use /api/diagram/modifyArch")
        return await self.graph.ainvoke(initial_state)


async def _run_modification_pipeline(
    source_xml: str,
    modification_prompt: str,
    connection_mode: str,
) -> Dict[str, Any]:
    sanitized_xml = _remove_generated_artifacts_from_xml(source_xml)
    baseline_architecture = _parse_drawio_xml_to_dict(sanitized_xml)
    csv_context_summary = _build_csv_context_summary(modification_prompt)
    hard_constraints = _read_hard_constraints()

    workflow = ModifyArchWorkflow()
    initial_state: ModifyArchState = {
        "modification_prompt": modification_prompt,
        "connection_mode": (connection_mode or "enhanced"),
        "baseline_architecture": baseline_architecture,
        "baseline_xml": source_xml,
        "csv_context_summary": csv_context_summary,
        "hard_constraints": hard_constraints,
        "correction_attempts": 0,
        "requires_correction": False,
        "workflow_trace": [],
    }

    final_state = await workflow.run(initial_state)
    services_to_add = final_state.get("services_to_add", [])
    validated_connections = final_state.get("validated_connections", [])

    updated_xml, inserted_services, reused_services = _inject_nodes_and_edges_into_xml(
        xml_content=sanitized_xml,
        current_architecture=baseline_architecture,
        services_to_add=services_to_add,
        validated_connections=validated_connections,
    )

    return {
        "updated_xml": updated_xml,
        "inserted_services": inserted_services,
        "reused_services": reused_services,
        "validated_connections_count": len(validated_connections),
        "review_result": final_state.get("review_result", {}),
        "workflow_trace": final_state.get("workflow_trace", []),
    }


@router.get("/api/diagram/modifyArch/files")
async def list_modify_arch_diagrams() -> Dict[str, Any]:
    diagrams = _list_available_diagram_files()
    diagrams_dir = _get_diagrams_dir()
    return {
        "success": True,
        "configured_folder": str(diagrams_dir),
        "count": len(diagrams),
        "diagrams": diagrams,
    }


@router.post("/api/diagram/modifyArch/lock")
async def lock_modify_arch_diagram(request: DiagramLockRequest) -> Dict[str, Any]:
    diagram_path = _resolve_diagram_path(request.diagram_id)
    original_xml = diagram_path.read_text(encoding="utf-8", errors="replace")

    lock_id = uuid.uuid4().hex
    LOCKED_DIAGRAM_SESSIONS[lock_id] = {
        "diagram_id": request.diagram_id,
        "diagram_path": str(diagram_path),
        "original_xml": original_xml,
        "staged_xml": None,
        "created_at": datetime.now().isoformat(),
    }

    return {
        "success": True,
        "lock_id": lock_id,
        "diagram_id": request.diagram_id,
        "diagram_path": str(diagram_path),
        "preview_xml": original_xml,
        "has_staged_changes": False,
    }


@router.get("/api/diagram/modifyArch/preview")
async def preview_modify_arch_diagram(
    diagram_id: Optional[str] = Query(default=None),
    lock_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    if lock_id:
        session = _get_session(lock_id)
        staged_xml = session.get("staged_xml")
        original_xml = session.get("original_xml")
        if staged_xml:
            preview_xml = _generate_highlighted_preview_xml(original_xml or "", staged_xml)
        else:
            preview_xml = original_xml
        return {
            "success": True,
            "lock_id": lock_id,
            "diagram_id": session.get("diagram_id"),
            "diagram_path": session.get("diagram_path"),
            "has_staged_changes": bool(session.get("staged_xml")),
            "preview_xml": preview_xml,
        }

    if not diagram_id:
        raise HTTPException(status_code=400, detail="Either lock_id or diagram_id is required")

    diagram_path = _resolve_diagram_path(diagram_id)
    preview_xml = diagram_path.read_text(encoding="utf-8", errors="replace")
    return {
        "success": True,
        "diagram_id": diagram_id,
        "diagram_path": str(diagram_path),
        "has_staged_changes": False,
        "preview_xml": preview_xml,
    }


@router.post("/api/diagram/modifyArch/accept")
async def accept_modify_arch_changes(request: DiagramLockDecisionRequest) -> Dict[str, Any]:
    session = _get_session(request.lock_id)
    staged_xml = session.get("staged_xml")
    final_xml = (request.manual_xml or "").strip() or staged_xml
    if not final_xml:
        raise HTTPException(status_code=400, detail="No staged updates found for this lock")

    final_xml = _strip_preview_highlight_markers(final_xml)

    diagram_path = Path(session["diagram_path"])
    current_xml = diagram_path.read_text(encoding="utf-8", errors="replace")
    backup_path = _create_rollback_backup(current_xml, diagram_path)
    diagram_path.write_text(final_xml, encoding="utf-8")

    LOCKED_DIAGRAM_SESSIONS.pop(request.lock_id, None)

    return {
        "success": True,
        "message": "Staged changes accepted and written to diagram",
        "diagram_path": str(diagram_path),
        "backup_file": str(backup_path),
        "preview_xml": final_xml,
    }


@router.post("/api/diagram/modifyArch/reject")
async def reject_modify_arch_changes(request: DiagramLockDecisionRequest) -> Dict[str, Any]:
    session = _get_session(request.lock_id)
    original_xml = session.get("original_xml", "")
    diagram_path = Path(session["diagram_path"])

    LOCKED_DIAGRAM_SESSIONS.pop(request.lock_id, None)

    return {
        "success": True,
        "message": "Staged changes rejected. Diagram reverted to original preview state.",
        "diagram_path": str(diagram_path),
        "preview_xml": original_xml,
    }


@router.post("/api/diagram/modifyArch")
async def modify_architecture_in_place(
    request: ModifyArchRequest,
    x_diagram_lock_id: Optional[str] = Header(default=None, alias="x-diagram-lock-id"),
) -> Dict[str, Any]:
    if not LANGGRAPH_AVAILABLE:
        raise HTTPException(status_code=500, detail="LangGraph is not installed in this environment")

    logger.info("modifyArch request received: %s", request.modification_prompt[:160])

    target_path = TARGET_DRAWIO_PATH
    source_xml = ""
    active_lock_id = x_diagram_lock_id

    if active_lock_id:
        session = _get_session(active_lock_id)
        target_path = Path(session["diagram_path"])
        source_xml = session.get("staged_xml") or session.get("original_xml") or ""
    else:
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Target drawio file not found: {target_path}")
        source_xml = target_path.read_text(encoding="utf-8", errors="replace")

    try:
        pipeline_result = await _run_modification_pipeline(
            source_xml=source_xml,
            modification_prompt=request.modification_prompt,
            connection_mode=request.connection_mode,
        )
    except Exception as e:
        logger.exception("modifyArch workflow failed")
        raise HTTPException(status_code=500, detail=f"modifyArch workflow failed: {str(e)}")

    updated_xml = pipeline_result["updated_xml"]

    if active_lock_id:
        session = _get_session(active_lock_id)
        session["staged_xml"] = updated_xml
        session["last_modified_at"] = datetime.now().isoformat()

        highlighted_preview_xml = _generate_highlighted_preview_xml(session.get("original_xml", ""), updated_xml)

        return {
            "success": True,
            "message": "Architecture update staged. Accept to persist or reject to discard.",
            "staged": True,
            "lock_id": active_lock_id,
            "target_file": str(target_path),
            "preview_xml": highlighted_preview_xml,
            "services_added": pipeline_result["inserted_services"],
            "services_reused": pipeline_result["reused_services"],
            "connections_validated_count": pipeline_result["validated_connections_count"],
            "review_result": pipeline_result["review_result"],
            "hard_constraints_header": "⚠️ HARD ARCHITECTURAL CONSTRAINTS - DO NOT VIOLATE",
            "workflow_trace": pipeline_result["workflow_trace"],
        }

    backup_path = _create_rollback_backup(source_xml, target_path)
    target_path.write_text(updated_xml, encoding="utf-8")
    logger.info("modifyArch write completed. File updated: %s", target_path)

    return {
        "success": True,
        "message": "Architecture diagram modified in place",
        "staged": False,
        "target_file": str(target_path),
        "backup_file": str(backup_path),
        "preview_xml": updated_xml,
        "services_added": pipeline_result["inserted_services"],
        "services_reused": pipeline_result["reused_services"],
        "connections_validated_count": pipeline_result["validated_connections_count"],
        "review_result": pipeline_result["review_result"],
        "hard_constraints_header": "⚠️ HARD ARCHITECTURAL CONSTRAINTS - DO NOT VIOLATE",
        "workflow_trace": pipeline_result["workflow_trace"],
    }
