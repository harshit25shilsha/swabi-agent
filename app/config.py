from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    GROQ_API_KEY:       str
    GROQ_MODEL:         str
    SWABI_API_BASE:     str

    # JWT secret — must match the Swabi Java backend signing key.
    # Leave empty if unknown; set SWABI_JWT_SKIP_VERIFY=true for local dev.
    SWABI_JWT_SECRET:      str = ""

    # Set to true in .env to skip JWT signature verification (dev only).
    # When true, tokens are decoded without verifying the signature.
    # NEVER set this in production.
    SWABI_JWT_SKIP_VERIFY: bool = False

    CHECKPOINT_DB_PATH: str = "swabi_checkpoints.db"

    class Config:
        env_file = ".env"


settings = Settings()