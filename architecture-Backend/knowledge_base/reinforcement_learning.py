"""
Reinforcement Learning Module
=============================
Provides reinforcement learning capabilities for AI Architecture Agents.

Features:
- Reward/punishment signals for pattern learning
- Experience replay buffer
- Q-learning style updates for pattern selection
- Exploration vs exploitation balancing
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single experience for replay buffer"""
    state: str                        # Requirements/context hash
    action: str                       # Pattern ID or decision made
    reward: float                     # Reward signal (-1.0 to 1.0)
    next_state: str                   # Resulting state
    done: bool = False                # Terminal state
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        return cls(**data)


class ReplayBuffer:
    """Experience replay buffer for reinforcement learning"""
    
    def __init__(self, max_size: int = 10000):
        self.buffer: deque = deque(maxlen=max_size)
        self.max_size = max_size
    
    def add(self, experience: Experience):
        """Add experience to buffer"""
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Sample random batch of experiences"""
        batch_size = min(batch_size, len(self.buffer))
        return random.sample(list(self.buffer), batch_size)
    
    def get_recent(self, n: int) -> List[Experience]:
        """Get n most recent experiences"""
        return list(self.buffer)[-n:]
    
    def __len__(self) -> int:
        return len(self.buffer)
    
    def to_list(self) -> List[Dict]:
        return [exp.to_dict() for exp in self.buffer]
    
    def from_list(self, data: List[Dict]):
        for item in data:
            self.buffer.append(Experience.from_dict(item))


class PatternQValues:
    """Q-value tracker for pattern selection (simplified Q-learning)"""
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.q_values: Dict[str, Dict[str, float]] = {}  # state -> {action: q_value}
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
    
    def get_q_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair"""
        if state not in self.q_values:
            return 0.0
        return self.q_values[state].get(action, 0.0)
    
    def update(self, state: str, action: str, reward: float, next_state: str):
        """Update Q-value using Q-learning update rule"""
        if state not in self.q_values:
            self.q_values[state] = {}
        
        current_q = self.get_q_value(state, action)
        
        # Get max Q-value for next state
        max_next_q = 0.0
        if next_state in self.q_values:
            max_next_q = max(self.q_values[next_state].values()) if self.q_values[next_state] else 0.0
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_values[state][action] = new_q
    
    def get_best_action(self, state: str, available_actions: List[str]) -> Optional[str]:
        """Get best action for a state"""
        if state not in self.q_values:
            return random.choice(available_actions) if available_actions else None
        
        best_action = None
        best_value = float('-inf')
        
        for action in available_actions:
            q_value = self.q_values[state].get(action, 0.0)
            if q_value > best_value:
                best_value = q_value
                best_action = action
        
        return best_action if best_action else (random.choice(available_actions) if available_actions else None)
    
    def to_dict(self) -> Dict:
        return self.q_values
    
    def from_dict(self, data: Dict):
        self.q_values = data


class ReinforcementLearner:
    """
    Main reinforcement learning system for architecture generation.
    
    Uses a simplified approach suitable for pattern selection:
    - State: Hash of requirements/context
    - Action: Pattern ID or service selection
    - Reward: User feedback signal
    """
    
    def __init__(self, 
                 exploration_rate: float = 0.2,
                 exploration_decay: float = 0.995,
                 min_exploration: float = 0.05):
        self.replay_buffer = ReplayBuffer()
        self.q_values = PatternQValues()
        
        # Exploration parameters
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.min_exploration = min_exploration
        
        # Track current episode
        self.current_state: Optional[str] = None
        self.current_actions: List[str] = []
        
        # Statistics
        self.total_rewards = 0.0
        self.episode_count = 0
        self.step_count = 0
        
        # Persistence path
        self.save_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "rl_state.json"
        )
        
        # Load saved state
        self._load_state()
    
    def _hash_state(self, state_data: Dict[str, Any]) -> str:
        """Create hash of state for Q-table lookup"""
        import hashlib
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]
    
    def start_episode(self, requirements: str, context: Dict[str, Any] = None) -> str:
        """Start new learning episode"""
        state_data = {
            "requirements": requirements,
            "context": context or {}
        }
        self.current_state = self._hash_state(state_data)
        self.current_actions = []
        self.episode_count += 1
        
        logger.info(f"Started RL episode {self.episode_count}, state: {self.current_state[:8]}...")
        return self.current_state
    
    def select_pattern(self, 
                       available_patterns: List[str],
                       pattern_confidences: Dict[str, float] = None) -> str:
        """Select a pattern using epsilon-greedy exploration"""
        if not available_patterns:
            return ""
        
        self.step_count += 1
        
        # Epsilon-greedy selection
        if random.random() < self.exploration_rate:
            # Explore: random selection (weighted by confidence if available)
            if pattern_confidences:
                weights = [pattern_confidences.get(p, 0.5) for p in available_patterns]
                selected = random.choices(available_patterns, weights=weights, k=1)[0]
            else:
                selected = random.choice(available_patterns)
            logger.debug(f"Exploring: selected {selected}")
        else:
            # Exploit: use Q-values
            selected = self.q_values.get_best_action(self.current_state, available_patterns)
            logger.debug(f"Exploiting: selected {selected}")
        
        self.current_actions.append(selected)
        return selected
    
    def receive_reward(self, reward: float, action: str = None):
        """Receive reward signal for an action"""
        if action is None and self.current_actions:
            action = self.current_actions[-1]
        
        if action and self.current_state:
            # Create next state (simplified - just the current state + action taken)
            next_state = self._hash_state({"prev": self.current_state, "action": action})
            
            # Store experience
            experience = Experience(
                state=self.current_state,
                action=action,
                reward=reward,
                next_state=next_state
            )
            self.replay_buffer.add(experience)
            
            # Update Q-values
            self.q_values.update(self.current_state, action, reward, next_state)
            
            self.total_rewards += reward
            
            # Decay exploration rate
            self.exploration_rate = max(
                self.min_exploration,
                self.exploration_rate * self.exploration_decay
            )
            
            logger.info(f"Received reward {reward} for action {action[:8]}...")
    
    def end_episode(self, final_reward: float = 0.0):
        """End current episode"""
        # Give final reward to all actions in episode
        if self.current_actions and final_reward != 0.0:
            # Distribute reward with recency weighting
            n_actions = len(self.current_actions)
            for i, action in enumerate(self.current_actions):
                # More recent actions get more of the reward
                weight = (i + 1) / n_actions
                weighted_reward = final_reward * weight
                self.receive_reward(weighted_reward, action)
        
        self.current_state = None
        self.current_actions = []
        
        # Save state periodically
        if self.episode_count % 10 == 0:
            self._save_state()
        
        logger.info(f"Ended episode {self.episode_count}, total rewards: {self.total_rewards:.2f}")
    
    def learn_from_feedback(self, 
                            pattern_id: str,
                            feedback_type: str,
                            feedback_value: Any):
        """Learn from user feedback"""
        # Convert feedback to reward signal
        if feedback_type == "positive":
            reward = 1.0
        elif feedback_type == "negative":
            reward = -1.0
        elif feedback_type == "rating":
            # Convert 1-5 rating to -1 to 1
            rating = int(feedback_value) if isinstance(feedback_value, (int, float)) else 3
            reward = (rating - 3) / 2  # Maps 1->-1, 3->0, 5->1
        elif feedback_type == "correction":
            reward = -0.5  # Correction implies something was wrong
        else:
            reward = 0.0
        
        self.receive_reward(reward, pattern_id)
    
    def get_pattern_rankings(self, 
                             available_patterns: List[str],
                             state: str = None) -> List[Tuple[str, float]]:
        """Get patterns ranked by expected value"""
        if state is None:
            state = self.current_state or ""
        
        rankings = []
        for pattern in available_patterns:
            q_value = self.q_values.get_q_value(state, pattern)
            rankings.append((pattern, q_value))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def _save_state(self):
        """Save RL state to disk"""
        state_data = {
            "q_values": self.q_values.to_dict(),
            "replay_buffer": self.replay_buffer.to_list(),
            "exploration_rate": self.exploration_rate,
            "total_rewards": self.total_rewards,
            "episode_count": self.episode_count,
            "step_count": self.step_count,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
        
        logger.info(f"Saved RL state to {self.save_path}")
    
    def _load_state(self):
        """Load RL state from disk"""
        if not os.path.exists(self.save_path):
            return
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            self.q_values.from_dict(state_data.get("q_values", {}))
            self.replay_buffer.from_list(state_data.get("replay_buffer", []))
            self.exploration_rate = state_data.get("exploration_rate", self.exploration_rate)
            self.total_rewards = state_data.get("total_rewards", 0.0)
            self.episode_count = state_data.get("episode_count", 0)
            self.step_count = state_data.get("step_count", 0)
            
            logger.info(f"Loaded RL state: {self.episode_count} episodes, {self.step_count} steps")
        except Exception as e:
            logger.warning(f"Failed to load RL state: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get RL statistics"""
        return {
            "episode_count": self.episode_count,
            "step_count": self.step_count,
            "total_rewards": round(self.total_rewards, 2),
            "exploration_rate": round(self.exploration_rate, 4),
            "replay_buffer_size": len(self.replay_buffer),
            "q_table_states": len(self.q_values.q_values),
            "average_reward": round(self.total_rewards / max(1, self.episode_count), 3)
        }


# Singleton instance
_rl_learner: Optional[ReinforcementLearner] = None


def get_rl_learner() -> ReinforcementLearner:
    """Get singleton ReinforcementLearner instance"""
    global _rl_learner
    if _rl_learner is None:
        _rl_learner = ReinforcementLearner()
    return _rl_learner
