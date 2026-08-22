from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from pressradar.application.media import InvalidMediaItemError, MediaIngestionService
from pressradar.domain.auth import Identity
from pressradar.domain.media import IngestionResult, MediaItem, MediaSourceType


class MediaItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    source_type: MediaSourceType
    author: str | None
    journalist: str | None
    headline: str
    body: str
    url: str | None
    published_at: datetime
    deadline: datetime | None
    topics: tuple[str, ...]
    external_id: str | None
    ingested_at: datetime


class IngestionResponse(BaseModel):
    created: int
    duplicates: int


def create_media_router(
    media_service: MediaIngestionService,
    current_identity: Callable[..., Identity],
) -> APIRouter:
    router = APIRouter(prefix="/media", tags=["media"])

    @router.post("/ingest", response_model=IngestionResponse)
    def ingest_media(
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> IngestionResult:
        try:
            return media_service.ingest()
        except InvalidMediaItemError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The media provider returned an invalid item",
            ) from error

    @router.get("", response_model=list[MediaItemResponse])
    def list_media(
        _identity: Annotated[Identity, Depends(current_identity)],
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[MediaItem]:
        return media_service.list(limit=limit)

    return router
