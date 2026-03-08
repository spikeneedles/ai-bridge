import asyncio
import logging
import os
import sys
import time
from runners.base import AgentRunner, RunResult

logger = logging.getLogger(__name__)

# Sentinel we inject after the task to know when output is done
OUTPUT_SENTINEL = "---TASK_COMPLETE_SENTINEL_12345---"


class CLIRunner(AgentRunner):
    """
    Drives an AI CLI (copilot/gemini) as a subprocess.
    Sends task via stdin, reads response until sentinel or timeout.
    """
    mode = "cli"
    
    def __init__(self, cli_command: list[str], agent_name: str, timeout: int = 180):
        self.cli_command = cli_command   # e.g. ["copilot"] or ["gemini"]
        self.name = agent_name
        self.timeout = timeout
        self._proc = None
        self._lock = asyncio.Lock()
    
    @property
    def is_available(self) -> bool:
        import shutil
        return shutil.which(self.cli_command[0]) is not None
    
    async def _ensure_process(self):
        """Start the CLI process if not running."""
        if self._proc is None or self._proc.returncode is not None:
            logger.info(f"Starting {self.name} CLI: {' '.join(self.cli_command)}")
            self._proc = await asyncio.create_subprocess_exec(
                *self.cli_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Give CLI time to initialize
            await asyncio.sleep(3)
    
    async def execute(self, task_title: str, task_description: str, context: dict = None) -> RunResult:
        start = time.time()
        async with self._lock:
            try:
                await self._ensure_process()
                
                prompt = f"{task_description}\n\nWhen done, output exactly this line by itself: {OUTPUT_SENTINEL}\n"
                if context:
                    prompt = "## Context from previous steps:\n" + "\n".join(f"{k}: {v}" for k, v in context.items()) + "\n\n" + prompt
                
                # Send task
                self._proc.stdin.write(prompt.encode() + b"\n")
                await self._proc.stdin.drain()
                
                # Read until sentinel or timeout
                output_lines = []
                try:
                    async with asyncio.timeout(self.timeout):
                        while True:
                            line = await self._proc.stdout.readline()
                            if not line:
                                break
                            decoded = line.decode("utf-8", errors="replace").rstrip()
                            if OUTPUT_SENTINEL in decoded:
                                break
                            output_lines.append(decoded)
                except asyncio.TimeoutError:
                    return RunResult(
                        success=False, output="\n".join(output_lines),
                        error=f"CLI timed out after {self.timeout}s",
                        duration=time.time() - start,
                    )
                
                output = "\n".join(output_lines).strip()
                # Remove CLI chrome (prompts, banners)
                output = _clean_cli_output(output)
                
                return RunResult(
                    success=True,
                    output=output,
                    duration=time.time() - start,
                )
            
            except Exception as e:
                logger.exception(f"CLIRunner {self.name} error: {e}")
                self._proc = None  # Reset so next call restarts
                return RunResult(success=False, output="", error=str(e), duration=time.time() - start)
    
    async def close(self):
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            await self._proc.wait()


def _clean_cli_output(text: str) -> str:
    """Remove CLI banners, prompts, ANSI codes from output."""
    import re
    # Remove ANSI escape codes
    text = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)
    # Remove common CLI prompts
    lines = [l for l in text.split('\n') if not any(
        l.strip().startswith(p) for p in ['>', '?', '❯', '>>']
    )]
    return '\n'.join(lines).strip()


# Singletons for CLI mode
copilot_cli_runner = CLIRunner(["copilot"], "copilot")
gemini_cli_runner = CLIRunner(["gemini"], "gemini")
