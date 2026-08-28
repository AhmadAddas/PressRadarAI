from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from pressradar.application.auth import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidOTPError,
    TOTPRequiredError,
)
from pressradar.application.email import EmailDeliveryError
from pressradar.domain.auth import Identity, WorkspaceKind
from pressradar.presentation.rate_limit import InMemoryRateLimiter, request_source

SESSION_COOKIE = "pressradar_session"
WORKSPACE_COOKIE = "pressradar_workspace"
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SignUpRequest(BaseModel):
    email: EmailStr
    name: DisplayName
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        if len(value.split(maxsplit=1)[0]) > 25:
            raise ValueError("First name must be 25 characters or fewer")
        return value


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TOTPCodeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class SecurityOTPRequest(BaseModel):
    purpose: Literal["setup_2fa", "disable_2fa"]


class SecurityOTPResponse(BaseModel):
    challenge_id: str


class ProtectedTOTPRequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=200)
    code: str = Field(pattern=r"^\d{6}$")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class SignupVerificationResponse(BaseModel):
    verification_required: bool = True
    user_id: str
    challenge_id: str


class SignupVerificationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    challenge_id: str = Field(min_length=20, max_length=200)
    code: str = Field(pattern=r"^\d{6}$")


class IdentityResponse(BaseModel):
    user_id: str
    workspace_id: str
    email: str
    name: str
    workspace_kind: WorkspaceKind
    totp_enabled: bool
    onboarding_completed: bool


class WorkspaceSelectionRequest(BaseModel):
    workspace_kind: WorkspaceKind


def create_auth_router(
    auth_service: AuthService,
    *,
    secure_cookies: bool,
    session_max_age: int,
    rate_limiter: InMemoryRateLimiter | None = None,
    auth_rate_limit: int = 10,
    email_rate_limit: int = 3,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["authentication"])

    current_identity = require_identity(auth_service)
    limiter = rate_limiter or InMemoryRateLimiter()

    @router.post(
        "/signup",
        response_model=IdentityResponse | SignupVerificationResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def sign_up(
        request: SignUpRequest, response: Response, http_request: Request
    ) -> Identity | SignupVerificationResponse:
        source = request_source(http_request)
        limiter.check(f"signup-ip:{source}", limit=auth_rate_limit, window_seconds=60)
        limiter.check(
            f"signup-email:{request.email.lower()}", limit=email_rate_limit, window_seconds=600
        )
        try:
            if auth_service.requires_email_verification:
                user_id, challenge_id = auth_service.begin_sign_up(
                    email=str(request.email), name=request.name, password=request.password
                )
                response.status_code = status.HTTP_202_ACCEPTED
                return SignupVerificationResponse(user_id=user_id, challenge_id=challenge_id)
            session = auth_service.sign_up(
                email=str(request.email), name=request.name, password=request.password
            )
        except DuplicateEmailError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="An account already uses this email"
            ) from error
        except EmailDeliveryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Verification email could not be sent",
            ) from error
        _set_session_cookie(response, session.token, secure=secure_cookies, max_age=session_max_age)
        return session.identity

    @router.post("/signup/verify", response_model=IdentityResponse)
    def verify_signup(
        request: SignupVerificationRequest, response: Response, http_request: Request
    ) -> Identity:
        limiter.check(
            f"signup-verify:{request_source(http_request)}:{request.user_id}",
            limit=auth_rate_limit,
            window_seconds=60,
        )
        try:
            session = auth_service.verify_sign_up(
                user_id=request.user_id,
                challenge_id=request.challenge_id,
                code=request.code,
            )
        except InvalidOTPError as error:
            raise HTTPException(
                status_code=400, detail="Invalid or expired verification code"
            ) from error
        _set_session_cookie(response, session.token, secure=secure_cookies, max_age=session_max_age)
        return session.identity

    @router.post("/signin", response_model=IdentityResponse)
    def sign_in(request: SignInRequest, response: Response, http_request: Request) -> Identity:
        source = request_source(http_request)
        limiter.check(f"signin-ip:{source}", limit=auth_rate_limit, window_seconds=60)
        limiter.check(
            f"signin-email:{request.email.lower()}", limit=auth_rate_limit, window_seconds=60
        )
        try:
            session = auth_service.sign_in(
                email=str(request.email),
                password=request.password,
                totp_code=request.totp_code,
            )
        except TOTPRequiredError as error:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="A valid authenticator code is required",
            ) from error
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

    @router.post("/2fa/setup", response_model=TOTPSetupResponse)
    def setup_totp(
        identity: Annotated[Identity, Depends(current_identity)],
        request: ProtectedTOTPRequest | None = None,
    ) -> TOTPSetupResponse:
        if identity.onboarding_completed:
            if request is None:
                raise HTTPException(status_code=428, detail="Email verification is required")
            try:
                auth_service.verify_security_otp(
                    identity,
                    challenge_id=request.challenge_id,
                    code=request.code,
                    purpose="setup_2fa",
                )
            except InvalidOTPError as error:
                raise HTTPException(
                    status_code=400, detail="Invalid or expired email code"
                ) from error
        secret, uri = auth_service.begin_totp_setup(identity)
        return TOTPSetupResponse(secret=secret, provisioning_uri=uri)

    @router.post("/2fa/email-code", response_model=SecurityOTPResponse)
    def request_2fa_email_code(
        request: SecurityOTPRequest,
        http_request: Request,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> SecurityOTPResponse:
        limiter.check(
            f"security-email:{request_source(http_request)}:{identity.user_id}",
            limit=email_rate_limit,
            window_seconds=600,
        )
        try:
            challenge_id = auth_service.request_security_otp(identity, request.purpose)
        except EmailDeliveryError as error:
            raise HTTPException(
                status_code=503, detail="Verification email could not be sent"
            ) from error
        return SecurityOTPResponse(challenge_id=challenge_id)

    @router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
    def disable_totp(
        request: ProtectedTOTPRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> None:
        try:
            auth_service.verify_security_otp(
                identity,
                challenge_id=request.challenge_id,
                code=request.code,
                purpose="disable_2fa",
            )
        except InvalidOTPError as error:
            raise HTTPException(status_code=400, detail="Invalid or expired email code") from error
        auth_service.disable_totp(identity)

    @router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
    def enable_totp(
        request: TOTPCodeRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> None:
        try:
            auth_service.enable_totp(identity, request.code)
        except TOTPRequiredError as error:
            raise HTTPException(status_code=400, detail="Invalid authenticator code") from error

    @router.post("/2fa/skip", status_code=status.HTTP_204_NO_CONTENT)
    def skip_totp(identity: Annotated[Identity, Depends(current_identity)]) -> None:
        auth_service.skip_totp(identity)

    @router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
    def change_password(
        request: PasswordChangeRequest,
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> None:
        try:
            auth_service.change_password(identity, request.current_password, request.new_password)
        except InvalidCredentialsError as error:
            raise HTTPException(status_code=400, detail="Current password is incorrect") from error

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
