"""
Agent Runner Daemon — polls the bridge for tasks and executes them autonomously.

Run as:
    python -m runners.daemon --agent copilot
    python -m runners.daemon --agent gemini
    python -m runners.daemon --agent any   # claims any unclaimed task
"""
import asyncio
import argparse
import logging
import os
import time
import httpx
import sys

# Allow running as script from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.pool import pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("daemon")

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:8765")
POLL_INTERVAL = int(os.getenv("DAEMON_POLL_INTERVAL", "5"))


async def run_daemon(agent_name: str):
    logger.info(f"🤖 Agent daemon starting: {agent_name}")
    logger.info(f"   Bridge: {BRIDGE_URL}")
    logger.info(f"   Poll interval: {POLL_INTERVAL}s")
    
    runner = pool.get_runner(agent_name)
    logger.info(f"   Runner: {runner.name}/{runner.mode} ({'available' if runner.is_available else 'UNAVAILABLE'})")
    
    async with httpx.AsyncClient(base_url=BRIDGE_URL, timeout=15) as client:
        # Announce startup
        await _post_message(client, agent_name, "system", 
            f"🤖 {agent_name} daemon started (mode: {runner.mode})")
        
        while True:
            try:
                # Find a claimable task
                resp = await client.get("/tasks", params={"status": "pending"})
                tasks = resp.json()
                
                # Filter: tasks assigned to us, or "any", not created by orchestrator for someone else
                claimable = [
                    t for t in tasks
                    if (
                        t.get("assigned_to") in (agent_name, None, "any") and
                        t.get("created_by") != agent_name  # don't claim own tasks
                    )
                ]
                
                if not claimable:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                
                # Claim highest priority task
                claimable.sort(key=lambda t: (-t.get("priority", 0), t.get("created_at", 0)))
                task = claimable[0]
                
                # Claim it on the bridge
                claim_resp = await client.post(f"/tasks/{task['id']}/claim", json={"agent": agent_name})
                if claim_resp.status_code != 200:
                    await asyncio.sleep(1)
                    continue
                
                task = claim_resp.json()
                logger.info(f"Claimed task [{task['id']}]: {task['title']}")
                await _post_message(client, agent_name, "broadcast",
                    f"⚙️  [{agent_name}] Starting task [{task['id']}]: {task['title']}")
                
                # Execute
                start = time.time()
                result = await runner.execute(
                    task_title=task["title"],
                    task_description=task["description"],
                    context={"task_id": task["id"]},
                )
                elapsed = time.time() - start
                
                # Post result
                if result.success:
                    await client.post(f"/tasks/{task['id']}/complete", json={
                        "agent": agent_name,
                        "result": result.output[:4000],  # bridge has field size limits
                    })
                    logger.info(f"Completed [{task['id']}] in {elapsed:.1f}s")
                    await _post_message(client, agent_name, "broadcast",
                        f"✅ [{agent_name}] Completed [{task['id']}]: {task['title']} ({elapsed:.0f}s)")
                else:
                    await client.post(f"/tasks/{task['id']}/fail", json={
                        "agent": agent_name,
                        "reason": result.error or "Unknown error",
                    })
                    logger.warning(f"Failed [{task['id']}]: {result.error}")
                    await _post_message(client, agent_name, "broadcast",
                        f"❌ [{agent_name}] Failed [{task['id']}]: {result.error}")
            
            except httpx.ConnectError:
                logger.warning(f"Bridge unreachable, retrying in {POLL_INTERVAL}s...")
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.exception(f"Daemon error: {e}")
                await asyncio.sleep(POLL_INTERVAL)


async def _post_message(client, sender, channel, content):
    try:
        await client.post("/messages", json={"sender": sender, "channel": channel, "content": content})
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="AI Bridge agent runner daemon")
    parser.add_argument("--agent", default="copilot", help="Agent name (copilot/gemini/any)")
    parser.add_argument("--bridge", default=BRIDGE_URL, help="Bridge URL")
    args = parser.parse_args()
    
    asyncio.run(run_daemon(args.agent))


if __name__ == "__main__":
    main()
