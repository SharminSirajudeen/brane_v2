"""
BRANE Configuration Settings
Uses pydantic-settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Application
    APP_NAME: str = "BRANE"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://brane:brane_dev_password@localhost:5432/brane_dev",
        description="PostgreSQL connection string"
    )

    # Authentication
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Google OAuth
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"

    # Redis (Optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Encryption
    ENCRYPTION_KEY: str = Field(
        default="dev-encryption-key-32-bytes-min",
        min_length=32
    )

    # Privacy
    DEFAULT_PRIVACY_TIER: Literal[0, 1, 2] = 0  # 0=local, 1=private cloud, 2=public

    # File Storage
    STORAGE_PATH: str = "./storage"
    AXON_STORAGE_PATH: str = "./storage/axon"
    MODELS_PATH: str = "./storage/models"

    # LLM Providers (Optional)
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API key")
    ANTHROPIC_API_KEY: str = Field(default="", description="Optional Anthropic API key")
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Model Defaults
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_CONTEXT_WINDOW: int = 4096
    DEFAULT_MAX_TOKENS: int = 2048

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use lru_cache to avoid re-reading .env file on every call.
    """
    return Settings()
