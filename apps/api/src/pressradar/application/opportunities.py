import builtins
import re
from datetime import UTC, datetime
from typing import Protocol

from pressradar.application.analytics import AnalyticsService
from pressradar.application.clients import ClientRepository
from pressradar.application.delivery import PitchSender, PitchSendError
from pressradar.application.integrations import (
    CRMIntegration,
    CRMSyncError,
    NotificationError,
    NotificationSender,
    OpportunityAlert,
    SentOpportunityActivity,
)
from pressradar.application.media import MediaRepository
from pressradar.application.pitches import (
    PitchGenerationError,
    PitchGenerator,
    validate_generated_pitch,
)
from pressradar.application.relevance import RelevanceAnalysisError, RelevanceAnalyzer
from pressradar.domain.analytics import ProductEvent, ProductEventName
from pressradar.domain.audit import AuditEvent
from pressradar.domain.clients import Client
from pressradar.domain.delivery import DeliveryReceipt, DeliveryRequest
from pressradar.domain.media import MediaItem
from pressradar.domain.opportunities import (
    ALLOWED_TRANSITIONS,
    Opportunity,
    OpportunityMatch,
    OpportunityStatus,
)
from pressradar.domain.pitches import GeneratedPitch
from pressradar.domain.relevance import RelevanceAnalysis


class OpportunityNotFoundError(Exception):
    """Raised when an opportunity is not visible in the current workspace."""


class InvalidOpportunityTransitionError(Exception):
    """Raised when an opportunity state transition is not allowed."""


class PitchNotEditableError(Exception):
    """Raised when an opportunity cannot accept pitch edits in its current state."""


class PitchApprovalError(Exception):
    """Raised when an opportunity does not contain an approvable pitch."""


class PitchDeliveryError(Exception):
    """Raised when an approved pitch could not be delivered."""


HIGH_PRIORITY_RELEVANCE_SCORE = 90


class OpportunityRepository(Protocol):
    def create_matches(self, matches: tuple[OpportunityMatch, ...]) -> int: ...

    def list(self, *, workspace_id: str) -> list[Opportunity]: ...

    def get(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None: ...

    def delete(self, *, workspace_id: str, opportunity_id: str) -> bool: ...

    def clear(self, *, workspace_id: str) -> None: ...

    def update_status(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        current_status: OpportunityStatus,
        new_status: OpportunityStatus,
    ) -> Opportunity | None: ...

    def complete_analysis(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        analysis: RelevanceAnalysis,
    ) -> Opportunity | None: ...

    def fail_analysis(self, *, workspace_id: str, opportunity_id: str) -> None: ...

    def save_generated_pitch(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        pitch: GeneratedPitch,
    ) -> Opportunity | None: ...

    def fail_pitch_generation(self, *, workspace_id: str, opportunity_id: str) -> None: ...

    def update_pitch(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        content: str,
    ) -> Opportunity | None: ...

    def approve(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None: ...

    def claim_send(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None: ...

    def complete_send(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        receipt: DeliveryReceipt,
    ) -> Opportunity | None: ...

    def fail_send(self, *, workspace_id: str, opportunity_id: str) -> None: ...

    def list_audit(
        self, *, workspace_id: str, opportunity_id: str
    ) -> builtins.list[AuditEvent]: ...

    def record_integration_failure(
        self, *, workspace_id: str, opportunity_id: str, detail: str
    ) -> None: ...


class OpportunityService:
    def __init__(
        self,
        clients: ClientRepository,
        media: MediaRepository,
        opportunities: OpportunityRepository,
        relevance_analyzer: RelevanceAnalyzer,
        pitch_generator: PitchGenerator,
        pitch_sender: PitchSender,
        notification_sender: NotificationSender,
        crm_integration: CRMIntegration,
        analytics: AnalyticsService,
    ) -> None:
        self._clients = clients
        self._media = media
        self._opportunities = opportunities
        self._relevance_analyzer = relevance_analyzer
        self._pitch_generator = pitch_generator
        self._pitch_sender = pitch_sender
        self._notification_sender = notification_sender
        self._crm_integration = crm_integration
        self._analytics = analytics

    def detect(self, *, workspace_id: str) -> int:
        matches = tuple(
            match
            for client in self._clients.list(workspace_id=workspace_id)
            for item in self._media.list(workspace_id=workspace_id, limit=100)
            if (match := _match(client, item)) is not None
        )
        created = self._opportunities.create_matches(matches)
        for opportunity in self._opportunities.list(workspace_id=workspace_id):
            self._track(
                ProductEventName.OPPORTUNITY_DETECTED,
                opportunity,
                occurred_at=opportunity.detected_at,
            )
        self.analyze_pending(workspace_id=workspace_id)
        return created

    def analyze_pending(self, *, workspace_id: str) -> None:
        pending = tuple(
            opportunity
            for opportunity in self._opportunities.list(workspace_id=workspace_id)
            if opportunity.status is OpportunityStatus.NEW
        )
        for opportunity in pending:
            claimed = self._opportunities.update_status(
                workspace_id=workspace_id,
                opportunity_id=opportunity.id,
                current_status=OpportunityStatus.NEW,
                new_status=OpportunityStatus.ANALYZING,
            )
            if claimed is None:
                continue
            client = self._clients.get(workspace_id=workspace_id, client_id=opportunity.client_id)
            media_item = self._media.get(
                workspace_id=workspace_id, media_item_id=opportunity.media_item_id
            )
            if client is None or media_item is None:
                self._opportunities.fail_analysis(
                    workspace_id=workspace_id, opportunity_id=opportunity.id
                )
                continue
            try:
                analysis = self._relevance_analyzer.analyze(
                    client=client,
                    media_item=media_item,
                    matched_topics=opportunity.matched_topics,
                )
                _validate_grounded_topics(analysis, client, media_item)
            except RelevanceAnalysisError:
                self._opportunities.fail_analysis(
                    workspace_id=workspace_id, opportunity_id=opportunity.id
                )
                continue
            ready = self._opportunities.complete_analysis(
                workspace_id=workspace_id,
                opportunity_id=opportunity.id,
                analysis=analysis,
            )
            if ready is not None:
                self._track(ProductEventName.ANALYSIS_COMPLETED, ready)
                self._notify_if_urgent(ready, recipient_phone=client.phone)
                self._generate_pitch(client=client, media_item=media_item, opportunity=ready)

    def list(self, *, workspace_id: str) -> list[Opportunity]:
        return self._opportunities.list(workspace_id=workspace_id)

    def delete(self, *, workspace_id: str, opportunity_id: str) -> None:
        if not self._opportunities.delete(workspace_id=workspace_id, opportunity_id=opportunity_id):
            raise OpportunityNotFoundError

    def clear(self, *, workspace_id: str) -> None:
        self._opportunities.clear(workspace_id=workspace_id)

    def update_pitch(self, *, workspace_id: str, opportunity_id: str, content: str) -> Opportunity:
        pitch = GeneratedPitch(content=content.strip())
        opportunity = self._opportunities.get(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if opportunity is None:
            raise OpportunityNotFoundError
        if opportunity.status is not OpportunityStatus.READY:
            raise PitchNotEditableError
        updated = self._opportunities.update_pitch(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            content=pitch.content,
        )
        if updated is None:
            raise PitchNotEditableError
        self._track(ProductEventName.PITCH_REVIEWED, updated)
        return updated

    def approve(self, *, workspace_id: str, opportunity_id: str) -> Opportunity:
        opportunity = self._get(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if opportunity.status is OpportunityStatus.APPROVED:
            return opportunity
        if opportunity.status is not OpportunityStatus.READY or opportunity.pitch is None:
            raise PitchApprovalError
        approved = self._opportunities.approve(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if approved is None:
            raise PitchApprovalError
        self._track(ProductEventName.PITCH_APPROVED, approved)
        return approved

    def send(self, *, workspace_id: str, opportunity_id: str) -> Opportunity:
        opportunity = self._get(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if opportunity.status is OpportunityStatus.SENT:
            return opportunity
        if opportunity.status is not OpportunityStatus.APPROVED or opportunity.pitch is None:
            raise PitchApprovalError
        client = self._clients.get(workspace_id=workspace_id, client_id=opportunity.client_id)
        claimed = self._opportunities.claim_send(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if claimed is None:
            raise PitchApprovalError
        try:
            receipt = self._pitch_sender.send(
                DeliveryRequest(
                    opportunity_id=opportunity.id,
                    recipient=(
                        client.email
                        if client is not None and client.email
                        else opportunity.journalist or opportunity.source
                    ),
                    content=opportunity.pitch.content,
                )
            )
        except PitchSendError as error:
            self._opportunities.fail_send(workspace_id=workspace_id, opportunity_id=opportunity_id)
            raise PitchDeliveryError from error
        sent = self._opportunities.complete_send(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            receipt=receipt,
        )
        if sent is None:
            raise PitchDeliveryError
        self._track(ProductEventName.PITCH_SENT, sent)
        self._sync_sent_opportunity(sent)
        return sent

    def list_audit(self, *, workspace_id: str, opportunity_id: str) -> builtins.list[AuditEvent]:
        self._get(workspace_id=workspace_id, opportunity_id=opportunity_id)
        return self._opportunities.list_audit(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )

    def _generate_pitch(
        self, *, client: Client, media_item: MediaItem, opportunity: Opportunity
    ) -> None:
        try:
            pitch = validate_generated_pitch(
                self._pitch_generator.generate(client=client, media_item=media_item),
                client=client,
                media_item=media_item,
            )
        except PitchGenerationError:
            self._opportunities.fail_pitch_generation(
                workspace_id=opportunity.workspace_id,
                opportunity_id=opportunity.id,
            )
            return
        self._opportunities.save_generated_pitch(
            workspace_id=opportunity.workspace_id,
            opportunity_id=opportunity.id,
            pitch=pitch,
        )

    def _notify_if_urgent(self, opportunity: Opportunity, *, recipient_phone: str | None) -> None:
        if (
            recipient_phone is None
            or not recipient_phone.strip()
            or opportunity.deadline is None
            or opportunity.relevance_score is None
            or opportunity.relevance_score < HIGH_PRIORITY_RELEVANCE_SCORE
        ):
            return
        try:
            self._notification_sender.send(
                OpportunityAlert(
                    opportunity_id=opportunity.id,
                    client_company=opportunity.client_company,
                    recipient_phone=recipient_phone,
                    relevance_score=opportunity.relevance_score,
                    deadline=opportunity.deadline,
                )
            )
        except NotificationError:
            self._opportunities.record_integration_failure(
                workspace_id=opportunity.workspace_id,
                opportunity_id=opportunity.id,
                detail="Notification delivery failed",
            )

    def _sync_sent_opportunity(self, opportunity: Opportunity) -> None:
        if opportunity.delivery is None:
            return
        try:
            self._crm_integration.record_sent(
                SentOpportunityActivity(
                    opportunity_id=opportunity.id,
                    client_name=opportunity.client_name,
                    client_company=opportunity.client_company,
                    headline=opportunity.headline,
                    sent_at=opportunity.delivery.sent_at,
                )
            )
        except CRMSyncError:
            self._opportunities.record_integration_failure(
                workspace_id=opportunity.workspace_id,
                opportunity_id=opportunity.id,
                detail="CRM synchronization failed",
            )

    def _track(
        self,
        name: ProductEventName,
        opportunity: Opportunity,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        self._analytics.track(
            ProductEvent(
                id=f"{opportunity.id}:{name.value}",
                workspace_id=opportunity.workspace_id,
                name=name,
                occurred_at=occurred_at or datetime.now(UTC),
                opportunity_id=opportunity.id,
                client_id=opportunity.client_id,
                client_name=opportunity.client_name,
                source=opportunity.source,
                relevance_score=opportunity.relevance_score,
                detected_at=opportunity.detected_at,
            )
        )

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
        if (
            new_status is not OpportunityStatus.DISMISSED
            or new_status not in ALLOWED_TRANSITIONS[opportunity.status]
        ):
            raise InvalidOpportunityTransitionError
        updated = self._opportunities.update_status(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            current_status=opportunity.status,
            new_status=new_status,
        )
        if updated is None:
            raise InvalidOpportunityTransitionError
        self._track(ProductEventName.OPPORTUNITY_DISMISSED, updated)
        return updated

    def _get(self, *, workspace_id: str, opportunity_id: str) -> Opportunity:
        opportunity = self._opportunities.get(
            workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if opportunity is None:
            raise OpportunityNotFoundError
        return opportunity


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


def _validate_grounded_topics(
    analysis: RelevanceAnalysis, client: Client, media_item: MediaItem
) -> None:
    known_topics = {
        _normalize(topic)
        for topic in (
            *client.monitoring_rules,
            *client.keywords,
            *client.preferred_topics,
            *client.expertise,
            *media_item.topics,
            *((client.location,) if client.location else ()),
            *((client.industry,) if client.industry else ()),
        )
    }
    if any(_normalize(topic) not in known_topics for topic in analysis.matched_topics):
        raise RelevanceAnalysisError("Relevance analysis returned an ungrounded topic")
