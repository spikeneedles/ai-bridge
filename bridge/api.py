import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from bridge.db import (
    init_db, save_message, get_messages, get_tasks, get_task,
    count_messages, count_tasks, get_channels, clear_all
)
from bridge.bus import manager
from bridge.tasks import queue
from bridge.models import Message, Task
from bridge.ui import get_dashboard

logger = logging.getLogger(__name__)

_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Post a system welcome message
    welcome = Message(channel="system", sender="system", content="AI Bridge server started. Waiting for agents.")
    await save_message(welcome)
    yield


app = FastAPI(title="AI Bridge", version="1.0.0", lifespan=lifespan)


# ─── Request bodies ──────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    channel: str
    sender: str
    content: str
    metadata: dict = {}


class TaskCreate(BaseModel):
    title: str
    description: str
    created_by: str
    priority: int = 0
    tags: list[str] = []


class ClaimBody(BaseModel):
    agent: str


class CompleteBody(BaseModel):
    agent: str
    result: str


class FailBody(BaseModel):
    agent: str
    reason: str


# ─── UI ───────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/ui", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=get_dashboard())


# ─── System ──────────────────────────────────────────────────────────────────

@app.get("/status")
async def status():
    return {
        "uptime": time.time() - _start_time,
        "message_count": await count_messages(),
        "task_count": await count_tasks(),
        "connected_clients": manager.connected_count(),
    }


@app.post("/reset")
async def reset():
    await clear_all()
    sys_msg = Message(channel="system", sender="system", content="Bridge reset — all data cleared.")
    await save_message(sys_msg)
    await manager.broadcast(sys_msg)
    return {"ok": True}


# ─── Messages ────────────────────────────────────────────────────────────────

@app.post("/messages", response_model=Message)
async def post_message(body: MessageCreate):
    msg = Message(
        channel=body.channel,
        sender=body.sender,
        content=body.content,
        metadata=body.metadata,
    )
    await save_message(msg)
    await manager.broadcast(msg)
    return msg


@app.get("/messages", response_model=list[Message])
async def list_messages(
    channel: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    return await get_messages(channel=channel, limit=limit)


@app.get("/channels")
async def list_channels():
    return await get_channels()


# ─── WebSocket ───────────────────────────────────────────────────────────────

@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await manager.connect(websocket, channel)
    try:
        # Send message history on connect
        history = await get_messages(
            channel=None if channel == "all" else channel,
            limit=50
        )
        import json
        await websocket.send_text(json.dumps({
            "type": "history",
            "messages": [m.model_dump() for m in history]
        }))
        # Keep connection alive, receiving pings
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, channel)


# ─── Tasks ───────────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=Task)
async def create_task(body: TaskCreate):
    task = Task(
        title=body.title,
        description=body.description,
        created_by=body.created_by,
        priority=body.priority,
        tags=body.tags,
    )
    task = await queue.post(task)
    # notify via WS and post a system message
    await manager.broadcast_task_update(task.model_dump())
    sys_msg = Message(
        channel="system",
        sender="system",
        content=f"Task [{task.id}] created by {task.created_by}: \"{task.title}\"",
    )
    await save_message(sys_msg)
    await manager.broadcast(sys_msg)
    return task


@app.get("/tasks", response_model=list[Task])
async def list_tasks(status: Optional[str] = Query(None)):
    return await queue.list_tasks(status=status)


@app.get("/tasks/{task_id}", response_model=Task)
async def get_single_task(task_id: str):
    task = await get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks/{task_id}/claim", response_model=Task)
async def claim_task(task_id: str, body: ClaimBody):
    task = await queue.claim(agent=body.agent, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=409, detail=f"Task {task_id} not available to claim")
    await manager.broadcast_task_update(task.model_dump())
    sys_msg = Message(
        channel="system",
        sender="system",
        content=f"Task [{task.id}] \"{task.title}\" claimed by {body.agent}",
    )
    await save_message(sys_msg)
    await manager.broadcast(sys_msg)
    return task


@app.post("/tasks/{task_id}/complete", response_model=Task)
async def complete_task(task_id: str, body: CompleteBody):
    try:
        task = await queue.complete(task_id=task_id, agent=body.agent, result=body.result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await manager.broadcast_task_update(task.model_dump())
    sys_msg = Message(
        channel="system",
        sender="system",
        content=f"Task [{task.id}] \"{task.title}\" completed by {body.agent}",
    )
    await save_message(sys_msg)
    await manager.broadcast(sys_msg)
    return task


    await save_message(sys_msg)
    await manager.broadcast(sys_msg)
    return task


# ─── Orchestrator endpoints ───────────────────────────────────────────────────

class OrchestrationRequest(BaseModel):
    goal: str
    context: str = ""
    background: bool = True


_active_plans: dict = {}


@app.post("/orchestrate")
async def start_orchestration(req: OrchestrationRequest):
    """Submit a high-level goal. The orchestrator decomposes and autonomously drives agents."""
    import asyncio
    try:
        from orchestrator import supervisor
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Orchestrator not available: {e}")

    if req.background:
        async def _run():
            plan = await supervisor.run_goal(req.goal, req.context)
            _active_plans[plan.id] = plan
        asyncio.create_task(_run())
        return {"status": "started", "message": "Running in background. Monitor at /orchestrate/plans"}
    else:
        plan = await supervisor.run_goal(req.goal, req.context)
        _active_plans[plan.id] = plan
        return plan.__dict__


@app.get("/orchestrate/plans")
async def list_plans():
    """List all orchestration plans and their status."""
    try:
        from orchestrator import supervisor
        return supervisor.all_plans()
    except ImportError:
        return []


@app.get("/orchestrate/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get detailed status of a plan including all steps."""
    try:
        from orchestrator import supervisor
        plan = supervisor.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {
            "id": plan.id, "goal": plan.goal, "status": plan.status,
            "created_at": plan.created_at, "completed_at": plan.completed_at,
            "steps": [
                {"id": s.id, "title": s.title, "assigned_to": s.assigned_to,
                 "status": s.status, "depends_on": s.depends_on,
                 "result": s.result, "retries": s.retries, "bridge_task_id": s.bridge_task_id}
                for s in plan.steps
            ],
        }
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/runners/status")
async def runner_status():
    """Show which agent runners are available."""
    try:
        from runners.pool import pool
        return pool.status()
    except ImportError as e:
        return {"error": str(e)}
