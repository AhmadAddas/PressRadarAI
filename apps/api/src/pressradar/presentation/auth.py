from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, StringConstraints

from pressradar.application.auth import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
)
from pressradar.domain.auth import Identity, WorkspaceKind

SESSION_COOKIE = "pressradar_session"
WORKSPACE_COOKIE = "pressradar_workspace"
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SignUpRequest(BaseModel):
    email: EmailStr
    name: DisplayName
    password: str = Field(min_length=12, max_length=128)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class IdentityResponse(BaseModel):
    user_id: str
    workspace_id: str
    email: str
    name: str
    workspace_kind: WorkspaceKind


class WorkspaceSelectionRequest(BaseModel):
    workspace_kind: WorkspaceKind


def create_auth_router(
    auth_service: AuthService, *, secure_cookies: bool, session_max_age: int
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["authentication"])

    current_identity = require_identity(auth_service)

    @router.post("/signup", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
    def sign_up(request: SignUpRequest, response: Response) -> Identity:
        try:
            session = auth_service.sign_up(
                email=str(request.email), name=request.name, password=request.password
            )
        except DuplicateEmailError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="An account already uses this email"
            ) from error
        _set_session_cookie(response, session.token, secure=secure_cookies, max_age=session_max_age)
        return session.identity

    @router.post("/signin", response_model=IdentityResponse)
    def sign_in(request: SignInRequest, response: Response) -> Identity:
        try:
            session = auth_service.sign_in(email=str(request.email), password=request.password)
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            ) from error
        _set_session_cookie(response, session.token, secure=secure_cookies, max_age=session_max_age)
        return session.identity

    @router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
    def sign_out(
        response: Response,
        session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> None:
        if session_token:
            auth_service.sign_out(session_token)
        response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=secure_cookies)
        response.delete_cookie(
            WORKSPACE_COOKIE, httponly=True, samesite="lax", secure=secure_cookies
        )

    @router.post("/workspace", response_model=IdentityResponse)
    def select_workspace(
        request: WorkspaceSelectionRequest,
        response: Response,
        session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Identity:
        identity = (
            auth_service.authenticate(session_token, request.workspace_kind)
            if session_token
            else None
        )
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )
        response.set_cookie(
            WORKSPACE_COOKIE,
            request.workspace_kind.value,
            httponly=True,
            secure=secure_cookies,
            samesite="lax",
            max_age=session_max_age,
            path="/",
        )
        return identity

    @router.get("/me", response_model=IdentityResponse)
    def me(identity: Annotated[Identity, Depends(current_identity)]) -> Identity:
        return identity

    return router


def require_identity(auth_service: AuthService) -> Callable[..., Identity]:
    def dependency(
        session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
        workspace: Annotated[str | None, Cookie(alias=WORKSPACE_COOKIE)] = None,
    ) -> Identity:
        try:
            workspace_kind = WorkspaceKind(workspace or WorkspaceKind.PROD)
        except ValueError:
            workspace_kind = WorkspaceKind.PROD
        identity = (
            auth_service.authenticate(session_token, workspace_kind) if session_token else None
        )
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )
        return identity

    return dependency


def _set_session_cookie(response: Response, token: str, *, secure: bool, max_age: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
