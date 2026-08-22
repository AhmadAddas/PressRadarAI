from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StringConstraints

from pressradar.application.opportunities import (
    InvalidOpportunityTransitionError,
    OpportunityNotFoundError,
    OpportunityService,
    PitchNotEditableError,
)
from pressradar.domain.auth import Identity
from pressradar.domain.opportunities import Opportunity, OpportunityStatus

PitchContent = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3_000)
]


class PitchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    opportunity_id: str
    content: str
    generated_at: datetime
    updated_at: datetime


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    client_name: str
    client_company: str
    media_item_id: str
    source: str
    headline: str
    journalist: str | None
    published_at: datetime
    deadline: datetime | None
    matched_topics: tuple[str, ...]
    relevance_score: int | None
    relevance_reason: str | None
    analysis_error: str | None
    pitch: PitchResponse | None
    pitch_error: str | None
    status: OpportunityStatus
    detected_at: datetime


class OpportunityStatusRequest(BaseModel):
    status: OpportunityStatus


class PitchUpdateRequest(BaseModel):
    content: PitchContent


def create_opportunities_router(
    opportunities: OpportunityService,
    current_identity: Callable[..., Identity],
) -> APIRouter:
    router = APIRouter(prefix="/opportunities", tags=["opportunities"])

    @router.get("", response_model=list[OpportunityResponse])
    def list_opportunities(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> list[Opportunity]:
        return opportunities.list(workspace_id=identity.workspace_id)

    @router.patch("/{opportunity_id}/status", response_model=OpportunityResponse)
    def transition_opportunity(
        opportunity_id: str,
        request: OpportunityStatusRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Opportunity:
        try:
            return opportunities.transition(
                workspace_id=identity.workspace_id,
                opportunity_id=opportunity_id,
                new_status=request.status,
            )
        except OpportunityNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found"
            ) from error
        except InvalidOpportunityTransitionError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invalid opportunity status transition",
            ) from error

    @router.put("/{opportunity_id}/pitch", response_model=OpportunityResponse)
    def update_pitch(
        opportunity_id: str,
        request: PitchUpdateRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Opportunity:
        try:
            return opportunities.update_pitch(
                workspace_id=identity.workspace_id,
                opportunity_id=opportunity_id,
                content=request.content,
            )
        except OpportunityNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found"
            ) from error
        except PitchNotEditableError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pitch cannot be edited in the current opportunity state",
            ) from error

    return router
