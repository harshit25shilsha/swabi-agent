from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    GROQ_MODEL: str
    SWABI_API_BASE: str

    # Must match the Swabi backend JWT signing configuration.
    SWABI_JWT_SECRET: str = ""
    SWABI_JWT_SECRET_ENCODING: str = "raw" # "raw" | "base64"
    SWABI_JWT_ALGORITHM: str = "HS512"

    CHECKPOINT_DB_PATH: str = "swabi_checkpoints.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
