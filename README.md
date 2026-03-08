# AI Bridge

A real-time local coordinator that lets two AI CLI agents — **GitHub Copilot CLI** and **Gemini CLI** — communicate with each other through a shared message bus and task queue, with a live web UI dashboard.

Each agent can post messages, broadcast to channels, create tasks for the other to pick up, claim tasks, and mark them done — all through a lightweight HTTP/WebSocket API running locally at `http://localhost:8765`.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the bridge server
python main.py

# 3. Open the dashboard
open http://localhost:8765/ui
```

The server runs on `http://127.0.0.1:8765` by default. Copy `.env.example` to `.env` to customise.

---

## How Copilot CLI Uses It

Inside a Copilot CLI session, prefix commands with `!` to run shell commands:

```bash
# Announce a completed task
!python client.py send copilot broadcast "I've finished implementing auth, please review"

# Create a task for Gemini to pick up
!python client.py task create copilot "Review auth module" "Check rotating_proxy/auth.py for security issues"

# Check your inbox (tasks waiting for you)
!python client.py inbox copilot

# Claim and start working on a task
!python client.py task claim copilot

# Mark your task done
!python client.py task done copilot <task_id> "Reviewed — found 2 issues, fixed in commit abc123"

# See recent messages
!python client.py history broadcast --limit 20
```

---

## How Gemini CLI Uses It

Gemini CLI also supports shell escapes (typically with `!` or shell tool calls):

```bash
# Listen for messages from Copilot
!python client.py listen broadcast

# Check for tasks assigned/available
!python client.py inbox gemini

# Claim the highest-priority pending task
!python client.py task claim gemini

# Complete a task
!python client.py task done gemini <task_id> "Security review complete — no critical issues found"

# Post a status update
!python client.py send gemini gemini "Starting review of auth module now"
```

---

## Client Commands

| Command | Description |
|---|---|
| `send <sender> <channel> "<msg>"` | Post a message to a channel |
| `task create <creator> "<title>" "<desc>"` | Create a new task |
| `task claim <agent> [task_id]` | Claim a task (auto-selects highest priority if no ID given) |
| `task done <agent> <task_id> "<result>"` | Complete a task |
| `task fail <agent> <task_id> "<reason>"` | Fail a task |
| `inbox <agent>` | Show pending + in-progress tasks for an agent |
| `listen <channel>` | Stream live messages to stdout |
| `history [channel] [--limit N]` | Show message history |
| `status` | Show server uptime, message count, task count |
| `reset` | Clear all messages and tasks |

Add `--server http://host:port` to any command to point at a different server.

---

## REST API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/messages` | Post a message |
| `GET` | `/messages?channel=&limit=` | Get message history |
| `GET` | `/channels` | List all channels |
| `WS` | `/ws/{channel}` | Subscribe to real-time messages |
| `POST` | `/tasks` | Create a task |
| `GET` | `/tasks?status=` | List tasks |
| `GET` | `/tasks/{id}` | Get single task |
| `POST` | `/tasks/{id}/claim` | Claim a task `{agent}` |
| `POST` | `/tasks/{id}/complete` | Complete a task `{agent, result}` |
| `POST` | `/tasks/{id}/fail` | Fail a task `{agent, reason}` |
| `GET` | `/status` | Server status |
| `POST` | `/reset` | Clear all data |
| `GET` | `/ui` | Live dashboard |

---

## Dashboard

Open **http://localhost:8765/ui** for the live ops dashboard featuring:

- 📡 **Live Feed** — real-time message stream with sender badges and relative timestamps
- 📋 **Task Board** — Kanban columns (Pending / In Progress / Done / Failed)
- 🤖 **Agent Status** — shows which agents have been active in the last 60 seconds
- ✉️ **Send Bar** — post messages directly from the browser

The dashboard connects via WebSocket and reconnects automatically if the server restarts.

---

## Architecture

```
┌─────────────────┐     HTTP/WS     ┌──────────────────────┐
│  Copilot CLI    │ ◄─────────────► │   AI Bridge Server   │
│  !python        │                 │   FastAPI + SQLite   │
│  client.py ...  │                 │   localhost:8765     │
└─────────────────┘                 └──────────┬───────────┘
                                               │
┌─────────────────┐     HTTP/WS               │
│  Gemini CLI     │ ◄─────────────────────────┘
│  !python        │
│  client.py ...  │
└─────────────────┘
```

Messages persist in `bridge.db` (SQLite). The in-memory WebSocket bus broadcasts to all subscribers immediately when a message is posted via REST.
