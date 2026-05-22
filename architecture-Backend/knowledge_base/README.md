# Knowledge Base

Centralized knowledge management system for AI Architecture Agents.

## Overview

The Knowledge Base provides:
- **Pattern Storage**: Store and retrieve architecture patterns, connections, and best practices
- **Reinforcement Learning**: Learn from user feedback to improve recommendations
- **Session Tracking**: Track agent sessions for continuous improvement
- **Service Knowledge Graph**: Learn service-to-service relationships

## Directory Structure

```
knowledge_base/
├── __init__.py              # Package exports
├── knowledge_manager.py     # Core knowledge management
├── reinforcement_learning.py # RL algorithms
├── patterns/                # Stored patterns (JSON files)
│   ├── architecture_patterns.json
│   ├── connection_patterns.json
│   └── service_graph.json
├── feedback/               # User feedback storage
│   └── all_feedback.json
├── embeddings/             # Future: vector embeddings
└── sessions/               # Session data
    └── session_*.json
```

## Usage

### Basic Usage

```python
from knowledge_base import get_knowledge_manager, PatternType, FeedbackType

# Get singleton manager
km = get_knowledge_manager()

# Store a pattern
pattern_id = km.store_pattern(
    pattern_type=PatternType.ARCHITECTURE,
    name="Web App with SQL",
    content={
        "services": ["Azure App Service", "Azure SQL Database", "Azure Key Vault"],
        "connections": [
            {"from": "Azure App Service", "to": "Azure SQL Database"},
            {"from": "Azure App Service", "to": "Azure Key Vault"}
        ]
    },
    tags=["web", "sql", "3-tier"]
)

# Search patterns
results = km.search_patterns(
    pattern_type=PatternType.ARCHITECTURE,
    query="web app",
    min_confidence=0.5
)

# Record feedback
km.record_feedback(
    knowledge_id=pattern_id,
    feedback_type=FeedbackType.POSITIVE,
    value=True
)
```

### Reinforcement Learning

```python
from knowledge_base import get_rl_learner

rl = get_rl_learner()

# Start learning episode
rl.start_episode(requirements="Build e-commerce platform")

# Select pattern using epsilon-greedy
selected = rl.select_pattern(
    available_patterns=["pattern1", "pattern2", "pattern3"],
    pattern_confidences={"pattern1": 0.8, "pattern2": 0.6, "pattern3": 0.7}
)

# Receive reward from user feedback
rl.receive_reward(reward=1.0)

# End episode
rl.end_episode(final_reward=1.0)

# Get statistics
stats = rl.get_statistics()
```

### Session Management

```python
km = get_knowledge_manager()

# Start session
session_id = km.start_session(requirements="E-commerce platform")

# Track services used
km.track_service_used("Azure App Service")
km.track_service_used("Azure SQL Database")

# Track patterns applied
km.track_pattern_applied(pattern_id)

# End session and save
session_data = km.end_session()
```

### Architecture-Specific Functions

```python
# Store complete architecture
pattern_id = km.store_architecture_pattern(
    name="Microservices E-commerce",
    services=["AKS", "Service Bus", "Cosmos DB"],
    connections=[...],
    requirements="Scalable e-commerce",
    tags=["microservices", "e-commerce"]
)

# Find similar architectures
similar = km.find_similar_architectures(
    services=["Azure App Service", "Azure SQL Database"],
    min_similarity=0.3
)

# Get best practices for a service
practices = km.get_best_practices_for_service("Azure Kubernetes Service")
```

## Pattern Types

| Type | Description |
|------|-------------|
| `ARCHITECTURE` | Full architecture patterns |
| `CONNECTION` | Service-to-service connections |
| `SERVICE` | Individual service patterns |
| `SECURITY` | Security patterns |
| `PERFORMANCE` | Performance patterns |
| `LAYOUT` | Diagram layout patterns |
| `PROMPT` | Successful prompts |
| `CUSTOM` | User-defined patterns |

## Feedback Types

| Type | Description | Reward |
|------|-------------|--------|
| `POSITIVE` | User approved | +1.0 |
| `NEGATIVE` | User rejected | -1.0 |
| `RATING` | 1-5 rating | -1.0 to +1.0 |
| `CORRECTION` | User correction | -0.5 |
| `COMMENT` | Text comment | 0.0 |

## Reinforcement Learning Algorithm

The system uses a simplified Q-learning approach:

1. **State**: Hash of requirements/context
2. **Action**: Pattern ID or decision
3. **Reward**: User feedback signal
4. **Policy**: Epsilon-greedy with decay

### Exploration vs Exploitation

- Initial exploration rate: 20%
- Decay rate: 0.995 per step
- Minimum exploration: 5%

## Export/Import

```python
# Export all knowledge
km.export_knowledge("kb_backup.json")

# Import knowledge (merge by default)
km.import_knowledge("kb_backup.json", merge=True)
```

## Statistics

```python
stats = km.get_statistics()
# Returns:
# {
#     "total_patterns": 42,
#     "total_feedback": 156,
#     "services_in_graph": 87,
#     "patterns_by_type": {...},
#     "average_confidence": 0.72,
#     "high_confidence_patterns": 28,
#     ...
# }
```

## Integration with Agents

The AgentOrchestrator automatically integrates with the knowledge base:

1. **Session Tracking**: Each generation starts a new session
2. **Learning**: Services and connections are learned automatically
3. **Feedback**: User feedback is recorded via `record_user_feedback()`
4. **Suggestions**: Knowledge base suggestions are included in responses

```python
from agents import AgentOrchestrator

orchestrator = AgentOrchestrator()

# Generate architecture (auto-learns)
result = await orchestrator.generate_architecture(requirements)

# Record user feedback
orchestrator.record_user_feedback(
    feedback_type="positive",
    feedback_value=True,
    architecture_id=result.get("session_id")
)
```

## Files

- `rl_state.json`: Reinforcement learning state (Q-values, replay buffer)
- `patterns/*.json`: Stored patterns by type
- `feedback/all_feedback.json`: All user feedback
- `sessions/*.json`: Individual session data
