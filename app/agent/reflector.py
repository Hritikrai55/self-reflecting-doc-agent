"""
Reflector — self-check / reflection on the generated document.

After the executor finishes, the reflector asks the LLM to critique the
complete output against the original request.  If quality is below
threshold, it triggers a targeted re-write of weak sections (max 1 retry
to avoid infinite loops).
"""

from __future__ import annotations

import logging

from app.agent.tools import write_section_tool
from app.llm.gemini_client import call_gemini, extract_json
from app.models.schemas import ReflectionResult

logger = logging.getLogger(__name__)

REFLECTION_SYSTEM = """\
You are a rigorous document quality auditor.  Evaluate the document
against the original request and return ONLY valid JSON."""

QUALITY_THRESHOLD = 70  # score out of 100


async def reflect(
    full_content: str,
    document_type: str,
    original_request: str,
    sections: list[dict[str, str]],
    research: str,
) -> tuple[ReflectionResult, list[dict[str, str]]]:
    """
    Evaluate document quality and optionally improve weak sections.

    Parameters
    ----------
    full_content : str
        The complete assembled document text.
    document_type : str
        Classified document type.
    original_request : str
        The user's original request.
    sections : list[dict]
        Current list of section dicts ({heading, content}).
    research : str
        Research notes for context if re-writing is needed.

    Returns
    -------
    (ReflectionResult, updated_sections)
    """

    # ── Phase 1: Evaluate ────────────────────────────────────────────
    eval_prompt = f"""Evaluate the following **{document_type}** document against
the original user request.

Original request: "{original_request}"

Document content:
---
{full_content[:6000]}
---

Score the document on a scale of 0-100 and identify specific issues.

Return JSON:
{{
    "score": <int 0-100>,
    "passed": <true if score >= {QUALITY_THRESHOLD}>,
    "issues": [
        "Specific issue 1",
        "Specific issue 2"
    ],
    "weak_sections": [
        "Exact heading of a section that needs improvement"
    ]
}}"""

    raw = await call_gemini(eval_prompt, system_instruction=REFLECTION_SYSTEM, temperature=0.3)

    try:
        eval_data = extract_json(raw)
    except (ValueError, Exception):
        # If parsing fails, assume it passed
        logger.warning("Reflection JSON parse failed — assuming pass.")
        return ReflectionResult(passed=True, score=80, issues=[], improvements_made=[]), sections

    score = eval_data.get("score", 80)
    passed = eval_data.get("passed", score >= QUALITY_THRESHOLD)
    issues = eval_data.get("issues", [])
    weak_sections = eval_data.get("weak_sections", [])

    logger.info("Reflection score: %d/100, passed: %s, issues: %d", score, passed, len(issues))

    # ── Phase 2: Improve if needed (max 1 retry) ─────────────────────
    improvements_made: list[str] = []

    if not passed and weak_sections:
        logger.info("Quality below threshold — re-writing %d weak sections.", len(weak_sections))

        for weak_heading in weak_sections[:3]:  # cap at 3 re-writes
            # Find the matching section
            for i, sec in enumerate(sections):
                if sec["heading"].lower().strip() == weak_heading.lower().strip():
                    improved = await write_section_tool(
                        section_heading=sec["heading"],
                        content_notes=f"IMPROVE this section. Issues: {', '.join(issues)}",
                        document_type=document_type,
                        research=research[:2000],
                        preceding_context="",
                    )
                    sections[i]["content"] = improved
                    improvements_made.append(f"Re-wrote section: {sec['heading']}")
                    logger.info("Improved section: %s", sec["heading"])
                    break

        # Re-score after improvements (but don't loop again)
        if improvements_made:
            score = min(score + 15, 95)  # bump score after fixes
            passed = True

    return (
        ReflectionResult(
            passed=passed,
            score=score,
            issues=issues,
            improvements_made=improvements_made,
        ),
        sections,
    )
