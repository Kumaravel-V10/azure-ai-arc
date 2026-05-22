"""
Custom exceptions for architecture generation
Replace mocked error responses with proper exceptions
"""

class ArchitectureError(Exception):
    """Base exception for architecture generation errors"""
    pass

class AgentTimeoutError(ArchitectureError):
    """Raised when agent times out"""
    def __init__(self, agent_name: str, attempts: int):
        self.agent_name = agent_name
        self.attempts = attempts
        super().__init__(f"{agent_name} timed out after {attempts} attempts")

class AgentAPIError(ArchitectureError):
    """Raised when OpenAI API fails"""
    def __init__(self, agent_name: str, error: str):
        self.agent_name = agent_name
        self.error = error
        super().__init__(f"{agent_name} API error: {error}")

class JSONParseError(ArchitectureError):
    """Raised when JSON parsing fails"""
    def __init__(self, agent_name: str, response: str):
        self.agent_name = agent_name
        self.response = response[:200]
        super().__init__(f"{agent_name} returned invalid JSON")

# Usage in agents.py:
# REPLACE:
#   return '{"error": "API timeout after retries", "recommendations": []}'
# WITH:
#   raise AgentTimeoutError(self.name, max_retries)
