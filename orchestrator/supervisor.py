import asyncio
import logging
import time
from typing import Optional

import httpx

from orchestrator.models import Plan, Step
from orchestrator.decomposer import decompose_goal, refine_step
from orchestrator.planner import validate_plan, inject_context

logger = logging.getLogger(__name__)

BRIDGE_URL = "http://localhost:8765"


class Supervisor:
    """
    Orchestrates a Plan by posting tasks to the AI Bridge and monitoring results.
    """

    def __init__(self, bridge_url: str = BRIDGE_URL):
        self.bridge = bridge_url
        self._plans: dict[str, Plan] = {}
        self._client = httpx.AsyncClient(base_url=bridge_url, timeout=15)

    async def run_goal(self, goal: str, context: str = "") -> Plan:
        """Full pipeline: decompose → validate → execute → return completed Plan."""
        await self._announce("system", f"🎯 New goal received: {goal}")
        plan = await decompose_goal(goal, context)

        errors = validate_plan(plan)
        if errors:
            await self._announce("system", f"❌ Plan validation failed: {'; '.join(errors)}")
            plan.status = "failed"
            return plan

        self._plans[plan.id] = plan
        step_list = "\n".join(f"  [{s.id}] {s.title} → {s.assigned_to}" for s in plan.steps)
        await self._announce("system", f"📋 Plan {plan.id} created ({len(plan.steps)} steps):\n{step_list}")

        plan.status = "running"
        await self._execute_plan(plan)
        return plan

    async def _execute_plan(self, plan: Plan) -> None:
        """Drive the plan to completion by posting ready tasks and monitoring bridge."""
        poll_interval = 5
        stall_timeout = 300  # 5 min without progress = stall
        last_progress = time.time()

        while not plan.is_complete() and not plan.is_failed():
            for step in plan.ready_steps():
                if step.status == "pending" and step.bridge_task_id is None:
                    step = inject_context(step, [s for s in plan.steps if s.status == "done"])
                    bridge_id = await self._post_task(step, plan.id)
                    step.bridge_task_id = bridge_id
                    step.status = "running"
                    logger.info(f"Posted step {step.id} to bridge as task {bridge_id}")

            updated = await self._poll_completions(plan)
            if updated:
                last_progress = time.time()

            if time.time() - last_progress > stall_timeout:
                running = [s for s in plan.steps if s.status == "running"]
                await self._announce("system",
                    f"⚠️  Plan {plan.id} stalled — {len(running)} tasks running with no progress for {stall_timeout}s")
                for s in running:
                    s.status = "failed"
                    s.result = "TIMEOUT: No completion received within stall timeout"
                last_progress = time.time()

            await asyncio.sleep(poll_interval)

        if plan.is_complete():
            plan.status = "done"
            plan.completed_at = time.time()
            done_count = sum(1 for s in plan.steps if s.status == "done")
            await self._announce("system",
                f"✅ Plan {plan.id} COMPLETE! {done_count}/{len(plan.steps)} steps done.\nGoal: {plan.goal}")
        else:
            plan.status = "failed"
            failed = [s for s in plan.steps if s.status == "failed"]
            await self._announce("system",
                f"❌ Plan {plan.id} FAILED. {len(failed)} steps could not complete.")

    async def _poll_completions(self, plan: Plan) -> bool:
        """Check bridge for task completions. Returns True if any step updated."""
        updated = False
        running_steps = [s for s in plan.steps if s.status == "running" and s.bridge_task_id]

        for step in running_steps:
            try:
                resp = await self._client.get(f"/tasks/{step.bridge_task_id}")
                if resp.status_code != 200:
                    continue
                task = resp.json()

                if task["status"] == "done":
                    step.status = "done"
                    step.result = task.get("result", "")
                    step.completed_at = time.time()
                    await self._announce("system",
                        f"✅ Step [{step.id}] '{step.title}' completed by {task.get('assigned_to', '?')}")
                    updated = True

                elif task["status"] == "failed":
                    if step.retries < step.max_retries:
                        step.retries += 1
                        reason = task.get("result", "unknown failure")
                        logger.warning(f"Step {step.id} failed (attempt {step.retries}): {reason}")
                        step.description = await refine_step(step, reason)
                        step.status = "pending"
                        step.bridge_task_id = None
                        await self._announce("system",
                            f"🔄 Retrying step [{step.id}] '{step.title}' (attempt {step.retries+1})")
                        updated = True
                    else:
                        step.status = "failed"
                        step.result = task.get("result", "")
                        await self._announce("system",
                            f"❌ Step [{step.id}] '{step.title}' permanently failed after {step.retries} retries")
                        updated = True

            except Exception as e:
                logger.debug(f"Error polling task {step.bridge_task_id}: {e}")

        return updated

    async def _post_task(self, step: Step, plan_id: str) -> str:
        """Post a step as a task on the bridge. Returns bridge task ID."""
        assigned = step.assigned_to if step.assigned_to != "any" else None

        resp = await self._client.post("/tasks", json={
            "title": step.title,
            "description": step.description,
            "created_by": "orchestrator",
            "assigned_to": assigned,
            "priority": 10,
            "tags": step.tags + [f"plan:{plan_id}", f"step:{step.id}"],
        })
        resp.raise_for_status()
        task = resp.json()

        target = step.assigned_to if step.assigned_to != "any" else "broadcast"
        await self._client.post("/messages", json={
            "sender": "orchestrator",
            "channel": target,
            "content": f"📌 New task for you [{task['id']}]: {step.title}",
            "metadata": {"plan_id": plan_id, "step_id": step.id, "task_id": task["id"]},
        })

        return task["id"]

    async def _announce(self, sender: str, content: str) -> None:
        """Post a message to the broadcast channel."""
        try:
            await self._client.post("/messages", json={
                "sender": sender,
                "channel": "broadcast",
                "content": content,
            })
        except Exception:
            logger.warning(f"Could not announce to bridge: {content[:60]}")

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def all_plans(self) -> list[dict]:
        return [p.summary() for p in self._plans.values()]


supervisor = Supervisor()
