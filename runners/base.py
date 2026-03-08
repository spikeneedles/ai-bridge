from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class RunResult:
    success: bool
    output: str
    error: Optional[str] = None
    duration: float = 0.0
    tokens_used: int = 0

class AgentRunner(ABC):
    """Abstract base for an agent that can execute a task."""
    
    name: str = "base"
    mode: str = "base"   # "api" | "cli"
    
    @abstractmethod
    async def execute(self, task_title: str, task_description: str, context: dict = None) -> RunResult:
        """Execute the task and return the result."""
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this runner is ready to accept tasks."""
    
    async def health_check(self) -> bool:
        """Verify the runner can reach its backend."""
        return self.is_available
