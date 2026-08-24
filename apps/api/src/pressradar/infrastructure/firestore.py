import builtins
import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from google.api_core.exceptions import AlreadyExists, GoogleAPICallError
from google.cloud import firestore

from pressradar.application.auth import DuplicateEmailError
from pressradar.application.media import MediaIngestionService
from pressradar.application.media_sources import DuplicateMediaSourceError, MediaSourceRepository
from pressradar.domain.audit import AuditAction, AuditEvent
from pressradar.domain.auth import Identity, WorkspaceKind
from pressradar.domain.clients import Client, ClientDetails
from pressradar.domain.delivery import Delivery, DeliveryReceipt
from pressradar.domain.media import IncomingMediaItem, IngestionResult, MediaItem, MediaSourceType
from pressradar.domain.media_sources import MediaSource, MediaSourceDetails, MediaSourceKind
from pressradar.domain.opportunities import Opportunity, OpportunityMatch, OpportunityStatus
from pressradar.domain.pitches import GeneratedPitch, Pitch
from pressradar.domain.relevance import RelevanceAnalysis


class FirestoreRepository:
    """Firestore adapter for the MVP operational repository boundaries."""

    def __init__(self, *, project: str, database: str = "(default)") -> None:
        self._db = firestore.Client(project=project, database=database)

    def create_identity(self, *, email: str, name: str, password_hash: str) -> Identity:
        user_id, workspace_id, demo_workspace_id = str(uuid4()), str(uuid4()), str(uuid4())
        email_ref = self._db.collection("user_emails").document(_key(email))
        transaction = self._db.transaction()
        try:
            if email_ref.get(transaction=transaction).exists:
                raise DuplicateEmailError
            transaction.create(
                self._db.collection("workspaces").document(workspace_id),
                {"name": f"{name}'s Prod workspace", "kind": WorkspaceKind.PROD.value},
            )
            transaction.create(
                self._db.collection("workspaces").document(demo_workspace_id),
                {"name": f"{name}'s Demo workspace", "kind": WorkspaceKind.DEMO.value},
            )
            transaction.create(
                self._db.collection("users").document(user_id),
                {
                    "workspace_id": workspace_id,
                    "demo_workspace_id": demo_workspace_id,
                    "email": email,
                    "name": name,
                    "password_hash": password_hash,
                },
            )
            transaction.create(email_ref, {"user_id": user_id})
            transaction.commit()
        except AlreadyExists as error:
            raise DuplicateEmailError from error
        return Identity(user_id=user_id, workspace_id=workspace_id, email=email, name=name)

    def find_credentials(self, email: str) -> tuple[Identity, str] | None:
        email_doc = self._db.collection("user_emails").document(_key(email)).get()
        if not email_doc.exists:
            return None
        user_doc = self._db.collection("users").document(str(email_doc.get("user_id"))).get()
        if not user_doc.exists:
            return None
        data = _data(user_doc)
        return _identity(user_doc.id, data), str(data["password_hash"])

    def create_session(self, *, token_hash: str, user_id: str, expires_at: datetime) -> None:
        self._db.collection("sessions").document(token_hash).create(
            {"user_id": user_id, "expires_at": expires_at}
        )

    def find_identity_by_session(
        self, *, token_hash: str, now: datetime, workspace_kind: WorkspaceKind
    ) -> Identity | None:
        session = self._db.collection("sessions").document(token_hash).get()
        if not session.exists or _datetime(session.get("expires_at")) <= now:
            return None
        user = self._db.collection("users").document(str(session.get("user_id"))).get()
        if not user.exists:
            return None
        data = _data(user)
        workspace_id = str(data["workspace_id"])
        if workspace_kind is WorkspaceKind.DEMO:
            workspace_id = str(data.get("demo_workspace_id") or f"{user.id}-demo")
            if "demo_workspace_id" not in data:
                self._db.collection("workspaces").document(workspace_id).set(
                    {"name": f"{data['name']}'s Demo workspace", "kind": "demo"}
                )
                user.reference.update({"demo_workspace_id": workspace_id})
        return _identity(user.id, data, workspace_id=workspace_id, workspace_kind=workspace_kind)

    def delete_session(self, token_hash: str) -> None:
        self._db.collection("sessions").document(token_hash).delete()

    def create(self, *, workspace_id: str, details: ClientDetails) -> Client:
        client_id = str(uuid4())
        self._db.collection("clients").document(client_id).create(
            {"workspace_id": workspace_id, **_client_details(details)}
        )
        return _client(client_id, {"workspace_id": workspace_id, **_client_details(details)})

    def list_clients(self, *, workspace_id: str) -> list[Client]:
        clients = [
            _client(document.id, _data(document))
            for document in self._db.collection("clients")
            .where("workspace_id", "==", workspace_id)
            .stream()
            if document.get("deleted_at") is None
        ]
        return sorted(clients, key=lambda item: (item.name.casefold(), item.id))

    def get_client(self, *, workspace_id: str, client_id: str) -> Client | None:
        document = self._db.collection("clients").document(client_id).get()
        if (
            not document.exists
            or document.get("workspace_id") != workspace_id
            or document.get("deleted_at") is not None
        ):
            return None
        return _client(document.id, _data(document))

    def update_client(
        self, *, workspace_id: str, client_id: str, details: ClientDetails
    ) -> Client | None:
        reference = self._db.collection("clients").document(client_id)
        document = reference.get()
        if (
            not document.exists
            or document.get("workspace_id") != workspace_id
            or document.get("deleted_at") is not None
        ):
            return None
        reference.update(_client_details(details))
        return _client(client_id, {"workspace_id": workspace_id, **_client_details(details)})

    def delete_client(self, *, workspace_id: str, client_id: str) -> bool:
        reference = self._db.collection("clients").document(client_id)
        document = reference.get()
        if (
            not document.exists
            or document.get("workspace_id") != workspace_id
            or document.get("deleted_at") is not None
        ):
            return False
        reference.update({"deleted_at": datetime.now(UTC)})
        return True

    def create_media_source(self, *, workspace_id: str, details: MediaSourceDetails) -> MediaSource:
        source_id = _key(f"{workspace_id}:{details.name.casefold()}")
        data = {"workspace_id": workspace_id, **vars(details), "kind": details.kind.value}
        try:
            self._db.collection("media_sources").document(source_id).create(data)
        except AlreadyExists as error:
            raise DuplicateMediaSourceError from error
        return _media_source(source_id, data)

    def list_media_sources(
        self, *, workspace_id: str, kind: MediaSourceKind | None
    ) -> list[MediaSource]:
        query = self._db.collection("media_sources").where("workspace_id", "==", workspace_id)
        if kind is not None:
            query = query.where("kind", "==", kind.value)
        sources = [_media_source(item.id, _data(item)) for item in query.stream()]
        return sorted(sources, key=lambda item: (item.name.casefold(), item.id))

    def delete_media_source(self, *, workspace_id: str, source_id: str) -> bool:
        reference = self._db.collection("media_sources").document(source_id)
        document = reference.get()
        if not document.exists or document.get("workspace_id") != workspace_id:
            return False
        reference.delete()
        return True

    def ingest(self, *, workspace_id: str, items: tuple[IncomingMediaItem, ...]) -> IngestionResult:
        created = 0
        for item in items:
            dedupe_key = MediaIngestionService.dedupe_key(item)
            reference = self._db.collection("media_items").document(
                _key(f"{workspace_id}:{dedupe_key}")
            )
            try:
                reference.create(
                    {
                        "workspace_id": workspace_id,
                        "source": item.source,
                        "source_type": item.source_type.value,
                        "author": item.author,
                        "journalist": item.journalist,
                        "headline": item.headline,
                        "body": item.body,
                        "url": item.url,
                        "published_at": item.published_at,
                        "deadline": item.deadline,
                        "topics": list(item.topics),
                        "external_id": item.external_id,
                        "ingested_at": datetime.now(UTC),
                    }
                )
                created += 1
            except AlreadyExists:
                pass
        return IngestionResult(created=created, duplicates=len(items) - created)

    def list_media(self, *, workspace_id: str, limit: int) -> list[MediaItem]:
        items = [
            _media(document.id, _data(document))
            for document in self._db.collection("media_items")
            .where("workspace_id", "==", workspace_id)
            .stream()
            if document.get("deleted_at") is None
        ]
        return sorted(items, key=lambda item: (item.published_at, item.id), reverse=True)[:limit]

    def get_media(self, *, workspace_id: str, media_item_id: str) -> MediaItem | None:
        document = self._db.collection("media_items").document(media_item_id).get()
        if (
            not document.exists
            or document.get("workspace_id") != workspace_id
            or document.get("deleted_at") is not None
        ):
            return None
        return _media(document.id, _data(document))

    def delete_media(self, *, workspace_id: str, media_item_id: str) -> bool:
        reference = self._db.collection("media_items").document(media_item_id)
        document = reference.get()
        if (
            not document.exists
            or document.get("workspace_id") != workspace_id
            or document.get("deleted_at") is not None
        ):
            return False
        reference.update({"deleted_at": datetime.now(UTC)})
        return True

    def clear_media(self, *, workspace_id: str) -> None:
        for document in (
            self._db.collection("media_items").where("workspace_id", "==", workspace_id).stream()
        ):
            document.reference.delete()

    def create_matches(self, matches: tuple[OpportunityMatch, ...]) -> int:
        created = 0
        for match in matches:
            client = self.get_client(workspace_id=match.workspace_id, client_id=match.client_id)
            media = self.get_media(
                workspace_id=match.workspace_id, media_item_id=match.media_item_id
            )
            if client is None or media is None:
                continue
            opportunity_id = _key(f"{match.client_id}:{match.media_item_id}")
            detected_at = datetime.now(UTC)
            try:
                self._db.collection("opportunities").document(opportunity_id).create(
                    {
                        "workspace_id": match.workspace_id,
                        "client_id": client.id,
                        "client_name": client.name,
                        "client_company": client.company,
                        "media_item_id": media.id,
                        "source": media.source,
                        "headline": media.headline,
                        "journalist": media.journalist,
                        "published_at": media.published_at,
                        "deadline": media.deadline,
                        "matched_topics": list(match.matched_topics),
                        "relevance_score": None,
                        "relevance_reason": None,
                        "analysis_error": None,
                        "pitch": None,
                        "pitch_error": None,
                        "delivery": None,
                        "send_error": None,
                        "status": OpportunityStatus.NEW.value,
                        "detected_at": detected_at,
                    }
                )
                self._audit(match.workspace_id, opportunity_id, AuditAction.OPPORTUNITY_DETECTED)
                created += 1
            except AlreadyExists:
                pass
        return created

    def list_opportunities(self, *, workspace_id: str) -> list[Opportunity]:
        items = [
            self._with_orphan_flags(_opportunity(document.id, _data(document)))
            for document in self._db.collection("opportunities")
            .where("workspace_id", "==", workspace_id)
            .stream()
        ]
        return sorted(
            items,
            key=lambda item: (
                item.deadline is None,
                item.deadline or datetime.max.replace(tzinfo=UTC),
                -(item.relevance_score or -1),
                -item.detected_at.timestamp(),
                item.id,
            ),
        )

    def get_opportunity(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        document = self._db.collection("opportunities").document(opportunity_id).get()
        if not document.exists or document.get("workspace_id") != workspace_id:
            return None
        return self._with_orphan_flags(_opportunity(document.id, _data(document)))

    def delete_opportunity(self, *, workspace_id: str, opportunity_id: str) -> bool:
        reference = self._db.collection("opportunities").document(opportunity_id)
        document = reference.get()
        if not document.exists or document.get("workspace_id") != workspace_id:
            return False
        for event in reference.collection("audit_events").stream():
            event.reference.delete()
        reference.delete()
        return True

    def clear_opportunities(self, *, workspace_id: str) -> None:
        documents = (
            self._db.collection("opportunities").where("workspace_id", "==", workspace_id).stream()
        )
        for document in documents:
            self.delete_opportunity(workspace_id=workspace_id, opportunity_id=document.id)

    def _with_orphan_flags(self, opportunity: Opportunity) -> Opportunity:
        return replace(
            opportunity,
            client_deleted=self.get_client(
                workspace_id=opportunity.workspace_id, client_id=opportunity.client_id
            )
            is None,
            media_deleted=self.get_media(
                workspace_id=opportunity.workspace_id,
                media_item_id=opportunity.media_item_id,
            )
            is None,
        )

    def update_status(
        self,
        *,
        workspace_id: str,
        opportunity_id: str,
        current_status: OpportunityStatus,
        new_status: OpportunityStatus,
    ) -> Opportunity | None:
        updated = self._conditional_update(
            workspace_id, opportunity_id, current_status, {"status": new_status.value}
        )
        action = {
            OpportunityStatus.ANALYZING: AuditAction.ANALYSIS_STARTED,
            OpportunityStatus.DISMISSED: AuditAction.OPPORTUNITY_DISMISSED,
        }.get(new_status)
        if updated and action:
            self._audit(workspace_id, opportunity_id, action)
        return (
            self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
            if updated
            else None
        )

    def complete_analysis(
        self, *, workspace_id: str, opportunity_id: str, analysis: RelevanceAnalysis
    ) -> Opportunity | None:
        updated = self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.ANALYZING,
            {
                "relevance_score": analysis.score,
                "relevance_reason": analysis.reason,
                "matched_topics": list(analysis.matched_topics),
                "analysis_error": None,
                "status": OpportunityStatus.READY.value,
            },
        )
        if updated:
            self._audit(workspace_id, opportunity_id, AuditAction.ANALYSIS_COMPLETED)
        return (
            self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
            if updated
            else None
        )

    def fail_analysis(self, *, workspace_id: str, opportunity_id: str) -> None:
        if self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.ANALYZING,
            {
                "status": OpportunityStatus.FAILED.value,
                "analysis_error": "Relevance analysis is temporarily unavailable.",
            },
        ):
            self._audit(
                workspace_id,
                opportunity_id,
                AuditAction.PROCESSING_FAILED,
                "Relevance analysis failed",
            )

    def save_generated_pitch(
        self, *, workspace_id: str, opportunity_id: str, pitch: GeneratedPitch
    ) -> Opportunity | None:
        current = self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if current is None or current.status is not OpportunityStatus.READY or current.pitch:
            return None
        now = datetime.now(UTC)
        self._db.collection("opportunities").document(opportunity_id).update(
            {
                "pitch": {
                    "id": str(uuid4()),
                    "content": pitch.content,
                    "generated_at": now,
                    "updated_at": now,
                }
            }
        )
        self._audit(workspace_id, opportunity_id, AuditAction.PITCH_GENERATED)
        return self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def fail_pitch_generation(self, *, workspace_id: str, opportunity_id: str) -> None:
        current = self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if current and current.status is OpportunityStatus.READY and current.pitch is None:
            self._db.collection("opportunities").document(opportunity_id).update(
                {"pitch_error": "Pitch generation is temporarily unavailable."}
            )
            self._audit(
                workspace_id,
                opportunity_id,
                AuditAction.PROCESSING_FAILED,
                "Pitch generation failed",
            )

    def update_pitch(
        self, *, workspace_id: str, opportunity_id: str, content: str
    ) -> Opportunity | None:
        current = self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if current is None or current.status is not OpportunityStatus.READY:
            return None
        now = datetime.now(UTC)
        generated_at = current.pitch.generated_at if current.pitch else now
        pitch_id = current.pitch.id if current.pitch else str(uuid4())
        self._db.collection("opportunities").document(opportunity_id).update(
            {
                "pitch": {
                    "id": pitch_id,
                    "content": content,
                    "generated_at": generated_at,
                    "updated_at": now,
                },
                "pitch_error": None,
            }
        )
        self._audit(workspace_id, opportunity_id, AuditAction.PITCH_EDITED)
        return self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)

    def approve(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        current = self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if current is None or current.pitch is None:
            return None
        updated = self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.READY,
            {"status": OpportunityStatus.APPROVED.value},
        )
        if updated:
            self._audit(workspace_id, opportunity_id, AuditAction.PITCH_APPROVED)
        return (
            self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
            if updated
            else None
        )

    def claim_send(self, *, workspace_id: str, opportunity_id: str) -> Opportunity | None:
        current = self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
        if current is None or current.pitch is None or current.delivery is not None:
            return None
        updated = self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.APPROVED,
            {"status": OpportunityStatus.SENDING.value, "send_error": None},
        )
        return (
            self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
            if updated
            else None
        )

    def complete_send(
        self, *, workspace_id: str, opportunity_id: str, receipt: DeliveryReceipt
    ) -> Opportunity | None:
        sent_at = datetime.now(UTC)
        updated = self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.SENDING,
            {
                "status": OpportunityStatus.SENT.value,
                "send_error": None,
                "delivery": {
                    "provider": receipt.provider,
                    "reference": receipt.reference,
                    "sent_at": sent_at,
                },
            },
        )
        if updated:
            self._audit(workspace_id, opportunity_id, AuditAction.PITCH_SENT)
        return (
            self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id)
            if updated
            else None
        )

    def fail_send(self, *, workspace_id: str, opportunity_id: str) -> None:
        if self._conditional_update(
            workspace_id,
            opportunity_id,
            OpportunityStatus.SENDING,
            {
                "status": OpportunityStatus.APPROVED.value,
                "send_error": "Simulated delivery failed. The approved pitch can be retried.",
            },
        ):
            self._audit(workspace_id, opportunity_id, AuditAction.SEND_FAILED)

    def list_audit(self, *, workspace_id: str, opportunity_id: str) -> builtins.list[AuditEvent]:
        if self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id) is None:
            return []
        events = [
            AuditEvent(
                id=document.id,
                opportunity_id=opportunity_id,
                action=AuditAction(str(document.get("action"))),
                occurred_at=_datetime(document.get("occurred_at")),
                detail=cast(str | None, document.get("detail")),
            )
            for document in self._db.collection("opportunities")
            .document(opportunity_id)
            .collection("audit_events")
            .stream()
        ]
        return sorted(events, key=lambda event: (event.occurred_at, event.id))

    def record_integration_failure(
        self, *, workspace_id: str, opportunity_id: str, detail: str
    ) -> None:
        if self.get_opportunity(workspace_id=workspace_id, opportunity_id=opportunity_id):
            self._audit(workspace_id, opportunity_id, AuditAction.INTEGRATION_SYNC_FAILED, detail)

    def _conditional_update(
        self,
        workspace_id: str,
        opportunity_id: str,
        expected: OpportunityStatus,
        values: dict[str, Any],
    ) -> bool:
        reference = self._db.collection("opportunities").document(opportunity_id)
        transaction = self._db.transaction()
        snapshot = reference.get(transaction=transaction)
        if (
            not snapshot.exists
            or snapshot.get("workspace_id") != workspace_id
            or snapshot.get("status") != expected.value
        ):
            return False
        transaction.update(reference, values)
        try:
            transaction.commit()
        except GoogleAPICallError:
            return False
        return True

    def _audit(
        self,
        workspace_id: str,
        opportunity_id: str,
        action: AuditAction,
        detail: str | None = None,
    ) -> None:
        self._db.collection("opportunities").document(opportunity_id).collection(
            "audit_events"
        ).document(str(uuid4())).create(
            {
                "workspace_id": workspace_id,
                "action": action.value,
                "occurred_at": datetime.now(UTC),
                "detail": detail,
            }
        )


class FirestoreClientRepository:
    def __init__(self, repository: FirestoreRepository) -> None:
        self._repository = repository

    def create(self, *, workspace_id: str, details: ClientDetails) -> Client:
        return self._repository.create(workspace_id=workspace_id, details=details)

    def list(self, *, workspace_id: str) -> list[Client]:
        return self._repository.list_clients(workspace_id=workspace_id)

    def get(self, *, workspace_id: str, client_id: str) -> Client | None:
        return self._repository.get_client(workspace_id=workspace_id, client_id=client_id)

    def update(self, *, workspace_id: str, client_id: str, details: ClientDetails) -> Client | None:
        return self._repository.update_client(
            workspace_id=workspace_id, client_id=client_id, details=details
        )

    def delete(self, *, workspace_id: str, client_id: str) -> bool:
        return self._repository.delete_client(workspace_id=workspace_id, client_id=client_id)


class FirestoreMediaRepository:
    def __init__(self, repository: FirestoreRepository) -> None:
        self._repository = repository

    def ingest(self, *, workspace_id: str, items: tuple[IncomingMediaItem, ...]) -> IngestionResult:
        return self._repository.ingest(workspace_id=workspace_id, items=items)

    def list(self, *, workspace_id: str, limit: int) -> list[MediaItem]:
        return self._repository.list_media(workspace_id=workspace_id, limit=limit)

    def get(self, *, workspace_id: str, media_item_id: str) -> MediaItem | None:
        return self._repository.get_media(workspace_id=workspace_id, media_item_id=media_item_id)

    def delete(self, *, workspace_id: str, media_item_id: str) -> bool:
        return self._repository.delete_media(workspace_id=workspace_id, media_item_id=media_item_id)

    def clear(self, *, workspace_id: str) -> None:
        self._repository.clear_media(workspace_id=workspace_id)


class FirestoreMediaSourceRepository(MediaSourceRepository):
    def __init__(self, repository: FirestoreRepository) -> None:
        self._repository = repository

    def create(self, *, workspace_id: str, details: MediaSourceDetails) -> MediaSource:
        return self._repository.create_media_source(workspace_id=workspace_id, details=details)

    def list(self, *, workspace_id: str, kind: MediaSourceKind | None) -> list[MediaSource]:
        return self._repository.list_media_sources(workspace_id=workspace_id, kind=kind)

    def delete(self, *, workspace_id: str, source_id: str) -> bool:
        return self._repository.delete_media_source(workspace_id=workspace_id, source_id=source_id)


class FirestoreOpportunityRepository:
    def __init__(self, repository: FirestoreRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        target = {
            "list": "list_opportunities",
            "get": "get_opportunity",
            "delete": "delete_opportunity",
            "clear": "clear_opportunities",
        }.get(name, name)
        return getattr(self._repository, target)


def _key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _data(document: Any) -> dict[str, Any]:
    return cast(dict[str, Any], document.to_dict())


def _datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("Firestore timestamp is invalid")
    return value.astimezone(UTC)


def _identity(
    user_id: str,
    data: dict[str, Any],
    *,
    workspace_id: str | None = None,
    workspace_kind: WorkspaceKind = WorkspaceKind.PROD,
) -> Identity:
    return Identity(
        user_id=user_id,
        workspace_id=workspace_id or str(data["workspace_id"]),
        email=str(data["email"]),
        name=str(data["name"]),
        workspace_kind=workspace_kind,
    )


def _client_details(details: ClientDetails) -> dict[str, Any]:
    return {
        field: list(value) if isinstance(value, tuple) else value
        for field, value in vars(details).items()
    }


def _media_source(source_id: str, data: dict[str, Any]) -> MediaSource:
    return MediaSource(
        id=source_id,
        workspace_id=str(data["workspace_id"]),
        name=str(data["name"]),
        kind=MediaSourceKind(str(data["kind"])),
        url=None if data.get("url") is None else str(data["url"]),
        provider=None if data.get("provider") is None else str(data["provider"]),
    )


def _client(client_id: str, data: dict[str, Any]) -> Client:
    return Client(
        id=client_id,
        workspace_id=str(data["workspace_id"]),
        name=str(data["name"]),
        company=str(data["company"]),
        website=cast(str | None, data.get("website")),
        industry=cast(str | None, data.get("industry")),
        description=cast(str | None, data.get("description")),
        location=cast(str | None, data.get("location")),
        expertise=tuple(data.get("expertise", [])),
        spokesperson_name=cast(str | None, data.get("spokesperson_name")),
        spokesperson_title=cast(str | None, data.get("spokesperson_title")),
        keywords=tuple(data.get("keywords", [])),
        excluded_keywords=tuple(data.get("excluded_keywords", [])),
        preferred_topics=tuple(data.get("preferred_topics", [])),
        tone=cast(str | None, data.get("tone")),
        monitoring_rules=tuple(data.get("monitoring_rules", [])),
    )


def _media(media_id: str, data: dict[str, Any]) -> MediaItem:
    return MediaItem(
        id=media_id,
        source=str(data["source"]),
        source_type=MediaSourceType(str(data["source_type"])),
        headline=str(data["headline"]),
        body=str(data["body"]),
        published_at=_datetime(data["published_at"]),
        ingested_at=_datetime(data["ingested_at"]),
        author=cast(str | None, data.get("author")),
        journalist=cast(str | None, data.get("journalist")),
        url=cast(str | None, data.get("url")),
        deadline=None if data.get("deadline") is None else _datetime(data["deadline"]),
        topics=tuple(data.get("topics", [])),
        external_id=cast(str | None, data.get("external_id")),
    )


def _opportunity(opportunity_id: str, data: dict[str, Any]) -> Opportunity:
    pitch_data = cast(dict[str, Any] | None, data.get("pitch"))
    delivery_data = cast(dict[str, Any] | None, data.get("delivery"))
    return Opportunity(
        id=opportunity_id,
        workspace_id=str(data["workspace_id"]),
        client_id=str(data["client_id"]),
        client_name=str(data["client_name"]),
        client_company=str(data["client_company"]),
        client_deleted=False,
        media_item_id=str(data["media_item_id"]),
        source=str(data["source"]),
        headline=str(data["headline"]),
        media_deleted=False,
        journalist=cast(str | None, data.get("journalist")),
        published_at=_datetime(data["published_at"]),
        deadline=None if data.get("deadline") is None else _datetime(data["deadline"]),
        matched_topics=tuple(data.get("matched_topics", [])),
        relevance_score=cast(int | None, data.get("relevance_score")),
        relevance_reason=cast(str | None, data.get("relevance_reason")),
        analysis_error=cast(str | None, data.get("analysis_error")),
        pitch=None
        if pitch_data is None
        else Pitch(
            id=str(pitch_data["id"]),
            opportunity_id=opportunity_id,
            content=str(pitch_data["content"]),
            generated_at=_datetime(pitch_data["generated_at"]),
            updated_at=_datetime(pitch_data["updated_at"]),
        ),
        pitch_error=cast(str | None, data.get("pitch_error")),
        delivery=None
        if delivery_data is None
        else Delivery(
            provider=str(delivery_data["provider"]),
            reference=str(delivery_data["reference"]),
            sent_at=_datetime(delivery_data["sent_at"]),
        ),
        send_error=cast(str | None, data.get("send_error")),
        status=OpportunityStatus(str(data["status"])),
        detected_at=_datetime(data["detected_at"]),
    )
