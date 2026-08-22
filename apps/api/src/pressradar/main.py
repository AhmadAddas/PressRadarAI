from fastapi import FastAPI

from pressradar.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="PressRadar API", version="0.1.0")

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.app_mode}

    return application


app = create_app()
