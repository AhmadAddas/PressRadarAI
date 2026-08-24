from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from pressradar.application.media import (
    InvalidMediaItemError,
    MediaIngestionService,
    MediaItemNotFoundError,
)
from pressradar.application.opportunities import OpportunityService
from pressradar.domain.auth import Identity, WorkspaceKind
from pressradar.domain.media import IngestionResult, MediaItem, MediaSourceType
from pressradar.infrastructure.configured_media import (
    ConfiguredMediaIngestionService,
    MediaSourceConfigurationError,
)


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
    configured_media_service: ConfiguredMediaIngestionService,
    opportunity_service: OpportunityService,
    demo_opportunity_service: OpportunityService,
    current_identity: Callable[..., Identity],
) -> APIRouter:
    router = APIRouter(prefix="/media", tags=["media"])

    @router.post("/ingest", response_model=IngestionResponse)
    def ingest_media(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> IngestionResult:
        try:
            result = (
                media_service.ingest(workspace_id=identity.workspace_id)
                if identity.workspace_kind is WorkspaceKind.DEMO
                else configured_media_service.ingest(workspace_id=identity.workspace_id)
            )
            (
                demo_opportunity_service
                if identity.workspace_kind is WorkspaceKind.DEMO
                else opportunity_service
            ).detect(workspace_id=identity.workspace_id)
            return result
        except MediaSourceConfigurationError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        except InvalidMediaItemError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The media provider returned an invalid item",
            ) from error

    @router.get("", response_model=list[MediaItemResponse])
    def list_media(
        identity: Annotated[Identity, Depends(current_identity)],
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[MediaItem]:
        return media_service.list(workspace_id=identity.workspace_id, limit=limit)

    @router.delete("/{media_item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_media(
        media_item_id: str,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> None:
        try:
            media_service.delete(workspace_id=identity.workspace_id, media_item_id=media_item_id)
        except MediaItemNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
            ) from error

    return router
