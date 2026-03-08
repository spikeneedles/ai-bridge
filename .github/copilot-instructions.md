# Copilot CLI — Multi-Agent Coordination

You are **copilot** in a two-agent system. A coordination bridge runs at http://localhost:8765.

## On every session start:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py status
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py inbox copilot
```

## Core commands:
| Action | Command |
|--------|---------|
| Announce completion | `!python client.py send copilot broadcast "<what you did>"` |
| Assign task to Gemini | `!python client.py task create copilot "<title>" "<details>"` |
| Check your inbox | `!python client.py inbox copilot` |
| Claim a task | `!python client.py task claim copilot` |
| Complete a task | `!python client.py task done copilot <id> "<result>"` |
| See recent activity | `!python client.py history` |

Dashboard: http://localhost:8765/ui
Full instructions: C:\Users\josht\Antigravity_projects\ai-bridge\AGENTS.md
