import re
from typing import Protocol

from pressradar.application.clients import ClientRepository
from pressradar.application.media import MediaRepository
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem
from pressradar.domain.opportunities import (
    ALLOWED_TRANSITIONS,
    Opportunity,
    OpportunityMatch,
    OpportunityStatus,
)


class OpportunityNotFoundError(Exception):
    """Raised when an opportunity is not visible in the current workspace."""


class InvalidOpportunityTransitionError(Exception):
    """Raised when an opportunity state transition is not allowed."""


class OpportunityRepository(Protocol):
    def create_matches(self, matches: tuple[OpportunityMatch, ...]) -> int: ...

    def list(self, *, workspace_id: str) -> list[Opportunity]: ...

    def get(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None: ...

    def update_status(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        current_status: OpportunityStatus,
        new_status: OpportunityStatus,
    ) -> Opportunity | None: ...


class OpportunityService:
    def __init__(
        self,
        clients: ClientRepository,
        media: MediaRepository,
        opportunities: OpportunityRepository,
    ) -> None:
        self._clients = clients
        self._media = media
        self._opportunities = opportunities

    def detect(self, *, workspace_id: str) -> int:
        matches = tuple(
            match
            for client in self._clients.list(workspace_id=workspace_id)
            for item in self._media.list(limit=100)
            if (match := _match(client, item)) is not None
        )
        return self._opportunities.create_matches(matches)

    def list(self, *, workspace_id: str) -> list[Opportunity]:
        return self._opportunities.list(workspace_id=workspace_id)

    def transition(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        new_status: OpportunityStatus,
    ) -> Opportunity:
        opportunity = self._opportunities.get(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if opportunity is None:
            raise OpportunityNotFoundError
        if new_status not in ALLOWED_TRANSITIONS[opportunity.status]:
            raise InvalidOpportunityTransitionError
        updated = self._opportunities.update_status(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            current_status=opportunity.status,
            new_status=new_status,
        )
        if updated is None:
            raise InvalidOpportunityTransitionError
        return updated


def _match(client: Client, item: MediaItem) -> OpportunityMatch | None:
    content = " ".join((item.headline, item.body, *item.topics))
    normalized_content = _normalize(content)
    if any(_contains(normalized_content, excluded) for excluded in client.excluded_keywords):
        return None

    primary_terms = (
        *client.monitoring_rules,
        *client.keywords,
        *client.preferred_topics,
        *client.expertise,
    )
    primary_matches = tuple(term for term in primary_terms if _contains(normalized_content, term))
    if not primary_matches:
        return None
    context_terms = tuple(
        term
        for term in (client.location, client.industry)
        if term and _contains(normalized_content, term)
    )
    matched = tuple(dict.fromkeys((*primary_matches, *context_terms)))
    return OpportunityMatch(
        workspace_id=client.workspace_id,
        client_id=client.id,
        media_item_id=item.id,
        matched_topics=matched,
    )


def _contains(normalized_content: str, term: str) -> bool:
    normalized_term = _normalize(term)
    return bool(normalized_term) and f" {normalized_term} " in f" {normalized_content} "


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[\w]+", value.casefold()))
