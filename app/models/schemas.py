"""
Pydantic models for request/response validation and internal data structures.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Request / Response ────────────────────────────────────────────────

class AgentRequest(BaseModel):
    """Incoming user request payload."""

    request: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Natural-language description of the document to generate.",
        examples=[
            "Create a project proposal for a mobile app that helps users track their daily water intake"
        ],
    )


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStep(BaseModel):
    """A single task in the agent's execution plan."""

    step_number: int
    action: str = Field(..., description="What this step does (e.g., 'research', 'outline', 'write_section', 'review').")
    description: str = Field(..., description="Human-readable explanation of this step.")
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None


class ReflectionResult(BaseModel):
    """Outcome of the agent's self-check on the generated document."""

    passed: bool = Field(..., description="Whether the document passed the quality check.")
    score: int = Field(default=0, ge=0, le=100, description="Quality score 0-100.")
    issues: list[str] = Field(default_factory=list, description="List of issues found.")
    improvements_made: list[str] = Field(default_factory=list, description="Improvements applied on retry.")


class AgentResponse(BaseModel):
    """Full response returned by the /agent endpoint."""

    request_id: str
    original_request: str
    document_type: str = Field(..., description="Detected document type (e.g., 'Project Proposal').")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions the agent made for ambiguous requests.")
    task_plan: list[TaskStep] = Field(..., description="The agent's autonomous execution plan.")
    reflection: ReflectionResult
    filename: str = Field(..., description="Name of the generated .docx file.")
    download_url: str = Field(..., description="Relative URL to download the document.")
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: str = "Document generated successfully."
