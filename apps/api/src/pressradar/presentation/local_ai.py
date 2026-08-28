import json
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pressradar.domain.auth import Identity
from pressradar.infrastructure.ollama_runtime import (
    LicenseDetails,
    LocalAIError,
    LocalAIStatus,
    OllamaRuntime,
)
from pressradar.presentation.rate_limit import InMemoryRateLimiter, request_source

ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class LicenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    summary: str
    source_url: str | None
    known: bool


class LocalAIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    reachable: bool
    model_available: bool
    installed_models: list[str]
    model: str
    analysis_model: str
    analysis_model_available: bool
    translation_model: str
    translation_model_available: bool
    license: LicenseResponse
    recommended_model: str
    recommendation: str


class ModelRequest(BaseModel):
    model: ModelName


class PullModelRequest(ModelRequest):
    accepted_license: str
    activate: bool = True


LanguageCode = Annotated[
    str, StringConstraints(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=6)
]
LanguageName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[A-Za-z][A-Za-z ()-]*$",
        min_length=2,
        max_length=50,
    ),
]
TranslationText = Annotated[str, StringConstraints(min_length=1, max_length=1_000)]


class TranslationRequest(BaseModel):
    language_code: LanguageCode
    language_name: LanguageName
    texts: list[TranslationText] = Field(min_length=1, max_length=100)


class TranslationResponse(BaseModel):
    translations: list[str]


class PublicLocalAIResponse(BaseModel):
    active: bool
    translation_available: bool
    analysis_model: str
    translation_model: str


def create_local_ai_router(
    runtime: OllamaRuntime,
    current_identity: Callable[..., Identity],
    *,
    admin_emails: frozenset[str] = frozenset(),
    rate_limiter: InMemoryRateLimiter | None = None,
    translation_limit: int = 10,
) -> APIRouter:
    router = APIRouter(prefix="/local-ai", tags=["local AI"])
    limiter = rate_limiter or InMemoryRateLimiter()

    def require_operator(identity: Identity) -> None:
        if identity.email.lower() not in admin_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Local AI administration requires operator access",
            )

    @router.get("/public-status", response_model=PublicLocalAIResponse)
    def public_status() -> PublicLocalAIResponse:
        return PublicLocalAIResponse.model_validate(runtime.availability(), from_attributes=True)

    @router.get("", response_model=LocalAIResponse)
    def get_status(
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        return runtime.status()

    @router.post("/license", response_model=LicenseResponse)
    def inspect_license(
        request: ModelRequest,
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> LicenseDetails:
        try:
            return runtime.inspect_license(request.model)
        except LocalAIError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/models", response_model=LocalAIResponse)
    def pull_model(
        request: PullModelRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        require_operator(identity)
        try:
            return runtime.pull_model(
                request.model,
                request.accepted_license,
                activate=request.activate,
            )
        except LocalAIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.post("/models/stream")
    def pull_model_stream(
        request: PullModelRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> StreamingResponse:
        require_operator(identity)
        try:
            model = runtime.validate_pull(request.model, request.accepted_license)
        except LocalAIError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        events = (
            json.dumps(event) + "\n"
            for event in runtime.pull_model_events(model, activate=request.activate)
        )
        return StreamingResponse(events, media_type="application/x-ndjson")

    @router.post("/models/active", response_model=LocalAIResponse)
    def activate_model(
        request: ModelRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        require_operator(identity)
        try:
            return runtime.activate_model(request.model)
        except LocalAIError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.delete("/models", response_model=LocalAIResponse)
    def delete_model(
        model: ModelName,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        require_operator(identity)
        try:
            return runtime.delete_model(model)
        except LocalAIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.post("/active", response_model=LocalAIResponse)
    def activate(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        require_operator(identity)
        try:
            return runtime.activate()
        except LocalAIError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.delete("/active", response_model=LocalAIResponse)
    def deactivate(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        require_operator(identity)
        return runtime.deactivate()

    @router.post("/translate", response_model=TranslationResponse)
    def translate(
        request: TranslationRequest,
        http_request: Request,
    ) -> TranslationResponse:
        limiter.check(
            f"translation:{request_source(http_request)}",
            limit=translation_limit,
            window_seconds=60,
        )
        try:
            translations = runtime.translate(
                texts=tuple(request.texts),
                language_code=request.language_code,
                language_name=request.language_name,
            )
        except LocalAIError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return TranslationResponse(translations=list(translations))

    return router
