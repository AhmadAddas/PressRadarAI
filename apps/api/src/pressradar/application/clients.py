from typing import Protocol

from pressradar.domain.clients import Client, ClientDetails


class ClientNotFoundError(Exception):
    """Raised when a client is not visible in the current workspace."""


class ClientRepository(Protocol):
    def create(self, *, workspace_id: str, details: ClientDetails) -> Client: ...

    def list(self, *, workspace_id: str) -> list[Client]: ...

    def get(self, *, workspace_id: str, client_id: str) -> Client | None: ...

    def update(
        self, *, workspace_id: str, client_id: str, details: ClientDetails
    ) -> Client | None: ...

    def delete(self, *, workspace_id: str, client_id: str) -> bool: ...


class ClientService:
    def __init__(self, repository: ClientRepository) -> None:
        self._repository = repository

    def create(self, *, workspace_id: str, details: ClientDetails) -> Client:
        return self._repository.create(workspace_id=workspace_id, details=details)

    def list(self, *, workspace_id: str) -> list[Client]:
        return self._repository.list(workspace_id=workspace_id)

    def get(self, *, workspace_id: str, client_id: str) -> Client:
        client = self._repository.get(workspace_id=workspace_id, client_id=client_id)
        if client is None:
            raise ClientNotFoundError
        return client

    def update(self, *, workspace_id: str, client_id: str, details: ClientDetails) -> Client:
        client = self._repository.update(
            workspace_id=workspace_id, client_id=client_id, details=details
        )
        if client is None:
            raise ClientNotFoundError
        return client

    def delete(self, *, workspace_id: str, client_id: str) -> None:
        if not self._repository.delete(workspace_id=workspace_id, client_id=client_id):
            raise ClientNotFoundError
