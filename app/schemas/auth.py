from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Request models ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr = Field(..., examples=["kumar@animelab.io"])
    password: str      = Field(..., min_length=1, examples=["Swabi@123"])

    # Optional overrides — defaults are fine for customer agent
    token_type:         str = Field("WEB",            alias="TokenType")
    user_type:          str = Field("USER",           alias="userType")
    notification_token: str = Field("",               alias="notificationToken")
    zone_id:            str = Field("Asia/Calcutta",  alias="zoneId")

    model_config = {"populate_by_name": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., examples=["kumar@animelab.io"])


class VerifyOtpRequest(BaseModel):
    email: EmailStr = Field(..., examples=["kumar@animelab.io"])
    otp:   str      = Field(..., examples=["123456"])


class ResetPasswordRequest(BaseModel):
    email:    EmailStr = Field(..., examples=["kumar@animelab.io"])
    password: str      = Field(..., min_length=6, examples=["Swabi@newpass"])


# ── Response models ────────────────────────────────────────────────────────

class LoginResponse(BaseModel):
    token:      str
    user_id:    int
    first_name: str
    last_name:  str
    email:      str
    user_type:  str
    message:    str = "Logged in successfully."


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully."


class OtpSentResponse(BaseModel):
    message: str = "OTP sent to your email."


class OtpVerifiedResponse(BaseModel):
    message: str = "OTP verified successfully."


class PasswordResetResponse(BaseModel):
    message: str = "Password updated successfully."