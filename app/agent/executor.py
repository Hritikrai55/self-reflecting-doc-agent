"""
Executor — walks through the task plan, calling the right tool for each step.

Maintains an execution context so each step can build on the results of
previous ones (a simple form of conversation memory).
"""

from __future__ import annotations

import logging

from app.agent.tools import (
    outline_tool,
    research_tool,
    review_content_tool,
    write_section_tool,
)
from app.llm.gemini_client import extract_json
from app.models.schemas import TaskStatus, TaskStep

logger = logging.getLogger(__name__)


class ExecutionContext:
    """Shared state that accumulates as steps execute."""

    def __init__(self, user_request: str, document_type: str) -> None:
        self.user_request = user_request
        self.document_type = document_type
        self.research: str = ""
        self.outline: dict | None = None
        self.sections: list[dict[str, str]] = []  # [{heading, content}]
        self.review_result: dict | None = None

    @property
    def preceding_context(self) -> str:
        """Return the last ~2000 chars of written sections for context."""
        parts = [f"## {s['heading']}\n{s['content']}" for s in self.sections]
        joined = "\n\n".join(parts)
        return joined[-2000:] if len(joined) > 2000 else joined

    @property
    def full_content(self) -> str:
        """Return the complete document content assembled so far."""
        return "\n\n".join(
            f"## {s['heading']}\n{s['content']}" for s in self.sections
        )


async def execute_plan(
    tasks: list[TaskStep],
    user_request: str,
    document_type: str,
) -> ExecutionContext:
    """
    Execute each step in the plan sequentially, updating context as we go.

    Parameters
    ----------
    tasks : list[TaskStep]
        The ordered plan from the Planner.
    user_request : str
        Original user input.
    document_type : str
        Classified document type.

    Returns
    -------
    ExecutionContext
        Accumulated results from all steps.
    """
    ctx = ExecutionContext(user_request, document_type)

    for task in tasks:
        task.status = TaskStatus.IN_PROGRESS
        logger.info("Executing step %d: [%s] %s", task.step_number, task.action, task.description)

        try:
            result = await _execute_step(task, ctx)
            task.result = result[:500] if result else "Completed"  # truncate for response
            task.status = TaskStatus.COMPLETED
            logger.info("Step %d completed.", task.step_number)

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.result = f"Error: {exc}"
            logger.error("Step %d failed: %s", task.step_number, exc, exc_info=True)
            # Continue with remaining steps rather than aborting entirely

    return ctx


async def _execute_step(task: TaskStep, ctx: ExecutionContext) -> str:
    """Dispatch a single task step to the correct tool."""

    if task.action == "research":
        ctx.research = await research_tool(ctx.user_request, ctx.document_type)
        return ctx.research

    elif task.action == "outline":
        raw_outline = await outline_tool(ctx.user_request, ctx.document_type, ctx.research)
        try:
            ctx.outline = extract_json(raw_outline)
        except (ValueError, Exception):
            # If JSON parsing fails, use a sensible default outline
            ctx.outline = {
                "title": ctx.document_type,
                "sections": [
                    {"heading": "Introduction", "content_notes": "Introduce the topic", "subsections": [], "include_table": False},
                    {"heading": "Background", "content_notes": "Provide context", "subsections": [], "include_table": False},
                    {"heading": "Analysis", "content_notes": "Core analysis", "subsections": [], "include_table": True},
                    {"heading": "Recommendations", "content_notes": "Key recommendations", "subsections": [], "include_table": False},
                    {"heading": "Conclusion", "content_notes": "Summarise findings", "subsections": [], "include_table": False},
                ],
            }
            logger.warning("Outline JSON parse failed — using default structure.")
        return f"Outline created: {ctx.outline.get('title', 'Document')} with {len(ctx.outline.get('sections', []))} sections"

    elif task.action == "write_section":
        # Determine which section to write from the description
        section_info = _match_section(task.description, ctx.outline)
        content = await write_section_tool(
            section_heading=section_info["heading"],
            content_notes=section_info.get("content_notes", task.description),
            document_type=ctx.document_type,
            research=ctx.research[:3000],  # limit context size
            preceding_context=ctx.preceding_context,
        )
        ctx.sections.append({"heading": section_info["heading"], "content": content})
        return content

    elif task.action == "review":
        raw_review = await review_content_tool(
            ctx.full_content,
            ctx.document_type,
            ctx.user_request,
        )
        try:
            ctx.review_result = extract_json(raw_review)
        except (ValueError, Exception):
            ctx.review_result = {"status": "approved", "notes": "Review completed."}
        return str(ctx.review_result)

    else:
        logger.warning("Unknown action '%s' — skipping.", task.action)
        return f"Unknown action: {task.action}"


def _match_section(description: str, outline: dict | None) -> dict:
    """
    Match a write_section task description to the corresponding section
    in the outline.  Falls back to using the description itself.
    """
    if not outline or "sections" not in outline:
        return {"heading": description, "content_notes": description}

    desc_lower = description.lower()
    for section in outline["sections"]:
        heading = section.get("heading", "")
        if heading.lower() in desc_lower or desc_lower in heading.lower():
            return section

    # If no match, try partial matching on keywords
    desc_words = set(desc_lower.split())
    best_match = None
    best_score = 0
    for section in outline["sections"]:
        heading_words = set(section.get("heading", "").lower().split())
        overlap = len(desc_words & heading_words)
        if overlap > best_score:
            best_score = overlap
            best_match = section

    if best_match and best_score > 0:
        return best_match

    # Final fallback — use the description as both heading and notes
    return {"heading": description.replace("Write section: ", ""), "content_notes": description}
