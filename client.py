#!/usr/bin/env python3
"""
AI Bridge Client — standalone CLI for Copilot and Gemini agents.

Usage:
  python client.py send <sender> <channel> "<message>"
  python client.py task create <creator> "<title>" "<description>"
  python client.py task claim <agent> [task_id]
  python client.py task done <agent> <task_id> "<result>"
  python client.py task fail <agent> <task_id> "<reason>"
  python client.py orchestrate "<goal>"              # Level 5: autonomous goal execution
  python client.py plans                             # list orchestration plans
  python client.py plan <plan_id>                    # get plan details
  python client.py runners                           # show runner availability
  python client.py watch [agent] [--interval N]      # live feed of new messages/tasks
  python client.py listen <channel>
  python client.py inbox <agent>
  python client.py history [channel] [--limit N]
  python client.py status
  python client.py reset

Options:
  --server URL    Override server URL (default: http://localhost:8765)
"""
import sys
import json
import time
import argparse

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)


DEFAULT_SERVER = "http://localhost:8765"


def time_ago(ts: float) -> str:
    diff = time.time() - ts
    if diff < 5:
        return "just now"
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff/60)}m ago"
    if diff < 86400:
        return f"{int(diff/3600)}h ago"
    return f"{int(diff/86400)}d ago"


def fmt_channel(ch: str) -> str:
    return f"#{ch:<10}"


def fmt_sender(s: str) -> str:
    return f"[{s}]"


def api(server: str, method: str, path: str, **kwargs):
    url = server.rstrip("/") + path
    try:
        resp = httpx.request(method, url, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to AI Bridge at {server}", file=sys.stderr)
        print("       Is the server running? Start with: python main.py", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
        except Exception:
            detail = e.response.text
        print(f"ERROR {e.response.status_code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_send(server: str, args):
    if len(args) < 3:
        print("Usage: python client.py send <sender> <channel> <message>", file=sys.stderr)
        sys.exit(1)
    sender, channel, content = args[0], args[1], " ".join(args[2:])
    result = api(server, "POST", "/messages", json={
        "sender": sender,
        "channel": channel,
        "content": content,
    })
    print(f"✓ Message sent [id: {result['id']}] to #{channel}")


def cmd_task(server: str, args):
    if not args:
        print("Usage: python client.py task <create|claim|done|fail> ...", file=sys.stderr)
        sys.exit(1)
    sub = args[0]
    rest = args[1:]

    if sub == "create":
        if len(rest) < 3:
            print("Usage: python client.py task create <creator> <title> <description>", file=sys.stderr)
            sys.exit(1)
        creator = rest[0]
        title = rest[1]
        description = " ".join(rest[2:])
        result = api(server, "POST", "/tasks", json={
            "created_by": creator,
            "title": title,
            "description": description,
        })
        print(f"✓ Task created [id: {result['id']}]: \"{result['title']}\"")

    elif sub == "claim":
        if len(rest) < 1:
            print("Usage: python client.py task claim <agent> [task_id]", file=sys.stderr)
            sys.exit(1)
        agent = rest[0]
        task_id = rest[1] if len(rest) > 1 else None

        if task_id:
            result = api(server, "POST", f"/tasks/{task_id}/claim", json={"agent": agent})
        else:
            # Auto-claim: get pending tasks and claim the first one not created by agent
            tasks = api(server, "GET", "/tasks", params={"status": "pending"})
            candidates = [t for t in tasks if t.get("created_by") != agent and t.get("assigned_to") is None]
            if not candidates:
                print("✗ No pending tasks available to claim")
                sys.exit(0)
            candidates.sort(key=lambda t: (-t.get("priority", 0), t.get("created_at", 0)))
            task_id = candidates[0]["id"]
            result = api(server, "POST", f"/tasks/{task_id}/claim", json={"agent": agent})

        print(f"✓ Claimed task [id: {result['id']}]: \"{result['title']}\"")
        print(f"  Description: {result['description']}")
        print(f"  Created by: {result['created_by']} | Priority: {result['priority']}")

    elif sub == "done":
        if len(rest) < 3:
            print("Usage: python client.py task done <agent> <task_id> <result>", file=sys.stderr)
            sys.exit(1)
        agent, task_id = rest[0], rest[1]
        result_str = " ".join(rest[2:])
        result = api(server, "POST", f"/tasks/{task_id}/complete", json={
            "agent": agent,
            "result": result_str,
        })
        print(f"✓ Task [id: {result['id']}] marked done: \"{result['title']}\"")

    elif sub == "fail":
        if len(rest) < 3:
            print("Usage: python client.py task fail <agent> <task_id> <reason>", file=sys.stderr)
            sys.exit(1)
        agent, task_id = rest[0], rest[1]
        reason = " ".join(rest[2:])
        result = api(server, "POST", f"/tasks/{task_id}/fail", json={
            "agent": agent,
            "reason": reason,
        })
        print(f"✗ Task [id: {result['id']}] marked failed: \"{result['title']}\"")
        print(f"  Reason: {reason}")

    else:
        print(f"Unknown task subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def cmd_listen(server: str, args):
    if not args:
        print("Usage: python client.py listen <channel>", file=sys.stderr)
        sys.exit(1)
    channel = args[0]
    # Use WebSocket via httpx (fall back to polling if ws not available)
    ws_url = server.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + f"/ws/{channel}"

    print(f"👂 Listening on #{channel} (Ctrl+C to stop)...")
    print(f"   WebSocket: {ws_url}")
    print()

    try:
        with httpx.Client() as client:
            # For WebSocket we need a different approach — use websockets if available
            try:
                import websockets
                import asyncio

                async def _listen():
                    async with websockets.connect(ws_url) as ws:
                        while True:
                            raw = await ws.recv()
                            pkt = json.loads(raw)
                            if pkt.get("type") == "history":
                                for msg in pkt["messages"][-10:]:
                                    _print_msg(msg)
                            elif pkt.get("type") == "message":
                                _print_msg(pkt["data"])

                asyncio.run(_listen())
            except ImportError:
                # Fallback: poll the REST API
                print("(websockets not installed — polling every 2s)")
                seen_ids = set()
                while True:
                    msgs = api(server, "GET", "/messages", params={"channel": channel, "limit": 20})
                    for msg in msgs:
                        if msg["id"] not in seen_ids:
                            seen_ids.add(msg["id"])
                            _print_msg(msg)
                    time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped.")


def _print_msg(msg: dict):
    ts = time_ago(msg.get("timestamp", 0))
    print(f"{fmt_channel(msg['channel'])} {fmt_sender(msg['sender'])} {ts}: {msg['content']}")


def cmd_inbox(server: str, args):
    if not args:
        print("Usage: python client.py inbox <agent>", file=sys.stderr)
        sys.exit(1)
    agent = args[0]
    tasks = api(server, "GET", "/tasks", params={"status": "pending"})
    # Show tasks not created by agent (claimable) or assigned to agent
    claimable = [t for t in tasks if t.get("created_by") != agent and t.get("assigned_to") is None]
    in_progress = api(server, "GET", "/tasks", params={"status": "in_progress"})
    mine = [t for t in in_progress if t.get("assigned_to") == agent]

    if not claimable and not mine:
        print(f"✓ No pending tasks for {agent}")
        return

    if claimable:
        print(f"{len(claimable)} pending task{'s' if len(claimable)!=1 else ''}:")
        for t in claimable:
            print(f"  [{t['id']}] {t['title']} (from: {t['created_by']}, priority: {t['priority']})")

    if mine:
        print(f"\n{len(mine)} in-progress task{'s' if len(mine)!=1 else ''} assigned to {agent}:")
        for t in mine:
            print(f"  [{t['id']}] {t['title']}")


def cmd_history(server: str, args, limit: int = 50):
    channel = args[0] if args else None
    params = {"limit": limit}
    if channel:
        params["channel"] = channel
    msgs = api(server, "GET", "/messages", params=params)
    if not msgs:
        print("No messages found.")
        return
    for msg in msgs:
        ts = time_ago(msg.get("timestamp", 0))
        ch_str = fmt_channel(msg["channel"])
        s_str = fmt_sender(msg["sender"])
        print(f"{ch_str} {s_str:<12} {ts:<12} {msg['content']}")


def cmd_status(server: str):
    s = api(server, "GET", "/status")
    up = s["uptime"]
    if up < 60:
        upstr = f"{int(up)}s"
    elif up < 3600:
        upstr = f"{int(up/60)}m {int(up%60)}s"
    else:
        upstr = f"{int(up/3600)}h {int((up%3600)/60)}m"
    print(f"AI Bridge Status")
    print(f"  Uptime:           {upstr}")
    print(f"  Messages:         {s['message_count']}")
    print(f"  Tasks:            {s['task_count']}")
    print(f"  Connected clients:{s['connected_clients']}")
    print(f"  Dashboard:        {server}/ui")


def cmd_orchestrate(server: str, args):
    if not args:
        print("Usage: python client.py orchestrate \"<goal>\"", file=sys.stderr)
        sys.exit(1)
    goal = " ".join(args)
    result = api(server, "POST", "/orchestrate", json={"goal": goal, "background": True})
    print(f"🎯 Orchestration started!")
    print(f"   Goal: {goal}")
    print(f"   {result.get('message', '')}")
    print(f"\n   Monitor: {server}/orchestrate/plans")
    print(f"   Dashboard: {server}/ui")
    print(f"\n   Tip: python client.py plans   (check progress)")
    print(f"        python client.py watch      (live feed)")


def cmd_plans(server: str, args):
    plans = api(server, "GET", "/orchestrate/plans")
    if not plans:
        print("No orchestration plans yet.")
        return
    print(f"{len(plans)} plan(s):")
    for p in plans:
        icon = {"planning": "🔍", "running": "⚙️ ", "done": "✅", "failed": "❌"}.get(p["status"], "•")
        steps = p.get("steps", {})
        step_str = " | ".join(f"{k}: {v}" for k, v in steps.items()) if steps else ""
        print(f"\n  {icon} [{p['plan_id']}] {p['goal']}")
        print(f"     Status: {p['status']}  Steps: {step_str}")


def cmd_plan(server: str, args):
    if not args:
        print("Usage: python client.py plan <plan_id>", file=sys.stderr)
        sys.exit(1)
    plan = api(server, "GET", f"/orchestrate/plans/{args[0]}")
    icon = {"planning": "🔍", "running": "⚙️ ", "done": "✅", "failed": "❌"}.get(plan["status"], "•")
    print(f"{icon} Plan [{plan['id']}] — {plan['status'].upper()}")
    print(f"  Goal: {plan['goal']}")
    print(f"\n  Steps ({len(plan['steps'])}):")
    for s in plan["steps"]:
        step_icon = {"pending": "⏳", "running": "⚙️ ", "done": "✅", "failed": "❌", "skipped": "⏭️ "}.get(s["status"], "•")
        deps = f" (needs: {', '.join(s['depends_on'])})" if s["depends_on"] else ""
        print(f"    {step_icon} [{s['id']}] {s['title']} → {s['assigned_to']}{deps}")
        if s.get("result"):
            preview = s["result"][:120].replace("\n", " ")
            print(f"         Result: {preview}{'...' if len(s['result']) > 120 else ''}")


def cmd_runners(server: str):
    status = api(server, "GET", "/runners/status")
    if "error" in status:
        print(f"⚠️  Runners not available: {status['error']}")
        return
    print("Agent Runner Status:")
    icons = {True: "✅", False: "❌"}
    print(f"  {icons[status.get('copilot_api', False)]} Copilot API  (GITHUB_TOKEN)")
    print(f"  {icons[status.get('gemini_api', False)]} Gemini API   (GEMINI_API_KEY)")
    print(f"  {icons[status.get('copilot_cli', False)]} Copilot CLI  (copilot on PATH)")
    print(f"  {icons[status.get('gemini_cli', False)]} Gemini CLI   (gemini on PATH)")
    print(f"  Preferred mode: {status.get('preferred_mode', 'api')}")
    if not any([status.get('copilot_api'), status.get('gemini_api'),
                status.get('copilot_cli'), status.get('gemini_cli')]):
        print("\n  ⚠️  No runners available! Set GITHUB_TOKEN or GEMINI_API_KEY")
        print("     Or start daemon manually: python -m runners.daemon --agent copilot")


def cmd_watch(server: str, args):
    """Poll for new messages and tasks, printing them as they arrive."""
    agent = args[0] if args else None
    interval = 3
    if "--interval" in args:
        idx = args.index("--interval")
        if idx + 1 < len(args):
            try:
                interval = float(args[idx + 1])
            except ValueError:
                pass

    label = f" for {agent}" if agent else ""
    print(f"👁  Watching AI Bridge{label} (Ctrl+C to stop, polling every {interval}s)...")
    print(f"   Dashboard: {server}/ui")
    print()

    seen_msg_ids: set = set()
    seen_task_ids: dict = {}  # id -> status

    # Seed with existing state so we don't replay history
    try:
        existing_msgs = api(server, "GET", "/messages", params={"limit": 200})
        for m in existing_msgs:
            seen_msg_ids.add(m["id"])
        existing_tasks = api(server, "GET", "/tasks")
        for t in existing_tasks:
            seen_task_ids[t["id"]] = t["status"]
        print(f"  (seeded with {len(seen_msg_ids)} messages, {len(seen_task_ids)} tasks)\n")
    except SystemExit:
        pass

    try:
        while True:
            time.sleep(interval)
            try:
                # Check new messages
                msgs = api(server, "GET", "/messages", params={"limit": 100})
                for msg in msgs:
                    if msg["id"] not in seen_msg_ids:
                        seen_msg_ids.add(msg["id"])
                        ch = msg["channel"]
                        if agent is None or ch in ("broadcast", agent, "tasks"):
                            sender = msg["sender"]
                            content = msg["content"]
                            ts = time_ago(msg.get("timestamp", 0))
                            print(f"💬 {fmt_channel(ch)} {fmt_sender(sender)} {ts}: {content}")

                # Check task changes
                tasks = api(server, "GET", "/tasks")
                for t in tasks:
                    tid = t["id"]
                    status = t["status"]
                    prev = seen_task_ids.get(tid)

                    if prev is None:
                        # New task
                        seen_task_ids[tid] = status
                        if agent is None or t.get("assigned_to") == agent or t.get("created_by") == agent:
                            flag = "📋"
                            if t.get("assigned_to") == agent:
                                flag = "📌"
                            print(f"{flag} NEW TASK [{tid}] \"{t['title']}\" — status: {status} | from: {t['created_by']}")
                            if agent and t.get("assigned_to") != agent and t.get("created_by") != agent:
                                pass  # skip unrelated
                            elif t.get("assigned_to") is None and t.get("created_by") != agent:
                                print(f"   → Run: python client.py task claim {agent or '<you>'}")

                    elif prev != status:
                        # Status changed
                        seen_task_ids[tid] = status
                        icons = {"pending": "📋", "in_progress": "⚙️ ", "done": "✅", "failed": "❌"}
                        icon = icons.get(status, "•")
                        print(f"{icon} TASK [{tid}] \"{t['title']}\" changed: {prev} → {status}")
                        if status == "done" and t.get("result"):
                            print(f"   Result: {t['result']}")

            except SystemExit:
                pass  # API errors — bridge may be restarting, keep watching
            except Exception:
                pass

    except KeyboardInterrupt:
        print("\nStopped watching.")


def cmd_reset(server: str):
    api(server, "POST", "/reset")
    print("✓ Bridge reset — all messages and tasks cleared.")


def main():
    # Pre-parse --server before argparse to allow it anywhere
    server = DEFAULT_SERVER
    raw_args = sys.argv[1:]
    filtered = []
    i = 0
    while i < len(raw_args):
        if raw_args[i] == "--server" and i + 1 < len(raw_args):
            server = raw_args[i + 1]
            i += 2
        else:
            filtered.append(raw_args[i])
            i += 1

    if not filtered:
        print(__doc__)
        sys.exit(0)

    cmd = filtered[0]
    rest = filtered[1:]

    # Handle --limit for history
    limit = 50
    if "--limit" in rest:
        idx = rest.index("--limit")
        if idx + 1 < len(rest):
            try:
                limit = int(rest[idx + 1])
                rest = rest[:idx] + rest[idx + 2:]
            except ValueError:
                pass

    if cmd == "send":
        cmd_send(server, rest)
    elif cmd == "task":
        cmd_task(server, rest)
    elif cmd == "listen":
        cmd_listen(server, rest)
    elif cmd == "inbox":
        cmd_inbox(server, rest)
    elif cmd == "history":
        cmd_history(server, rest, limit=limit)
    elif cmd == "status":
        cmd_status(server)
    elif cmd == "orchestrate":
        cmd_orchestrate(server, rest)
    elif cmd == "plans":
        cmd_plans(server, rest)
    elif cmd == "plan":
        cmd_plan(server, rest)
    elif cmd == "runners":
        cmd_runners(server)
    elif cmd == "watch":
        cmd_watch(server, rest)
    elif cmd == "reset":
        cmd_reset(server)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print("Run 'python client.py' with no arguments for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
