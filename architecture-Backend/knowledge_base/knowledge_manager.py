"""
Knowledge Manager
==================
Core knowledge management system for AI Architecture Agents.

Features:
- Store and retrieve architecture patterns
- Reinforcement learning from user feedback
- Session-based learning with persistence
- Pattern similarity matching
- Knowledge graph for service relationships
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be stored"""
    ARCHITECTURE = "architecture"      # Full architecture patterns
    CONNECTION = "connection"          # Service-to-service connections
    SERVICE = "service"               # Individual service patterns
    SECURITY = "security"             # Security patterns
    PERFORMANCE = "performance"       # Performance patterns
    LAYOUT = "layout"                 # Diagram layout patterns
    PROMPT = "prompt"                 # Successful prompts
    CUSTOM = "custom"                 # User-defined patterns


class FeedbackType(Enum):
    """Types of user feedback for reinforcement learning"""
    POSITIVE = "positive"             # User approved the output
    NEGATIVE = "negative"             # User rejected the output
    CORRECTION = "correction"         # User provided correction
    RATING = "rating"                 # Numeric rating (1-5)
    COMMENT = "comment"               # Text comment


@dataclass
class KnowledgeEntry:
    """A single knowledge entry"""
    id: str
    type: str                         # PatternType value
    name: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5           # 0.0 to 1.0
    usage_count: int = 0
    success_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    source: str = ""                  # Where this knowledge came from
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
            
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeEntry':
        return cls(**data)


@dataclass
class FeedbackEntry:
    """User feedback for reinforcement learning"""
    id: str
    knowledge_id: str                 # ID of the knowledge entry
    feedback_type: str                # FeedbackType value
    value: Any                        # Rating value, correction text, etc.
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
            
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        return cls(**data)


@dataclass
class SessionContext:
    """Session context for tracking agent interactions"""
    session_id: str
    started_at: str
    requirements: str = ""
    services_used: List[str] = field(default_factory=list)
    patterns_applied: List[str] = field(default_factory=list)
    feedback_received: List[str] = field(default_factory=list)
    outputs_generated: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeManager:
    """
    Centralized knowledge management for AI Architecture Agents.
    
    Handles:
    - Pattern storage and retrieval
    - Reinforcement learning from feedback
    - Session-based learning
    - Knowledge persistence
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__))
        )
        
        # In-memory caches
        self._patterns: Dict[str, KnowledgeEntry] = {}
        self._feedback: List[FeedbackEntry] = []
        self._service_graph: Dict[str, Set[str]] = defaultdict(set)
        self._confidence_scores: Dict[str, float] = {}
        self._current_session: Optional[SessionContext] = None
        
        # Load existing knowledge
        self._load_knowledge()
        
        logger.info(f"KnowledgeManager initialized with {len(self._patterns)} patterns")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def _load_knowledge(self):
        """Load all knowledge from disk"""
        # Load patterns
        patterns_dir = os.path.join(self.base_path, "patterns")
        if os.path.exists(patterns_dir):
            for filename in os.listdir(patterns_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(patterns_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    entry = KnowledgeEntry.from_dict(item)
                                    self._patterns[entry.id] = entry
                            else:
                                entry = KnowledgeEntry.from_dict(data)
                                self._patterns[entry.id] = entry
                    except Exception as e:
                        logger.warning(f"Failed to load pattern from {filename}: {e}")
        
        # Load feedback
        feedback_file = os.path.join(self.base_path, "feedback", "all_feedback.json")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._feedback = [FeedbackEntry.from_dict(fb) for fb in data]
            except Exception as e:
                logger.warning(f"Failed to load feedback: {e}")
        
        # Load service graph
        graph_file = os.path.join(self.base_path, "patterns", "service_graph.json")
        if os.path.exists(graph_file):
            try:
                with open(graph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._service_graph = defaultdict(set)
                    for service, connections in data.items():
                        self._service_graph[service] = set(connections)
            except Exception as e:
                logger.warning(f"Failed to load service graph: {e}")
        
        # Recalculate confidence scores based on feedback
        self._recalculate_confidence_scores()
    
    def _save_patterns(self):
        """Save patterns to disk"""
        patterns_dir = os.path.join(self.base_path, "patterns")
        os.makedirs(patterns_dir, exist_ok=True)
        
        # Group patterns by type
        patterns_by_type: Dict[str, List[Dict]] = defaultdict(list)
        for pattern in self._patterns.values():
            patterns_by_type[pattern.type].append(pattern.to_dict())
        
        # Save each type to a separate file
        for pattern_type, patterns in patterns_by_type.items():
            filepath = os.path.join(patterns_dir, f"{pattern_type}_patterns.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2, ensure_ascii=False)
    
    def _save_feedback(self):
        """Save feedback to disk"""
        feedback_dir = os.path.join(self.base_path, "feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        
        filepath = os.path.join(feedback_dir, "all_feedback.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([fb.to_dict() for fb in self._feedback], f, indent=2)
    
    def _save_service_graph(self):
        """Save service graph to disk"""
        patterns_dir = os.path.join(self.base_path, "patterns")
        os.makedirs(patterns_dir, exist_ok=True)
        
        filepath = os.path.join(patterns_dir, "service_graph.json")
        graph_data = {k: list(v) for k, v in self._service_graph.items()}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # PATTERN MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID from content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def store_pattern(self, 
                      pattern_type: PatternType,
                      name: str,
                      content: Dict[str, Any],
                      tags: List[str] = None,
                      source: str = "",
                      metadata: Dict[str, Any] = None) -> str:
        """Store a new pattern in the knowledge base"""
        
        pattern_id = self._generate_id(f"{pattern_type.value}_{name}_{json.dumps(content)}")
        
        # Check if pattern already exists
        if pattern_id in self._patterns:
            # Update usage count
            self._patterns[pattern_id].usage_count += 1
            self._patterns[pattern_id].updated_at = datetime.now().isoformat()
            self._save_patterns()
            return pattern_id
        
        entry = KnowledgeEntry(
            id=pattern_id,
            type=pattern_type.value,
            name=name,
            content=content,
            tags=tags or [],
            source=source,
            metadata=metadata or {},
            confidence=0.5  # Start with neutral confidence
        )
        
        self._patterns[pattern_id] = entry
        self._save_patterns()
        
        logger.info(f"Stored new pattern: {name} (type: {pattern_type.value})")
        return pattern_id
    
    def get_pattern(self, pattern_id: str) -> Optional[KnowledgeEntry]:
        """Retrieve a pattern by ID"""
        return self._patterns.get(pattern_id)
    
    def search_patterns(self,
                        pattern_type: PatternType = None,
                        tags: List[str] = None,
                        query: str = None,
                        min_confidence: float = 0.0,
                        limit: int = 10) -> List[KnowledgeEntry]:
        """Search patterns by type, tags, or query"""
        
        results = []
        
        for pattern in self._patterns.values():
            # Filter by type
            if pattern_type and pattern.type != pattern_type.value:
                continue
            
            # Filter by confidence
            if pattern.confidence < min_confidence:
                continue
            
            # Filter by tags
            if tags and not any(tag in pattern.tags for tag in tags):
                continue
            
            # Filter by query (simple text matching)
            if query:
                query_lower = query.lower()
                name_match = query_lower in pattern.name.lower()
                content_match = query_lower in json.dumps(pattern.content).lower()
                tag_match = any(query_lower in tag.lower() for tag in pattern.tags)
                
                if not (name_match or content_match or tag_match):
                    continue
            
            results.append(pattern)
        
        # Sort by confidence * usage_count (relevance score)
        results.sort(key=lambda p: p.confidence * (1 + p.usage_count * 0.1), reverse=True)
        
        return results[:limit]
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[KnowledgeEntry]:
        """Get all patterns of a specific type"""
        return [p for p in self._patterns.values() if p.type == pattern_type.value]
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a pattern"""
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            self._save_patterns()
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # REINFORCEMENT LEARNING
    # ═══════════════════════════════════════════════════════════════════════
    
    def record_feedback(self,
                        knowledge_id: str,
                        feedback_type: FeedbackType,
                        value: Any,
                        context: Dict[str, Any] = None) -> str:
        """Record user feedback for reinforcement learning"""
        
        feedback_id = self._generate_id(f"{knowledge_id}_{feedback_type.value}_{time.time()}")
        
        entry = FeedbackEntry(
            id=feedback_id,
            knowledge_id=knowledge_id,
            feedback_type=feedback_type.value,
            value=value,
            context=context or {},
            session_id=self._current_session.session_id if self._current_session else ""
        )
        
        self._feedback.append(entry)
        self._save_feedback()
        
        # Update pattern confidence based on feedback
        self._update_confidence_from_feedback(knowledge_id, feedback_type, value)
        
        # Track in current session
        if self._current_session:
            self._current_session.feedback_received.append(feedback_id)
        
        logger.info(f"Recorded {feedback_type.value} feedback for {knowledge_id}")
        return feedback_id
    
    def record_success(self, knowledge_id: str):
        """Record successful use of a pattern (implicit positive feedback)"""
        if knowledge_id in self._patterns:
            self._patterns[knowledge_id].success_count += 1
            self._patterns[knowledge_id].usage_count += 1
            self._update_confidence_from_usage(knowledge_id)
            self._save_patterns()
    
    def record_failure(self, knowledge_id: str, reason: str = ""):
        """Record failed use of a pattern (implicit negative feedback)"""
        if knowledge_id in self._patterns:
            self._patterns[knowledge_id].usage_count += 1
            self._update_confidence_from_usage(knowledge_id)
            self._save_patterns()
            
            # Optionally record as explicit negative feedback
            if reason:
                self.record_feedback(
                    knowledge_id,
                    FeedbackType.NEGATIVE,
                    {"reason": reason}
                )
    
    def _update_confidence_from_feedback(self, 
                                          knowledge_id: str,
                                          feedback_type: FeedbackType,
                                          value: Any):
        """Update pattern confidence based on feedback"""
        if knowledge_id not in self._patterns:
            return
        
        pattern = self._patterns[knowledge_id]
        
        if feedback_type == FeedbackType.POSITIVE:
            # Increase confidence (up to 1.0)
            pattern.confidence = min(1.0, pattern.confidence + 0.05)
            pattern.success_count += 1
            
        elif feedback_type == FeedbackType.NEGATIVE:
            # Decrease confidence (down to 0.0)
            pattern.confidence = max(0.0, pattern.confidence - 0.1)
            
        elif feedback_type == FeedbackType.RATING:
            # Adjust based on rating (1-5 scale)
            rating = int(value) if isinstance(value, (int, float)) else 3
            adjustment = (rating - 3) * 0.05  # -0.1 to +0.1
            pattern.confidence = max(0.0, min(1.0, pattern.confidence + adjustment))
            
        elif feedback_type == FeedbackType.CORRECTION:
            # Store correction and slightly decrease confidence
            pattern.confidence = max(0.0, pattern.confidence - 0.03)
            # Store correction in metadata for learning
            if 'corrections' not in pattern.metadata:
                pattern.metadata['corrections'] = []
            pattern.metadata['corrections'].append({
                'timestamp': datetime.now().isoformat(),
                'correction': value
            })
        
        pattern.updated_at = datetime.now().isoformat()
        self._save_patterns()
    
    def _update_confidence_from_usage(self, knowledge_id: str):
        """Update confidence based on success/usage ratio"""
        if knowledge_id not in self._patterns:
            return
        
        pattern = self._patterns[knowledge_id]
        
        if pattern.usage_count > 0:
            success_rate = pattern.success_count / pattern.usage_count
            # Blend current confidence with success rate
            pattern.confidence = (pattern.confidence * 0.7) + (success_rate * 0.3)
            pattern.confidence = max(0.0, min(1.0, pattern.confidence))
    
    def _recalculate_confidence_scores(self):
        """Recalculate all confidence scores based on feedback history"""
        # Group feedback by knowledge_id
        feedback_by_pattern: Dict[str, List[FeedbackEntry]] = defaultdict(list)
        for fb in self._feedback:
            feedback_by_pattern[fb.knowledge_id].append(fb)
        
        # Update each pattern's confidence
        for pattern_id, feedback_list in feedback_by_pattern.items():
            if pattern_id not in self._patterns:
                continue
            
            positive = sum(1 for fb in feedback_list if fb.feedback_type == FeedbackType.POSITIVE.value)
            negative = sum(1 for fb in feedback_list if fb.feedback_type == FeedbackType.NEGATIVE.value)
            ratings = [fb.value for fb in feedback_list if fb.feedback_type == FeedbackType.RATING.value]
            
            total_signals = positive + negative + len(ratings)
            if total_signals > 0:
                # Calculate weighted score
                positive_weight = positive / total_signals
                negative_weight = negative / total_signals
                avg_rating = (sum(ratings) / len(ratings) / 5) if ratings else 0.5
                
                confidence = (positive_weight * 0.4) + ((1 - negative_weight) * 0.4) + (avg_rating * 0.2)
                self._patterns[pattern_id].confidence = max(0.1, min(0.95, confidence))
    
    def get_high_confidence_patterns(self, 
                                      pattern_type: PatternType = None,
                                      min_confidence: float = 0.7,
                                      limit: int = 10) -> List[KnowledgeEntry]:
        """Get patterns with highest confidence scores"""
        patterns = self.search_patterns(
            pattern_type=pattern_type,
            min_confidence=min_confidence,
            limit=limit
        )
        return sorted(patterns, key=lambda p: p.confidence, reverse=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # SERVICE KNOWLEDGE GRAPH
    # ═══════════════════════════════════════════════════════════════════════
    
    def learn_service_connection(self, source: str, target: str):
        """Learn a service-to-service connection"""
        self._service_graph[source].add(target)
        self._save_service_graph()
    
    def learn_connections_from_architecture(self, connections: List[Dict]):
        """Learn multiple connections from an architecture"""
        for conn in connections:
            source = conn.get("from") or conn.get("source", "")
            target = conn.get("to") or conn.get("target", "")
            if source and target:
                self.learn_service_connection(source, target)
    
    def get_related_services(self, service: str) -> List[str]:
        """Get services that connect to/from the given service"""
        related = set(self._service_graph.get(service, set()))
        
        # Also find reverse connections
        for source, targets in self._service_graph.items():
            if service in targets:
                related.add(source)
        
        return list(related)
    
    def get_downstream_services(self, service: str) -> List[str]:
        """Get services that this service connects to"""
        return list(self._service_graph.get(service, set()))
    
    def suggest_connections_for_services(self, services: List[str]) -> List[Tuple[str, str, float]]:
        """Suggest connections between given services based on learned patterns"""
        suggestions = []
        service_set = set(services)
        
        for source in services:
            downstream = self._service_graph.get(source, set())
            for target in downstream:
                if target in service_set and source != target:
                    # Calculate confidence based on frequency
                    suggestions.append((source, target, 0.8))
        
        return suggestions
    
    # ═══════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def start_session(self, requirements: str = "") -> str:
        """Start a new learning session"""
        session_id = self._generate_id(f"session_{time.time()}")
        
        self._current_session = SessionContext(
            session_id=session_id,
            started_at=datetime.now().isoformat(),
            requirements=requirements
        )
        
        logger.info(f"Started session: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[Dict[str, Any]]:
        """End current session and save session data"""
        if not self._current_session:
            return None
        
        # Save session data
        sessions_dir = os.path.join(self.base_path, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        
        session_data = self._current_session.to_dict()
        session_data['ended_at'] = datetime.now().isoformat()
        
        filepath = os.path.join(sessions_dir, f"{self._current_session.session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"Ended session: {self._current_session.session_id}")
        
        result = session_data
        self._current_session = None
        return result
    
    def track_service_used(self, service: str):
        """Track a service being used in current session"""
        if self._current_session and service not in self._current_session.services_used:
            self._current_session.services_used.append(service)
    
    def track_pattern_applied(self, pattern_id: str):
        """Track a pattern being applied in current session"""
        if self._current_session:
            self._current_session.patterns_applied.append(pattern_id)
            # Also record usage
            if pattern_id in self._patterns:
                self._patterns[pattern_id].usage_count += 1
    
    def track_output_generated(self, output: Dict[str, Any]):
        """Track an output generated in current session"""
        if self._current_session:
            self._current_session.outputs_generated.append({
                'timestamp': datetime.now().isoformat(),
                'output_summary': str(output)[:500]  # Truncate for storage
            })
    
    # ═══════════════════════════════════════════════════════════════════════
    # ARCHITECTURE-SPECIFIC KNOWLEDGE
    # ═══════════════════════════════════════════════════════════════════════
    
    def store_architecture_pattern(self,
                                   name: str,
                                   services: List[str],
                                   connections: List[Dict],
                                   requirements: str = "",
                                   tags: List[str] = None) -> str:
        """Store a complete architecture pattern"""
        content = {
            "services": services,
            "connections": connections,
            "requirements": requirements
        }
        
        pattern_id = self.store_pattern(
            pattern_type=PatternType.ARCHITECTURE,
            name=name,
            content=content,
            tags=tags or [],
            source="user_generated"
        )
        
        # Also learn the connections
        self.learn_connections_from_architecture(connections)
        
        return pattern_id
    
    def find_similar_architectures(self, 
                                   services: List[str],
                                   min_similarity: float = 0.3,
                                   limit: int = 5) -> List[Tuple[KnowledgeEntry, float]]:
        """Find architecture patterns similar to given services"""
        architecture_patterns = self.get_patterns_by_type(PatternType.ARCHITECTURE)
        
        results = []
        service_set = set(services)
        
        for pattern in architecture_patterns:
            pattern_services = set(pattern.content.get("services", []))
            
            # Calculate Jaccard similarity
            intersection = len(service_set & pattern_services)
            union = len(service_set | pattern_services)
            
            if union > 0:
                similarity = intersection / union
                if similarity >= min_similarity:
                    results.append((pattern, similarity))
        
        # Sort by similarity * confidence
        results.sort(key=lambda x: x[1] * x[0].confidence, reverse=True)
        
        return results[:limit]
    
    def get_best_practices_for_service(self, service: str) -> List[Dict]:
        """Get learned best practices for a specific service"""
        best_practices = []
        
        # Search patterns involving this service
        patterns = self.search_patterns(
            query=service,
            min_confidence=0.6
        )
        
        for pattern in patterns:
            if service in str(pattern.content):
                best_practices.append({
                    "pattern_name": pattern.name,
                    "pattern_type": pattern.type,
                    "confidence": pattern.confidence,
                    "usage_count": pattern.usage_count,
                    "content": pattern.content
                })
        
        return best_practices
    
    # ═══════════════════════════════════════════════════════════════════════
    # KNOWLEDGE EXPORT/IMPORT
    # ═══════════════════════════════════════════════════════════════════════
    
    def export_knowledge(self, filepath: str):
        """Export all knowledge to a single JSON file"""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "patterns": [p.to_dict() for p in self._patterns.values()],
            "feedback": [fb.to_dict() for fb in self._feedback],
            "service_graph": {k: list(v) for k, v in self._service_graph.items()},
            "statistics": {
                "total_patterns": len(self._patterns),
                "total_feedback": len(self._feedback),
                "services_in_graph": len(self._service_graph),
                "patterns_by_type": {
                    pt.value: len([p for p in self._patterns.values() if p.type == pt.value])
                    for pt in PatternType
                }
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported knowledge to {filepath}")
    
    def import_knowledge(self, filepath: str, merge: bool = True):
        """Import knowledge from a JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Import patterns
        for pattern_data in import_data.get("patterns", []):
            pattern = KnowledgeEntry.from_dict(pattern_data)
            if merge and pattern.id in self._patterns:
                # Merge: keep higher confidence
                if pattern.confidence > self._patterns[pattern.id].confidence:
                    self._patterns[pattern.id] = pattern
            else:
                self._patterns[pattern.id] = pattern
        
        # Import feedback
        existing_ids = {fb.id for fb in self._feedback}
        for fb_data in import_data.get("feedback", []):
            fb = FeedbackEntry.from_dict(fb_data)
            if fb.id not in existing_ids:
                self._feedback.append(fb)
        
        # Import service graph
        for service, connections in import_data.get("service_graph", {}).items():
            self._service_graph[service].update(connections)
        
        # Save all
        self._save_patterns()
        self._save_feedback()
        self._save_service_graph()
        
        logger.info(f"Imported knowledge from {filepath}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return {
            "total_patterns": len(self._patterns),
            "total_feedback": len(self._feedback),
            "services_in_graph": len(self._service_graph),
            "total_connections": sum(len(v) for v in self._service_graph.values()),
            "patterns_by_type": {
                pt.value: len([p for p in self._patterns.values() if p.type == pt.value])
                for pt in PatternType
            },
            "average_confidence": (
                sum(p.confidence for p in self._patterns.values()) / len(self._patterns)
                if self._patterns else 0
            ),
            "high_confidence_patterns": len([p for p in self._patterns.values() if p.confidence >= 0.7]),
            "low_confidence_patterns": len([p for p in self._patterns.values() if p.confidence < 0.3]),
            "feedback_by_type": {
                ft.value: len([fb for fb in self._feedback if fb.feedback_type == ft.value])
                for ft in FeedbackType
            },
            "active_session": self._current_session.session_id if self._current_session else None
        }


# Singleton accessor
_knowledge_manager: Optional[KnowledgeManager] = None


def get_knowledge_manager() -> KnowledgeManager:
    """Get the singleton KnowledgeManager instance"""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_architecture(architecture: Dict[str, Any], 
                            feedback: str = "positive",
                            requirements: str = "") -> str:
    """Convenience function to learn from an architecture output"""
    km = get_knowledge_manager()
    
    services = architecture.get("services", [])
    service_names = [s.get("name", "") for s in services if isinstance(s, dict)]
    connections = architecture.get("connections", [])
    
    # Store as architecture pattern
    pattern_id = km.store_architecture_pattern(
        name=f"architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        services=service_names,
        connections=connections,
        requirements=requirements,
        tags=["auto_learned"]
    )
    
    # Record feedback
    if feedback == "positive":
        km.record_feedback(pattern_id, FeedbackType.POSITIVE, True)
    elif feedback == "negative":
        km.record_feedback(pattern_id, FeedbackType.NEGATIVE, True)
    
    return pattern_id


def get_suggestions_for_services(services: List[str]) -> Dict[str, Any]:
    """Get knowledge-based suggestions for a list of services"""
    km = get_knowledge_manager()
    
    return {
        "similar_architectures": [
            {"name": arch[0].name, "similarity": arch[1], "confidence": arch[0].confidence}
            for arch in km.find_similar_architectures(services)
        ],
        "suggested_connections": km.suggest_connections_for_services(services),
        "related_services": {
            service: km.get_related_services(service)[:5]
            for service in services[:10]
        }
    }
