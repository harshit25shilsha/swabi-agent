"""
Auth router — Phase 4.

Endpoints:
  POST /auth/login           — login with email + password → JWT
  POST /auth/logout          — invalidate session (Bearer token required)
  GET  /auth/otp/send        — send OTP to email (forgot password flow)
  POST /auth/otp/verify      — verify OTP code
  PUT  /auth/password/reset  — update password after OTP verified
"""

import httpx

from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    ForgotPasswordRequest,
    OtpSentResponse,
    VerifyOtpRequest,
    OtpVerifiedResponse,
    ResetPasswordRequest,
    PasswordResetResponse,
)
from app.services.auth_service import login, logout
from app.services.swabi_client import swabi_client
from app.core.auth import decode_swabi_token
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Login ──────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in to Swabi and get a JWT for the agent",
    description=(
        "Authenticate with email and password. Returns a JWT token and "
        "user details. Pass the token in AgentRequest.token on the first "
        "turn of your agent conversation to enable booking and personalized "
        "features."
    ),
)
async def login_endpoint(body: LoginRequest):
    try:
        result    = await login(body.email, body.password)
        auth_user = result["auth_user"]

        logger.info(
            "Login success | user_id=%s | email=%s",
            auth_user.user_id,
            auth_user.email,
        )

        return LoginResponse(
            token=auth_user.token,
            user_id=auth_user.user_id,
            first_name=auth_user.first_name,
            last_name=auth_user.last_name,
            email=auth_user.email,
            user_type=auth_user.user_type,
        )

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Login failed | status=%s | body=%s",
            e.response.status_code,
            e.response.text[:200],
        )
        if e.response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Swabi authentication service unavailable.",
        )


# ── Logout ─────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out and invalidate the Swabi session",
    description=(
        "Invalidates the user session on the Swabi backend. "
        "Send the JWT in the Authorization: Bearer header. "
        "Discard the token on the frontend after calling this."
    ),
)
async def logout_endpoint(
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed. Expected: Bearer <token>",
        )

    token     = authorization.removeprefix("Bearer ").strip()
    auth_user = decode_swabi_token(token)

    try:
        await logout(auth_user.user_id, token)
        logger.info("Logout | user_id=%s", auth_user.user_id)
        return LogoutResponse()

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Logout Swabi error | user_id=%s | status=%s",
            auth_user.user_id,
            e.response.status_code,
        )
        # Non-fatal — token already discarded client-side
        return LogoutResponse(message="Logged out (session may already have expired).")


# ── Forgot password — OTP send ─────────────────────────────────────────────

@router.get(
    "/otp/send",
    response_model=OtpSentResponse,
    summary="Send OTP to email for password reset",
    description="Triggers Swabi to send a one-time password to the given email address.",
)
async def otp_send(email: str):
    try:
        await swabi_client.get(f"/otp_send?email={email}")
        logger.info("OTP sent | email=%s", email)
        return OtpSentResponse()

    except httpx.HTTPStatusError as e:
        logger.warning("OTP send failed | email=%s | status=%s", email, e.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send OTP. Please check the email address and try again.",
        )


# ── Forgot password — OTP verify ───────────────────────────────────────────

@router.post(
    "/otp/verify",
    response_model=OtpVerifiedResponse,
    summary="Verify OTP code",
    description="Verify the OTP sent to the user's email. Call password/reset after this succeeds.",
)
async def otp_verify(body: VerifyOtpRequest):
    try:
        await swabi_client.post(
            f"/otp_verify?email={body.email}&otp={body.otp}",
            {},
        )
        logger.info("OTP verified | email=%s", body.email)
        return OtpVerifiedResponse()

    except httpx.HTTPStatusError as e:
        logger.warning(
            "OTP verify failed | email=%s | status=%s",
            body.email,
            e.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )


# ── Forgot password — password reset ──────────────────────────────────────

@router.put(
    "/password/reset",
    response_model=PasswordResetResponse,
    summary="Reset password after OTP verification",
    description="Update the user's password. Only call after otp/verify succeeds.",
)
async def password_reset(body: ResetPasswordRequest):
    try:
        await swabi_client.put(
            f"/password_update?email={body.email}&password={body.password}",
        )
        logger.info("Password reset | email=%s", body.email)
        return PasswordResetResponse()

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Password reset failed | email=%s | status=%s",
            body.email,
            e.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Password update failed. Please try again.",
        )