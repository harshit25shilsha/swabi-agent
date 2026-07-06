from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import HTTPException, status

from app.config import settings


@dataclass(frozen=True)
class AuthUser:
    user_id:    int
    user_type:  str
    email:      str
    first_name: str
    last_name:  str
    token:      str


def _jwt_secret() -> bytes:
    secret   = settings.SWABI_JWT_SECRET
    encoding = settings.SWABI_JWT_SECRET_ENCODING.lower()

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT verification secret is missing.",
        )

    if encoding == "raw":
        return secret.encode("utf-8")

    if encoding == "base64":
        try:
            return base64.b64decode(secret, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT verification secret is not valid Base64.",
            )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="JWT verification secret encoding must be 'raw' or 'base64'.",
    )


def decode_swabi_token(token: str) -> AuthUser:
    """
    Decode and validate a Swabi JWT using the backend signing secret.

    leeway tolerates small clock skew between this server and whatever
    issued the token (Swabi's backend). Without it, PyJWT >=2.6 rejects
    a token outright if this machine's clock is even a few seconds
    behind the issuer's — surfacing as "The token is not yet valid
    (iat)" on an otherwise-valid, freshly-issued token. This doesn't
    fix a badly wrong system clock (see settings.SWABI_JWT_LEEWAY_SECONDS
    if more tolerance is needed), just normal clock drift.
    """
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[settings.SWABI_JWT_ALGORITHM],
            leeway=settings.SWABI_JWT_LEEWAY_SECONDS,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except jwt.InvalidAlgorithmError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token algorithm: {e}",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    user_type = payload.get("userType", "")
    if user_type != "USER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent is for customers only. Received userType='{user_type}'.",
        )

    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing userId claim.",
        )

    return AuthUser(
        user_id=int(user_id),
        user_type=user_type,
        email=payload.get("sub", ""),
        first_name="",
        last_name="",
        token=token,
    )


def maybe_decode_token(token: Optional[str]) -> Optional[AuthUser]:
    """Return None for guests; otherwise require a valid Swabi JWT."""
    if not token:
        return None
    return decode_swabi_token(token)