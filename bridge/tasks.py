from typing import Optional
from bridge.models import Task
from bridge.db import save_task, update_task, get_tasks, get_task
import time


class TaskQueue:

    async def post(self, task: Task) -> Task:
        """Save new task to DB."""
        await save_task(task)
        return task

    async def claim(self, agent: str, task_id: str = None) -> Optional[Task]:
        """
        Claim a task for an agent.
        If task_id given, claim that specific one.
        Otherwise claim the highest-priority pending task not created by agent.
        Sets status to in_progress, assigned_to to agent.
        """
        if task_id:
            task = await get_task(task_id)
            if task is None:
                return None
            if task.status != "pending":
                return None
        else:
            pending = await get_tasks(status="pending")
            # Find the highest-priority unclaimed task not created by this agent
            candidates = [t for t in pending if t.created_by != agent and t.assigned_to is None]
            if not candidates:
                return None
            # get_tasks already orders by priority DESC, so first is highest priority
            task = candidates[0]

        task.status = "in_progress"
        task.assigned_to = agent
        task.updated_at = time.time()
        await update_task(task)
        return task

    async def complete(self, task_id: str, agent: str, result: str) -> Task:
        """Mark task done with result."""
        task = await get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        task.status = "done"
        task.result = result
        task.assigned_to = agent
        task.updated_at = time.time()
        await update_task(task)
        return task

    async def fail(self, task_id: str, agent: str, reason: str) -> Task:
        """Mark task failed."""
        task = await get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        task.status = "failed"
        task.result = reason
        task.assigned_to = agent
        task.updated_at = time.time()
        await update_task(task)
        return task

    async def list_tasks(self, status: str = None) -> list[Task]:
        return await get_tasks(status=status)


queue = TaskQueue()
