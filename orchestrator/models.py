from dataclasses import dataclass, field
from typing import Optional
import time, uuid

@dataclass
class Step:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    assigned_to: str = ""           # "copilot" | "gemini" | "any"
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"         # pending | running | done | failed | skipped
    result: Optional[str] = None
    context: dict = field(default_factory=dict)
    bridge_task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    retries: int = 0
    max_retries: int = 2
    tags: list[str] = field(default_factory=list)

@dataclass
class Plan:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: list[Step] = field(default_factory=list)
    status: str = "planning"        # planning | running | done | failed
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[Step]:
        return next((s for s in self.steps if s.id == step_id), None)

    def ready_steps(self) -> list[Step]:
        """Steps whose dependencies are all done and which are still pending."""
        done_ids = {s.id for s in self.steps if s.status == "done"}
        return [
            s for s in self.steps
            if s.status == "pending" and all(dep in done_ids for dep in s.depends_on)
        ]

    def is_complete(self) -> bool:
        return all(s.status in ("done", "skipped") for s in self.steps)

    def is_failed(self) -> bool:
        return any(s.status == "failed" and s.retries >= s.max_retries for s in self.steps)

    def summary(self) -> dict:
        counts = {}
        for s in self.steps:
            counts[s.status] = counts.get(s.status, 0) + 1
        return {"plan_id": self.id, "goal": self.goal[:60], "status": self.status, "steps": counts}
