"""
Azure Docs Local Scanner
Scans the local azure-docs folder to build a searchable index of all 
Azure Architecture Center reference architectures, patterns, guides, 
and example scenarios with their metadata, content summaries, and diagram paths.
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from config import external_url_config, content_config

logger = logging.getLogger(__name__)

# Base URL for Azure Architecture Center (used to construct live URLs from local paths)
AZURE_ARCH_BASE_URL = external_url_config.AZURE_ARCH_BASE_URL


class AzureDocsScanner:
    """Scans the local azure-docs folder and builds a searchable reference catalog."""

    def __init__(self, docs_root: str = None):
        """Initialize with the path to the azure-docs folder."""
        if docs_root is None:
            # Default: look for azure-docs relative to this file's parent
            base_dir = Path(__file__).resolve().parent.parent
            docs_root = str(base_dir / "azure-docs")
        
        self.docs_root = Path(docs_root)
        if not self.docs_root.exists():
            logger.warning(f"Azure docs folder not found at {self.docs_root}")
        
        self._index: List[Dict[str, Any]] = []
        self._indexed = False

    def build_index(self) -> List[Dict[str, Any]]:
        """Scan all docs and build the full searchable index. Cached after first call."""
        if self._indexed:
            return self._index

        if not self.docs_root.exists():
            logger.error(f"Azure docs root does not exist: {self.docs_root}")
            self._indexed = True
            return self._index

        logger.info(f"Scanning azure-docs at: {self.docs_root}")

        # Scan YAML architecture files (richest metadata)
        self._scan_yaml_files()
        # Scan standalone markdown files (patterns, guides, etc.)
        self._scan_markdown_files()

        self._indexed = True
        logger.info(f"Azure docs index built: {len(self._index)} entries")
        return self._index

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search the index using keyword/phrase matching. Returns ranked results."""
        if not self._indexed:
            self.build_index()

        query_lower = query.lower()
        query_terms = set(re.findall(r'\b\w{3,}\b', query_lower))

        scored_results = []
        for entry in self._index:
            score = self._score_entry(entry, query_lower, query_terms)
            if score > 0:
                scored_results.append({**entry, "_score": score})

        scored_results.sort(key=lambda x: x["_score"], reverse=True)
        return scored_results[:max_results]

    def search_by_components(self, components: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
        """Search the index using extracted component data from ComponentExtractionAgent."""
        if not self._indexed:
            self.build_index()

        # Build search text from all component sections
        search_parts = []
        for section in ["apis", "nfrs", "technical_requirements", "tech_stack",
                        "business_requirements", "data_requirements", "integration_points"]:
            items = components.get(section, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        for val in item.values():
                            if isinstance(val, str):
                                search_parts.append(val.lower())
                    elif isinstance(item, str):
                        search_parts.append(item.lower())
            elif isinstance(items, str):
                search_parts.append(items.lower())

        full_text = " ".join(search_parts)
        query_terms = set(re.findall(r'\b\w{3,}\b', full_text))

        scored_results = []
        for entry in self._index:
            score = self._score_entry(entry, full_text, query_terms)
            if score > 0:
                scored_results.append({**entry, "_score": score})

        scored_results.sort(key=lambda x: x["_score"], reverse=True)
        return scored_results[:max_results]

    def get_doc_content(self, doc_path: str, max_chars: int = 3000) -> str:
        """Read the content of a specific doc file, truncated to max_chars."""
        full_path = self.docs_root / doc_path
        if not full_path.exists():
            return ""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read(max_chars)
            return content
        except Exception as e:
            logger.error(f"Error reading doc {doc_path}: {e}")
            return ""

    def find_diagrams(self, doc_path: str) -> List[str]:
        """Find SVG/PNG diagram files associated with a doc."""
        full_path = self.docs_root / doc_path
        doc_dir = full_path.parent
        diagrams = []

        # Check for images/ subfolder
        images_dir = doc_dir / "images"
        if images_dir.exists():
            for img in images_dir.iterdir():
                if img.suffix.lower() in ('.svg', '.png'):
                    diagrams.append(str(img.relative_to(self.docs_root)))

        # Check for _images/ subfolder
        _images_dir = doc_dir / "_images"
        if _images_dir.exists():
            for img in _images_dir.iterdir():
                if img.suffix.lower() in ('.svg', '.png'):
                    diagrams.append(str(img.relative_to(self.docs_root)))

        # Check for media/ subfolder
        media_dir = doc_dir / "media"
        if media_dir.exists():
            for img in media_dir.iterdir():
                if img.suffix.lower() in ('.svg', '.png'):
                    diagrams.append(str(img.relative_to(self.docs_root)))

        return diagrams

    def get_entry_for_prompt(self, entry: Dict[str, Any], include_content: bool = True) -> Dict[str, Any]:
        """Format a catalog entry for inclusion in an LLM prompt."""
        result = {
            "title": entry.get("title", ""),
            "url": entry.get("url", ""),
            "summary": entry.get("summary", ""),
            "category": entry.get("category", ""),
            "products": entry.get("products", []),
            "tags": entry.get("tags", []),
            "local_path": entry.get("doc_path", ""),
            "diagrams": entry.get("diagrams", []),
        }
        if include_content and entry.get("doc_path"):
            result["content_excerpt"] = self.get_doc_content(entry["doc_path"], max_chars=2000)
        return result

    # ─── Internal scanning methods ───────────────────────────────────────

    def _scan_yaml_files(self):
        """Scan .yml files for YamlMime:Architecture entries."""
        yml_patterns = [
            "reference-architectures/**/*.yml",
            "networking/architecture/*.yml",
            "web-apps/**/*.yml",
            "databases/architecture/*.yml",
            "databases/guide/*.yml",
            "databases/idea/*.yml",
            "ai-ml/architecture/*.yml",
            "ai-ml/idea/*.yml",
            "ai-ml/openai/**/*.yml",
            "ai-ml/guide/*.yml",
            "example-scenario/**/*.yml",
            "serverless/**/*.yml",
            "hybrid/*.yml",
            "high-availability/*.yml",
            "identity/*.yml",
            "integration/*.yml",
            "solution-ideas/articles/*.yml",
            "microservices/*.yml",
            "microservices/design/*.yml",
            "microservices/model/*.yml",
            "guide/aks/*.yml",
            "guide/devsecops/*.yml",
            "guide/security/*.yml",
            "guide/multitenant/considerations/*.yml",
            "guide/networking/global-web-applications/*.yml",
            "guide/iot/*.yml",
            "guide/devops/*.yml",
            "guide/infrastructure/*.yml",
            "guide/spot/*.yml",
            "best-practices/*.yml",
            "industries/**/*.yml",
        ]

        for pattern in yml_patterns:
            for yml_path in self.docs_root.glob(pattern):
                entry = self._parse_yaml_file(yml_path)
                if entry:
                    self._index.append(entry)

    def _scan_markdown_files(self):
        """Scan standalone markdown files that don't have a paired .yml."""
        md_scan_paths = [
            "patterns/*.md",
            "guide/architecture-styles/*.md",
            "guide/design-principles/*.md",
            "guide/technology-choices/*.md",
            "guide/multitenant/overview.md",
            "guide/multitenant/approaches/*.md",
            "guide/multitenant/service/*.md",
            "guide/devops/*.md",
            "microservices/design/*.md",
            "microservices/model/*.md",
            "best-practices/*.md",
            "ai-ml/guide/*.md",
            "ai-ml/guide/rag/*.md",
            "networking/guide/*.md",
            "hybrid/*.md",
        ]

        # Track which content files are already indexed via YAML
        indexed_content_files = set()
        for entry in self._index:
            if entry.get("content_file"):
                indexed_content_files.add(entry["content_file"])

        for pattern in md_scan_paths:
            for md_path in self.docs_root.glob(pattern):
                rel_path = str(md_path.relative_to(self.docs_root)).replace("\\", "/")
                # Skip if this content file is already indexed via a YAML pair
                if rel_path in indexed_content_files:
                    continue
                # Skip index files and non-content files
                if md_path.name in ("index.md", "toc.yml", "overview.md"):
                    continue
                entry = self._parse_markdown_file(md_path)
                if entry:
                    self._index.append(entry)

    def _parse_yaml_file(self, yml_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a YAML architecture file to extract metadata."""
        try:
            with open(yml_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.debug(f"Error reading {yml_path}: {e}")
            return None

        # Only process YamlMime:Architecture files
        if "YamlMime:Architecture" not in content[:content_config.YAML_HEADER_PEEK]:
            return None

        rel_path = str(yml_path.relative_to(self.docs_root)).replace("\\", "/")

        entry = {
            "doc_path": rel_path,
            "source_type": "yaml_architecture",
        }

        # Extract fields using regex (avoids YAML library dependency)
        entry["title"] = self._extract_yaml_field(content, "name") or \
                         self._extract_yaml_nested_field(content, "metadata", "title") or ""
        entry["summary"] = self._extract_yaml_field(content, "summary") or \
                           self._extract_yaml_nested_field(content, "metadata", "description") or ""

        # Extract products list
        products = self._extract_yaml_list(content, "products")
        entry["products"] = products

        # Extract categories
        categories = self._extract_yaml_list(content, "azureCategories")
        entry["category"] = ", ".join(categories) if categories else self._infer_category(rel_path)

        # Extract content file reference
        content_file = self._extract_content_file_ref(content)
        if content_file:
            content_file_path = str((yml_path.parent / content_file).relative_to(self.docs_root)).replace("\\", "/")
            entry["content_file"] = content_file_path
        else:
            entry["content_file"] = None

        # Build URL from path
        entry["url"] = self._path_to_url(rel_path)

        # Build tags from title, summary, products, categories
        entry["tags"] = self._build_tags(entry)

        # Find associated diagrams
        entry["diagrams"] = self.find_diagrams(rel_path)

        # Extract topic type
        topic = self._extract_yaml_nested_field(content, "metadata", "ms.topic") or ""
        entry["topic_type"] = topic

        return entry

    def _parse_markdown_file(self, md_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a standalone markdown file for metadata from YAML frontmatter and headings."""
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read(5000)  # Read first 5000 chars for metadata
        except Exception as e:
            logger.debug(f"Error reading {md_path}: {e}")
            return None

        rel_path = str(md_path.relative_to(self.docs_root)).replace("\\", "/")

        entry = {
            "doc_path": rel_path,
            "content_file": rel_path,
            "source_type": "markdown",
        }

        # Try YAML frontmatter
        title = ""
        summary = ""
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            frontmatter = fm_match.group(1)
            title_match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
            desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip().strip('"\'')
            if desc_match:
                summary = desc_match.group(1).strip().strip('"\'')

        # Fallback: first H1 heading
        if not title:
            h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()

        if not title:
            return None  # Skip files with no discoverable title

        # Extract first paragraph after heading as summary if not from frontmatter
        if not summary:
            para_match = re.search(r'^#\s+.+\n\n(.+?)(?:\n\n|\n#)', content, re.MULTILINE | re.DOTALL)
            if para_match:
                summary = para_match.group(1).strip()[:content_config.SUMMARY_TRUNCATION]

        entry["title"] = title
        entry["summary"] = summary
        entry["products"] = []
        entry["category"] = self._infer_category(rel_path)
        entry["url"] = self._path_to_url(rel_path)
        entry["tags"] = self._build_tags(entry)
        entry["diagrams"] = self.find_diagrams(rel_path)
        entry["topic_type"] = ""

        return entry

    # ─── Helper methods ──────────────────────────────────────────────────

    def _extract_yaml_field(self, content: str, field: str) -> Optional[str]:
        """Extract a top-level YAML field value."""
        # Match field at the start of a line (not indented)
        match = re.search(rf'^{field}:\s*(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip().strip('"\'')
        return None

    def _extract_yaml_nested_field(self, content: str, parent: str, field: str) -> Optional[str]:
        """Extract a nested YAML field value (e.g., metadata.title)."""
        # Find the parent section, then look for the field within indented lines
        parent_match = re.search(rf'^{parent}:\s*$', content, re.MULTILINE)
        if parent_match:
            remaining = content[parent_match.end():]
            # Get all indented lines
            field_match = re.search(rf'^\s+{field}:\s*(.+)$', remaining, re.MULTILINE)
            if field_match:
                return field_match.group(1).strip().strip('"\'')
        return None

    def _extract_yaml_list(self, content: str, field: str) -> List[str]:
        """Extract a YAML list field (e.g., products: list items)."""
        results = []
        match = re.search(rf'^{field}:\s*$', content, re.MULTILINE)
        if match:
            remaining = content[match.end():]
            for line in remaining.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    results.append(line[2:].strip().strip('"\''))
                elif line and not line.startswith('#') and ':' in line:
                    break  # Hit next YAML field
                elif line and not line.startswith('-') and not line.startswith('#'):
                    break
        return results

    def _extract_content_file_ref(self, content: str) -> Optional[str]:
        """Extract the referenced content markdown file from a YAML arch file."""
        # Pattern: [!INCLUDE[](filename.md)] or [!include[](filename.md)]
        match = re.search(r'\[!(?:INCLUDE|include)\[.*?\]\((.*?\.md)\)', content)
        if match:
            return match.group(1)
        return None

    def _path_to_url(self, rel_path: str) -> str:
        """Convert a local doc path to its Azure Architecture Center URL."""
        # Remove .yml or .md extension
        url_path = re.sub(r'\.(yml|md)$', '', rel_path)
        # Remove -content suffix (content files have this)
        url_path = re.sub(r'-content$', '', url_path)
        return f"{AZURE_ARCH_BASE_URL}/{url_path}"

    def _infer_category(self, rel_path: str) -> str:
        """Infer category from file path."""
        parts = rel_path.split("/")
        if len(parts) >= 1:
            category_map = {
                "reference-architectures": "reference-architecture",
                "patterns": "design-pattern",
                "example-scenario": "example-scenario",
                "guide": "architecture-guide",
                "solution-ideas": "solution-idea",
                "best-practices": "best-practice",
                "microservices": "microservices",
                "serverless": "serverless",
                "ai-ml": "ai-ml",
                "networking": "networking",
                "databases": "databases",
                "web-apps": "web-apps",
                "hybrid": "hybrid",
                "high-availability": "high-availability",
                "identity": "identity",
                "integration": "integration",
                "industries": "industries",
            }
            return category_map.get(parts[0], parts[0])
        return "general"

    def _build_tags(self, entry: Dict) -> List[str]:
        """Build searchable tags from entry metadata."""
        tags = set()

        # From title words (skip common words)
        stop_words = {"on", "in", "for", "the", "a", "an", "and", "or", "with", "to", "of", "azure", "learn", "about", "how"}
        if entry.get("title"):
            for word in entry["title"].lower().split():
                word = word.strip(".,;:-()[]")
                if len(word) >= 3 and word not in stop_words:
                    tags.add(word)

        # From products
        for product in entry.get("products", []):
            product_clean = product.replace("azure-", "").replace("-", " ")
            tags.add(product_clean)
            # Also add the full product name
            tags.add(product)

        # From category
        if entry.get("category"):
            for cat in entry["category"].split(", "):
                tags.add(cat.strip())

        # Multi-word phrases from summary
        if entry.get("summary"):
            summary_lower = entry["summary"].lower()
            # Extract key architecture terms
            arch_terms = [
                "microservices", "event-driven", "serverless", "hub-spoke", "hub spoke",
                "n-tier", "web queue worker", "cqrs", "event sourcing", "saga",
                "api gateway", "api management", "kubernetes", "aks", "container",
                "machine learning", "iot", "data warehouse", "data lake",
                "service bus", "event hub", "event grid", "cosmos db",
                "sql database", "app service", "functions", "logic apps",
                "virtual network", "firewall", "vpn", "expressroute",
                "active directory", "key vault", "monitor", "devops",
                "ci/cd", "disaster recovery", "high availability",
                "load balancer", "front door", "traffic manager",
                "redis", "search", "cognitive", "openai", "bot",
                "multi-tenant", "saas", "hybrid", "on-premises",
            ]
            for term in arch_terms:
                if term in summary_lower:
                    tags.add(term)

        return list(tags)

    def _score_entry(self, entry: Dict, query_text: str, query_terms: set) -> float:
        """Score a catalog entry against query text and terms."""
        score = 0.0

        title_lower = (entry.get("title") or "").lower()
        summary_lower = (entry.get("summary") or "").lower()
        tags = entry.get("tags", [])
        products = [p.lower() for p in entry.get("products", [])]

        # Exact phrase matches in title (highest weight)
        if query_text and len(query_text) > 5:
            # Check for multi-word query segments
            segments = [s.strip() for s in re.split(r'[,;.]', query_text) if len(s.strip()) > 4]
            for segment in segments:
                if segment in title_lower:
                    score += 30
                if segment in summary_lower:
                    score += 15

        # Tag matches (high weight for phrase tags)
        for tag in tags:
            if tag in query_text:
                score += 10
            # Individual term matches in tags
            tag_terms = set(tag.split())
            common = tag_terms & query_terms
            if common:
                score += len(common) * 3

        # Product matches
        for product in products:
            product_clean = product.replace("azure-", "").replace("-", " ")
            if product_clean in query_text or product in query_text:
                score += 8
            product_terms = set(product_clean.split())
            common = product_terms & query_terms
            if common:
                score += len(common) * 2

        # Individual term matches in title
        title_terms = set(re.findall(r'\b\w{3,}\b', title_lower))
        title_overlap = title_terms & query_terms
        score += len(title_overlap) * 4

        # Individual term matches in summary
        summary_terms = set(re.findall(r'\b\w{3,}\b', summary_lower))
        summary_overlap = summary_terms & query_terms
        score += len(summary_overlap) * 1

        # Bonus for architecture/reference types
        if entry.get("topic_type") == "reference-architecture":
            score *= 1.3
        elif entry.get("source_type") == "yaml_architecture":
            score *= 1.2

        # Bonus for having diagrams
        if entry.get("diagrams"):
            score *= 1.1

        return score


# Singleton instance
_scanner_instance: Optional[AzureDocsScanner] = None


def get_scanner(docs_root: str = None) -> AzureDocsScanner:
    """Get or create the singleton AzureDocsScanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = AzureDocsScanner(docs_root)
    return _scanner_instance
