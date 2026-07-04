"""
FastAPI application — the main entry point.

Endpoints:
    POST /agent           — Accept a request, run the autonomous agent, return results + .docx
    GET  /download/{name} — Download a generated document
    GET  /health          — Health check
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.agent.executor import execute_plan
from app.agent.planner import create_plan
from app.agent.reflector import reflect
from app.docgen.word_generator import generate_docx
from app.models.schemas import AgentRequest, AgentResponse

# ── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Autonomous AI Agent",
    description=(
        "An autonomous agent that accepts natural-language requests, "
        "creates its own task plan, executes it step-by-step, and "
        "produces a polished Microsoft Word document."
    ),
    version="1.0.0",
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")


# ── POST /agent ──────────────────────────────────────────────────────

@app.post("/agent", response_model=AgentResponse)
async def run_agent(payload: AgentRequest) -> AgentResponse:
    """
    Main endpoint — orchestrates the full agent pipeline:

    1. **Plan**     — LLM decomposes the request into a task list
    2. **Execute**  — Each task is executed via tool calls
    3. **Reflect**  — Self-check evaluates quality, triggers fixes
    4. **Generate** — Assemble a polished .docx document
    """
    request_id = uuid.uuid4().hex[:12]
    logger.info("═══ Request %s: %s", request_id, payload.request[:80])

    # ── Step 1: Plan ─────────────────────────────────────────────
    logger.info("Step 1/4 — Planning...")
    plan = await create_plan(payload.request)
    document_type = plan["document_type"]
    assumptions = plan["assumptions"]
    tasks = plan["tasks"]

    logger.info(
        "Plan: type=%s, %d tasks, %d assumptions",
        document_type,
        len(tasks),
        len(assumptions),
    )

    # ── Step 2: Execute ──────────────────────────────────────────
    logger.info("Step 2/4 — Executing %d tasks...", len(tasks))
    ctx = await execute_plan(tasks, payload.request, document_type)

    # ── Step 3: Reflect ──────────────────────────────────────────
    logger.info("Step 3/4 — Reflecting on output quality...")
    reflection, updated_sections = await reflect(
        full_content=ctx.full_content,
        document_type=document_type,
        original_request=payload.request,
        sections=ctx.sections,
        research=ctx.research,
    )
    ctx.sections = updated_sections

    logger.info(
        "Reflection: score=%d, passed=%s, improvements=%d",
        reflection.score,
        reflection.passed,
        len(reflection.improvements_made),
    )

    # ── Step 4: Generate DOCX ────────────────────────────────────
    logger.info("Step 4/4 — Generating .docx...")

    doc_title = (
        ctx.outline.get("title", document_type)
        if ctx.outline
        else document_type
    )

    filename = generate_docx(
        title=doc_title,
        sections=ctx.sections,
        document_type=document_type,
        output_dir=OUTPUT_DIR,
    )

    logger.info("═══ Request %s completed: %s", request_id, filename)

    return AgentResponse(
        request_id=request_id,
        original_request=payload.request,
        document_type=document_type,
        assumptions=assumptions,
        task_plan=tasks,
        reflection=reflection,
        filename=filename,
        download_url=f"/download/{filename}",
        message=f"Document '{doc_title}' generated successfully with {len(ctx.sections)} sections.",
    )


# ── GET /download/{filename} ─────────────────────────────────────────

@app.get("/download/{filename}")
async def download_document(filename: str) -> FileResponse:
    """Download a previously generated .docx file."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── GET /health ──────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "autonomous-ai-agent", "version": "1.0.0"}
