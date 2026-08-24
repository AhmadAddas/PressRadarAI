from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from pressradar.application.clients import ClientNotFoundError, ClientService
from pressradar.domain.auth import Identity
from pressradar.domain.clients import Client, ClientDetails

RequiredText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
ListItem = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ClientRequest(BaseModel):
    name: RequiredText
    company: str | None = Field(default=None, max_length=200)
    website: AnyHttpUrl | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    industry: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    expertise: list[ListItem] = Field(default_factory=list, max_length=50)
    spokesperson_name: str | None = Field(default=None, max_length=200)
    spokesperson_title: str | None = Field(default=None, max_length=200)
    keywords: list[ListItem] = Field(default_factory=list, max_length=50)
    excluded_keywords: list[ListItem] = Field(default_factory=list, max_length=50)
    preferred_topics: list[ListItem] = Field(default_factory=list, max_length=50)
    tone: str | None = Field(default=None, max_length=200)
    monitoring_rules: list[ListItem] = Field(default_factory=list, max_length=25)

    @field_validator(
        "industry",
        "company",
        "description",
        "location",
        "spokesperson_name",
        "spokesperson_title",
        "tone",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def details(self) -> ClientDetails:
        return ClientDetails(
            name=self.name,
            company=self.company or "",
            website=None if self.website is None else str(self.website),
            industry=self.industry,
            description=self.description,
            location=self.location,
            expertise=_unique(self.expertise),
            spokesperson_name=self.spokesperson_name,
            spokesperson_title=self.spokesperson_title,
            keywords=_unique(self.keywords),
            excluded_keywords=_unique(self.excluded_keywords),
            preferred_topics=_unique(self.preferred_topics),
            tone=self.tone,
            monitoring_rules=_unique(self.monitoring_rules),
            email=None if self.email is None else str(self.email),
            phone=self.phone,
        )


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    company: str
    website: str | None
    email: str | None
    phone: str | None
    industry: str | None
    description: str | None
    location: str | None
    expertise: tuple[str, ...]
    spokesperson_name: str | None
    spokesperson_title: str | None
    keywords: tuple[str, ...]
    excluded_keywords: tuple[str, ...]
    preferred_topics: tuple[str, ...]
    tone: str | None
    monitoring_rules: tuple[str, ...]


def create_clients_router(
    client_service: ClientService, current_identity: Callable[..., Identity]
) -> APIRouter:
    router = APIRouter(prefix="/clients", tags=["clients"])

    @router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
    def create_client(
        request: ClientRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Client:
        return client_service.create(workspace_id=identity.workspace_id, details=request.details())

    @router.get("", response_model=list[ClientResponse])
    def list_clients(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> list[Client]:
        return client_service.list(workspace_id=identity.workspace_id)

    @router.get("/{client_id}", response_model=ClientResponse)
    def get_client(
        client_id: str,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Client:
        return _get_client(client_service, identity.workspace_id, client_id)

    @router.put("/{client_id}", response_model=ClientResponse)
    def update_client(
        client_id: str,
        request: ClientRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Client:
        try:
            return client_service.update(
                workspace_id=identity.workspace_id,
                client_id=client_id,
                details=request.details(),
            )
        except ClientNotFoundError as error:
            raise _not_found() from error

    @router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_client(
        client_id: str,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> None:
        try:
            client_service.delete(workspace_id=identity.workspace_id, client_id=client_id)
        except ClientNotFoundError as error:
            raise _not_found() from error

    return router


def _get_client(client_service: ClientService, workspace_id: str, client_id: str) -> Client:
    try:
        return client_service.get(workspace_id=workspace_id, client_id=client_id)
    except ClientNotFoundError as error:
        raise _not_found() from error


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


def _unique(values: list[str]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return tuple(unique)
