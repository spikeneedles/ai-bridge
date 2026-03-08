import logging
import os
from runners.base import AgentRunner, RunResult
from runners.api_runner import CopilotAPIRunner, GeminiAPIRunner
from runners.cli_runner import CLIRunner, copilot_cli_runner, gemini_cli_runner

logger = logging.getLogger(__name__)

# Prefer API mode if keys are set, fall back to CLI
USE_API = os.getenv("RUNNER_MODE", "api").lower() == "api"


class RunnerPool:
    """Routes tasks to the right runner. Prefers API mode, falls back to CLI."""
    
    def __init__(self):
        self._copilot_api = CopilotAPIRunner()
        self._gemini_api = GeminiAPIRunner()
        self._copilot_cli = copilot_cli_runner
        self._gemini_cli = gemini_cli_runner
    
    def get_runner(self, agent: str) -> AgentRunner:
        """Return the best available runner for the given agent name."""
        agent = agent.lower()
        
        if agent in ("copilot", "any"):
            if USE_API and self._copilot_api.is_available:
                return self._copilot_api
            if self._copilot_cli.is_available:
                return self._copilot_cli
        
        if agent == "gemini":
            if USE_API and self._gemini_api.is_available:
                return self._gemini_api
            if self._gemini_cli.is_available:
                return self._gemini_cli
        
        # Last resort: try any available runner
        for runner in [self._copilot_api, self._gemini_api, self._copilot_cli, self._gemini_cli]:
            if runner.is_available:
                logger.warning(f"No runner for '{agent}', falling back to {runner.name}/{runner.mode}")
                return runner
        
        raise RuntimeError(f"No runner available for agent '{agent}'")
    
    def status(self) -> dict:
        return {
            "copilot_api": self._copilot_api.is_available,
            "gemini_api": self._gemini_api.is_available,
            "copilot_cli": self._copilot_cli.is_available,
            "gemini_cli": self._gemini_cli.is_available,
            "preferred_mode": "api" if USE_API else "cli",
        }


pool = RunnerPool()
