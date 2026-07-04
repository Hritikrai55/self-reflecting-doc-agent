"""
Agent tools — callable functions the executor invokes for each task step.

Each tool accepts context and returns a string result that feeds into the
next step.  Tools use the Gemini LLM for intelligent content generation
and mock data where appropriate.
"""

from __future__ import annotations

import logging

from app.llm.gemini_client import call_gemini

logger = logging.getLogger(__name__)


# ── Research Tool ────────────────────────────────────────────────────

async def research_tool(topic: str, document_type: str) -> str:
    """
    Gather background information and mock data relevant to the request.

    For a real production system this would call external APIs, databases,
    or web search.  Here we use the LLM to synthesise realistic research
    data, which is acceptable per the assignment rules (mock data allowed).
    """
    prompt = f"""You are a research analyst. Generate realistic background research
and supporting data for a **{document_type}** about the following topic:

Topic: {topic}

Provide:
1. Key industry context and trends (2-3 paragraphs)
2. Relevant statistics or metrics (use realistic mock data with sources)
3. Key stakeholders or target audience insights
4. Potential challenges and risk factors
5. Competitive landscape or benchmarks (if applicable)

Format your response as structured research notes. Be specific and data-driven."""

    return await call_gemini(
        prompt,
        system_instruction="You are a thorough research analyst producing realistic, data-driven research notes.",
        temperature=0.6,
    )


# ── Outline Tool ─────────────────────────────────────────────────────

async def outline_tool(
    topic: str,
    document_type: str,
    research: str,
) -> str:
    """
    Generate a structured document outline based on the research.
    """
    prompt = f"""Based on the following research, create a detailed outline for a
**{document_type}** document.

Topic: {topic}

Research Notes:
{research}

Create a professional outline with:
- Document title
- All major sections with descriptive headings
- Sub-sections where appropriate
- Notes on what content each section should contain
- Suggested tables or data displays

Return the outline in this JSON format:
{{
    "title": "Document Title",
    "sections": [
        {{
            "heading": "Section Heading",
            "subsections": ["Sub 1", "Sub 2"],
            "content_notes": "What to write here",
            "include_table": false
        }}
    ]
}}"""

    return await call_gemini(
        prompt,
        system_instruction="You are a professional document architect. Return ONLY valid JSON.",
        temperature=0.5,
    )


# ── Section Writer Tool ─────────────────────────────────────────────

async def write_section_tool(
    section_heading: str,
    content_notes: str,
    document_type: str,
    research: str,
    preceding_context: str = "",
) -> str:
    """
    Write a single section of the document with professional prose.
    """
    prompt = f"""Write the following section for a **{document_type}** document.

Section: {section_heading}
Content guidance: {content_notes}

Background research:
{research}

{"Previous sections for context:" + chr(10) + preceding_context if preceding_context else ""}

Requirements:
- Write 2-4 substantial paragraphs (unless it's a short intro/conclusion)
- Use professional business language
- Include specific data points and metrics from the research where relevant
- Use bullet points or numbered lists where they improve clarity
- If a table would help, describe it in this format:
  TABLE_START
  Header1 | Header2 | Header3
  Value1 | Value2 | Value3
  TABLE_END
- Do NOT include the section heading in your output (it will be added separately)
- Maintain logical flow with the preceding content"""

    return await call_gemini(
        prompt,
        system_instruction="You are an expert business writer producing polished, publication-ready content.",
        temperature=0.7,
    )


# ── Review / Format Tool ────────────────────────────────────────────

async def review_content_tool(
    full_content: str,
    document_type: str,
    original_request: str,
) -> str:
    """
    Review and polish the complete document content before DOCX generation.
    Returns improved content or confirmation that it's ready.
    """
    prompt = f"""Review the following **{document_type}** document content.

Original request: {original_request}

Document content:
{full_content}

Check for:
1. Consistency of tone and style
2. Logical flow between sections
3. Completeness relative to the original request
4. Professional language quality
5. Any gaps or weak sections

If everything looks good, respond with:
{{"status": "approved", "notes": "brief summary"}}

If improvements are needed, respond with:
{{"status": "needs_improvement", "issues": ["issue1", "issue2"], "suggestions": ["fix1", "fix2"]}}"""

    return await call_gemini(
        prompt,
        system_instruction="You are a senior editor reviewing business documents. Return ONLY valid JSON.",
        temperature=0.3,
    )


# ── Tool Registry ───────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "research": research_tool,
    "outline": outline_tool,
    "write_section": write_section_tool,
    "review": review_content_tool,
}
