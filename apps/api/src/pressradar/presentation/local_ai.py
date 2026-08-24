from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StringConstraints

from pressradar.domain.auth import Identity
from pressradar.infrastructure.ollama_runtime import (
    LicenseDetails,
    LocalAIError,
    LocalAIStatus,
    OllamaRuntime,
)

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
    model: str
    license: LicenseResponse
    recommended_model: str
    recommendation: str


class ModelRequest(BaseModel):
    model: ModelName


class PullModelRequest(ModelRequest):
    accepted_license: str


def create_local_ai_router(
    runtime: OllamaRuntime, current_identity: Callable[..., Identity]
) -> APIRouter:
    router = APIRouter(prefix="/local-ai", tags=["local AI"])

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
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        try:
            return runtime.pull_and_activate(request.model, request.accepted_license)
        except LocalAIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.post("/active", response_model=LocalAIResponse)
    def activate(
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        return runtime.activate()

    @router.delete("/active", response_model=LocalAIResponse)
    def deactivate(
        _identity: Annotated[Identity, Depends(current_identity)],
    ) -> LocalAIStatus:
        return runtime.deactivate()

    return router
