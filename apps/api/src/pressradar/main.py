from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pressradar.application.analytics import AnalyticsError, AnalyticsService, AnalyticsStore
from pressradar.application.auth import AuthRepository, AuthService
from pressradar.application.clients import ClientRepository, ClientService
from pressradar.application.delivery import PitchSender
from pressradar.application.demo import DemoSetupService
from pressradar.application.integrations import CRMIntegration, NotificationSender
from pressradar.application.media import MediaIngestionService, MediaRepository
from pressradar.application.media_sources import MediaSourceRepository, MediaSourceService
from pressradar.application.opportunities import OpportunityRepository, OpportunityService
from pressradar.application.pitches import PitchGenerator
from pressradar.application.relevance import RelevanceAnalyzer
from pressradar.config import Settings, get_settings
from pressradar.infrastructure.bigquery_analytics import BigQueryAnalyticsStore
from pressradar.infrastructure.configured_media import ConfiguredMediaIngestionService
from pressradar.infrastructure.fake_integrations import (
    FakeCRMIntegration,
    FakeNotificationSender,
)
from pressradar.infrastructure.fake_pitch import FakePitchGenerator
from pressradar.infrastructure.fake_relevance import FakeRelevanceAnalyzer
from pressradar.infrastructure.firestore import (
    FirestoreClientRepository,
    FirestoreMediaRepository,
    FirestoreMediaSourceRepository,
    FirestoreOpportunityRepository,
    FirestoreRepository,
)
from pressradar.infrastructure.hubspot_crm import HubSpotCRMIntegration
from pressradar.infrastructure.noop_analytics import NoOpAnalyticsStore
from pressradar.infrastructure.ollama_pitch import OllamaPitchGenerator
from pressradar.infrastructure.ollama_relevance import OllamaRelevanceAnalyzer
from pressradar.infrastructure.security import PasswordHasher, SessionTokens
from pressradar.infrastructure.simulated_media import SimulatedMediaProvider
from pressradar.infrastructure.simulated_sender import SimulatedPitchSender
from pressradar.infrastructure.sqlite_analytics import SQLiteAnalyticsStore
from pressradar.infrastructure.sqlite_auth import SQLiteAuthRepository
from pressradar.infrastructure.sqlite_clients import SQLiteClientRepository
from pressradar.infrastructure.sqlite_media import SQLiteMediaRepository
from pressradar.infrastructure.sqlite_media_sources import SQLiteMediaSourceRepository
from pressradar.infrastructure.sqlite_opportunities import SQLiteOpportunityRepository
from pressradar.infrastructure.twilio_notifications import TwilioNotificationSender
from pressradar.presentation.analytics import create_analytics_router
from pressradar.presentation.auth import create_auth_router, require_identity
from pressradar.presentation.clients import create_clients_router
from pressradar.presentation.demo import create_demo_router
from pressradar.presentation.media import create_media_router
from pressradar.presentation.media_sources import create_media_sources_router
from pressradar.presentation.opportunities import create_opportunities_router


def create_app(
    settings: Settings | None = None,
    relevance_analyzer: RelevanceAnalyzer | None = None,
    pitch_generator: PitchGenerator | None = None,
    pitch_sender: PitchSender | None = None,
    notification_sender: NotificationSender | None = None,
    crm_integration: CRMIntegration | None = None,
    analytics_store: AnalyticsStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    custom_demo_workflow = any(
        dependency is not None
        for dependency in (
            relevance_analyzer,
            pitch_generator,
            pitch_sender,
            notification_sender,
            crm_integration,
        )
    )
    auth_repository: AuthRepository
    client_repository: ClientRepository
    media_repository: MediaRepository
    media_source_repository: MediaSourceRepository
    opportunity_repository: OpportunityRepository
    if settings.operational_provider == "firestore":
        firestore_repository = FirestoreRepository(
            project=settings.gcp_project_id or "", database=settings.firestore_database
        )
        auth_repository = firestore_repository
        client_repository = FirestoreClientRepository(firestore_repository)
        media_repository = FirestoreMediaRepository(firestore_repository)
        media_source_repository = FirestoreMediaSourceRepository(firestore_repository)
        opportunity_repository = FirestoreOpportunityRepository(firestore_repository)
    else:
        sqlite_auth = SQLiteAuthRepository(settings.database_path)
        sqlite_auth.initialize()
        auth_repository = sqlite_auth
        sqlite_clients = SQLiteClientRepository(settings.database_path)
        sqlite_clients.initialize()
        client_repository = sqlite_clients
        sqlite_media = SQLiteMediaRepository(settings.database_path)
        sqlite_media.initialize()
        media_repository = sqlite_media
        sqlite_media_sources = SQLiteMediaSourceRepository(settings.database_path)
        sqlite_media_sources.initialize()
        media_source_repository = sqlite_media_sources
        sqlite_opportunities = SQLiteOpportunityRepository(settings.database_path)
        sqlite_opportunities.initialize()
        opportunity_repository = sqlite_opportunities
    auth_service = AuthService(
        auth_repository,
        PasswordHasher(),
        SessionTokens(),
        timedelta(hours=settings.session_ttl_hours),
    )
    client_service = ClientService(client_repository)
    media_providers = {"simulated": SimulatedMediaProvider()}
    media_service = MediaIngestionService(
        media_providers[settings.media_provider], media_repository
    )
    if analytics_store is None:
        if settings.analytics_provider == "sqlite":
            sqlite_analytics = SQLiteAnalyticsStore(settings.analytics_database_path)
            try:
                sqlite_analytics.initialize()
            except AnalyticsError:
                pass
            analytics_store = sqlite_analytics
        elif settings.analytics_provider == "bigquery":
            analytics_store = BigQueryAnalyticsStore(
                project=settings.gcp_project_id or "",
                dataset=settings.bigquery_dataset,
                table=settings.bigquery_events_table,
            )
        else:
            analytics_store = NoOpAnalyticsStore()
    analytics_service = AnalyticsService(analytics_store)
    if relevance_analyzer is None:
        relevance_analyzer = (
            FakeRelevanceAnalyzer()
            if settings.ai_provider == "fake"
            else OllamaRelevanceAnalyzer(
                base_url=str(settings.ollama_base_url),
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            )
        )
    if pitch_generator is None:
        pitch_generator = (
            FakePitchGenerator()
            if settings.ai_provider == "fake"
            else OllamaPitchGenerator(
                base_url=str(settings.ollama_base_url),
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            )
        )
    if pitch_sender is None:
        pitch_senders = {"simulated": SimulatedPitchSender()}
        pitch_sender = pitch_senders[settings.pitch_sender]
    if notification_sender is None:
        notification_sender = (
            FakeNotificationSender()
            if settings.notification_provider == "fake"
            else TwilioNotificationSender(
                account_sid=settings.twilio_account_sid or "",
                auth_token=(
                    ""
                    if settings.twilio_auth_token is None
                    else settings.twilio_auth_token.get_secret_value()
                ),
                from_number=settings.twilio_from_number or "",
                to_number=settings.twilio_to_number or "",
                timeout_seconds=settings.external_provider_timeout_seconds,
            )
        )
    if crm_integration is None:
        crm_integration = (
            FakeCRMIntegration()
            if settings.crm_provider == "fake"
            else HubSpotCRMIntegration(
                access_token=(
                    ""
                    if settings.hubspot_access_token is None
                    else settings.hubspot_access_token.get_secret_value()
                ),
                timeout_seconds=settings.external_provider_timeout_seconds,
            )
        )
    opportunity_service = OpportunityService(
        client_repository,
        media_repository,
        opportunity_repository,
        relevance_analyzer,
        pitch_generator,
        pitch_sender,
        notification_sender,
        crm_integration,
        analytics_service,
    )
    demo_opportunity_service = (
        opportunity_service
        if custom_demo_workflow
        else OpportunityService(
            client_repository,
            media_repository,
            opportunity_repository,
            FakeRelevanceAnalyzer(),
            FakePitchGenerator(),
            SimulatedPitchSender(),
            FakeNotificationSender(),
            FakeCRMIntegration(),
            analytics_service,
        )
    )
    application = FastAPI(title="PressRadar API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(
        create_auth_router(
            auth_service,
            secure_cookies=settings.secure_cookies,
            session_max_age=settings.session_ttl_hours * 60 * 60,
        )
    )
    application.include_router(
        create_clients_router(client_service, require_identity(auth_service))
    )
    identity_dependency = require_identity(auth_service)
    application.include_router(
        create_media_router(
            media_service,
            ConfiguredMediaIngestionService(
                media_source_repository,
                media_repository,
                newsapi_api_key=(
                    ""
                    if settings.newsapi_api_key is None
                    else settings.newsapi_api_key.get_secret_value()
                ),
                timeout_seconds=settings.external_provider_timeout_seconds,
            ),
            opportunity_service,
            demo_opportunity_service,
            identity_dependency,
        )
    )
    application.include_router(
        create_media_sources_router(
            MediaSourceService(media_source_repository), identity_dependency
        )
    )
    application.include_router(
        create_opportunities_router(opportunity_service, identity_dependency)
    )
    application.include_router(create_analytics_router(analytics_service, identity_dependency))
    application.include_router(
        create_demo_router(
            DemoSetupService(client_service, media_service, demo_opportunity_service),
            identity_dependency,
        )
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.app_mode}

    return application


app = create_app()
