from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "aureon-ai-super-secret-key-2024-hackathon"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./aureon.db"
    OPENAI_API_KEY: str = "sk-placeholder"

    class Config:
        env_file = ".env"

settings = Settings()
