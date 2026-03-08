# AI Bridge — Agent Coordination Instructions

You are working in a multi-agent environment. A coordination bridge is running at
**http://localhost:8765** that lets you communicate in real time with other AI agents
(Copilot CLI, Gemini CLI) working on the same project.

## YOUR IDENTITY
- If you are **GitHub Copilot CLI**, your agent name is: `copilot`
- If you are **Gemini CLI**, your agent name is: `gemini`

## STARTUP — DO THIS FIRST
At the start of every session, run these two commands:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py status
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py inbox <your-agent-name>
```
This tells you if the bridge is live and shows any tasks waiting for you.

## COMMUNICATION RULES

### When you finish a piece of work:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py send <you> broadcast "<what you just did>"
```

### When you need the other agent to do something:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py task create <you> "<short title>" "<detailed description of what to do>"
```

### When you want to check for work assigned to you:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py inbox <you>
```

### When you claim and start a task:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py task claim <you>
```

### When you finish a task:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py task done <you> <task-id> "<summary of result>"
```

### When you want to see the full conversation history:
```
!python C:\Users\josht\Antigravity_projects\ai-bridge\client.py history
```

## CHANNELS
- `broadcast` — general announcements visible to everyone
- `copilot` — messages directed specifically at Copilot
- `gemini` — messages directed specifically at Gemini
- `tasks` — automatic task update notifications (read-only)

## EXAMPLE WORKFLOW
```
# Copilot finishes auth module:
!python client.py send copilot broadcast "Auth module complete at rotating_proxy/auth.py"
!python client.py task create copilot "Security review" "Review rotating_proxy/auth.py for vulnerabilities — check JWT expiry, token storage, and replay attack surface"

# Gemini picks it up:
!python client.py inbox gemini
!python client.py task claim gemini
# ... does the review ...
!python client.py task done gemini <id> "Found 2 issues: JWT has no exp claim (line 47), tokens stored in plaintext (line 89). Fixed both."

# Copilot sees the result:
!python client.py history
```

## DASHBOARD
Live view of all messages and tasks: **http://localhost:8765/ui**

## AUTONOMY GUIDELINES
- **Check inbox before starting new work** — there may already be a task for you
- **Post tasks instead of waiting** — if you need something from the other agent, create a task
- **Be specific in task descriptions** — include file paths, line numbers, exact requirements
- **Always post a broadcast when done** — so the other agent knows the state has changed
- If the bridge is unreachable, continue working independently and sync when it comes back
