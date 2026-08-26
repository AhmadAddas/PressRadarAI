from collections.abc import Callable, Mapping
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, StringConstraints, model_validator

from pressradar.application.media_sources import (
    UAE_SOURCE_SUGGESTIONS,
    DuplicateMediaSourceError,
    MediaSourceNotFoundError,
    MediaSourceService,
)
from pressradar.domain.auth import Identity, WorkspaceKind
from pressradar.domain.media_sources import MediaSource, MediaSourceDetails, MediaSourceKind

SourceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class MediaSourceRequest(BaseModel):
    name: SourceName
    kind: MediaSourceKind
    url: AnyHttpUrl | None = None
    provider: Literal["newsapi", "journalist_requests"] | None = None

    @model_validator(mode="after")
    def validate_configuration(self) -> "MediaSourceRequest":
        if self.kind is MediaSourceKind.RSS:
            if self.url is None or self.url.scheme != "https":
                raise ValueError("RSS sources require an HTTPS URL")
            if self.provider not in {None, "journalist_requests"}:
                raise ValueError("RSS sources only support journalist-request feed mode")
        elif self.provider != "newsapi" or self.url is not None:
            raise ValueError("API sources require the NewsAPI provider and no custom URL")
        return self

    def details(self) -> MediaSourceDetails:
        return MediaSourceDetails(
            name=self.name,
            kind=self.kind,
            url=None if self.url is None else str(self.url),
            provider=self.provider,
        )


class MediaSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    kind: MediaSourceKind
    url: str | None
    provider: str | None


class MediaSourceSuggestion(BaseModel):
    name: str
    kind: MediaSourceKind
    url: str | None
    provider: str | None


def create_media_sources_router(
    sources: MediaSourceService, current_identity: Callable[..., Identity]
) -> APIRouter:
    router = APIRouter(prefix="/media/sources", tags=["media sources"])

    @router.post("", response_model=MediaSourceResponse, status_code=status.HTTP_201_CREATED)
    def create_source(
        request: MediaSourceRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> MediaSource:
        _require_prod(identity)
        try:
            return sources.create(workspace_id=identity.workspace_id, details=request.details())
        except DuplicateMediaSourceError as error:
            raise HTTPException(
                status_code=409, detail="Media source name already exists"
            ) from error

    @router.get("", response_model=list[MediaSourceResponse])
    def list_sources(
        identity: Annotated[Identity, Depends(current_identity)],
        kind: Annotated[MediaSourceKind | None, Query()] = None,
    ) -> list[MediaSource]:
        _require_prod(identity)
        return sources.list(workspace_id=identity.workspace_id, kind=kind)

    @router.get("/suggestions", response_model=list[MediaSourceSuggestion])
    def suggestions(
        identity: Annotated[Identity, Depends(current_identity)],
        kind: Annotated[MediaSourceKind | None, Query()] = None,
    ) -> list[MediaSourceSuggestion]:
        _require_prod(identity)
        configured = sources.list(workspace_id=identity.workspace_id, kind=None)
        return [
            MediaSourceSuggestion.model_validate(item)
            for item in UAE_SOURCE_SUGGESTIONS
            if (kind is None or item["kind"] == kind)
            and not _is_configured_suggestion(item, configured)
        ]

    @router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_source(
        source_id: str, identity: Annotated[Identity, Depends(current_identity)]
    ) -> None:
        _require_prod(identity)
        try:
            sources.delete(workspace_id=identity.workspace_id, source_id=source_id)
        except MediaSourceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Media source not found") from error

    return router


def _is_configured_suggestion(
    suggestion: Mapping[str, object], configured: list[MediaSource]
) -> bool:
    return any(
        source.kind == suggestion["kind"]
        and (
            source.provider == suggestion["provider"]
            if source.kind is MediaSourceKind.API
            else source.url == suggestion["url"]
        )
        for source in configured
    )


def _require_prod(identity: Identity) -> None:
    if identity.workspace_kind is not WorkspaceKind.PROD:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media sources are managed in the Prod workspace",
        )
