import os, json, re
import aiohttp

class LLMClient:
    """
    Supports:
    - OpenAI-compatible (GPT-4, Claude via proxy, Ollama, GitHub Copilot API)
    - Google Gemini API
    """

    def __init__(self):
        self.provider = os.getenv("ORCHESTRATOR_LLM", "openai")  # openai | gemini | ollama | copilot
        self.api_key = os.getenv("ORCHESTRATOR_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.model = os.getenv("ORCHESTRATOR_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("ORCHESTRATOR_BASE_URL", "https://api.openai.com/v1")
        if self.provider == "copilot":
            self.base_url = "https://api.githubcopilot.com"
            self.api_key = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", ""))
            self.model = "gpt-4o"
        elif self.provider == "gemini":
            self.gemini_key = os.getenv("GEMINI_API_KEY", "")
            self.model = os.getenv("ORCHESTRATOR_MODEL", "gemini-1.5-flash")
        elif self.provider == "ollama":
            self.base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:11434/v1")
            self.model = os.getenv("ORCHESTRATOR_MODEL", "llama3")

    async def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the text response."""
        if self.provider == "gemini":
            return await self._gemini(system, user)
        return await self._openai_compat(system, user)

    async def complete_json(self, system: str, user: str) -> dict:
        """Complete and parse JSON response. Retries once on parse failure."""
        for attempt in range(2):
            text = await self.complete(system + "\n\nRespond ONLY with valid JSON. No markdown, no explanation.", user)
            text = re.sub(r"^```(?:json)?\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r'\{.*\}', text, re.DOTALL)
                if m:
                    try:
                        return json.loads(m.group())
                    except Exception:
                        pass
        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")

    async def _openai_compat(self, system: str, user: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _gemini(self, system: str, user: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.gemini_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

llm = LLMClient()
