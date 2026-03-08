import logging
from orchestrator.models import Plan, Step

logger = logging.getLogger(__name__)


def validate_plan(plan: Plan) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []
    step_ids = {s.id for s in plan.steps}

    for step in plan.steps:
        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(f"Step '{step.id}' depends on unknown step '{dep}'")

    if _has_cycle(plan):
        errors.append("Plan contains a dependency cycle")

    return errors


def _has_cycle(plan: Plan) -> bool:
    """Detect cycles using DFS."""
    deps = {s.id: set(s.depends_on) for s in plan.steps}
    visited, rec_stack = set(), set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in deps.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    return any(dfs(s.id) for s in plan.steps if s.id not in visited)


def execution_order(plan: Plan) -> list[list[Step]]:
    """
    Return steps in execution waves — each wave can run in parallel.
    Wave N contains steps whose dependencies are all in waves 0..N-1.
    """
    assigned = set()
    waves = []

    while len(assigned) < len(plan.steps):
        wave = [
            s for s in plan.steps
            if s.id not in assigned and all(dep in assigned for dep in s.depends_on)
        ]
        if not wave:
            break
        waves.append(wave)
        assigned.update(s.id for s in wave)

    return waves


def inject_context(step: Step, completed_steps: list[Step]) -> Step:
    """
    Inject results from upstream completed steps into this step's description
    so the agent has full context.
    """
    upstream = [s for s in completed_steps if s.id in step.depends_on and s.result]
    if not upstream:
        return step

    context_block = "\n\n## Context from previous steps:\n"
    for s in upstream:
        context_block += f"\n### {s.title} (completed)\n{s.result}\n"

    step.description = step.description + context_block
    step.context = {s.id: s.result for s in upstream if s.result}
    return step
