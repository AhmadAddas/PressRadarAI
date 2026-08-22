from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from pressradar.application.analytics import AnalyticsError, AnalyticsService
from pressradar.domain.analytics import AnalyticsSummary
from pressradar.domain.auth import Identity


class SourcePerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    opportunities: int
    sent: int


class ClientVolumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: str
    client_name: str
    opportunities: int


class AnalyticsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunities_detected: int
    average_relevance_score: float | None
    average_seconds_to_review: float | None
    average_seconds_to_send: float | None
    approval_rate: float
    pitch_send_rate: float
    dismissal_rate: float
    sources: tuple[SourcePerformanceResponse, ...]
    clients: tuple[ClientVolumeResponse, ...]


def create_analytics_router(
    analytics: AnalyticsService, current_identity: Callable[..., Identity]
) -> APIRouter:
    router = APIRouter(prefix="/analytics", tags=["analytics"])

    @router.get("/summary", response_model=AnalyticsSummaryResponse)
    def summary(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> AnalyticsSummary:
        try:
            return analytics.summary(workspace_id=identity.workspace_id)
        except AnalyticsError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics reporting is temporarily unavailable",
            ) from error

    return router
