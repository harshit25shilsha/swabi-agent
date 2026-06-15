from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    GROQ_API_KEY: str

    GROQ_MODEL: str
    
    SWABI_API_BASE: str

    class Config:
        env_file = ".env"


settings = Settings()