from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from pressradar.application.demo import DemoSetupResult, DemoSetupService
from pressradar.domain.auth import Identity


class DemoSetupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clients_created: int
    media_created: int
    opportunities_created: int


def create_demo_router(
    demo_service: DemoSetupService, current_identity: Callable[..., Identity]
) -> APIRouter:
    router = APIRouter(prefix="/demo", tags=["demo"])

    @router.post("/setup", response_model=DemoSetupResponse)
    def setup_demo(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> DemoSetupResult:
        return demo_service.setup(workspace_id=identity.workspace_id)

    return router
