"""
Planner — autonomous task decomposition.

Takes a raw user request, classifies the document type, identifies
ambiguities (making reasonable assumptions), and produces a structured
execution plan the Executor can follow.
"""

from __future__ import annotations

import logging
from typing import Any

from app.llm.gemini_client import call_gemini, extract_json
from app.models.schemas import TaskStep, TaskStatus

logger = logging.getLogger(__name__)

PLANNING_SYSTEM_INSTRUCTION = """\
You are an autonomous AI planning agent. Your job is to analyze a user's
document request and produce a detailed, executable task plan.

You MUST return valid JSON — no prose outside the JSON block."""


async def create_plan(user_request: str) -> dict[str, Any]:
    """
    Analyse the user request and return a structured plan.

    Returns
    -------
    dict with keys:
        document_type : str   — e.g. "Project Proposal", "Meeting Minutes"
        assumptions   : list[str] — assumptions made for ambiguous inputs
        tasks         : list[TaskStep] — ordered execution steps
    """

    prompt = f"""Analyze the following user request and create an execution plan
for generating a professional document.

User request: "{user_request}"

Return a JSON object with this exact structure:
{{
    "document_type": "The type of document to create (e.g., Project Proposal, Meeting Minutes, Business Report, Technical Design, SOP, Product Specification)",
    "assumptions": [
        "List any assumptions you're making because the request is ambiguous, incomplete, or missing information",
        "Be specific about what you assumed and why"
    ],
    "tasks": [
        {{
            "step_number": 1,
            "action": "research",
            "description": "Research [specific topic]"
        }},
        {{
            "step_number": 2,
            "action": "outline",
            "description": "Create document outline with sections: [list sections]"
        }},
        {{
            "step_number": 3,
            "action": "write_section",
            "description": "Write section: [Section Name]"
        }},
        {{
            "step_number": 4,
            "action": "write_section",
            "description": "Write section: [Another Section]"
        }},
        {{
            "step_number": 5,
            "action": "review",
            "description": "Review and polish the complete document"
        }}
    ]
}}

Rules:
1. Always start with a "research" step.
2. Always include an "outline" step after research.
3. Include one "write_section" step per major document section (at least 3-5 sections).
4. Always end with a "review" step.
5. Action must be one of: "research", "outline", "write_section", "review".
6. If the request is vague, make reasonable assumptions and list them.
7. Aim for 6-10 total steps for a comprehensive document."""

    raw = await call_gemini(
        prompt,
        system_instruction=PLANNING_SYSTEM_INSTRUCTION,
        temperature=0.4,
    )

    plan_data = extract_json(raw)

    # Validate and normalise
    document_type = plan_data.get("document_type", "Business Document")
    assumptions = plan_data.get("assumptions", [])

    raw_tasks = plan_data.get("tasks", [])
    tasks: list[TaskStep] = []
    for i, t in enumerate(raw_tasks, start=1):
        tasks.append(
            TaskStep(
                step_number=i,
                action=t.get("action", "write_section"),
                description=t.get("description", f"Step {i}"),
                status=TaskStatus.PENDING,
            )
        )

    # Ensure we have at least the essential steps
    action_types = {t.action for t in tasks}
    if "research" not in action_types:
        tasks.insert(0, TaskStep(step_number=0, action="research", description="Research the topic"))
    if "review" not in action_types:
        tasks.append(TaskStep(step_number=len(tasks) + 1, action="review", description="Final review"))

    # Re-number steps sequentially
    for i, t in enumerate(tasks, start=1):
        t.step_number = i

    logger.info(
        "Plan created: type=%s, steps=%d, assumptions=%d",
        document_type,
        len(tasks),
        len(assumptions),
    )

    return {
        "document_type": document_type,
        "assumptions": assumptions,
        "tasks": tasks,
    }
