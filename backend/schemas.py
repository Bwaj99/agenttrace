"""
Pydantic response/request models for the API.

Kept separate from the SQLAlchemy models (models.py) since the shapes
differ: JSON text columns (input_json, output_json, ...) are decoded
into real JSON here, and steps are nested into a tree instead of the
flat FK relationship the DB stores.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class TokenUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None


class StepNode(BaseModel):
    id: str
    parent_step_id: Optional[str] = None
    name: str
    step_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    children: List["StepNode"] = []


# Needed because StepNode references itself in `children`.
StepNode.model_rebuild()


class RunSummary(BaseModel):
    """One row of `GET /runs` — cheap to compute, no step tree."""

    id: str
    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    metadata: dict = {}
    step_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    duration_ms: Optional[int] = None


class RunDetail(RunSummary):
    """`GET /runs/{run_id}` — the summary plus the full nested step tree."""

    steps: List[StepNode] = []
    slowest_step_id: Optional[str] = None


class ReplayRequest(BaseModel):
    """Body of `POST /runs/{run_id}/steps/{step_id}/replay`."""

    modified_input: Any


class ReplayResult(BaseModel):
    replay_id: str
    step_id: str
    requested_at: datetime
    modified_input: Any
    original_output: Optional[Any] = None
    replayed_output: Optional[Any] = None
    token_usage: Optional[TokenUsage] = None
    error: Optional[str] = None
