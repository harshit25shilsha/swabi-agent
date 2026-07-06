from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    GROQ_MODEL: str
    SWABI_API_BASE: str

    # Must match the Swabi backend JWT signing configuration.
    SWABI_JWT_SECRET: str = ""
    SWABI_JWT_SECRET_ENCODING: str = "raw" # "raw" | "base64"
    SWABI_JWT_ALGORITHM: str = "HS512"
    # Tolerance (seconds) for clock skew between this server and Swabi's
    # token issuer, applied to exp/nbf/iat checks. Raise this if logins
    # fail with "not yet valid (iat)" and syncing the system clock isn't
    # an option; keep it small in production — it's a skew tolerance,
    # not a way to accept stale/future tokens on purpose.
    SWABI_JWT_LEEWAY_SECONDS: int = 60

    CHECKPOINT_DB_PATH: str = "swabi_checkpoints.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()