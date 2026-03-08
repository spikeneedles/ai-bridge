import logging
import uuid
from orchestrator.models import Plan, Step
from orchestrator.llm import llm

logger = logging.getLogger(__name__)

DECOMPOSE_SYSTEM = """You are a technical project orchestrator. Your job is to break down a software development goal into concrete, executable subtasks.

Rules:
- Each step must be something ONE agent can execute completely
- Steps should be as small and specific as possible (15-45 min of work each)
- Assign each step to the best agent:
  * "copilot" = writing/modifying code, implementing features, fixing bugs
  * "gemini" = research, analysis, documentation, code review, planning
  * "any" = either agent can do it (simple tasks)
- depends_on lists step IDs that must complete BEFORE this step starts
- The description MUST be a complete, self-contained instruction the agent can execute without further clarification
- Include file paths, function names, and specific requirements in descriptions
- Maximum 12 steps per plan

Respond with JSON in this exact format:
{
  "steps": [
    {
      "id": "step-1",
      "title": "Short title",
      "description": "Complete instruction with all context needed...",
      "assigned_to": "copilot",
      "depends_on": [],
      "tags": ["backend", "auth"]
    },
    {
      "id": "step-2",
      "title": "Another step",
      "description": "...",
      "assigned_to": "gemini",
      "depends_on": ["step-1"],
      "tags": ["review"]
    }
  ]
}"""


async def decompose_goal(goal: str, context: str = "") -> Plan:
    """Break a high-level goal into a Plan with ordered Steps."""
    logger.info(f"Decomposing goal: {goal[:80]}")

    user_prompt = f"Goal: {goal}"
    if context:
        user_prompt += f"\n\nContext:\n{context}"

    data = await llm.complete_json(DECOMPOSE_SYSTEM, user_prompt)

    plan = Plan(goal=goal)
    for s in data.get("steps", []):
        step = Step(
            id=s.get("id", ""),
            title=s.get("title", ""),
            description=s.get("description", ""),
            assigned_to=s.get("assigned_to", "any"),
            depends_on=s.get("depends_on", []),
            tags=s.get("tags", []),
        )
        if not step.id:
            step.id = str(uuid.uuid4())[:8]
        plan.steps.append(step)

    logger.info(f"Plan {plan.id}: {len(plan.steps)} steps decomposed")
    return plan


async def refine_step(step: Step, failed_result: str) -> str:
    """Given a failed step and its error, generate a revised description."""
    system = "You are a debugging assistant. A software task failed. Rewrite the task description to fix the issue. Return ONLY the new description text, no JSON."
    user = f"Original task: {step.description}\n\nFailure: {failed_result}\n\nRewrite the task to fix this."
    return await llm.complete(system, user)
