from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pressradar.application.auth import AuthService
from pressradar.application.clients import ClientService
from pressradar.application.delivery import PitchSender
from pressradar.application.demo import DemoSetupService
from pressradar.application.media import MediaIngestionService
from pressradar.application.opportunities import OpportunityService
from pressradar.application.pitches import PitchGenerator
from pressradar.application.relevance import RelevanceAnalyzer
from pressradar.config import Settings, get_settings
from pressradar.infrastructure.fake_pitch import FakePitchGenerator
from pressradar.infrastructure.fake_relevance import FakeRelevanceAnalyzer
from pressradar.infrastructure.ollama_pitch import OllamaPitchGenerator
from pressradar.infrastructure.ollama_relevance import OllamaRelevanceAnalyzer
from pressradar.infrastructure.security import PasswordHasher, SessionTokens
from pressradar.infrastructure.simulated_media import SimulatedMediaProvider
from pressradar.infrastructure.simulated_sender import SimulatedPitchSender
from pressradar.infrastructure.sqlite_auth import SQLiteAuthRepository
from pressradar.infrastructure.sqlite_clients import SQLiteClientRepository
from pressradar.infrastructure.sqlite_media import SQLiteMediaRepository
from pressradar.infrastructure.sqlite_opportunities import SQLiteOpportunityRepository
from pressradar.presentation.auth import create_auth_router, require_identity
from pressradar.presentation.clients import create_clients_router
from pressradar.presentation.demo import create_demo_router
from pressradar.presentation.media import create_media_router
from pressradar.presentation.opportunities import create_opportunities_router


def create_app(
    settings: Settings | None = None,
    relevance_analyzer: RelevanceAnalyzer | None = None,
    pitch_generator: PitchGenerator | None = None,
    pitch_sender: PitchSender | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    auth_repository = SQLiteAuthRepository(settings.database_path)
    auth_repository.initialize()
    auth_service = AuthService(
        auth_repository,
        PasswordHasher(),
        SessionTokens(),
        timedelta(hours=settings.session_ttl_hours),
    )
    client_repository = SQLiteClientRepository(settings.database_path)
    client_repository.initialize()
    client_service = ClientService(client_repository)
    media_repository = SQLiteMediaRepository(settings.database_path)
    media_repository.initialize()
    media_providers = {"simulated": SimulatedMediaProvider()}
    media_service = MediaIngestionService(
        media_providers[settings.media_provider], media_repository
    )
    opportunity_repository = SQLiteOpportunityRepository(settings.database_path)
    opportunity_repository.initialize()
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
    opportunity_service = OpportunityService(
        client_repository,
        media_repository,
        opportunity_repository,
        relevance_analyzer,
        pitch_generator,
        pitch_sender,
    )
    demo_opportunity_service = OpportunityService(
        client_repository,
        media_repository,
        opportunity_repository,
        FakeRelevanceAnalyzer(),
        FakePitchGenerator(),
        SimulatedPitchSender(),
    )
    application = FastAPI(title="PressRadar API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH"],
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
        create_media_router(media_service, opportunity_service, identity_dependency)
    )
    application.include_router(
        create_opportunities_router(opportunity_service, identity_dependency)
    )
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
