# from __future__ import annotations
 
# import time
# from dataclasses import dataclass
# from typing import Optional
# import jwt

# from fastapi import HTTPException, status

# from app.config import settings

# # Typed identity object stored in agent state 
# @dataclass(frozen=True)
# class AuthUser:
#     user_id: int
#     user_type: str
#     email: str
#     first_name: str
#     last_name: str
#     token: str
    

# # Token Decoder 

# def decode_swabi_token(token:str)-> AuthUser:
#     """
#     Decode and validate a Swabi JWT. Returns AuthUser on success.
#     Raises HTTPException on any failure so FastAPI returns the correct
#     HTTP status code to the client automatically.
 
#     Validation order:
#       1. Signature — rejects tampered tokens
#       2. Expiry    — rejects expired tokens (jwt library does this)
#       3. userType  — rejects non-USER tokens (agent is customer-only)
#     """
#     try:
#         payload = jwt.decode(
#             token,
#             settings.SWABI_JWT_SECRET,
#             algorithms=["HS512"],
#         )
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code= status.HTTP_401_UNAUTHORIZED,
#             detail ="Session expired. please log in again."
#         )
        
#     except jwt.InvalidTokenError as e:
#         raise HTTPException(
#             status_code= status.HTTP_401_UNAUTHORIZED,
#             detail = f"Invalid token: {e}",
#         )
        
#     user_type = payload.get("userType","")
#     if user_type != "USER":
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=(
#                 f"This agent is for customers only. "
#                 f"Received userType='{user_type}'."
#                 ),
#         )
        
#     user_id = payload.get("user_id")
#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail = "Token missing userId claim.",
#         )
        
#     return AuthUser(
#         user_id=int(user_id),
#         user_type=user_type,
#         email=payload.get("sub", ""),
#         first_name="",
#         last_name="",
#         token=token,
#     )

# def maybe_decode_token(token:Optional[str])-> Optional[AuthUser]:
#     """
#     Decode token if provided; return None for guest sessions.
#     Used by the agent router — guests can still search/recommend,
#     they just can't book or get personalized results.
#     """
#     if not token:
#         return None
#     return decode_swabi_token(token)



from __future__ import annotations

import base64
import json
import time
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


def _decode_payload_unverified(token: str) -> dict:
    """Decode JWT payload without signature verification (dev only)."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not decode token: {e}",
        )


def decode_swabi_token(token: str) -> AuthUser:
    """
    Decode and validate a Swabi JWT.
    If SWABI_JWT_SKIP_VERIFY=true in .env — skips signature check (dev only).
    If SWABI_JWT_SKIP_VERIFY=false — full HS512 verification.
    """
    if settings.SWABI_JWT_SKIP_VERIFY:
        payload = _decode_payload_unverified(token)
        # Still check expiry manually
        exp = payload.get("exp", 0)
        if exp and time.time() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )
    else:
        try:
            payload = jwt.decode(
                token,
                settings.SWABI_JWT_SECRET,
                algorithms=["HS512"],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
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

    user_id = payload.get("userId")   # capital I — matches Swabi JWT payload
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
    """Guest-safe wrapper — returns None if no token provided."""
    if not token:
        return None
    return decode_swabi_token(token)