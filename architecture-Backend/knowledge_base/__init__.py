"""
Knowledge Base Module
=====================
Centralized knowledge management for AI Architecture Agents.

Provides:
- Pattern storage and retrieval
- Reinforcement learning from user feedback
- Session-based learning persistence
- Semantic search capabilities
- Architecture knowledge graph
"""

from .knowledge_manager import (
    KnowledgeManager,
    get_knowledge_manager,
    PatternType,
    FeedbackType,
    KnowledgeEntry,
    FeedbackEntry,
    learn_from_architecture,
    get_suggestions_for_services
)

from .reinforcement_learning import (
    ReinforcementLearner,
    get_rl_learner,
    Experience,
    ReplayBuffer
)

__all__ = [
    # Knowledge Manager
    'KnowledgeManager',
    'get_knowledge_manager',
    'PatternType',
    'FeedbackType',
    'KnowledgeEntry',
    'FeedbackEntry',
    'learn_from_architecture',
    'get_suggestions_for_services',
    # Reinforcement Learning
    'ReinforcementLearner',
    'get_rl_learner',
    'Experience',
    'ReplayBuffer'
]
