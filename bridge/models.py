from pydantic import BaseModel
from typing import Optional, Literal
import time
import uuid


class Message(BaseModel):
    id: str = ""
    channel: str          # e.g. "copilot", "gemini", "broadcast", "system"
    sender: str           # "copilot" | "gemini" | "system"
    content: str
    timestamp: float = 0.0
    metadata: dict = {}

    def model_post_init(self, _):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = time.time()


class Task(BaseModel):
    id: str = ""
    title: str
    description: str
    created_by: str       # "copilot" | "gemini"
    assigned_to: Optional[str] = None   # None = unclaimed
    status: Literal["pending", "in_progress", "done", "failed"] = "pending"
    result: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    priority: int = 0     # higher = more urgent
    tags: list[str] = []

    def model_post_init(self, _):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
