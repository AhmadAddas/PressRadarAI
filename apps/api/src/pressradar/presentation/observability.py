import json
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import uuid4

from fastapi import Request, Response

LOGGER = logging.getLogger("pressradar.http")


async def observe_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id", "").strip()[:128] or str(uuid4())
    started = monotonic()
    try:
        response = await call_next(request)
    except Exception:
        LOGGER.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request_id,
                    "path": request.url.path,
                }
            )
        )
        raise
    response.headers["x-request-id"] = request_id
    LOGGER.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((monotonic() - started) * 1000),
            }
        )
    )
    return response
