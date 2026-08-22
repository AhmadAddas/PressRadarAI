from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pressradar.application.auth import AuthService
from pressradar.config import Settings, get_settings
from pressradar.infrastructure.security import PasswordHasher, SessionTokens
from pressradar.infrastructure.sqlite_auth import SQLiteAuthRepository
from pressradar.presentation.auth import create_auth_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    auth_repository = SQLiteAuthRepository(settings.database_path)
    auth_repository.initialize()
    auth_service = AuthService(
        auth_repository,
        PasswordHasher(),
        SessionTokens(),
        timedelta(hours=settings.session_ttl_hours),
    )
    application = FastAPI(title="PressRadar API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(
        create_auth_router(
            auth_service,
            secure_cookies=settings.secure_cookies,
            session_max_age=settings.session_ttl_hours * 60 * 60,
        )
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.app_mode}

    return application


app = create_app()
