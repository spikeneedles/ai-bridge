import asyncio
import logging
import os
import time
import aiohttp
from runners.base import AgentRunner, RunResult

logger = logging.getLogger(__name__)


COPILOT_SYSTEM = """You are GitHub Copilot, an expert software engineer. You are working autonomously as part of a multi-agent team.

Execute the given task completely and concisely. Your response will be parsed as a task result and passed to other agents, so:
- Be specific and actionable
- Include file paths and code snippets where relevant
- If you write code, include the complete implementation
- End with a clear summary of what was done

Work on the task directly. Do not ask clarifying questions."""


GEMINI_SYSTEM = """You are Gemini, an expert in research, analysis, and technical review. You are working autonomously as part of a multi-agent team.

Execute the given task completely and concisely. Your response will be used by other agents, so:
- Be specific and structured
- Use headers and bullet points for clarity
- Include concrete recommendations, not vague advice
- End with a clear summary of findings/actions

Work on the task directly. Do not ask clarifying questions."""


class CopilotAPIRunner(AgentRunner):
    """
    Calls GitHub Copilot API directly.
    Uses GITHUB_TOKEN env var. API is OpenAI-compatible.
    """
    name = "copilot"
    mode = "api"
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", ""))
        self.base_url = "https://api.githubcopilot.com"
        self.model = os.getenv("COPILOT_MODEL", "gpt-4o")
    
    @property
    def is_available(self) -> bool:
        return bool(self.token)
    
    async def execute(self, task_title: str, task_description: str, context: dict = None) -> RunResult:
        start = time.time()
        if not self.is_available:
            return RunResult(success=False, output="", error="GITHUB_TOKEN not set", duration=0)
        
        user_content = f"# Task: {task_title}\n\n{task_description}"
        if context:
            user_content += "\n\n## Additional context:\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot/1.155.0",
            "User-Agent": "GitHubCopilotChat/0.12.0",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": COPILOT_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
            "stream": False,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        return RunResult(
                            success=False, output="", 
                            error=f"API error {resp.status}: {body[:200]}",
                            duration=time.time() - start
                        )
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    return RunResult(
                        success=True,
                        output=content,
                        duration=time.time() - start,
                        tokens_used=tokens,
                    )
        except asyncio.TimeoutError:
            return RunResult(success=False, output="", error="Request timed out after 120s", duration=time.time() - start)
        except Exception as e:
            logger.exception(f"CopilotAPIRunner error: {e}")
            return RunResult(success=False, output="", error=str(e), duration=time.time() - start)


class GeminiAPIRunner(AgentRunner):
    """
    Calls Google Gemini API directly.
    Uses GEMINI_API_KEY env var.
    """
    name = "gemini"
    mode = "api"
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def execute(self, task_title: str, task_description: str, context: dict = None) -> RunResult:
        start = time.time()
        if not self.is_available:
            return RunResult(success=False, output="", error="GEMINI_API_KEY not set", duration=0)
        
        user_content = f"# Task: {task_title}\n\n{task_description}"
        if context:
            user_content += "\n\n## Additional context:\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": GEMINI_SYSTEM}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
            },
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        return RunResult(
                            success=False, output="",
                            error=f"Gemini API error {resp.status}: {body[:200]}",
                            duration=time.time() - start,
                        )
                    data = await resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return RunResult(
                        success=True,
                        output=content,
                        duration=time.time() - start,
                    )
        except asyncio.TimeoutError:
            return RunResult(success=False, output="", error="Request timed out after 120s", duration=time.time() - start)
        except Exception as e:
            logger.exception(f"GeminiAPIRunner error: {e}")
            return RunResult(success=False, output="", error=str(e), duration=time.time() - start)
