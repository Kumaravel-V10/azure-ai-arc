import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
from shared_services import get_openai_client
from agents.base import (
    KNOWLEDGE_BASE_AVAILABLE,
    get_knowledge_manager, get_rl_learner,
)
from agents.security import SecurityAgent
from agents.performance import PerformanceAgent
from agents.cost import CostOptimizationAgent
from agents.architecture import ArchitectureAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates multiple agents for comprehensive analysis"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.agents = [
            SecurityAgent(self.openai_client),
            PerformanceAgent(self.openai_client),
            CostOptimizationAgent(self.openai_client),
            ArchitectureAgent(self.openai_client)
        ]
        
        # Initialize knowledge base if available
        self.knowledge_manager = get_knowledge_manager() if KNOWLEDGE_BASE_AVAILABLE else None
        self.rl_learner = get_rl_learner() if KNOWLEDGE_BASE_AVAILABLE else None
    
    async def generate_architecture(self, requirements: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive architecture analysis using all agents"""
        try:
            logger.info(f"Starting agent orchestration for requirements: {requirements[:100]}...")
            
            # Start knowledge base session for this generation
            session_id = None
            if self.knowledge_manager:
                session_id = self.knowledge_manager.start_session(requirements)
            
            # Start RL episode
            if self.rl_learner:
                self.rl_learner.start_episode(requirements, context)
            
            # Get suggestions from knowledge base
            kb_suggestions = {}
            if self.knowledge_manager and KNOWLEDGE_BASE_AVAILABLE:
                kb_suggestions = self._get_knowledge_base_context(requirements)
            
            # Run all agents concurrently
            agent_tasks = [
                agent.analyze(requirements, context) 
                for agent in self.agents
            ]
            
            # Wait for all agents to complete with timeout
            agent_results = await asyncio.wait_for(
                asyncio.gather(*agent_tasks, return_exceptions=True),
                timeout=60.0  # 60 second timeout
            )
            
            # Process results
            successful_results = []
            failed_agents = []
            
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    logger.error(f"Agent {self.agents[i].name} failed: {str(result)}")
                    failed_agents.append(self.agents[i].name)
                else:
                    successful_results.append(result)
            
            # Combine results from successful agents
            combined_architecture = self._combine_agent_results(successful_results)
            
            # Learn from this generation
            if self.knowledge_manager:
                self._learn_from_generation(combined_architecture, requirements)

            return combined_architecture

        except asyncio.TimeoutError:
            logger.error("Agent orchestration timed out")
            return {"error": "Agent orchestration timed out", "components": [], "connections": []}
        except Exception as e:
            logger.error(f"Agent orchestration failed: {str(e)}")
            return {"error": str(e), "components": [], "connections": []}

    def _combine_agent_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from multiple agents into a single architecture."""
        combined = {"components": [], "connections": [], "recommendations": []}
        for result in results:
            if isinstance(result, dict):
                combined["components"].extend(result.get("components", []))
                combined["connections"].extend(result.get("connections", []))
                combined["recommendations"].extend(result.get("recommendations", []))
        return combined

    def _get_knowledge_base_context(self, requirements: str) -> Dict[str, Any]:
        """Get suggestions from the knowledge base for the given requirements."""
        try:
            return self.knowledge_manager.get_suggestions(requirements) if self.knowledge_manager else {}
        except Exception as e:
            logger.warning(f"Knowledge base lookup failed: {e}")
            return {}

    def _learn_from_generation(self, architecture: Dict[str, Any], requirements: str):
        """Record generation results for future learning."""
        try:
            if self.knowledge_manager:
                self.knowledge_manager.record_generation(requirements, architecture)
        except Exception as e:
            logger.warning(f"Learning from generation failed: {e}")
